"""
📄 CADB Report Generator
ComfyUI OUTPUT 节点：Knowledge → Markdown / JSON / Timeline JSON / Tags JSON
"""

from pathlib import Path

from .objects import ReportObject, save_json
from .utils import CacheManager, project_root


class CADBReportGenerator:
    """报告生成：最终输出 Markdown + JSON + Tags"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "知识对象": ("CADB_KNOWLEDGE", {"tooltip": "来自 CADB 知识构建 的输出"}),
                "视频名称": ("STRING", {"default": "", "placeholder": "输出文件名前缀"}),
                "输出格式": (["all", "json", "markdown", "timeline_json", "tags_json"], {"default": "all"}),
                "输出目录": ("STRING", {"default": "", "placeholder": "输出目录（留空用默认 output/）"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("Markdown文本", "JSON路径", "调试摘要")
    FUNCTION = "process"
    CATEGORY = "CADB/Core"
    OUTPUT_NODE = True

    def __init__(self):
        self.cache = CacheManager("ReportGenerator")

    def process(
        self,
        知识对象=None,
        视频名称: str = "",
        输出格式: str = "all",
        输出目录: str = "",
    ):
        knowledge = 知识对象
        video_name = 视频名称
        output_format = 输出格式
        output_dir = 输出目录

        if knowledge is None:
            from .objects import KnowledgeObject
            knowledge = KnowledgeObject()

        k = knowledge
        stem = Path(video_name).stem if video_name else "output"
        base = Path(output_dir) if output_dir else project_root() / "output"
        json_path = str(base / "json" / f"{stem}.json")
        md_path = str(base / "markdown" / f"{stem}.md")
        tl_path = str(base / "timeline" / f"{stem}.timeline.json")
        tags_path = str(base / "tags" / f"{stem}.tags.json")
        saved = []

        if output_format in ("all", "json"):
            save_json(k, json_path); saved.append("JSON")

        md = ""
        if output_format in ("all", "markdown"):
            md = self._build_markdown(k, video_name)
            Path(md_path).parent.mkdir(parents=True, exist_ok=True)
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md)
            saved.append("Markdown")

        if output_format in ("all", "timeline_json"):
            save_json(k.timeline, tl_path); saved.append("Timeline")

        if output_format in ("all", "tags_json"):
            save_json({"tags": k.tags, "metadata": k.metadata}, tags_path)
            saved.append("Tags")

        return (md, json_path, f"✅ 已保存: {', '.join(saved)} → {base}")

    def _build_markdown(self, k, video_name: str) -> str:
        lines = []
        name = video_name or k.metadata.get("video_name", "Video")
        lines.append(f"# CADB 分析报告：{name}\n")
        lines.append("## 📊 基本信息\n")
        lines.append(f"- 总时长：{self._fmt(k.total_duration)}")
        lines.append(f"- 事件总数：{len(k.timeline)}")
        lines.append(f"- 连续片段：{len(k.segments)}\n")
        if k.summary:
            lines.append(k.summary + "\n")
        if k.timeline:
            lines.append("## ⏱️ 时间轴\n")
            lines.append("| 开始 | 结束 | 动作 | 触发音 | 道具 | 置信度 |")
            lines.append("|------|------|------|--------|------|--------|")
            for e in k.timeline[:100]:
                props_str = ", ".join(e.props[:3])
                lines.append(f"| {self._fmt(e.start)} | {self._fmt(e.end)} | {e.action} | {e.trigger} | {props_str} | {e.confidence:.0%} |")
            if len(k.timeline) > 100:
                lines.append(f"\n*（仅显示前100条，共{len(k.timeline)}条）*\n")
        if k.segments:
            lines.append("## 📦 连续片段\n")
            lines.append("| 开始 | 结束 | 持续 | 动作 | 触发音 | 事件数 |")
            lines.append("|------|------|------|------|--------|--------|")
            for s in k.segments[:50]:
                lines.append(f"| {self._fmt(s.start)} | {self._fmt(s.end)} | {self._fmt(s.duration())} | {s.action} | {s.trigger} | {s.event_count} |")
        for title, data in [("🔊 触发音统计", k.triggers), ("🎬 动作统计", k.actions), ("🛠️ 道具统计", k.props)]:
            if data:
                lines.append(f"\n## {title}\n")
                lines.append("| 项目 | 次数 |"); lines.append("|------|------|")
                for item, count in sorted(data.items(), key=lambda x: -x[1]):
                    lines.append(f"| {item} | {count} |")
        if k.prompt:
            lines.append(f"\n## 🎨 AI 绘图 Prompt\n```\n{k.prompt}\n```\n")
        if k.tags:
            lines.append(f"\n## 🏷️ 标签\n{', '.join(k.tags)}")
        return "\n".join(lines)

    @staticmethod
    def _fmt(s: float) -> str:
        m, sec = divmod(int(s), 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


NODE_CLASS_MAPPINGS = {"CADB_ReportGenerator": CADBReportGenerator}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_ReportGenerator": "📄 CADB 报告生成"}
