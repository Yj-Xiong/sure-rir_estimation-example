# Rec-RIR 的 SURE Harness 后端复现

本目录提供一条可以重新生成模型预测和评测报告的 20 条 Rec-RIR 单通道参考链路：
固定版本 SURE -> Harness Runtime -> 独立 Rec-RIR 模型环境 -> `estimate_rir` MCP
真实推理 -> SURE Harness RIR bridge -> `evaluate_predictions.py` 外部评分 ->
锁定的 Evaluation Runtime -> 版本化 pipeline bundle -> `report.json`。参考 RIR
仅传给 bridge/评分器，模型 MCP 只收到输入音频和目标输出路径。

此脚本复现的是 **Harness 后端链路**，与 SE 示例中的开发 smoke 范围相同；它不声称
完成交互式 `/sure_onboard`、正向 Approve、模型发布或完整 slash-command 生命周期。
网页 `data/results.json` 的 60 条固定 SNR 分数来自另一组数据与较新的 NPM pipeline，
不能和本目录的 20 条 `rir_nmse` 报告直接比较。`fixture/cases/` 中保存的四种通道分支
预测和部分报告是已有证据；本脚本目前重新执行的是 Rec-RIR channel-0 分支，
不能把其余三种分支的已保存预测称为本次模型重跑。

## 1. 获取固定源码和 Harness Runtime

需要 Git、`uv`、能下载 Python 依赖的网络，以及 Bash。本次实测使用 CUDA；CPU
推理路径未验证。以下命令在同一个工作目录执行。当前固定的 SURE 与评测引擎提交存在于
本地工作区；本地远端跟踪分支尚未显示这两个提交。先用包含提交对象的本地源码
克隆，待相应提交公开后可把源码变量换成 GitHub URL。

```bash
RIR_EXAMPLE="/absolute/path/to/sure-rir_estimation-example/example"
SURE_SOURCE="/absolute/path/to/sure-harness"
ENGINE_SOURCE="$SURE_SOURCE/sure/external/sure-evaluation"
git clone --no-checkout "$SURE_SOURCE" sure-rir-repro
git -C sure-rir-repro checkout 73975931da1353c3b97a422e796612d8b363fe3b
git -C sure-rir-repro config submodule.sure/external/sure-evaluation.url "$ENGINE_SOURCE"
git -C sure-rir-repro -c protocol.file.allow=always submodule update --init sure/external/sure-evaluation
git -C sure-rir-repro/sure/external/sure-evaluation rev-parse HEAD

SURE_REPO="$PWD/sure-rir-repro"
HARNESS_PYTHON_BIN=$(python3 "$SURE_REPO/sure/runtime/harness/bootstrap.py")
"$HARNESS_PYTHON_BIN" --version
```

子模块必须是 `8041b1249c5d0ce39a96c72cab01e49b09cc87e9`。`bootstrap.py`
通过锁文件准备并核验 Harness Runtime；系统的 `python3` 只负责启动 bootstrap，
后续脚本必须使用 `$HARNESS_PYTHON_BIN`。首次安装可能下载 Python 3.11 与依赖。
在本工作区，`SURE_SOURCE` 可指向 `AutoResearch/sure-harness`，`ENGINE_SOURCE`
可指向其 `sure/external/sure-evaluation`。若已有 Python 3.11 但 uv 的解释器下载
不可用，将该解释器目录放到 `PATH` 前面，并设置 `UV_PYTHON_DOWNLOADS=never`；
依赖镜像可以通过 `UV_INDEX_URL` 指定，锁文件的哈希验证仍会执行。

## 2. 准备真实 Rec-RIR 模型

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

checkpoint 的 SHA-256 必须是
`afe36e477f6fb3656d162d906a47da2d40a789634b476564266fc1ba36037478`。
模型源码提交、权重哈希和输出目录由脚本在推理前强制检查。`mamba-ssm` /
`causal-conv1d` 需要与本机 PyTorch/CUDA 匹配；如果在 CPU 环境不能安装，先在
匹配的 CUDA 主机准备模型环境。全新安装可能触发 CUDA 扩展编译，必须在集群作业
中执行上述 `uv` 安装命令；调试机只可复用已有环境进行短时检查。模型依赖和
Harness/Evaluation 依赖分别安装，
模型权重包含在固定的 Rec-RIR 源码提交中，不随本示例仓库分发。上游 `requirements.txt` 的 `python==2.9.0` 是
同名 PyPI 包，不能用它安装 Python 解释器。
上面的版本是本次实测环境的直接依赖；实测使用 PyTorch 2.2.0+cu121 和 NumPy
1.26.4。全新安装的 CUDA wheel 组合仍需在目标机器验证，不能保证跨硬件字节一致。
本工作区的 `MODEL_SOURCE` 可指向 `AutoResearch/Rec-RIR`；该模型提交也在
`Audio-WestlakeU/Rec-RIR` 的本地 `origin/main` 跟踪分支中。安装后可先运行不加载
checkpoint 的适配器与公开报告检查：

