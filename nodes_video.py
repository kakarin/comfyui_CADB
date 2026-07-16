"""
🧩 CADB 视频分析
ComfyUI 节点：接收视频对象 → FFmpeg抽帧 → VLM视觉分析 → FrameEvents
连线模型加载节点获取 VLM，不连线则输出空结果。
"""

import subprocess
import tempfile
import json
from pathlib import Path

from .objects import VideoObject, FrameObject, FrameEvent
from .utils import CacheManager


class CADBVideoAnalyzer:
    """视频分析：抽帧 + VLM 视觉识别"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "视频": ("CADB_VIDEO", {"tooltip": "来自 📂 CADB 加载视频 或 ✂️ CADB 音视频分离 的 视频画面"}),
                "采样模式": (["fast", "standard", "high_quality", "dynamic"], {"default": "standard"}),
            },
            "optional": {
                "视觉模型": ("CADB_VISION_MODEL", {"tooltip": "连线 🔮 CADB 加载视觉模型，不连线则跳过识别"}),
                "视觉提示词": ("STRING", {"multiline": True, "default": "", "placeholder": "自定义 VLM prompt（留空用默认）"}),
                "最大帧率": ("FLOAT", {"default": 3.0, "min": 0.1, "max": 30.0, "step": 0.1}),
                "场景检测": ("BOOLEAN", {"default": True}),
                "强制刷新": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("CADB_FRAMEEVENTS", "STRING", "STRING")
    RETURN_NAMES = ("帧事件", "调试摘要", "视频信息")
    FUNCTION = "process"
    CATEGORY = "CADB/Video"

    DEFAULT_PROMPT = """Analyze this frame from a video. Identify:
1. Action (pick_up, put_down, brush, tap, rub, scratch, rotate, hold_up, squeeze, shake, close_up, idle)
2. Props visible in the frame
3. Scene type (front_view, close_up, hand_focus, dual_ear)
Return ONLY valid JSON: {"action": "idle", "props": [], "scene": "front_view"}"""

    def __init__(self):
        self.cache = CacheManager("VideoAnalyzer")

    def process(
        self,
        视频=None,
        采样模式: str = "standard",
        视觉模型=None,
        视觉提示词: str = "",
        最大帧率: float = 3.0,
        场景检测: bool = True,
        强制刷新: bool = False,
    ):
        video = 视频
        profile = 采样模式
        vision_model = 视觉模型
        vision_prompt = 视觉提示词
        max_fps = 最大帧率
        scene_detection = 场景检测
        force_update = 强制刷新

        if video is None or not video.path or not Path(video.path).exists():
            return ([], f"⚠️ 视频不存在: {video.path if video else 'None'}", "")

        video_path = video.path
        has_model = vision_model is not None and vision_model[0] is not None

        if not force_update:
            cached = self.cache.get(video_path, profile, vision_prompt[:100], max_fps, scene_detection)
            if cached is not None:
                fe, info = cached
                return (fe, f"✅ 缓存命中: {len(fe)} 个事件", info)

        info_str = f"{video.filename} | {video.width}x{video.height} | {video.fps:.1f}fps | {video.duration:.0f}s"

        fps_map = {"fast": 0.2, "standard": 0.5, "high_quality": 1.0, "dynamic": min(max_fps, 3.0)}
        target_fps = fps_map.get(profile, 0.5)
        frames = self._extract_frames(video_path, target_fps, scene_detection)

        if has_model:
            frame_events = self._infer_frames(frames, vision_model, vision_prompt)
        else:
            frame_events = [FrameEvent(timestamp=f.timestamp, action="idle", frame_index=f.index) for f in frames]

        self.cache.set((frame_events, info_str), video_path, profile, vision_prompt[:100], max_fps, scene_detection)

        model_tag = "VLM" if has_model else "占位"
        return (frame_events, f"✅ [{model_tag}] {len(frames)} 帧 → {len(frame_events)} 事件", info_str)

    def _extract_frames(self, video_path: str, fps: float, scene_detection: bool) -> list:
        out_dir = Path(tempfile.mkdtemp(prefix="cadb_vf_"))
        vf = f"fps={fps},scale=1280:-1"
        if scene_detection:
            vf += f",select='gte(scene,0.3)'"
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", video_path, "-vf", vf, "-q:v", "3", "-frame_pts", "1",
                 str(out_dir / "frame_%06d.jpg")],
                capture_output=True, text=True, timeout=600,
            )
        except Exception:
            pass
        frames = []
        for i, f in enumerate(sorted(out_dir.glob("frame_*.jpg"))):
            frames.append(FrameObject(index=i, timestamp=i / max(fps, 0.01), path=str(f), is_keyframe=True))
        return frames

    def _infer_frames(self, frames: list, vision_model, custom_prompt: str) -> list:
        model, processor, config = vision_model
        prompt_text = custom_prompt or self.DEFAULT_PROMPT
        max_tokens = config.get("max_tokens", 512)
        temperature = config.get("temperature", 0.1)

        events = []
        for f in frames:
            try:
                event = self._infer_single(f.path, model, processor, prompt_text, max_tokens, temperature)
                event.timestamp = f.timestamp
                event.frame_index = f.index
                events.append(event)
            except Exception as e:
                events.append(FrameEvent(timestamp=f.timestamp, action="idle", frame_index=f.index, raw_response=f"error: {e}"))
        return events

    def _infer_single(self, image_path: str, model, processor, prompt: str, max_tokens: int, temperature: float) -> FrameEvent:
        from PIL import Image
        import torch

        image = Image.open(image_path).convert("RGB")
        messages = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": prompt}]}]
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=[text], images=[image], return_tensors="pt")
        device = model.device if hasattr(model, "device") else next(model.parameters()).device
        inputs = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}

        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=max_tokens,
                                           temperature=temperature if temperature > 0 else None,
                                           do_sample=temperature > 0)
        generated_ids_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs["input_ids"], generated_ids)]
        raw = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True)[0]
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> FrameEvent:
        json_str = raw
        if "```json" in raw:
            json_str = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            json_str = raw.split("```")[1].split("```")[0]
        elif "{" in raw:
            json_str = raw[raw.index("{"):raw.rindex("}") + 1]
        try:
            data = json.loads(json_str.strip())
        except json.JSONDecodeError:
            return FrameEvent(action="idle", raw_response=raw)
        return FrameEvent(
            action=data.get("action", "idle"),
            action_confidence=data.get("action_confidence", 0.8),
            props=data.get("props", []),
            props_confidence=data.get("props_confidence", 0.8),
            scene=data.get("scene", "front_view"),
            scene_confidence=data.get("scene_confidence", 0.8),
            tags=data.get("tags", []),
            raw_response=raw,
        )


NODE_CLASS_MAPPINGS = {"CADB_VideoAnalyzer": CADBVideoAnalyzer}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_VideoAnalyzer": "🧩 CADB 视频分析"}
