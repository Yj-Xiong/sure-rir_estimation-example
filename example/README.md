# Rec-RIR 的 SURE Harness 复现

本目录提供 20 条 Rec-RIR 单通道 RIR 估计链路：

```text
SURE Harness Runtime
  -> Rec-RIR 模型环境
  -> estimate_rir MCP 推理
  -> SURE RIR bridge
  -> evaluate_predictions.py
  -> Evaluation Runtime
  -> pipeline bundle
  -> report.json
```

模型 MCP 只接收输入音频和输出路径；reference RIR 由 Harness bridge
传给评测器。网页 `data/results.json` 使用 60 条固定 SNR 数据和 NPM
pipeline，本目录使用 20 条 fixture 数据和
`rir_nmse`/`rir_corr`/`rt60_mae`。

## 1. 获取源码和运行时

需要 Git、`uv`、Bash 和 Python 依赖下载权限。以下命令在同一个工作目录执行。
`SURE_SOURCE` 指向包含指定提交的 SURE 源码，评测引擎子模块从个人 fork 获取。

```bash
RIR_EXAMPLE="/absolute/path/to/sure-rir_estimation-example/example"
SURE_SOURCE="/absolute/path/to/sure-harness"
git clone --no-checkout "$SURE_SOURCE" sure-rir-repro
git -C sure-rir-repro checkout 73975931da1353c3b97a422e796612d8b363fe3b
git -C sure-rir-repro config submodule.sure/external/sure-evaluation.url https://github.com/Yj-Xiong/sure-evaluation.git
git -C sure-rir-repro submodule update --init sure/external/sure-evaluation
git -C sure-rir-repro/sure/external/sure-evaluation rev-parse HEAD

SURE_REPO="$PWD/sure-rir-repro"
HARNESS_PYTHON_BIN=$(python3 "$SURE_REPO/sure/runtime/harness/bootstrap.py")
"$HARNESS_PYTHON_BIN" --version
```

评测引擎提交为 `8041b1249c5d0ce39a96c72cab01e49b09cc87e9`。
`bootstrap.py` 根据锁文件准备 Harness Runtime。后续命令使用
`$HARNESS_PYTHON_BIN`。首次安装会下载 Python 3.11 和依赖。

## 2. 准备 Rec-RIR 模型

```bash
MODEL_SOURCE="/absolute/path/to/Rec-RIR"
git clone --no-checkout "$MODEL_SOURCE" rec-rir-source
git -C rec-rir-source checkout 6914eea792f0117e39f87510ffbda7cd04dffbbb
MODEL_REPO="$PWD/rec-rir-source"

MODEL_CHECKPOINT="$MODEL_REPO/ckpt/epoch35.tar"
sha256sum "$MODEL_CHECKPOINT"

uv venv --python 3.10 .venv-rir-model
MODEL_PYTHON="$PWD/.venv-rir-model/bin/python"
uv pip install --python "$MODEL_PYTHON" \
  'torch==2.2.0' 'torchaudio==2.2.0' 'mamba-ssm==2.1.0' \
  'causal-conv1d==1.4.0' 'numpy==1.26.4' 'soundfile==0.13.1' \
  'toml==0.10.2' 'tqdm==4.68.2' 'jsonargparse==4.48.0' 'matplotlib==3.10.8'
```

checkpoint SHA-256:
`afe36e477f6fb3656d162d906a47da2d40a789634b476564266fc1ba36037478`。
模型提交、权重哈希和输出目录由脚本检查。`mamba-ssm` 和
`causal-conv1d` 需要与 PyTorch/CUDA 匹配；安装 CUDA 扩展时使用集群作业。
模型权重不包含在本示例仓库中。模型依赖和 Harness/Evaluation 依赖分别安装。

模型依赖版本：PyTorch 2.2.0、torchaudio 2.2.0、NumPy 1.26.4，CUDA 12.1
wheel。`MODEL_SOURCE` 可指向 `Audio-WestlakeU/Rec-RIR`。

安装后运行适配器检查：

```bash
"$MODEL_PYTHON" "$RIR_EXAMPLE/test_example.py"
```

## 3. 推理和评测

以下命令逐条处理 20 条输入，需要在已分配的集群 GPU/CPU 作业内执行。
输出目录需位于作业可写的共享存储。

```bash
"$HARNESS_PYTHON_BIN" "$RIR_EXAMPLE/run_example.py" \
  --repo "$SURE_REPO" \
  --model-repo "$MODEL_REPO" \
  --checkpoint "$MODEL_CHECKPOINT" \
  --model-python "$MODEL_PYTHON" \
  --device cuda:0 \
  --output-dir "$PWD/rir-run-001"
```

`--device cpu` 可用于支持 CPU 依赖的环境。输出目录必须不存在。
脚本校验 20 条输入及 channel-0 reference 的 SHA-256，然后调用 Rec-RIR
`inference.py` 生成 16 kHz 单通道 RIR。Harness bridge 按 `sample_id`
对齐 prediction 和 reference，评分 `rir_nmse`、`rir_corr`、`rt60_mae`，
并运行版本化 pipeline：

```text
rir.any.multi.rir_nmse.rir_nmse_v1__rir_corr.rir_corr_v1__rt60_mae.rt60_mae_v1
```

检查输出：

```bash
"$HARNESS_PYTHON_BIN" -m json.tool "$PWD/rir-run-001/summary.json"
"$HARNESS_PYTHON_BIN" -m json.tool "$PWD/rir-run-001/evaluation/report.json"
```

输出目录包含 MCP 日志、预测 WAV、输入清单、运行时身份、模型环境、Harness
评分 payload、pipeline 描述和 report。使用 `--resume` 可从已校验的
`infer-contract.json` 继续评分；重新推理时使用新的输出目录。

## 文件

`fixture/provenance.json` 和 `fixture/sha256.json` 记录数据来源、选样和哈希。
`fixture/cases/` 保存四种通道分支的输入、输出和部分报告。
`harness-run/` 保存 20 条运行的报告、pipeline 身份和环境信息。

四麦 demo 的 60 条选择见仓库根目录的
`data/four_mic_demo_selection.json`，来源为
`Rec-BIR/NeuSIRI/data/four_mic_fixed_v2/test/test_manifest.jsonl`。
选择规则为 10/20/30 dB、每个相邻间距 2 条，共 60 条；四通道模型输出可由
双通道模型两次推理后合并。

网页数据和本目录使用不同的数据集、引擎版本和指标定义，分数分别解释。
