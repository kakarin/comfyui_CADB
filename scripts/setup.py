#!/usr/bin/env python3
"""
CADB 安装到 ComfyUI
用法：
  python CADB/scripts/setup.py install --comfyui /path/to/ComfyUI
  python CADB/scripts/setup.py verify --comfyui /path/to/ComfyUI
"""

import shutil
import sys
from pathlib import Path

CADB_ROOT = Path(__file__).resolve().parent.parent


def install(comfyui_path: str):
    dst = Path(comfyui_path) / "custom_nodes" / "CADB"
    print(f"📦 安装 CADB → {dst}")

    if dst.exists():
        print("⚠️  已存在，覆盖中...")
        shutil.rmtree(dst)

    # 只复制必要的目录
    shutil.copytree(CADB_ROOT, dst, ignore=shutil.ignore_patterns(
        "__pycache__", "*.pyc", ".DS_Store",
        "cache", "output", "input", "workflow", "scripts",
        "*.egg-info",
    ))

    # 创建运行时目录
    for d in ["cache", "input/video", "output/json", "output/markdown",
              "output/timeline", "output/tags", "output/debug"]:
        (dst / d).mkdir(parents=True, exist_ok=True)

    print(f"✅ 安装完成！重启 ComfyUI 后可用。")
    print(f"   节点分类：CADB/Video, CADB/Audio, CADB/Core")
    print(f"   5 个节点：Video Analyzer | Audio Analyzer | Timeline Fusion | Knowledge Builder | Report Generator")


def verify(comfyui_path: str):
    dst = Path(comfyui_path) / "custom_nodes" / "CADB"
    if not dst.exists():
        print(f"❌ 未安装: {dst}")
        return

    required = ["__init__.py", "objects.py", "utils.py",
                 "nodes_video.py", "nodes_audio.py", "nodes_timeline.py",
                 "nodes_knowledge.py", "nodes_report.py"]
    all_ok = True
    for f in required:
        ok = (dst / f).exists()
        print(f"   {'✅' if ok else '❌'} {f}")
        if not ok: all_ok = False

    if all_ok:
        print(f"\n✅ 所有文件就绪。期待 ComfyUI 中看到 5 个 CADB 节点。")
    else:
        print(f"\n❌ 请重新安装：python CADB/scripts/setup.py install --comfyui ...")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="CADB 安装工具")
    p.add_argument("action", choices=["install", "verify"])
    p.add_argument("--comfyui", required=True, help="ComfyUI 根目录")
    args = p.parse_args()

    if args.action == "install":
        install(args.comfyui)
    else:
        verify(args.comfyui)
