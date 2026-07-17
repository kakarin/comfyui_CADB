"""
🧩 CADB 视频分析
ComfyUI 节点：接收视频路径 → FFmpeg抽帧 → VLM视觉分析 → FrameEvents
"""

import subprocess
import tempfile
import json
import shutil
from pathlib import Path

from .objects import FrameObject, FrameEvent
from .utils import CacheManager


def _find_ffmpeg() -> str:
    """查找 ffmpeg 可执行文件"""
    # 1. imageio_ffmpeg（ComfyUI 最常用的方式）
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path:
            return path
    except Exception:
        pass
    # 2. 系统 PATH
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    if shutil.which("ffmpeg.exe"):
        return "ffmpeg.exe"
    # 3. ComfyUI portable 常见位置
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "python_embeded" / "Scripts" / "ffmpeg.exe",
        Path(__file__).resolve().parent.parent.parent / "python_embeded" / "ffmpeg.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return "ffmpeg"


class CADBVideoAnalyzer:
    """视频分析：抽帧 + VLM 视觉识别"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "视频路径": ("STRING", {"multiline": False, "default": "", "placeholder": "视频文件路径，可从 📂 CADB 加载视频 连线"}),
                "采样模式": (["fast", "standard", "high_quality", "dynamic"], {"default": "standard"}),
            },
            "optional": {
                "视觉模型": ("CADB_VISION_MODEL", {"tooltip": "连线 🔮 CADB 加载视觉模型"}),
                "视觉提示词": ("STRING", {"multiline": True, "default": "", "placeholder": "自定义 VLM prompt（留空用默认）"}),
                "最大帧率": ("FLOAT", {"default": 3.0, "min": 0.1, "max": 30.0, "step": 0.1}),
                "场景检测": ("BOOLEAN", {"default": True}),
                "强制刷新": ("BOOLEAN", {"default": False}),
                "批处理帧数": ("INT", {"default": 3, "min": 1, "max": 10, "tooltip": "一次VLM调用分析几帧，越大越快但可能丢失细节"}),
                "缩放宽度": ("INT", {"default": 640, "min": 320, "max": 1920, "step": 64, "tooltip": "抽帧缩放宽度，越小越快，推荐640"}),
            },
        }

    RETURN_TYPES = ("CADB_FRAMEEVENTS", "STRING")
    RETURN_NAMES = ("帧事件", "调试摘要")
    FUNCTION = "process"
    CATEGORY = "CADB/Video"

    DEFAULT_PROMPT = """请分析这张视频帧，用中文回答：
1. 动作类型（拿起、放下、刷/涂抹、敲击、摩擦、刮擦、旋转、展示、挤压、摇晃、靠近、远离、跳舞、摆姿势、静止）
2. 可见道具（列出所有你能看到的物品，用中文描述）
3. 场景类型（正面、特写、手部、双耳、侧面、俯视、全身、暗光、室外、舞台/演播室）
只返回 JSON 格式：{"action": "静止", "props": ["道具1", "道具2"], "scene": "正面"}"""

    BATCH_PROMPT = """请分析以下{count}张连续视频帧，每帧返回一个JSON：
动作类型：拿起、放下、刷/涂抹、敲击、摩擦、刮擦、旋转、展示、挤压、摇晃、靠近、远离、跳舞、摆姿势、静止
场景类型：正面、特写、手部、双耳、侧面、俯视、全身、暗光、室外、舞台/演播室

