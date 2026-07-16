#!/usr/bin/env python3
"""
CADB 命令行入口
用法:
  python -m CADB.scripts.run --video demo.mp4 --profile high_quality
  python -m CADB.scripts.run --batch input/batch/
"""

import argparse
import logging
import sys
from pathlib import Path

# 确保 CADB 包可导入
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

from CADB.objects import KnowledgeObject
from CADB.nodes_video import CADBVideoAnalyzer
from CADB.nodes_audio import CADBAudioAnalyzer
from CADB.nodes_timeline import CADBTimelineFusion
from CADB.nodes_knowledge import CADBKnowledgeBuilder
from CADB.nodes_report import CADBReportGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CADB")


def analyze_video(video_path: str, profile: str = "standard") -> KnowledgeObject:
    """单视频完整分析"""
    logger.info(f"开始: {video_path} (profile={profile})")

    vn = CADBVideoAnalyzer()
    fe, vdbg, vinfo = vn.process(video_path=video_path, profile=profile)
    logger.info(f"  Video: {vinfo} → {len(fe)} frame events")

    an = CADBAudioAnalyzer()
    ae, adbg = an.process(video_path=video_path)
    logger.info(f"  Audio: {len(ae)} events")

    tn = CADBTimelineFusion()
    tl, tdbg = tn.process(frame_events=fe, audio_events=ae)
    logger.info(f"  Timeline: {len(tl)} events")

    kn = CADBKnowledgeBuilder()
    k, kdbg = kn.process(timeline=tl, video_name=Path(video_path).name)
    logger.info(f"  Knowledge: {len(k.tags)} tags")

    rn = CADBReportGenerator()
    md, jp, rdbg = rn.process(knowledge=k, video_name=Path(video_path).name)
    logger.info(f"  Report: {rdbg}")
    logger.info(f"  JSON → {jp}")

    return k


def analyze_batch(batch_dir: str, workers: int = 2):
    import concurrent.futures
    vd = Path(batch_dir)
    videos = list(vd.glob("*.mp4")) + list(vd.glob("*.mkv"))
    logger.info(f"发现 {len(videos)} 个视频")

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(analyze_video, str(v)): v for v in videos}
        for f in concurrent.futures.as_completed(futs):
            v = futs[f]
            try:
                f.result(); logger.info(f"✅ {v.name}")
            except Exception as e:
                logger.error(f"❌ {v.name}: {e}")


def main():
    p = argparse.ArgumentParser(description="CADB - ComfyUI ASMR Dataset Builder")
    p.add_argument("--video", help="单视频路径")
    p.add_argument("--batch", help="批量目录")
    p.add_argument("--profile", default="standard", choices=["fast","standard","high_quality","dynamic"])
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--debug", action="store_true")
    args = p.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.batch:
        analyze_batch(args.batch, args.workers)
    elif args.video:
        analyze_video(args.video, args.profile)
    else:
        p.print_help(); sys.exit(1)


if __name__ == "__main__":
    main()
