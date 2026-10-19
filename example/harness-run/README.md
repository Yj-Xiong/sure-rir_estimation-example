# 2026-10-19 Harness 后端运行证据

这一组结果来自 `example/run_example.py` 的 20 条 Rec-RIR channel-0 真实推理。
首次运行完整生成 20 个新 RIR WAV；修复 float WAV 验证与 Evaluation Runtime
调用后，`--resume` 按 `infer-contract.json` 逐条核对预测 SHA-256，再执行
SURE Harness `evaluate_predictions.py --evaluation-backend external` 的三个指标，
最后执行同一锁定引擎的 bundle pipeline。评分没有复用旧报告。

- SURE: `73975931da1353c3b97a422e796612d8b363fe3b`。
- Evaluation engine: `8041b1249c5d0ce39a96c72cab01e49b09cc87e9`。
- Rec-RIR: `6914eea792f0117e39f87510ffbda7cd04dffbbb`，epoch35 checkpoint SHA-256
  `afe36e477f6fb3656d162d906a47da2d40a789634b476564266fc1ba36037478`。
- Harness Runtime: `sure-harness-v1-m3-py311-03393a2780e1`。
- Evaluation Runtime: `sure-evaluation-root-v1-m5-8041b1249c5d-py311-fb2f0b85b36f`。

| 指标 | 20 条均值 |
| --- | ---: |
| `rir_nmse` | 225.1464392939488 |
| `rir_corr` | -0.01816639841539773 |
| `rt60_mae` | 0.6230814872020897 |

报告见 [report.json](report.json)，pipeline 身份与计算节点见
[pipeline_description.json](pipeline_description.json)，模型依赖版本见
[model_environment.json](model_environment.json)。三项 Harness payload 的
`evaluation_backend` 均为 `external`、`num_samples` 均为 20；原始 MCP 日志、
逐条预测 WAV、Harness payload 与桥接 `samples.jsonl` 留在本机忽略目录
`.runtime/full-run-002/`，其中含本机绝对路径，未复制进公开材料。

这组数值与旧 `reference-run/` 不相等；两者不能作为同一预测字节的回归断言。
网页 60 条固定 SNR 数据还使用另一组数据及较新的 NPM 指标。当前公开证据只
覆盖 Rec-RIR 单通道后端链路，不代表其它三个通道分支的新模型推理，也不代表
正式审批或发布。
