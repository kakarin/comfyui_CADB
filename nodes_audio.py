"""
🎧 CADB 音频分析
ComfyUI 节点：接收视频路径 → 提取音频 → Whisper转录 → Trigger分类 → AudioEvents
"""

import subprocess
import tempfile
import shutil
from pathlib import Path

from .objects import AudioEvent
from .utils import CacheManager, match_trigger


def _find_ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path: return path
    except Exception: pass
    if shutil.which("ffmpeg"): return "ffmpeg"
    if shutil.which("ffmpeg.exe"): return "ffmpeg.exe"
    for c in [
        Path(__file__).resolve().parent.parent.parent / "python_embeded" / "Scripts" / "ffmpeg.exe",
        Path(__file__).resolve().parent.parent.parent / "python_embeded" / "ffmpeg.exe",
    ]:
        if c.exists(): return str(c)
    return "ffmpeg"


class CADBAudioAnalyzer:
    """音频分析：提取音频 + Whisper 转录 + Trigger 识别"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "视频路径": ("STRING", {"multiline": False, "default": "", "placeholder": "视频文件路径，可从 📂 CADB 加载视频 连线"}),
            },
            "optional": {
                "Whisper模型": ("CADB_WHISPER_MODEL", {"tooltip": "连线 🎙️ CADB 加载Whisper模型"}),
                "分段长度": ("FLOAT", {"default": 30.0, "min": 5.0, "max": 120.0, "step": 5.0}),
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
        视频路径: str = "",
        Whisper模型=None,
        分段长度: float = 30.0,
        强制刷新: bool = False,
    ):
        path = 视频路径
        whisper_model = Whisper模型
        segment_length = 分段长度
        force_update = 强制刷新

        if not path or not Path(path).exists():
            return ([], f"⚠️ 视频不存在: {path}")

        has_model = whisper_model is not None

        if not force_update:
            cached = self.cache.get(path, segment_length)
            if cached is not None:
                return (cached, f"✅ 缓存: {len(cached)} 事件")

        # 提取音频
        audio_path = self._extract_audio(path)

        # Whisper
        if has_model:
            segments = self._transcribe(audio_path, whisper_model)
        else:
            segments = []

        events = self._classify_triggers(segments)
        self.cache.set(events, path, segment_length)

        tag = "Whisper" if has_model else "占位"
        dbg = f"✅ [{tag}] {len(events)} 事件"
        if getattr(self, '_last_error', ''):
            dbg = f"❌ {self._last_error}"
        return (events, dbg)

    def _extract_audio(self, path: str) -> str:
        ffmpeg = _find_ffmpeg()
        out = Path(tempfile.mkdtemp(prefix="cadb_aa_")) / "audio.wav"
        try:
            result = subprocess.run(
                [ffmpeg, "-y", "-i", path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(out)],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                self._last_error = f"FFmpeg 失败: {result.stderr[:200]}"
                return ""
        except FileNotFoundError:
            self._last_error = f"找不到 FFmpeg ({ffmpeg})"
            return ""
        except Exception as e:
            self._last_error = f"音频提取异常: {e}"
            return ""
        return str(out)

    def _transcribe(self, path: str, model) -> list[dict]:
        segments, _ = model.transcribe(path, beam_size=5, vad_filter=True)
        return [{"start":s.start,"end":s.end,"text":s.text.strip()} for s in segments]

    def _classify_triggers(self, segments: list[dict]) -> list:
        evts = []
        for s in segments:
            text = s.get("text","").strip()
            if not text: continue
            m = match_trigger(text)
            evts.append(AudioEvent(start=s["start"],end=s["end"],
                        trigger=m[0]["id"] if m else "",
                        trigger_confidence=0.8 if m else 0,
                        transcript=text, segment_index=len(evts)))
        return evts


NODE_CLASS_MAPPINGS = {"CADB_AudioAnalyzer": CADBAudioAnalyzer}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_AudioAnalyzer": "🎧 CADB 音频分析"}