只返回 JSON 数组：
[{"action": "静止", "props": ["道具"], "scene": "正面"}, ...]"""

    def __init__(self):
        self.cache = CacheManager("VideoAnalyzer")

    def process(
        self,
        视频路径: str = "",
        采样模式: str = "standard",
        视觉模型=None,
        视觉提示词: str = "",
        最大帧率: float = 3.0,
        场景检测: bool = True,
        强制刷新: bool = False,
        批处理帧数: int = 3,
        缩放宽度: int = 640,
    ):
        path = 视频路径
        profile = 采样模式
        vision_model = 视觉模型
        vision_prompt = 视觉提示词
        max_fps = 最大帧率
        scene_detection = 场景检测
        force_update = 强制刷新

        if not path or not Path(path).exists():
            return ([], f"⚠️ 视频不存在: {path}")

        has_model = vision_model is not None and vision_model[0] is not None

        if not force_update:
            cached = self.cache.get(path, profile, vision_prompt[:100], max_fps, scene_detection)
            if cached is not None:
                fe, info = cached
                return (fe, f"✅ 缓存: {len(fe)} 事件")

        fps_map = {"fast": 0.2, "standard": 0.5, "high_quality": 1.0, "dynamic": min(max_fps, 3.0)}
        target_fps = fps_map.get(profile, 0.5)
        frames = self._extract_frames(path, target_fps, scene_detection, 缩放宽度)

        if has_model:
            frame_events = self._infer_frames(frames, vision_model, vision_prompt, 批处理帧数)
        else:
            frame_events = [FrameEvent(timestamp=f.timestamp, action="idle", frame_index=f.index) for f in frames]

        self.cache.set((frame_events, ""), path, profile, vision_prompt[:100], max_fps, scene_detection)

        tag = "VLM" if has_model else "占位"
        dbg = f"✅ [{tag}] {len(frames)}帧→{len(frame_events)}事件"
        if getattr(self, '_last_error', ''):
            dbg = f"❌ {self._last_error}"
        return (frame_events, dbg)

    def _extract_frames(self, path: str, fps: float, scene: bool, scale_width: int = 640) -> list:
        ffmpeg = _find_ffmpeg()
        d = Path(tempfile.mkdtemp(prefix="cadb_vf_"))
        vf = f"fps={fps},scale={scale_width}:-1"
        if scene: vf += ",select='gte(scene,0.3)'"
        try:
            result = subprocess.run(
                [ffmpeg, "-y", "-i", path, "-vf", vf, "-q:v", "3", "-frame_pts", "1",
                 str(d / "frame_%06d.jpg")],
                capture_output=True, text=True, timeout=600,
            )
            if result.returncode != 0:
                self._last_error = f"FFmpeg 失败: {result.stderr[:200]}"
                return []
        except FileNotFoundError:
            self._last_error = f"找不到 FFmpeg ({ffmpeg})，请安装 ffmpeg"
            return []
        except Exception as e:
            self._last_error = f"抽帧异常: {e}"
            return []
        frames = [FrameObject(index=i, timestamp=i/max(fps,0.01), path=str(f), is_keyframe=True)
                  for i,f in enumerate(sorted(d.glob("frame_*.jpg")))]
        if not frames:
            self._last_error = f"抽帧结果为空 (ffmpeg={ffmpeg})"
        return frames

    def _infer_frames(self, frames, vm, prompt, batch_size=3):
        model, backend, cfg = vm
        mt = cfg.get("max_tokens", 128)
        temp = cfg.get("temperature", 0.1)
        prompt = prompt or self.DEFAULT_PROMPT
        evts = []

        # 批量推理：每 batch_size 帧合并成一次 VLM 调用
        for i in range(0, len(frames), batch_size):
            batch = frames[i:i + batch_size]
            try:
                if len(batch) == 1:
                    # 单帧走快速路径
                    if backend == "gguf":
                        e = self._infer_gguf(batch[0].path, model, prompt, mt, temp)
                    else:
                        e = self._infer_hf(batch[0].path, model, backend, prompt, mt, temp)
                    e.timestamp = batch[0].timestamp; e.frame_index = batch[0].index
                    evts.append(e)
                else:
                    # 多帧批量推理
                    batch_evts = self._infer_batch_gguf(batch, model, mt, temp) if backend == "gguf" else []
                    if batch_evts:
                        for j, e in enumerate(batch_evts):
                            e.timestamp = batch[j].timestamp
                            e.frame_index = batch[j].index
                            evts.append(e)
                    else:
                        # 回退单帧
                        for f in batch:
                            evts.append(FrameEvent(timestamp=f.timestamp, action="idle", frame_index=f.index))
            except Exception as ex:
                for f in batch:
                    evts.append(FrameEvent(timestamp=f.timestamp, action="idle", frame_index=f.index, raw_response=f"error:{ex}"))

        return evts

    def _infer_hf(self, img, model, processor, prompt, mt, temp):
        from PIL import Image; import torch
        image = Image.open(img).convert("RGB")
        msgs = [{"role":"user","content":[{"type":"image","image":image},{"type":"text","text":prompt}]}]
        text = processor.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=[text], images=[image], return_tensors="pt")
        dev = model.device if hasattr(model,"device") else next(model.parameters()).device
        inputs = {k:v.to(dev) if isinstance(v,torch.Tensor) else v for k,v in inputs.items()}
        with torch.no_grad():
            ids = model.generate(**inputs, max_new_tokens=mt, temperature=temp if temp>0 else None, do_sample=temp>0)
        ids_t = [o[len(i):] for i,o in zip(inputs["input_ids"],ids)]
        raw = processor.batch_decode(ids_t, skip_special_tokens=True)[0]
        return self._parse(raw)

    def _infer_gguf(self, img_path, model, prompt, mt, temp):
        """GGUF (llama-cpp) VLM 推理"""
        import base64
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                {"type": "text", "text": prompt},
            ]
        }]

        result = model.create_chat_completion(
            messages=messages,
            max_tokens=mt,
            temperature=temp if temp > 0 else 0.0,
        )
        raw = result["choices"][0]["message"]["content"]
        return self._parse(raw)

    def _infer_batch_gguf(self, batch, model, mt, temp):
        """GGUF 批量多帧推理：一次调用分析多帧"""
        import base64
        batch_prompt = self.BATCH_PROMPT.format(count=len(batch))

        # 构建多图消息
        content = [{"type": "text", "text": batch_prompt}]
        for f in batch:
            with open(f.path, "rb") as img_file:
                img_b64 = base64.b64encode(img_file.read()).decode()
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})

        messages = [{"role": "user", "content": content}]

        result = model.create_chat_completion(
            messages=messages,
            max_tokens=mt * len(batch),  # 更多token给多帧
            temperature=temp if temp > 0 else 0.0,
        )
        raw = result["choices"][0]["message"]["content"]
        return self._parse_array(raw, len(batch))

    def _parse(self, raw):
        js = raw
        if "```json" in raw: js = raw.split("```json")[1].split("```")[0]
        elif "```" in raw: js = raw.split("```")[1].split("```")[0]
        elif "{" in raw: js = raw[raw.index("{"):raw.rindex("}")+1]
        try: d = json.loads(js.strip())
        except: return FrameEvent(timestamp=0, action="idle", raw_response=raw)
        return FrameEvent(timestamp=0, action=d.get("action","静止"), action_confidence=d.get("action_confidence",0.8),
                          props=d.get("props",[]), scene=d.get("scene","正面"),
                          tags=d.get("tags",[]), raw_response=raw)

    def _parse_array(self, raw, expected_count):
        """解析批量 JSON 数组响应"""
        js = raw
        if "```json" in raw: js = raw.split("```json")[1].split("```")[0]
        elif "```" in raw: js = raw.split("```")[1].split("```")[0]
        elif "[" in raw: js = raw[raw.index("["):raw.rindex("]") + 1]

        try:
            arr = json.loads(js.strip())
            if isinstance(arr, list):
                evts = []
                for item in arr[:expected_count]:
                    if isinstance(item, dict):
                        evts.append(FrameEvent(
                            timestamp=0, action=item.get("action", "静止"),
                            props=item.get("props", []), scene=item.get("scene", "正面"),
                            raw_response=raw,
                        ))
                # 补齐不够的帧
                while len(evts) < expected_count:
                    evts.append(FrameEvent(timestamp=0, action="静止", raw_response=raw))
                return evts
        except json.JSONDecodeError:
            pass

        # 解析失败，全部返回 idle
        return [FrameEvent(timestamp=0, action="静止", raw_response=raw) for _ in range(expected_count)]


NODE_CLASS_MAPPINGS = {"CADB_VideoAnalyzer": CADBVideoAnalyzer}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_VideoAnalyzer": "🧩 CADB 视频分析"}
