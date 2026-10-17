# 运行这个 RIR 样例

这个示例的公开页面使用真实的 Rec-RIR SURE report；真实评分由 SURE Harness 调用已合并的
`sure-evaluation` RIR pipeline 执行。模型输出只能提供 `prediction_rir`，
参考 RIR 只进入评分链路。

VariableMSpacingTest 选择为 10 个麦克风间距、每个间距 2 条样本。选择
`single_channel` 时，参考 RIR 只保存 channel 0。NeuBIRE 单通道适配将
channel 0 复制到两个模型输入；Rec-RIR 双通道适配分别推理左右输入后合并。

```bash
python3 /path/to/sure-harness/fixtures/tasks/rir/rir_smoke/prepare_variable_mspacing.py --manifest /path/to/variableMspacingTestSet/test_manifest.jsonl --prediction-root /path/to/predictions --output /tmp/rir_samples.jsonl --allow-missing-predictions
```

选择并执行 SURE pipeline：

```bash
sure-eval metric describe rir --metric rir_iacc_mae --output /tmp/rir_pipeline.json --json
sure-eval metric run --pipeline /tmp/rir_pipeline.json --samples-jsonl /tmp/rir_samples.jsonl --output-dir /tmp/rir_eval --validate-env --json
```

双耳链路要求恰好两个通道；单通道链路使用 RIR-NMSE、Correlation、RT60、
DRR、C50、C80。报告会同时保存 `report.json` 和 `pipeline_description.json`。
