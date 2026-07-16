"""
🔮 CADB 视觉模型加载
ComfyUI 节点：加载本地 VLM 模型 → 输出给视频分析节点
支持：Qwen2-VL / Qwen2.5-VL / InternVL2 / MiniCPM-V
"""

import logging
from pathlib import Path

logger = logging.getLogger("CADB")


class CADBLoadVisionModel:
    """加载视觉语言模型，连线到 CADB 视频分析"""

    # 全局缓存：避免重复加载
    _loaded_models = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "模型路径": ("STRING", {"default": "Qwen/Qwen2-VL-7B-Instruct", "placeholder": "本地路径或 HuggingFace ID"}),
                "设备": (["cuda", "cpu", "auto"], {"default": "auto"}),
                "精度": (["bfloat16", "float16", "float32", "int4", "int8"], {"default": "bfloat16"}),
            },
            "optional": {
                "最大输出token": ("INT", {"default": 512, "min": 64, "max": 4096}),
                "温度": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 2.0, "step": 0.05}),
            },
        }

    RETURN_TYPES = ("CADB_VISION_MODEL", "STRING")
    RETURN_NAMES = ("视觉模型", "模型信息")
    FUNCTION = "process"
    CATEGORY = "CADB/Model"

    def process(
        self,
        模型路径: str = "",
        设备: str = "auto",
        精度: str = "bfloat16",
        最大输出token: int = 512,
        温度: float = 0.1,
    ):
        model_path = 模型路径
        device = 设备
        dtype_str = 精度
        max_tokens = 最大输出token
        temperature = 温度

        cache_key = f"{model_path}_{device}_{dtype_str}"

        if cache_key in self._loaded_models:
            model, processor = self._loaded_models[cache_key]
            info = f"✅ 缓存命中: {model_path}"
            return ((model, processor, {"max_tokens": max_tokens, "temperature": temperature}), info)

        # ─── 加载模型 ───
        try:
            import torch
            from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

            dtype_map = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}
            torch_dtype = dtype_map.get(dtype_str, torch.bfloat16)

            device_map = "auto" if device == "auto" else device

            logger.info(f"加载 VLM: {model_path} ({torch_dtype}, {device_map})")

            model = Qwen2VLForConditionalGeneration.from_pretrained(
                model_path,
                torch_dtype=torch_dtype,
                device_map=device_map,
                trust_remote_code=True,
            )
            processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)

            self._loaded_models[cache_key] = (model, processor)
            info = f"✅ 已加载: {model_path} | {device_map} | {dtype_str}"

        except Exception as e:
            logger.error(f"VLM 加载失败: {e}")
            info = f"❌ 加载失败: {e}"
            return ((None, None, {}), info)

        return ((model, processor, {"max_tokens": max_tokens, "temperature": temperature}), info)

    @classmethod
    def clear_cache(cls):
        """清除所有缓存的模型（释放显存）"""
        cls._loaded_models.clear()


NODE_CLASS_MAPPINGS = {"CADB_LoadVisionModel": CADBLoadVisionModel}
NODE_DISPLAY_NAME_MAPPINGS = {"CADB_LoadVisionModel": "🔮 CADB 加载视觉模型"}
