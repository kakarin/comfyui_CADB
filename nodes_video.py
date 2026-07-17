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
            },
        }

    RETURN_TYPES = ("CADB_FRAMEEVENTS", "STRING")
    RETURN_NAMES = ("帧事件", "调试摘要")
    FUNCTION = "process"
    CATEGORY = "CADB/Video"

    DEFAULT_PROMPT = """Analyze this frame. Identify action, props, scene.
Return ONLY JSON: {"action": "idle", "props": [], "scene": "front_view"}"""

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
        frames = self._extract_frames(path, target_fps, scene_detection)

        if has_model:
            frame_events = self._infer_frames(frames, vision_model, vision_prompt)
        else:
            frame_events = [FrameEvent(timestamp=f.timestamp, action="idle", frame_index=f.index) for f in frames]

        self.cache.set((frame_events, ""), path, profile, vision_prompt[:100], max_fps, scene_detection)

        tag = "VLM" if has_model else "占位"
        dbg = f"✅ [{tag}] {len(frames)}帧→{len(frame_events)}事件"
        if getattr(self, '_last_error', ''):
            dbg = f"❌ {self._last_error}"
        return (frame_events, dbg)

    def _extract_frames(self, path: str, fps: float, scene: bool) -> list:
        ffmpeg = _find_ffmpeg()
        d = Path(tempfile.mkdtemp(prefix="cadb_vf_"))
        vf = f"fps={fps},scale=1280:-1"
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

    def _infer_frames(self, frames, vm, prompt):
        model, backend, cfg = vm
        mt = cfg.get("max_tokens", 512)
        temp = cfg.get("temperature", 0.1)
        prompt = prompt or self.DEFAULT_PROMPT
        evts = []
        for f in frames:
            try:
                if backend == "gguf":
                    e = self._infer_gguf(f.path, model, prompt, mt, temp)
                else:
                    e = self._infer_hf(f.path, model, backend, prompt, mt, temp)
                e.timestamp = f.timestamp; e.frame_index = f.index; evts.append(e)
            except Exception as ex:
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

    def _parse(self, raw):
        js = raw
        if "```json" in raw: js = raw.split("```json")[1].split("```")[0]
        elif "```" in raw: js = raw.split("```")[1].split("```")[0]
        elif "{" in raw: js = raw[raw.index("{"):raw.rindex("}")+1]
        try: d = json.loads(js.strip())
        except: return FrameEvent(action="idle", raw_response=raw)
        return FrameEvent(action=d.get("action","idle"), action_confidence=d.get("action_confidence",0.8),
                          props=d.get("props",[]), scene=d.get("scene","front_view"),
                          tags=d.get("tags",[]), raw_response=raw)


NODE_CLASS_MAPPINGS = {"CADB_VideoAnalyzer": CADBVideoAnalyzer}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_VideoAnalyzer": "🧩 CADB 视频分析"}
