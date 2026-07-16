"""
导出工具
JSON / Markdown / Tags 批量导出
"""

import json
from pathlib import Path


def export_json(data: dict, path: str, indent: int = 2):
    """通用 JSON 导出"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    return path


def export_text(text: str, path: str):
    """通用文本导出"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    return path


def export_batch_summary(results: list, output_dir: str):
    """批量结果汇总"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    summary = {
        "total_videos": len(results),
        "videos": [],
        "aggregate": {
            "triggers": {},
            "actions": {},
            "props": {},
        },
    }

    for r in results:
        item = {
            "video": r.get("video", ""),
            "duration": r.get("duration", 0),
            "events": r.get("events", 0),
            "tags": r.get("tags", []),
        }
        summary["videos"].append(item)

        for t, c in r.get("triggers", {}).items():
            summary["aggregate"]["triggers"][t] = summary["aggregate"]["triggers"].get(t, 0) + c
        for a, c in r.get("actions", {}).items():
            summary["aggregate"]["actions"][a] = summary["aggregate"]["actions"].get(a, 0) + c
        for p, c in r.get("props", {}).items():
            summary["aggregate"]["props"][p] = summary["aggregate"]["props"].get(p, 0) + c

    export_json(summary, f"{output_dir}/batch_summary.json")
