"""
🔗 CADB Timeline Fusion
ComfyUI 节点：FrameEvents + AudioEvents → Timeline（时间轴融合）
"""

from .objects import TimelineEvent
from .utils import CacheManager


class CADBTimelineFusion:
    """时间轴融合：视觉 + 音频 → 统一时间轴"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "帧事件": ("CADB_FRAMEEVENTS", {"tooltip": "来自 CADB 视频分析 的输出"}),
                "音频事件": ("CADB_AUDIOEVENTS", {"tooltip": "来自 CADB 音频分析 的输出"}),
                "合并间隔": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.1, "tooltip": "时间相近且动作相同的相邻事件会合并"}),
                "最小置信度": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.05, "tooltip": "低于此置信度的事件将被过滤"}),
                "强制刷新": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("CADB_TIMELINE", "STRING")
    RETURN_NAMES = ("时间轴", "调试摘要")
    FUNCTION = "process"
    CATEGORY = "CADB/Core"

    def __init__(self):
        self.cache = CacheManager("TimelineFusion")

    def process(
        self,
        帧事件: list = None,
        音频事件: list = None,
        合并间隔: float = 1.0,
        最小置信度: float = 0.0,
        强制刷新: bool = False,
    ):
        fe = 帧事件 or []
        ae = 音频事件 or []
        merge_gap_sec = 合并间隔
        min_confidence = 最小置信度
        force_update = 强制刷新

        if not force_update:
            cached = self.cache.get(fe, ae, merge_gap_sec, min_confidence)
            if cached is not None:
                return (cached, f"✅ 缓存命中: {len(cached)} 个事件")

        aligned = self._align_by_time(fe, ae)
        merged = self._deduplicate_and_merge(aligned, merge_gap_sec)
        timeline = self._merge_confidence(merged, min_confidence)

        self.cache.set(timeline, fe, ae, merge_gap_sec, min_confidence)
        return (timeline, f"✅ 视觉:{len(fe)} + 音频:{len(ae)} → 时间轴:{len(timeline)}")

    def _align_by_time(self, fe: list, ae: list) -> list[dict]:
        aligned = []
        ai = 0
        for f in fe:
            best = None
            while ai < len(ae):
                a = ae[ai]
                if a.start <= f.timestamp <= a.end:
                    best = a; break
                elif a.end < f.timestamp:
                    ai += 1
                else:
                    break
            aligned.append({"timestamp": f.timestamp, "frame_event": f, "audio_event": best})
        return aligned

    def _deduplicate_and_merge(self, aligned: list[dict], gap: float) -> list[dict]:
        if not aligned:
            return []
        merged = [aligned[0]]
        for item in aligned[1:]:
            prev = merged[-1]
            pf = prev["frame_event"]; cf = item["frame_event"]
            time_diff = cf.timestamp - pf.timestamp
            same_action = (pf.action == cf.action and cf.action != "idle")
            same_trigger = False
            if prev.get("audio_event") and item.get("audio_event"):
                same_trigger = (prev["audio_event"].trigger == item["audio_event"].trigger != "")
            if (same_action or same_trigger) and time_diff <= gap:
                prev["frame_event"] = cf
                if item["audio_event"]:
                    prev["audio_event"] = item["audio_event"]
                continue
            merged.append(item)
        return merged

    def _merge_confidence(self, aligned: list[dict], min_conf: float) -> list[TimelineEvent]:
        tl = []
        for item in aligned:
            fe = item["frame_event"]; ae = item.get("audio_event")
            if ae and fe.action != "idle":
                src, conf = "both", (fe.action_confidence + ae.trigger_confidence) / 2
            elif ae:
                src, conf = "audio", ae.trigger_confidence
            else:
                src, conf = "vision", fe.action_confidence
            if conf < min_conf:
                continue
            tl.append(TimelineEvent(
                start=ae.start if ae else fe.timestamp,
                end=ae.end if ae else fe.timestamp,
                action=fe.action, trigger=ae.trigger if ae else "",
                props=fe.props, scene=fe.scene, tags=fe.tags,
                transcript=ae.transcript if ae else "",
                confidence=round(conf, 4), source=src,
            ))
        return tl


NODE_CLASS_MAPPINGS = {"CADB_TimelineFusion": CADBTimelineFusion}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_TimelineFusion": "🔗 CADB 时间轴融合"}