```bash
"$MODEL_PYTHON" "$RIR_EXAMPLE/test_example.py"
```

## 3. 在集群作业中重新执行推理和评分

这一节会对 20 条输入逐条加载模型并推理，属于批量高负载任务。调试机只运行源码、
哈希和已有环境中的 `test_example.py` 等短时检查；以下命令必须在已分配的集群 GPU/CPU 作业
内执行，输出目录需位于作业可写的共享存储。将第 1、2 节设置的路径变量传入作业环境。

```bash
"$HARNESS_PYTHON_BIN" "$RIR_EXAMPLE/run_example.py" \
  --repo "$SURE_REPO" \
  --model-repo "$MODEL_REPO" \
  --checkpoint "$MODEL_CHECKPOINT" \
  --model-python "$MODEL_PYTHON" \
  --device cuda:0 \
  --output-dir "$PWD/rir-run-001"
```

若集群环境的模型依赖支持 CPU，可将 `--device` 设为 `cpu`，但本次未验证该路径。
输出目录必须不存在。脚本校验 20 条输入和
channel-0 参考的 SHA-256，然后调用上游 `inference.py` 的 PIM RIR 估计：每条双通道
混合音频只取 channel 0，输出一个 16 kHz 单通道 RIR。MCP 返回 `rir_path`；
Harness 的 `_write_external_audio_samples_jsonl` 将预测与参考按 `sample_id` 对齐。
脚本调用 SURE 的 `evaluation_runtime.py --prepare`，再通过
`evaluate_predictions.py --evaluation-backend external` 评分三个指标，并用该 Runtime
的 Python 加载固定引擎 CLI，执行 bundle 的 `metric describe` 和
`metric run --validate-env`。Evaluation Runtime 只安装锁定依赖，因此脚本通过
`from sure_eval.cli import app; app()` 调用 CLI，不假设 `bin/sure-eval` 已安装。
运行时显式校验 MCP `initialize(id=1)`、`tools/list(id=2)` 与 `shutdown` 响应。
所选版本的基础 bundle 是
`rir_nmse,rir_corr,rt60_mae`，其 pipeline ID 为
`rir.any.multi.rir_nmse.rir_nmse_v1__rir_corr.rir_corr_v1__rt60_mae.rt60_mae_v1`。

成功后检查：

```bash
"$HARNESS_PYTHON_BIN" -m json.tool "$PWD/rir-run-001/summary.json"
"$HARNESS_PYTHON_BIN" -m json.tool "$PWD/rir-run-001/evaluation/report.json"
```

`rir-run-001/` 保存 `infer-mcp.log`、每条新生成的 `predictions/*.wav`、
`infer-contract.json`、Harness bridge 的 `samples.jsonl`、Evaluation Runtime
身份 `evaluation_runtime.json`、模型环境 `model_environment.json`、Harness 的
`harness-evaluation/payload.json` 与
逐指标报告、`pipeline.json`、bundle 评分日志及
`evaluation/{pipeline_description.json,report.json}`。`summary.json` 记录提交、
checkpoint 哈希、两个 Runtime ID、样本数、pipeline ID 和指标分数；
脚本会验证 describe/run/report 的 pipeline ID 与计算节点一致。失败时保留已创建的
输出目录与日志。模型推理已经成功、仅后续评分失败时，可用原命令加 `--resume`
恢复：它核验 `infer-contract.json` 中全部 20 条路径与 SHA-256，保留原始
`infer-mcp.log`，只重新执行 bridge 与评分；需要重新推理时换一个新输出目录。

## 已保存材料

`reference-run/` 是旧版 `rir_nmse`/`rir_corr`/`rt60_mae` 报告与汇总，
`fixture/cases/` 还包含后续 NPM 与双耳指标链路的部分报告。两组材料的引擎版本与
metric 定义不同；不能把已有报告视为上述命令新生成的完整复现证据。素材来源、
选样和文件哈希见 [fixture/provenance.json](fixture/provenance.json) 与
[fixture/sha256.json](fixture/sha256.json)。

2026-10-19 的真实 20 条运行报告及模型环境见 [harness-run/README.md](harness-run/README.md)。
在可导入 NumPy 和 SoundFile 的 Python 环境里运行
`python example/test_example.py`，可不加载 checkpoint 地复核已保存报告、
逐条样本身份和 MCP 握手；这一步不重新执行 20 条模型推理。
