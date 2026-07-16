"""
时间轴工具函数
Timeline 导出、转换、合并
"""

import json
from pathlib import Path
from typing import Optional


def timeline_to_srt(timeline: list, output_path: str):
    """Timeline → SRT 字幕格式"""
    lines = []
    for i, event in enumerate(timeline, 1):
        start = _srt_time(getattr(event, "start", 0))
        end = _srt_time(getattr(event, "end", 0))

        action = getattr(event, "action", "")
        trigger = getattr(event, "trigger", "")
        transcript = getattr(event, "transcript", "")
        confidence = getattr(event, "confidence", 0)

        parts = [f"[{action}]"] if action else []
        parts.append(f"[{trigger}]" if trigger else "")
        txt = " ".join(filter(None, parts))
        if transcript:
            txt += f" | {transcript}"
        if confidence:
            txt += f" ({confidence:.0%})"

        lines.append(f"{i}\n{start} --> {end}\n{txt}\n")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


def timeline_to_csv(timeline: list, output_path: str):
    """Timeline → CSV 格式"""
    import csv

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["start", "end", "action", "trigger", "props", "scene", "confidence", "source"])

        for e in timeline:
            writer.writerow([
                getattr(e, "start", 0),
                getattr(e, "end", 0),
                getattr(e, "action", ""),
                getattr(e, "trigger", ""),
                ",".join(getattr(e, "props", [])),
                getattr(e, "scene", ""),
                getattr(e, "confidence", 0),
                getattr(e, "source", ""),
            ])


def segments_to_edl(segments: list, output_path: str, video_path: str = ""):
    """Segments → EDL (Edit Decision List) 格式"""
    lines = [f"TITLE: CADB EDL Export", f"FCM: NON-DROP FRAME", ""]

    for i, seg in enumerate(segments, 1):
        start = getattr(seg, "start", 0)
        end = getattr(seg, "end", 0)
        action = getattr(seg, "action", "")
        trigger = getattr(seg, "trigger", "")

        # EDL 格式: 001  AX  V  C  00:00:00:00 00:00:00:00 00:00:00:00 00:00:00:00
        start_tc = _edl_time(start)
        end_tc = _edl_time(end)
        name = f"CADB_{i:03d}_{action}_{trigger}".replace(" ", "_")[:70]
        lines.append(f"{i:03d}  {start_tc} {end_tc} {start_tc} {end_tc}")
        lines.append(f"* FROM CLIP NAME: {name}")
        lines.append("")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


def _srt_time(seconds: float) -> str:
    """秒 → SRT 时间格式 HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _edl_time(seconds: float) -> str:
    """秒 → EDL 时间格式 HH:MM:SS:FF (假定 30fps)"""
    fps = 30
    total_frames = int(seconds * fps)
    h = total_frames // (3600 * fps)
    m = (total_frames % (3600 * fps)) // (60 * fps)
    s = (total_frames % (60 * fps)) // fps
    f = total_frames % fps
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"
