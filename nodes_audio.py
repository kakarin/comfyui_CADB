"""
🎧 CADB 音频分析
ComfyUI 节点：接收音频对象 → Whisper转录 → Trigger分类 → AudioEvents
连线模型加载节点获取 Whisper，不连线则跳过转录。
"""

from .objects import AudioEvent
from .utils import CacheManager, match_trigger


class CADBAudioAnalyzer:
    """音频分析：Whisper 转录 + Trigger 识别"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "音频": ("CADB_AUDIO", {"tooltip": "来自 ✂️ CADB 音视频分离 的 音频 输出"}),
            },
            "optional": {
                "Whisper模型": ("CADB_WHISPER_MODEL", {"tooltip": "连线 🎙️ CADB 加载Whisper模型，不连线则跳过转录"}),
                "分段长度": ("FLOAT", {"default": 30.0, "min": 5.0, "max": 120.0, "step": 5.0, "tooltip": "Whisper 分段长度（秒）"}),
                "强制刷新": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("CADB_AUDIOEVENTS", "STRING")
    RETURN_NAMES = ("音频事件", "调试摘要")
    FUNCTION = "process"
    CATEGORY = "CADB/Audio"

    def __init__(self):
        self.cache = CacheManager("AudioAnalyzer")

    def process(
        self,
        音频=None,
        Whisper模型=None,
        分段长度: float = 30.0,
        强制刷新: bool = False,
    ):
        audio = 音频
        whisper_model = Whisper模型
        segment_length = 分段长度
        force_update = 强制刷新

        if audio is None or not audio.path:
            return ([], "⚠️ 没有音频输入，请连线 ✂️ CADB 音视频分离")

        has_model = whisper_model is not None

        if not force_update:
            cached = self.cache.get(audio.path, segment_length)
            if cached is not None:
                return (cached, f"✅ 缓存命中: {len(cached)} 个事件")

        # Whisper 转录
        if has_model:
            segments = self._transcribe(audio.path, whisper_model)
        else:
            segments = []

        # Trigger 分类
        events = self._classify_triggers(segments)

        self.cache.set(events, audio.path, segment_length)
        model_tag = "Whisper" if has_model else "占位"
        return (events, f"✅ [{model_tag}] {len(events)} 个音频事件")

    def _transcribe(self, audio_path: str, model) -> list[dict]:
        try:
            segments, info = model.transcribe(audio_path, beam_size=5, vad_filter=True)
        except Exception as e:
            raise RuntimeError(f"Whisper 转录失败: {e}")

        results = []
        for seg in segments:
            results.append({
                "start": seg.start, "end": seg.end, "text": seg.text.strip(),
                "avg_logprob": seg.avg_logprob,
            })
        return results

    def _classify_triggers(self, segments: list[dict]) -> list:
        events = []
        for seg in segments:
            text = seg.get("text", "").strip()
            if not text:
                continue
            matched = match_trigger(text)
            trigger = matched[0]["id"] if matched else ""
            confidence = 0.8 if matched else 0.0
            events.append(AudioEvent(
                start=seg.get("start", 0), end=seg.get("end", 0),
                trigger=trigger, trigger_confidence=confidence,
                transcript=text, segment_index=len(events),
            ))
        return events


NODE_CLASS_MAPPINGS = {"CADB_AudioAnalyzer": CADBAudioAnalyzer}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_AudioAnalyzer": "🎧 CADB 音频分析"}
