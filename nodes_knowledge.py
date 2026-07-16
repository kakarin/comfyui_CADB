"""
🧠 CADB Knowledge Builder
ComfyUI 节点：Timeline → KnowledgeObject（统计/分段/摘要/Prompt/Tags）
"""

from collections import Counter

from .objects import Segment, KnowledgeObject
from .utils import CacheManager


class CADBKnowledgeBuilder:
    """知识构建：Timeline → 结构化知识"""

    TRIGGER_CN = {
        "whisper": "耳语", "breathing": "呼吸音", "mouth_sounds": "口腔音",
        "ear_blowing": "耳吹气", "ear_cleaning": "掏耳", "scratch": "刮擦",
        "tapping": "敲击", "brushing": "刷子", "paper": "纸张", "water": "水声",
        "plastic": "塑料", "glass": "玻璃/瓶", "wood": "木头",
    }
    ACTION_CN = {
        "brush": "刷/涂抹", "tap": "敲击", "rub": "摩擦", "scratch": "刮擦",
        "hold_up": "展示", "squeeze": "挤压", "pick_up": "拿起", "put_down": "放下",
        "close_up": "靠近", "idle": "静止",
    }

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "时间轴": ("CADB_TIMELINE", {"tooltip": "来自 CADB 时间轴融合 的输出"}),
                "视频名称": ("STRING", {"default": "", "placeholder": "视频名（用于报告标题）"}),
                "强制刷新": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("CADB_KNOWLEDGE", "STRING")
    RETURN_NAMES = ("知识对象", "调试摘要")
    FUNCTION = "process"
    CATEGORY = "CADB/Core"

    def __init__(self):
        self.cache = CacheManager("KnowledgeBuilder")

    def process(self, 时间轴: list = None, 视频名称: str = "", 强制刷新: bool = False):
        tl = 时间轴 or []
        video_name = 视频名称
        force_update = 强制刷新

        if not force_update:
            cached = self.cache.get(tl, video_name)
            if cached is not None:
                return (cached, f"✅ 缓存命中: {len(cached.tags)} 个标签")

        stats = self._compute_statistics(tl)
        segments = self._build_segments(tl)
        summary = self._generate_summary(stats, video_name)
        prompt = self._generate_prompt(stats)
        tags = self._generate_tags(stats)
        total_dur = max(e.end for e in tl) - min(e.start for e in tl) if tl else 0.0

        knowledge = KnowledgeObject(
            summary=summary, prompt=prompt, tags=tags,
            triggers=stats["triggers"], actions=stats["actions"],
            props=stats["props"], scenes=stats["scenes"],
            segments=segments, timeline=tl,
            total_duration=total_dur,
            metadata={"video_name": video_name},
        )
        self.cache.set(knowledge, tl, video_name)
        return (knowledge, f"✅ 标签:{len(tags)} | 片段:{len(segments)} | 事件:{stats['total_events']}")

    def _compute_statistics(self, tl: list) -> dict:
        tr, ac, pr, sc = Counter(), Counter(), Counter(), Counter()
        for e in tl:
            if e.trigger: tr[e.trigger] += 1
            if e.action: ac[e.action] += 1
            for p in e.props: pr[p] += 1
            if e.scene: sc[e.scene] += 1
        return {
            "triggers": dict(tr.most_common()),
            "actions": dict(ac.most_common()),
            "props": dict(pr.most_common()),
            "scenes": dict(sc.most_common()),
            "total_events": len(tl),
        }

    def _build_segments(self, tl: list) -> list[Segment]:
        if not tl: return []
        segs = []
        cur = Segment(start=tl[0].start, end=tl[0].end, action=tl[0].action,
                      trigger=tl[0].trigger, props=tl[0].props, scene=tl[0].scene,
                      tags=tl[0].tags, transcript=tl[0].transcript,
                      confidence=tl[0].confidence, event_count=1)
        for e in tl[1:]:
            same = (e.action == cur.action and e.trigger == cur.trigger)
            gap = e.start - cur.end
            if same and gap <= 3.0:
                cur.end = e.end; cur.event_count += 1
                cur.confidence = max(cur.confidence, e.confidence)
            else:
                segs.append(cur)
                cur = Segment(start=e.start, end=e.end, action=e.action, trigger=e.trigger,
                              props=e.props, scene=e.scene, tags=e.tags, transcript=e.transcript,
                              confidence=e.confidence, event_count=1)
        segs.append(cur)
        return segs

    def _generate_summary(self, stats: dict, name: str) -> str:
        lines = [f"## {name or 'Video'} 分析摘要\n", f"共识别 {stats['total_events']} 个事件。\n"]
        if stats["triggers"]:
            lines.append("### 主要触发音")
            for t, c in list(stats["triggers"].items())[:8]:
                lines.append(f"- {self.TRIGGER_CN.get(t,t)}: {c}次")
        if stats["actions"]:
            lines.append("\n### 主要动作")
            for a, c in list(stats["actions"].items())[:5]:
                lines.append(f"- {self.ACTION_CN.get(a,a)}: {c}次")
        if stats["props"]:
            lines.append("\n### 使用道具")
            lines.append(", ".join(list(stats["props"].keys())[:8]))
        return "\n".join(lines)

    def _generate_prompt(self, stats: dict) -> str:
        parts = []
        top_t = list(stats["triggers"].keys())[:3]
        if top_t:
            parts.append("ASMR, " + ", ".join(self.TRIGGER_CN.get(t, t) for t in top_t))
        top_p = list(stats["props"].keys())[:3]
        if top_p: parts.append(", ".join(top_p))
        parts.append("soft lighting, high quality")
        return ", ".join(parts)

    def _generate_tags(self, stats: dict) -> list[str]:
        tags = set()
        for t in stats["triggers"]: tags.add(self.TRIGGER_CN.get(t, t))
        for a in stats["actions"]: tags.add(self.ACTION_CN.get(a, a))
        for p in stats["props"]: tags.add(p)
        return sorted(tags)


NODE_CLASS_MAPPINGS = {"CADB_KnowledgeBuilder": CADBKnowledgeBuilder}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_KnowledgeBuilder": "🧠 CADB 知识构建"}
