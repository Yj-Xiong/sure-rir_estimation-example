# RIR 最小指标样例

merge 核查使用三类小样例覆盖全部 RIR 评测指标，包括 ISO 3382 EDT 和 JND 路线：

| 样例 | 通道 | 指标 |
| --- | ---: | --- |
| `monaural` | 1 | acoustic + octave-band/broadband EDT + EDT/C80/D50/Ts JND |
| `binaural` | 2 | 上述指标 + IACC full/early/late、ITD、ILD、IPD、DOA |
| `four_channel` | 4 | 上述指标 + ITD、ILD、IPD、DOA |

ISO 3382 JND 指标在 1、2、4 通道上都逐通道计算并取通道均值；每项指标
单独报告 within-one-JND 通过率。四通道空间路径使用 `chN` 相对 `ch0` 的
指标。双通道模型可以分两次推理，再把两次结果合并为四通道输出；IACC
full/early/late 只在 `binaural` 样例中运行。

完整 pipeline ID、输入 contract 和报告字段见评测引擎的
`docs/tasks/rir.md`。运行引擎测试：

```bash
PYTHONPATH=src python -m pytest -q tests/test_rir_task.py
```

测试 `test_rir_minimal_examples_cover_every_registered_metric` 会生成短时
合成 RIR，执行三类样例并断言指标集合覆盖全部注册指标。

## Reproduce the new ISO routes

After installing the ISO metric branch of `sure-evaluation`, run the same
CLI contract against generated 1/2/4-channel fixtures:

```bash
python3 example/minimal/reproduce_iso3382.py \
  --sure-eval "$PWD/sure-evaluation/.venv/bin/sure-eval"
```

The script executes `metric describe`, `metric run`, and report validation for
each channel count. It checks EDT, broadband EDT, EDT/C80/D50/Ts JND, the base
RIR metrics, and the applicable spatial metrics. Each JND result must contain
its own `within_one_jnd_percent`; IACC is only requested for the two-channel
case. Generated fixtures and reports remain under `.sure-rir-iso3382-minimal/`
and are not part of the repository.
