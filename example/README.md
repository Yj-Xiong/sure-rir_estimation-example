# 运行这个 RIR 样例

这个示例的公开页面使用真实的 Rec-RIR SURE report；真实评分由 SURE Harness 调用已合并的
`sure-evaluation` RIR pipeline 执行。模型输出只能提供 `prediction_rir`，
参考 RIR 只进入评分链路。

页面展示的固定 SNR 评测选择为 10/20/30 dB 三档，每档 20 条：两个 scene
(`scene_0000`、`scene_0096`) 与十个麦克风间距。选择
`single_channel` 时，参考 RIR 只保存 channel 0。NeuBIRE 单通道适配将
channel 0 复制到两个模型输入；Rec-RIR 双通道适配分别推理左右输入后合并。

```bash
python3 /path/to/sure-harness/fixtures/tasks/rir/rir_smoke/prepare_variable_mspacing.py --manifest /path/to/variableMspacingFixedSNR_30scenes_260928/test_manifest.jsonl --prediction-root /path/to/predictions --output /tmp/rir_samples.jsonl --allow-missing-predictions
```

选择并执行 SURE pipeline：

```bash
sure-eval metric describe rir --metric rir_npm --output /tmp/rir_pipeline.json --json
sure-eval metric run --pipeline /tmp/rir_pipeline.json --samples-jsonl /tmp/rir_samples.jsonl --output-dir /tmp/rir_eval --validate-env --json
```

双耳链路要求恰好两个通道；单通道和多通道基础链路都使用 NPM、RT60，
空间链路再附加 IACC、ITD。报告会同时保存 `report.json` 和
`pipeline_description.json`。
