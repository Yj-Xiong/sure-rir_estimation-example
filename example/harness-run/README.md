# Rec-RIR Harness 运行结果

20 条 Rec-RIR channel-0 输入经过 `estimate_rir` MCP、SURE Harness RIR
bridge 和 Evaluation Runtime 生成以下报告。模型输出为 16 kHz 单通道 RIR。

| 项目 | 版本或数值 |
| --- | --- |
| SURE | `73975931da1353c3b97a422e796612d8b363fe3b` |
| Evaluation engine | `8041b1249c5d0ce39a96c72cab01e49b09cc87e9` |
| Rec-RIR | `6914eea792f0117e39f87510ffbda7cd04dffbbb` |
| checkpoint SHA-256 | `afe36e477f6fb3656d162d906a47da2d40a789634b476564266fc1ba36037478` |
| Harness Runtime | `sure-harness-v1-m3-py311-03393a2780e1` |
| Evaluation Runtime | `sure-evaluation-root-v1-m5-8041b1249c5d-py311-fb2f0b85b36f` |
| sample count | `20` |

| 指标 | 20 条均值 |
| --- | ---: |
| `rir_nmse` | 225.1464392939488 |
| `rir_corr` | -0.01816639841539773 |
| `rt60_mae` | 0.6230814872020897 |

报告文件：

- [report.json](report.json)
- [pipeline_description.json](pipeline_description.json)
- [model_environment.json](model_environment.json)
- [summary.json](summary.json)

三个 Harness payload 的 `evaluation_backend` 为 `external`，每个指标包含
20 条样本。原始 MCP 日志、预测 WAV、Harness payload 和 bridge 输入清单位于
本地运行目录 `.runtime/full-run-002/`，不包含在仓库中。

网页中的 60 条固定 SNR 数据使用 NPM 和另一组数据；本页报告使用
`rir_nmse`、`rir_corr` 和 `rt60_mae`。
