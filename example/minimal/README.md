# RIR 最小指标样例

merge 核查使用三类小样例覆盖全部 RIR 评测指标：

| 样例 | 通道 | 指标 |
| --- | ---: | --- |
| `monaural` | 1 | NPM、RT30、RT60、DRR、C50、C80、EDC |
| `binaural` | 2 | 上述 acoustic 指标 + IACC、ITD、ILD、IPD |
| `four_channel` | 4 | 上述 acoustic 指标 + ITD、ILD、IPD、DOA |

四通道路径使用 `chN` 相对 `ch0` 的空间指标。双通道模型可以分两次推理，
再把两次结果合并为四通道输出；IACC 只在 `binaural` 样例中运行。

完整 pipeline ID、输入 contract 和报告字段见评测引擎的
`docs/tasks/rir.md`。运行引擎测试：

```bash
PYTHONPATH=src python -m pytest -q tests/test_rir_task.py
```

测试 `test_rir_minimal_examples_cover_every_registered_metric` 会生成短时
合成 RIR，执行三类样例并断言指标集合覆盖全部注册指标。
