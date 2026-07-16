"""
✂️ CADB 音视频分离
ComfyUI 节点：接收视频路径（兼容任何视频加载节点） → 提取音频 + 输出视频对象
"""

import subprocess
import tempfile
import json
from pathlib import Path

from .objects import VideoObject, AudioObject


class CADBAVSplitter:
    """通用音视频分离：输入视频路径 → FFmpeg 提取音频 → 输出视频对象 + 音频对象"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "视频路径": ("STRING", {"multiline": False, "default": "", "placeholder": "视频文件路径，可从任何加载视频节点连线"}),
            },
            "optional": {
                "采样率": ("INT", {"default": 16000, "min": 8000, "max": 48000, "step": 1000}),
                "声道": (["单声道", "立体声"], {"default": "单声道"}),
            },
        }

    RETURN_TYPES = ("CADB_VIDEO", "CADB_AUDIO", "STRING")
    RETURN_NAMES = ("视频画面", "音频", "调试信息")
    FUNCTION = "process"
    CATEGORY = "CADB/Video"

    def process(self, 视频路径: str = "", 采样率: int = 16000, 声道: str = "单声道"):
        path = 视频路径
        channels = 1 if 声道 == "单声道" else 2

        if not path:
            return (VideoObject(), AudioObject(), "⚠️ 未输入视频路径")

        if not Path(path).exists():
            return (VideoObject(path=path), AudioObject(), f"⚠️ 文件不存在: {path}")

        # 1. 探测视频信息
        video = self._probe(path)

        # 2. 提取音频
        out_dir = Path(tempfile.mkdtemp(prefix="cadb_split_"))
        audio_path = str(out_dir / f"{Path(path).stem}.wav")

        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", path,
                 "-vn", "-acodec", "pcm_s16le",
                 "-ar", str(采样率), "-ac", str(channels),
                 audio_path],
                capture_output=True, text=True, timeout=120,
            )
        except Exception as e:
            return (video, AudioObject(), f"❌ 音频提取失败: {e}")

        audio = AudioObject(
            path=audio_path,
            sample_rate=采样率,
            channels=channels,
            duration=video.duration,
            source_video=path,
        )

        debug = f"✅ {video.filename} | {video.width}x{video.height} | {video.duration:.0f}s → 音频 {采样率}Hz"
        return (video, audio, debug)

    def _probe(self, path: str) -> VideoObject:
        video = VideoObject(path=path)
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", path],
                capture_output=True, text=True, timeout=30,
            )
            info = json.loads(result.stdout)
            for s in info.get("streams", []):
                if s["codec_type"] == "video":
                    fps_frac = s.get("r_frame_rate", "0/1")
                    num, den = (fps_frac.split("/") + ["1"])[:2]
                    video.fps = float(num) / float(den) if float(den) != 0 else 0
                    video.width = s.get("width", 0)
                    video.height = s.get("height", 0)
                    video.codec = s.get("codec_name", "")
                elif s["codec_type"] == "audio":
                    video.audio_codec = s.get("codec_name", "")
                    video.has_audio = True
            fmt = info.get("format", {})
            video.duration = float(fmt.get("duration", 0))
            video.file_size = int(fmt.get("size", 0))
        except Exception:
            pass
        return video


NODE_CLASS_MAPPINGS = {"CADB_AVSplitter": CADBAVSplitter}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_AVSplitter": "✂️ CADB 音视频分离"}
