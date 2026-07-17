"""
CADB 工具函数：配置加载 / 词典匹配 / 缓存管理
"""

import hashlib
import json
import logging
import pickle
import time
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger("CADB")

# ── 项目根目录 ──

def project_root() -> Path:
    return Path(__file__).resolve().parent


def _load_json(filename: str) -> dict:
    path = project_root() / filename
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_dictionary(name: str) -> dict:
    return _load_json(f"dictionary/{name}.json")


# ── 词典匹配 ──

def match_trigger(text: str) -> list[dict]:
    triggers = get_dictionary("triggers")
    results = []
    text_lower = text.lower()
    for key, info in triggers.get("triggers", {}).items():
        for kw in info.get("keywords", []):
            if kw.lower() in text_lower:
                results.append({"id": key, "name": info["name"], "category": info["category"], "matched_keyword": kw})
                break
    return results


def match_action(text: str) -> list[dict]:
    actions = get_dictionary("actions")
    results = []
    text_lower = text.lower()
    for key, info in actions.get("actions", {}).items():
        name_lower = info["name"].lower()
        if name_lower in text_lower:
            results.append({"id": key, "name": info["name"]})
    return results


def match_props(text: str) -> list[dict]:
    props = get_dictionary("props")
    results = []
    text_lower = text.lower()
    for key, info in props.get("props", {}).items():
        name_lower = info["name"].lower()
        if name_lower in text_lower:
            results.append({"id": key, "name": info["name"], "category": info["category"]})
    return results


def match_scene(text: str) -> str:
    scenes = get_dictionary("scenes")
    text_lower = text.lower()
    for key, info in scenes.get("scenes", {}).items():
        if info["name"].lower() in text_lower:
            return info["name"]
    return "front_view"


# ── 缓存管理 ──

class CacheManager:
    def __init__(self, node_name: str, cache_dir: Optional[str] = None):
        self.node_name = node_name
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = project_root() / "cache" / node_name
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _make_key(self, *args, **kwargs) -> str:
        content = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, *args, **kwargs) -> Optional[Any]:
        key = self._make_key(*args, **kwargs)
        path = self.cache_dir / f"{key}.pkl"
        if not path.exists():
            return None
        age_hours = (time.time() - path.stat().st_mtime) / 3600
        if age_hours > 168:  # 7 days
            path.unlink(missing_ok=True)
            return None
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            path.unlink(missing_ok=True)
            return None

    def set(self, value: Any, *args, **kwargs):
        key = self._make_key(*args, **kwargs)
        path = self.cache_dir / f"{key}.pkl"
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(path, 'wb') as f:
                pickle.dump(value, f)
        except Exception as e:
            logger.warning(f"Cache save failed for {self.node_name}: {e}")

    def clear(self):
        for f in self.cache_dir.glob("*.pkl"):
            f.unlink()
