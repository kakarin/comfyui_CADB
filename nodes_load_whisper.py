"""
🎙️ CADB Whisper 模型加载
ComfyUI 节点：加载本地 Whisper 模型 → 输出给音频分析节点
使用 faster-whisper（比原版 whisper 快 4 倍，内存更低）
"""

import logging
from pathlib import Path

logger = logging.getLogger("CADB")


class CADBLoadWhisperModel:
    """加载 Whisper 模型，连线到 CADB 音频分析"""

    _loaded_models = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "模型大小": (["large-v3-turbo", "large-v3", "large-v2", "medium", "small", "base", "tiny"], {"default": "large-v3-turbo"}),
                "设备": (["cuda", "cpu", "auto"], {"default": "auto"}),
                "计算精度": (["float16", "int8_float16", "int8", "float32"], {"default": "float16"}),
            },
            "optional": {
                "语言": (["auto", "zh", "en", "ja", "ko"], {"default": "auto"}),
                "模型路径": ("STRING", {"default": "", "placeholder": "留空自动下载，或指定本地路径"}),
            },
        }

    RETURN_TYPES = ("CADB_WHISPER_MODEL", "STRING")
    RETURN_NAMES = ("Whisper模型", "模型信息")
    FUNCTION = "process"
    CATEGORY = "CADB/Model"

    def process(
        self,
        模型大小: str = "large-v3-turbo",
        设备: str = "auto",
        计算精度: str = "float16",
        语言: str = "auto",
        模型路径: str = "",
    ):
        model_size = 模型大小
        device = 设备
        compute_type = 计算精度
        language = 语言
        custom_path = 模型路径

        cache_key = f"{model_size}_{device}_{compute_type}_{custom_path}"

        if cache_key in self._loaded_models:
            model = self._loaded_models[cache_key]
            info = f"✅ 缓存命中: {model_size}"
            return (model, info)

        # ─── 加载模型 ───
        try:
            from faster_whisper import WhisperModel

            # 确定模型：优先本地路径 → 自动下载
            if custom_path and Path(custom_path).exists():
                model_path = custom_path
            else:
                model_path = model_size  # faster-whisper 会自动下载

            # 设备判断
            device_str = "cuda" if device == "cuda" else ("cuda" if device == "auto" else "cpu")

            logger.info(f"加载 Whisper: {model_path} ({device_str}, {compute_type})")

            model = WhisperModel(
                model_path,
                device=device_str,
                compute_type=compute_type,
                download_root=custom_path if custom_path else None,
            )

            self._loaded_models[cache_key] = model
            info = f"✅ 已加载: {model_size} | {device_str} | {compute_type}"

        except ImportError:
            info = "❌ 请安装 faster-whisper: pip install faster-whisper"
            return (None, info)
        except Exception as e:
            logger.error(f"Whisper 加载失败: {e}")
            info = f"❌ 加载失败: {e}"
            return (None, info)

        return (model, info)

    @classmethod
    def clear_cache(cls):
        cls._loaded_models.clear()


NODE_CLASS_MAPPINGS = {"CADB_LoadWhisperModel": CADBLoadWhisperModel}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_LoadWhisperModel": "🎙️ CADB 加载Whisper模型"}
