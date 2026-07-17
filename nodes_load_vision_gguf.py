"""
🔮 CADB 加载视觉模型 (GGUF)
ComfyUI 节点：下拉选取 models/LLM/ 中的 GGUF 模型 → 输出给视频分析节点
"""

import logging
from pathlib import Path

logger = logging.getLogger("CADB")


class CADBLoadVisionModelGGUF:
    """加载 GGUF 格式视觉语言模型"""

    _loaded_models = {}

    @classmethod
    def _get_models_dir(cls) -> Path:
        try:
            from folder_paths import models_dir
            return Path(models_dir) / "LLM"
        except Exception:
            return Path(__file__).resolve().parent.parent.parent / "models" / "LLM"

    @classmethod
    def _scan_models(cls, pattern: str = "*.gguf") -> list:
        """扫描 models/LLM/ 下的 GGUF 文件"""
        d = cls._get_models_dir()
        if not d.exists():
            return []
        files = sorted([f.name for f in d.glob(pattern)])
        return files if files else []

    @classmethod
    def _resolve_model_path(cls, name: str, is_mmproj: bool = False) -> str:
        """将文件名解析为完整路径"""
        if not name:
            return ""
        # 已是完整路径
        if Path(name).is_absolute() or "/" in name or "\\" in name:
            return name
        # 拼接 models/LLM/
        return str(cls._get_models_dir() / name)

    @classmethod
    def INPUT_TYPES(cls):
        all_gguf = cls._scan_models("*.gguf")
        models_list = [f for f in all_gguf if "mmproj" not in f.lower()]
        mmproj_list = [f for f in all_gguf if "mmproj" in f.lower()]

        if models_list:
            model_input = (models_list, {"default": models_list[0]})
        else:
            model_input = ("STRING", {"default": "", "placeholder": "无 .gguf 文件，请手动输入路径"})

        if mmproj_list:
            mmproj_input = (mmproj_list, {"default": mmproj_list[0]})
        else:
            mmproj_input = ("STRING", {"default": "", "placeholder": "无 mmproj 文件，请手动输入路径"})

        return {
            "required": {
                "GGUF模型": model_input,
                "投影模型": mmproj_input,
            },
            "optional": {
                "GPU层数": ("INT", {"default": -1, "min": -1, "max": 999, "tooltip": "-1=全部GPU"}),
                "上下文长度": ("INT", {"default": 4096, "min": 512, "max": 32768}),
                "最大输出token": ("INT", {"default": 128, "min": 64, "max": 2048}),
                "温度": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 2.0, "step": 0.05}),
            },
        }

    RETURN_TYPES = ("CADB_VISION_MODEL", "STRING")
    RETURN_NAMES = ("视觉模型", "模型信息")
    FUNCTION = "process"
    CATEGORY = "CADB/Model"

    @classmethod
    def _detect_model_family(cls, model_path: str) -> str:
        name = Path(model_path).name.lower()
        if "qwen3-vl" in name or "qwen3vl" in name:
            return "qwen3vl"
        if "qwen2-vl" in name or "qwen2vl" in name:
            return "qwen2vl"
        if "llava" in name:
            return "llava"
        return "llava"

    @classmethod
    def _get_chat_handler(cls, model_family: str, mmproj_path: str):
        try:
            if model_family in ("qwen3vl", "qwen2vl"):
                try:
                    from llama_cpp.llama_chat_format import Qwen3VLChatHandler
                    return Qwen3VLChatHandler(clip_model_path=mmproj_path, verbose=False)
                except ImportError:
                    pass
                from llama_cpp.llama_chat_format import Llava16ChatHandler
                return Llava16ChatHandler(clip_model_path=mmproj_path, verbose=False)
            else:
                from llama_cpp.llama_chat_format import Llava15ChatHandler
                return Llava15ChatHandler(clip_model_path=mmproj_path, verbose=False)
        except Exception as e:
            logger.warning(f"Chat handler 创建失败: {e}")
            raise

    def process(
        self,
        GGUF模型: str = "",
        投影模型: str = "",
        GPU层数: int = -1,
        上下文长度: int = 4096,
        最大输出token: int = 128,
        温度: float = 0.1,
    ):
        model_path = self._resolve_model_path(GGUF模型)
        mmproj_path = self._resolve_model_path(投影模型, is_mmproj=True)
        n_gpu_layers = GPU层数
        n_ctx = 上下文长度
        max_tokens = 最大输出token
        temperature = 温度

        if not model_path or not Path(model_path).exists():
            return ((None, None, {}), f"❌ 模型不存在: {model_path}")
        if not mmproj_path or not Path(mmproj_path).exists():
            return ((None, None, {}), f"❌ 投影模型不存在: {mmproj_path}")

        model_family = self._detect_model_family(model_path)
        cache_key = f"{model_path}_{mmproj_path}_{n_gpu_layers}"

        if cache_key in self._loaded_models:
            model = self._loaded_models[cache_key]
            info = f"✅ 缓存: {Path(model_path).name}"
            return ((model, "gguf", {"max_tokens": max_tokens, "temperature": temperature, "mmproj": mmproj_path}), info)

        try:
            from llama_cpp import Llama
            logger.info(f"加载 GGUF [{model_family}]: {Path(model_path).name}")
            mmproj = self._get_chat_handler(model_family, mmproj_path)
            model = Llama(
                model_path=model_path, chat_handler=mmproj,
                n_ctx=n_ctx, n_gpu_layers=n_gpu_layers,
                verbose=False, logits_all=False, embedding=False,
            )
            self._loaded_models[cache_key] = model
            info = f"✅ [{model_family}] {Path(model_path).name} | GPU:{n_gpu_layers}"
        except ImportError as e:
            return ((None, None, {}), f"❌ 缺少依赖: {e}")
        except Exception as e:
            logger.error(f"GGUF 加载失败: {e}")
            return ((None, None, {}), f"❌ 加载失败: {e}")

        return ((model, "gguf", {"max_tokens": max_tokens, "temperature": temperature, "mmproj": mmproj_path}), info)

    @classmethod
    def clear_cache(cls):
        cls._loaded_models.clear()


NODE_CLASS_MAPPINGS = {"CADB_LoadVisionModelGGUF": CADBLoadVisionModelGGUF}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_LoadVisionModelGGUF": "🔮 CADB 加载视觉模型(GGUF)"}
