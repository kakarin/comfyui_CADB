"""
✂️ CADB 音视频分离
ComfyUI 节点：接收视频 → FFmpeg 提取音频 → 分别输出视频对象和音频对象
"""

import subprocess
import tempfile
from pathlib import Path

from .objects import VideoObject, AudioObject


class CADBAVSplitter:
    """从视频中分离音频轨道，输出视频和音频两个对象"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "视频": ("CADB_VIDEO", {"tooltip": "来自 📂 CADB 加载视频 的输出"}),
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

    def process(self, 视频=None, 采样率: int = 16000, 声道: str = "单声道"):
        if 视频 is None:
            return (VideoObject(), AudioObject(), "⚠️ 没有视频输入")

        video = 视频
        channels = 1 if 声道 == "单声道" else 2

        if not video.path or not Path(video.path).exists():
            return (video, AudioObject(), f"⚠️ 文件不存在: {video.path}")

        # 提取音频到临时文件
        out_dir = Path(tempfile.mkdtemp(prefix="cadb_split_"))
        audio_path = str(out_dir / f"{Path(video.path).stem}.wav")

        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", video.path,
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
            source_video=video.path,
        )

        debug = f"✅ {video.filename} → 音频 {采样率}Hz/{声道}"
        return (video, audio, debug)


NODE_CLASS_MAPPINGS = {"CADB_AVSplitter": CADBAVSplitter}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_AVSplitter": "✂️ CADB 音视频分离"}
