# comfyui_CADB — ComfyUI ASMR Dataset Builder

将 ASMR / VTuber / 真人视频转换为结构化数据的 ComfyUI 自定义节点。

```
视频 → 抽帧 + VLM视觉分析 + Whisper音频转录 → 时间轴融合 → 知识构建 → Markdown/JSON报告
```

## 🧩 节点清单（7个）

| 分类 | 节点 | 作用 |
|------|------|------|
| CADB/Model | 🔮 CADB 加载视觉模型 | 本地加载 Qwen2-VL / InternVL2 |
| CADB/Model | 🎙️ CADB 加载Whisper模型 | 本地加载 faster-whisper |
| CADB/Video | 🧩 CADB 视频分析 | FFmpeg 抽帧 + VLM 逐帧识别 |
| CADB/Audio | 🎧 CADB 音频分析 | 提取音频 + Whisper 转录 + Trigger 分类 |
| CADB/Core | 🔗 CADB 时间轴融合 | FrameEvents + AudioEvents → Timeline |
| CADB/Core | 🧠 CADB 知识构建 | Timeline → 统计/分段/摘要/Prompt/Tags |
| CADB/Core | 📄 CADB 报告生成 | 输出 Markdown + JSON + Tags |

## 📥 安装

```bash
# 复制到 ComfyUI custom_nodes
git clone https://github.com/<user>/comfyui_CADB.git
cp -r comfyui_CADB /path/to/ComfyUI/custom_nodes/

# 或一键安装
python comfyui_CADB/scripts/setup.py install --comfyui /path/to/ComfyUI
```

## 🚀 使用

1. 拉入 `🔮 CADB 加载视觉模型` → 填 HuggingFace 模型 ID 或本地路径
2. 拉入 `🎙️ CADB 加载Whisper模型` → 选模型大小
3. 拉入 `🧩 CADB 视频分析` → 填视频路径，连线视觉模型
4. 拉入 `🎧 CADB 音频分析` → 填视频路径，连线 Whisper 模型
5. 后续三个节点依次连线
6. `📄 CADB 报告生成` 设置输出目录
7. Queue → 本地 GPU 推理

```
🔮 加载视觉模型 ──→ 🧩 视频分析 ─┐
                                  ├→ 🔗 时间轴融合 → 🧠 知识构建 → 📄 报告生成
🎙️ 加载Whisper模型 → 🎧 音频分析 ─┘
```

## 📦 依赖

```bash
pip install faster-whisper transformers torch Pillow
# FFmpeg 需系统安装
apt install ffmpeg
```

## ⚙️ 配置

- `config/models.yaml` — 模型配置
- `config/workflow.yaml` — 工作流 Profile（fast/standard/high_quality/dynamic）
- `dictionary/` — 触发音/动作/道具/场景/标签词典
- `prompts/` — VLM/Whisper Prompt 模板 + 6 种 Preset

## 🛠️ 命令行

```bash
python -m CADB.scripts.run --video demo.mp4 --profile high_quality
python -m CADB.scripts.run --batch input/batch/ --workers 2
```
