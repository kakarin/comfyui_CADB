"""
🎙️ CADB Whisper 模型加载
ComfyUI 节点：加载本地 Whisper 模型 → 输出给音频分析节点
搜索顺序：ComfyUI/models/whisper/ → 用户缓存 → 自动下载
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
                "模型路径": ("STRING", {"default": "", "placeholder": "留空自动搜索，或指定本地.pt路径"}),
            },
        }

    RETURN_TYPES = ("CADB_WHISPER_MODEL", "STRING")
    RETURN_NAMES = ("Whisper模型", "模型信息")
    FUNCTION = "process"
    CATEGORY = "CADB/Model"

    @classmethod
    def _resolve_path(cls, model_size: str, custom_path: str = "") -> str:
        """解析模型路径：ComfyUI/models/whisper/ → 用户缓存 → 自动下载"""
        filename = f"{model_size}.pt"

        # 1. 用户指定路径
        if custom_path and Path(custom_path).exists():
            return custom_path

        # 2. ComfyUI/models/whisper/
        try:
            from folder_paths import models_dir
            candidate = Path(models_dir) / "whisper" / filename
            if candidate.exists():
                return str(candidate)
        except ImportError:
            pass

        # 3. 相对路径搜索
        search_dirs = [
            Path(__file__).resolve().parent.parent.parent / "models" / "whisper",
            Path.home() / ".cache" / "whisper",
        ]
        for d in search_dirs:
            candidate = d / filename
            if candidate.exists():
                return str(candidate)

        # 4. 只返回名称，让后端自动下载
        return model_size

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
        custom_path = 模型路径

        # 解析实际路径
        model_path = self._resolve_path(model_size, custom_path)
        cache_key = f"{model_path}_{device}_{compute_type}"

        if cache_key in self._loaded_models:
            model, backend = self._loaded_models[cache_key]
            return ((model, backend), f"✅ 缓存命中: {model_size}")

        device_str = "cuda" if device in ("cuda", "auto") else "cpu"
        source = "本地" if Path(model_path).exists() else "下载"

        # 1. faster-whisper
        try:
            from faster_whisper import WhisperModel
            logger.info(f"加载 Whisper (faster/{source}): {model_path}")
            model = WhisperModel(model_path, device=device_str, compute_type=compute_type,
                                 download_root=str(Path(model_path).parent) if Path(model_path).exists() else None)
            self._loaded_models[cache_key] = (model, "faster")
            info = f"✅ faster-whisper [{source}]: {model_size} | {device_str}"
            return ((model, "faster"), info)
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"faster-whisper 失败: {e}")

        # 2. openai-whisper
        try:
            import whisper
            logger.info(f"加载 Whisper (openai/{source}): {model_path}")
            model = whisper.load_model(model_path, device=device_str)
            self._loaded_models[cache_key] = (model, "openai")
            info = f"✅ openai-whisper [{source}]: {model_size} | {device_str}"
            return ((model, "openai"), info)
        except ImportError:
            info = "❌ 请安装: pip install faster-whisper 或 openai-whisper"
            return ((None, "none"), info)
        except Exception as e:
            logger.error(f"Whisper 加载失败: {e}")
            return ((None, "none"), f"❌ 加载失败: {e}")

    @classmethod
    def clear_cache(cls):
        cls._loaded_models.clear()


NODE_CLASS_MAPPINGS = {"CADB_LoadWhisperModel": CADBLoadWhisperModel}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_LoadWhisperModel": "🎙️ CADB 加载Whisper模型"}
