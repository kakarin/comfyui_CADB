"""
📂 CADB 加载视频
ComfyUI 节点：选择视频文件 → 输出 VideoObject（连线到分析节点）
"""

import subprocess
import json
from pathlib import Path

from .objects import VideoObject


class CADBLoadVideo:
    """加载视频，输出 VideoObject 给下游分析节点"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "视频文件": ("STRING", {"multiline": False, "default": "", "placeholder": "/path/to/video.mp4"}),
            },
        }

    RETURN_TYPES = ("CADB_VIDEO", "STRING")
    RETURN_NAMES = ("视频", "视频信息")
    FUNCTION = "process"
    CATEGORY = "CADB/Video"

    def process(self, 视频文件: str = ""):
        path = 视频文件
        if not path or not Path(path).exists():
            video = VideoObject(path=path)
            return (video, f"⚠️ 文件不存在: {path}")

        video = self._probe(path)
        info = f"{video.filename} | {video.width}x{video.height} | {video.fps:.1f}fps | {video.duration:.0f}s"
        return (video, info)

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


NODE_CLASS_MAPPINGS = {"CADB_LoadVideo": CADBLoadVideo}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_LoadVideo": "📂 CADB 加载视频"}
