"""
🔮 CADB 加载视觉模型 (GGUF)
ComfyUI 节点：加载本地 GGUF 格式 VLM → 输出给视频分析节点
自动检测 Qwen2-VL / Qwen3-VL / LLaVA 格式
"""

import logging
from pathlib import Path

logger = logging.getLogger("CADB")


class CADBLoadVisionModelGGUF:
    """加载 GGUF 格式视觉语言模型"""

    _loaded_models = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "GGUF模型路径": ("STRING", {"default": "", "placeholder": "E:/.../Qwen3-VL-8B.Q6_K.gguf"}),
                "投影模型路径": ("STRING", {"default": "", "placeholder": "E:/.../mmproj-f16.gguf（多模态投影层）"}),
            },
            "optional": {
                "GPU层数": ("INT", {"default": -1, "min": -1, "max": 999, "tooltip": "-1=全部GPU, 0=纯CPU"}),
                "上下文长度": ("INT", {"default": 4096, "min": 512, "max": 32768}),
                "最大输出token": ("INT", {"default": 256, "min": 64, "max": 2048}),
                "温度": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 2.0, "step": 0.05}),
            },
        }

    RETURN_TYPES = ("CADB_VISION_MODEL", "STRING")
    RETURN_NAMES = ("视觉模型", "模型信息")
    FUNCTION = "process"
    CATEGORY = "CADB/Model"

    @classmethod
    def _detect_model_family(cls, model_path: str) -> str:
        """从文件名检测模型家族"""
        name = Path(model_path).name.lower()
        if "qwen3-vl" in name or "qwen3vl" in name:
            return "qwen3vl"
        if "qwen2-vl" in name or "qwen2vl" in name:
            return "qwen2vl"
        if "llava" in name:
            return "llava"
        return "llava"  # 默认

    @classmethod
    def _get_chat_handler(cls, model_family: str, mmproj_path: str):
        """根据模型家族获取合适的 chat handler"""
        try:
            if model_family in ("qwen3vl", "qwen2vl"):
                # Qwen VL 系列：尝试不同方式
                # 方式1: 直接尝试 Qwen3VL 专用 handler
                try:
                    from llama_cpp.llama_chat_format import Qwen3VLChatHandler
                    return Qwen3VLChatHandler(clip_model_path=mmproj_path, verbose=False)
                except ImportError:
                    pass
                # 方式2: 回退到 Llava16
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
        GGUF模型路径: str = "",
        投影模型路径: str = "",
        GPU层数: int = -1,
        上下文长度: int = 4096,
        最大输出token: int = 256,
        温度: float = 0.1,
    ):
        model_path = GGUF模型路径
        mmproj_path = 投影模型路径
        n_gpu_layers = GPU层数
        n_ctx = 上下文长度
        max_tokens = 最大输出token
        temperature = 温度

        if not model_path or not Path(model_path).exists():
            return ((None, None, {}), f"❌ GGUF 模型不存在: {model_path}")
        if not mmproj_path or not Path(mmproj_path).exists():
            return ((None, None, {}), f"❌ 投影模型不存在: {mmproj_path}")

        model_family = self._detect_model_family(model_path)
        cache_key = f"{model_path}_{mmproj_path}_{n_gpu_layers}"

        if cache_key in self._loaded_models:
            model = self._loaded_models[cache_key]
            info = f"✅ 缓存命中: {Path(model_path).name}"
            return ((model, "gguf", {"max_tokens": max_tokens, "temperature": temperature, "mmproj": mmproj_path}), info)

        try:
            from llama_cpp import Llama

            logger.info(f"加载 GGUF VLM [{model_family}]: {Path(model_path).name}")

            mmproj = self._get_chat_handler(model_family, mmproj_path)

            model = Llama(
                model_path=model_path,
                chat_handler=mmproj,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                verbose=False,
                logits_all=False,
                embedding=False,
            )

            self._loaded_models[cache_key] = model
            info = f"✅ [{model_family}] {Path(model_path).name} | GPU:{n_gpu_layers} | ctx:{n_ctx}"

        except ImportError as e:
            info = f"❌ 缺少依赖: {e}"
            return ((None, None, {}), info)
        except Exception as e:
            logger.error(f"GGUF 加载失败: {e}")
            return ((None, None, {}), f"❌ 加载失败: {e}")

        return ((model, "gguf", {"max_tokens": max_tokens, "temperature": temperature, "mmproj": mmproj_path}), info)

    @classmethod
    def clear_cache(cls):
        cls._loaded_models.clear()


NODE_CLASS_MAPPINGS = {"CADB_LoadVisionModelGGUF": CADBLoadVisionModelGGUF}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_LoadVisionModelGGUF": "🔮 CADB 加载视觉模型(GGUF)"}
