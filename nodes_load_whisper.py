"""
🎙️ CADB Whisper 模型加载
ComfyUI 节点：加载 Whisper 模型 → 输出给音频分析节点
优先 faster-whisper (CTranslate2)，回退 openai-whisper
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
                "计算精度": (["float16", "int8_float16", "int8", "float32"], {"default": "int8_float16"}),
            },
            "optional": {
                "语言": (["auto", "zh", "en", "ja", "ko"], {"default": "auto"}),
                "模型路径": ("STRING", {"default": "", "placeholder": "留空自动下载，openai模型需指定.pt路径"}),
            },
        }

    RETURN_TYPES = ("CADB_WHISPER_MODEL", "STRING")
    RETURN_NAMES = ("Whisper模型", "模型信息")
    FUNCTION = "process"
    CATEGORY = "CADB/Model"

    @classmethod
    def _find_local_pt(cls, model_size: str, custom_path: str = "") -> str:
        """查找本地 openai-whisper .pt 文件路径"""
        filename = f"{model_size}.pt"
        if custom_path and Path(custom_path).exists():
            return custom_path
        try:
            from folder_paths import models_dir
            candidate = Path(models_dir) / "whisper" / filename
            if candidate.exists():
                return str(candidate)
        except ImportError:
            pass
        for d in [
            Path(__file__).resolve().parent.parent.parent / "models" / "whisper",
            Path.home() / ".cache" / "whisper",
        ]:
            candidate = d / filename
            if candidate.exists():
                return str(candidate)
        return ""

    def process(
        self,
        模型大小: str = "large-v3-turbo",
        设备: str = "auto",
        计算精度: str = "int8_float16",
        语言: str = "auto",
        模型路径: str = "",
    ):
        model_size = 模型大小
        device = 设备
        compute_type = 计算精度
        custom_path = 模型路径

        cache_key = f"{model_size}_{device}_{compute_type}"
        if cache_key in self._loaded_models:
            model, backend = self._loaded_models[cache_key]
            return ((model, backend), f"✅ 缓存命中: {model_size}")

        device_str = "cuda" if device in ("cuda", "auto") else "cpu"
        local_pt = self._find_local_pt(model_size, custom_path)

        # 1. faster-whisper（传模型名，自动下载CTranslate2格式）
        try:
            from faster_whisper import WhisperModel
            logger.info(f"加载 faster-whisper: {model_size}")
            model = WhisperModel(model_size, device=device_str, compute_type=compute_type)
            self._loaded_models[cache_key] = (model, "faster")
            tag = "本地" if local_pt else "下载"
            info = f"✅ faster-whisper [{tag}]: {model_size} | {device_str} | {compute_type}"
            return ((model, "faster"), info)
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"faster-whisper 失败: {e}")

        # 2. openai-whisper（需要.pt文件路径）
        try:
            import whisper
            model_path = local_pt if local_pt else model_size
            logger.info(f"加载 openai-whisper: {model_path}")
            model = whisper.load_model(model_path, device=device_str)
            self._loaded_models[cache_key] = (model, "openai")
            tag = "本地" if local_pt else "下载"
            info = f"✅ openai-whisper [{tag}]: {model_size} | {device_str}"
            return ((model, "openai"), info)
        except ImportError:
            return ((None, "none"), "❌ 请安装: pip install faster-whisper 或 openai-whisper")
        except Exception as e:
            logger.error(f"Whisper 加载失败: {e}")
            return ((None, "none"), f"❌ 加载失败: {e}")

    @classmethod
    def clear_cache(cls):
        cls._loaded_models.clear()


NODE_CLASS_MAPPINGS = {"CADB_LoadWhisperModel": CADBLoadWhisperModel}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_LoadWhisperModel": "🎙️ CADB 加载Whisper模型"}
