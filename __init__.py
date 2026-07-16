"""
CADB — ComfyUI ASMR Dataset Builder
====================================
将视频转换为结构化数据的 ComfyUI 自定义节点包。

节点链路：
  📂 CADB 加载视频  →  ✂️ CADB 音视频分离  ─→ 🧩 CADB 视频分析  ─┐
                                                                    ├→ 🔗 时间轴融合 → 🧠 知识构建 → 📄 报告生成
                                      └→ 🎧 CADB 音频分析  ────────┘
             🔮 加载视觉模型 ↗                        🎙️ 加载Whisper模型 ↗

安装：
  复制整个 CADB/ 目录到 ComfyUI/custom_nodes/ 即可。
"""

from .nodes_load_video import NODE_CLASS_MAPPINGS as LD_MAP, NODE_DISPLAY_NAME_MAPPINGS as LD_DISP
from .nodes_splitter import NODE_CLASS_MAPPINGS as SP_MAP, NODE_DISPLAY_NAME_MAPPINGS as SP_DISP
from .nodes_load_vision import NODE_CLASS_MAPPINGS as LV_MAP, NODE_DISPLAY_NAME_MAPPINGS as LV_DISP
from .nodes_load_whisper import NODE_CLASS_MAPPINGS as LW_MAP, NODE_DISPLAY_NAME_MAPPINGS as LW_DISP
from .nodes_video import NODE_CLASS_MAPPINGS as V_MAP, NODE_DISPLAY_NAME_MAPPINGS as V_DISP
from .nodes_audio import NODE_CLASS_MAPPINGS as A_MAP, NODE_DISPLAY_NAME_MAPPINGS as A_DISP
from .nodes_timeline import NODE_CLASS_MAPPINGS as T_MAP, NODE_DISPLAY_NAME_MAPPINGS as T_DISP
from .nodes_knowledge import NODE_CLASS_MAPPINGS as K_MAP, NODE_DISPLAY_NAME_MAPPINGS as K_DISP
from .nodes_report import NODE_CLASS_MAPPINGS as R_MAP, NODE_DISPLAY_NAME_MAPPINGS as R_DISP

NODE_CLASS_MAPPINGS = {}
NODE_CLASS_MAPPINGS.update(LD_MAP)
NODE_CLASS_MAPPINGS.update(SP_MAP)
NODE_CLASS_MAPPINGS.update(LV_MAP)
NODE_CLASS_MAPPINGS.update(LW_MAP)
NODE_CLASS_MAPPINGS.update(V_MAP)
NODE_CLASS_MAPPINGS.update(A_MAP)
NODE_CLASS_MAPPINGS.update(T_MAP)
NODE_CLASS_MAPPINGS.update(K_MAP)
NODE_CLASS_MAPPINGS.update(R_MAP)

NODE_DISPLAY_NAME_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS.update(LD_DISP)
NODE_DISPLAY_NAME_MAPPINGS.update(SP_DISP)
NODE_DISPLAY_NAME_MAPPINGS.update(LV_DISP)
NODE_DISPLAY_NAME_MAPPINGS.update(LW_DISP)
NODE_DISPLAY_NAME_MAPPINGS.update(V_DISP)
NODE_DISPLAY_NAME_MAPPINGS.update(A_DISP)
NODE_DISPLAY_NAME_MAPPINGS.update(T_DISP)
NODE_DISPLAY_NAME_MAPPINGS.update(K_DISP)
NODE_DISPLAY_NAME_MAPPINGS.update(R_DISP)

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
