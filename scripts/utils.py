"""
通用工具
"""

import hashlib
import time
import re
from pathlib import Path


def file_md5(path: str) -> str:
    """文件 MD5"""
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def safe_filename(name: str) -> str:
    """去除文件名中的非法字符"""
    return re.sub(r'[<>:"/\\|?*]', '_', name)


def format_time(seconds: float) -> str:
    """格式化时间 mm:ss 或 hh:mm:ss"""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def find_videos(directory: str, extensions: list = None) -> list[str]:
    """递归查找视频文件"""
    if extensions is None:
        extensions = [".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv"]

    videos = []
    for ext in extensions:
        videos.extend(str(p) for p in Path(directory).rglob(f"*{ext}"))
    return sorted(videos)


def ensure_dir(path: str):
    """确保目录存在"""
    Path(path).mkdir(parents=True, exist_ok=True)


class Timer:
    """计时器上下文"""
    def __init__(self, name: str = ""):
        self.name = name
        self.start = 0.0
        self.elapsed = 0.0

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.elapsed = time.time() - self.start

    def __str__(self):
        return f"{self.name}: {self.elapsed:.2f}s" if self.name else f"{self.elapsed:.2f}s"
