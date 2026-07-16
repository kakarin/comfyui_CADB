"""
CADB 核心数据对象
所有节点统一使用这些 dataclass 传递数据。
支持 pickle 序列化（ComfyUI 节点间传递）。
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum
import json
import hashlib
from pathlib import Path


# ═══════════ 枚举 ═══════════

class SamplingProfile(str, Enum):
    FAST = "fast"
    STANDARD = "standard"
    HIGH_QUALITY = "high_quality"
    DYNAMIC = "dynamic"


class OutputFormat(str, Enum):
    JSON = "json"
    MARKDOWN = "markdown"
    TIMELINE_JSON = "timeline_json"
    TAGS_JSON = "tags_json"
    ALL = "all"


# ═══════════ 核心对象 ═══════════

@dataclass
class VideoObject:
    path: str
    filename: str = ""
    duration: float = 0.0
    fps: float = 0.0
    width: int = 0
    height: int = 0
    codec: str = ""
    audio_codec: str = ""
    has_audio: bool = True
    file_size: int = 0
    md5: str = ""

    def __post_init__(self):
        if self.path and not self.filename:
            self.filename = Path(self.path).name
        if self.path and not self.md5:
            self.md5 = hashlib.md5(self.path.encode()).hexdigest()


@dataclass
class FrameObject:
    index: int
    timestamp: float
    path: str = ""
    scene_id: int = 0
    motion_score: float = 0.0
    is_keyframe: bool = False
    is_scene_change: bool = False


@dataclass
class FrameEvent:
    timestamp: float
    action: str = ""
    action_confidence: float = 0.0
    props: list = field(default_factory=list)
    props_confidence: float = 0.0
    scene: str = ""
    scene_confidence: float = 0.0
    tags: list = field(default_factory=list)
    raw_response: str = ""
    frame_index: int = 0


@dataclass
class AudioEvent:
    start: float
    end: float
    trigger: str = ""
    trigger_confidence: float = 0.0
    transcript: str = ""
    transcript_confidence: float = 0.0
    volume_db: float = 0.0
    segment_index: int = 0


@dataclass
class TimelineEvent:
    start: float
    end: float
    action: str = ""
    trigger: str = ""
    props: list = field(default_factory=list)
    scene: str = ""
    tags: list = field(default_factory=list)
    transcript: str = ""
    confidence: float = 0.0
    source: str = ""

    def duration(self) -> float:
        return self.end - self.start


@dataclass
class Segment:
    start: float
    end: float
    action: str = ""
    trigger: str = ""
    props: list = field(default_factory=list)
    scene: str = ""
    tags: list = field(default_factory=list)
    transcript: str = ""
    confidence: float = 0.0
    event_count: int = 0

    def duration(self) -> float:
        return self.end - self.start


@dataclass
class KnowledgeObject:
    video: Optional[VideoObject] = None
    summary: str = ""
    prompt: str = ""
    tags: list = field(default_factory=list)
    triggers: dict = field(default_factory=dict)
    actions: dict = field(default_factory=dict)
    props: dict = field(default_factory=dict)
    scenes: dict = field(default_factory=dict)
    segments: list = field(default_factory=list)
    timeline: list = field(default_factory=list)
    total_duration: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class ReportObject:
    knowledge: Optional[KnowledgeObject] = None
    markdown: str = ""
    json_path: str = ""
    markdown_path: str = ""
    timeline_path: str = ""
    tags_path: str = ""


# ═══════════ 序列化 ═══════════

class ObjectEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, '__dataclass_fields__'):
            return asdict(obj)
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


def to_json(obj) -> str:
    return json.dumps(obj, cls=ObjectEncoder, indent=2, ensure_ascii=False)


def save_json(obj, path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, cls=ObjectEncoder, indent=2, ensure_ascii=False)
