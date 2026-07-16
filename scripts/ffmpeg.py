#!/usr/bin/env python3
"""
FFmpeg 工具函数
"""

import subprocess
import json
import re
from pathlib import Path
from typing import Optional


def probe_video(video_path: str) -> dict:
    """获取视频元数据"""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", video_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}


def get_video_info(video_path: str) -> dict:
    """获取视频关键信息"""
    info = probe_video(video_path)
    if "error" in info:
        return info

    video_info = {"path": video_path, "streams": {}}

    for stream in info.get("streams", []):
        codec_type = stream.get("codec_type")
        if codec_type == "video":
            video_info["fps"] = _parse_fps(stream.get("r_frame_rate", "0/1"))
            video_info["width"] = stream.get("width", 0)
            video_info["height"] = stream.get("height", 0)
            video_info["codec"] = stream.get("codec_name", "")
            video_info["duration"] = float(stream.get("duration", 0))
        elif codec_type == "audio":
            video_info["has_audio"] = True
            video_info["audio_codec"] = stream.get("codec_name", "")

    fmt = info.get("format", {})
    video_info["duration"] = float(fmt.get("duration", video_info.get("duration", 0)))
    video_info["file_size"] = int(fmt.get("size", 0))
    video_info["bit_rate"] = int(fmt.get("bit_rate", 0))

    return video_info


def extract_frames(
    video_path: str,
    output_dir: str,
    fps: float = 1.0,
    max_width: int = 1280,
    quality: int = 3,
    scene_threshold: float = 0.3,
) -> list[str]:
    """抽帧"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    vf_parts = [f"fps={fps}", f"scale={max_width}:-1"]

    if scene_threshold > 0:
        vf_parts.append(f"select='gte(scene,{scene_threshold})'")

    vf = ",".join(vf_parts)

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", vf, "-q:v", str(quality),
        "-frame_pts", "1",
        f"{output_dir}/frame_%06d.jpg",
    ]

    subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return sorted(str(p) for p in Path(output_dir).glob("frame_*.jpg"))


def extract_audio(
    video_path: str, output_path: str,
    sample_rate: int = 16000, channels: int = 1,
) -> str:
    """从视频中提取音频"""
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", str(sample_rate), "-ac", str(channels),
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return output_path


def _parse_fps(fps_str: str) -> float:
    """解析帧率字符串 '30000/1001' → 29.97"""
    try:
        if "/" in fps_str:
            num, den = fps_str.split("/")
            return float(num) / float(den)
        return float(fps_str)
    except (ValueError, ZeroDivisionError):
        return 0.0
