# Reproduce the complete RIR example

This is the end-to-end reproduction entry point for the six model/output scenarios shown on
the [GitHub Pages demo](https://yj-xiong.github.io/sure-rir_estimation-example/).
It regenerates 60 samples for each scenario:

| Scenario | Inference | Reported metrics |
| --- | --- | --- |
| Rec-RIR monaural | channel 0 | normalized waveform MAE, NPM, RT60, DRR, C50, EDC |
| NeuBIRE monaural | score channel 0 from the native two-channel estimate | same acoustic metrics |
| Rec-RIR binaural | independent channel 0/1 passes | acoustic metrics + IACC full/early/late, ITD, ILD, IPD |
| NeuBIRE binaural | native two-channel pass | acoustic metrics + IACC full/early/late, ITD, ILD, IPD |
| Rec-RIR four-channel | four paths | acoustic metrics + channel-0-relative ITD, ILD, IPD, DOA |
| NeuBIRE four-channel | two two-channel passes | acoustic metrics + channel-0-relative ITD, ILD, IPD, DOA |

The four monaural/binaural scenarios use the fixed `VariableMSpacingFixedSNR` selection;
the last two use the four-microphone selection. Both selections are generated
from manifests rather than copied from `data/results.json`.

Model checkpoints, input audio, reference RIRs, and generated WAV files stay in
the local `Rec-BIR` workspace. Only the bounded JSON report is copied into the
example repository after validation.

## 1. Get the sources

```bash
git clone https://github.com/Yj-Xiong/sure-rir_estimation-example.git
git clone https://github.com/Yj-Xiong/sure-evaluation.git sure-evaluation
git -C sure-evaluation checkout 39b4146
export MODEL_PYTHON="/absolute/path/to/python-with-recbir-dependencies"
"$MODEL_PYTHON" -m venv sure-evaluation/.venv
sure-evaluation/.venv/bin/python -m pip install --upgrade pip setuptools wheel
sure-evaluation/.venv/bin/python -m pip install -e 'sure-evaluation[audio]'

export EXAMPLE_ROOT="$PWD/sure-rir_estimation-example"
export RECBIR_ROOT="/absolute/path/to/Rec-BIR"
export DATA_ROOT="/absolute/path/to/variableMspacingFixedSNR_30scenes_260928"
export SCORING_PYTHON="/absolute/path/to/python-with-recbir-and-fins-metric-dependencies"
export SURE_EVAL="$PWD/sure-evaluation/.venv/bin/sure-eval"
```

Use the same `Rec-BIR` checkout for both model families. The public Rec-RIR
source is [Audio-WestlakeU/Rec-RIR](https://github.com/Audio-WestlakeU/Rec-RIR);
the NeuBIRE checkpoint and implementation are recorded in
[`../data/provenance.json`](../data/provenance.json).
The model environment needs the Rec-BIR inference dependencies. The scoring
environment also needs NumPy, SciPy, SoundFile, PyTorch, and the local FiNS
metric module. The saved run was checked with NumPy 1.26.4 and SciPy 1.11.4.
Check `import scipy.special` in both interpreters before submitting jobs. If
using an existing environment with an incompatible SciPy installation, set
`MODEL_EXTRA_PYTHONPATH` and `SCORING_EXTRA_PYTHONPATH` to a directory containing
the compatible SciPy wheel; the submission scripts pass these paths to the
cluster workers.

## 2. Select the exact 60-row sets

The legacy selection is two scenes (`scene_0000`, `scene_0025`) at ten spacings
and SNR 10/20/30 dB, two rows per spacing/SNR combination. The four-microphone
selection is ten adjacent spacings from 0.02 to 0.20 m, two rows per spacing/SNR
combination.

```bash
python3 "$EXAMPLE_ROOT/scripts/select_legacy_demo.py" \
  --dataset-root "$DATA_ROOT" \
  --output "$EXAMPLE_ROOT/data/legacy_demo_selection.jsonl"

python3 "$EXAMPLE_ROOT/scripts/select_four_mic_demo.py" \
  --manifest "$RECBIR_ROOT/NeuSIRI/data/four_mic_fixed_v2/test/test_manifest.jsonl" \
  --output "$EXAMPLE_ROOT/data/four_mic_demo_selection.json"
```

Both commands must report 60 selected rows. The generated legacy JSONL must
have the same sample IDs as the four legacy scenarios in the final report.

## 3. Run legacy monaural and binaural inference

Run this command through the cluster queue. It produces four directories under
`$LEGACY_RUN`: Rec-RIR/NeuBIRE x monaural/binaural. It does not use the saved
page data as input.

```bash
export LEGACY_RUN="$RECBIR_ROOT/NeuSIRI/data/rir_demo_runs/legacy_60"
export RECRIR_CONFIG="$RECBIR_ROOT/../fins-main/configs/recrir/first_channel/original_recrir_1ch_2chrender_ch0_dataset30mm_noise92_full50_bs2x2.toml"
export RECRIR_CHECKPOINT="$RECBIR_ROOT/eval_results/unified_10testsets_recrir_1ch_baselines_with_iacc_260805/checkpoint_snapshots/official_recrir_epoch35.tar"
export NEUBIRE_DIR="$RECBIR_ROOT/eval_results/variable_mspacing_fixedsnr_delta01_260922_bestnpm1_260929/checkpoint_snapshot"
export NEUBIRE_CONFIG="$NEUBIRE_DIR/config.toml"
export NEUBIRE_CHECKPOINT="$NEUBIRE_DIR/best_npm_1.tar"
sha256sum "$NEUBIRE_CHECKPOINT"

JOB=rir_legacy_60_$(date +%Y%m%d_%H%M%S)
LOG="$RECBIR_ROOT/NeuSIRI/logs/demo/$JOB.JOB.log"
mkdir -p "$(dirname "$LOG")"
vc submit --nopassenv --enable-rdma 1 \
  --image docker.v2.aispeech.com/hpc/ai_on_device_base-nsp:1.1.1 \
  --partition pdgpu-4090 --gpu-per-task 1 --mem-per-task 32G --cpu-per-task 8 \
  --project neusiri --job "$JOB" JOB=1:1 "$LOG" \
  --cmd "cd '$RECBIR_ROOT' && export PYTHONPATH='$RECBIR_ROOT':\${PYTHONPATH:-} && '$MODEL_PYTHON' '$EXAMPLE_ROOT/scripts/run_legacy_demo_inference.py' --selection '$EXAMPLE_ROOT/data/legacy_demo_selection.jsonl' --output '$LEGACY_RUN' --recrir-config '$RECRIR_CONFIG' --recrir-checkpoint '$RECRIR_CHECKPOINT' --neubire-config '$NEUBIRE_CONFIG' --neubire-checkpoint '$NEUBIRE_CHECKPOINT' --device cuda:0"
```

The output must contain four `samples.jsonl` files with 60 rows each. The
NeuBIRE monaural uses channel 0 from the same native pair as its binaural
scenario; the Rec-RIR binaural path runs the one-channel model independently on
channels 0 and 1. This follows the samples currently published on the page.

## 4. Run four-channel inference

Use the existing direct-RIR runner for the two four-channel scenarios:

```bash
export FOUR_RUN="$RECBIR_ROOT/NeuSIRI/data/rir_demo_runs/four_channel_60"
JOB=rir_four_channel_60_$(date +%Y%m%d_%H%M%S)
LOG="$RECBIR_ROOT/NeuSIRI/logs/demo/$JOB.JOB.log"
mkdir -p "$(dirname "$LOG")"
vc submit --nopassenv --enable-rdma 1 \
  --image docker.v2.aispeech.com/hpc/ai_on_device_base-nsp:1.1.1 \
  --partition pdgpu-4090 --gpu-per-task 1 --mem-per-task 32G --cpu-per-task 8 \
  --project neusiri --job "$JOB" JOB=1:1 "$LOG" \
  --cmd "cd '$RECBIR_ROOT' && export PYTHONPATH='$RECBIR_ROOT':\${PYTHONPATH:-} && '$MODEL_PYTHON' scripts/run_demo_recrir_neubire_three_cases.py --selection '$EXAMPLE_ROOT/data/four_mic_demo_selection.json' --output '$FOUR_RUN' --device cuda:0"
```

This run writes the six model/channel directories. Use only the two
`four_channel` directories for the page's final four-channel scenarios. The
other four outputs are useful for checking the shared inference implementation.

## 5. Score, assemble, and verify on the CPU queue

The legacy report uses the one-second Rec-BIR/FiNS acoustic and spatial
protocol. The four-channel report uses the pinned SURE RIR bundle. The scoring
script writes into a separate output directory and checks all six scenario IDs,
60 samples per scenario, metric means, waveform shapes, and native-WAV frequency
analysis before it exits successfully.
Legacy scoring first matches each estimate channel's peak amplitude to
its reference channel, as in the published protocol. Reference RIRs remain
outside model inputs; this calibration happens after inference.

```bash
export OUTPUT_ROOT="$RECBIR_ROOT/NeuSIRI/data/rir_demo_runs/page_report_60"
JOB=rir_page_report_$(date +%Y%m%d_%H%M%S)
LOG="$RECBIR_ROOT/NeuSIRI/logs/demo/$JOB.JOB.log"
mkdir -p "$(dirname "$LOG")"
vc submit --nopassenv \
  --image docker.v2.aispeech.com/hpc/ai_on_device_base-nsp:1.1.1 \
  --partition pdcpu --mem-per-task 32G --cpu-per-task 8 \
  --project neusiri --job "$JOB" JOB=1:1 "$LOG" \
  --cmd "EXAMPLE_ROOT='$EXAMPLE_ROOT' RECBIR_ROOT='$RECBIR_ROOT' LEGACY_RUN='$LEGACY_RUN' FOUR_RUN='$FOUR_RUN' MODEL_PYTHON='$MODEL_PYTHON' SCORING_PYTHON='$SCORING_PYTHON' SURE_EVAL='$SURE_EVAL' OUTPUT_ROOT='$OUTPUT_ROOT' bash '$EXAMPLE_ROOT/example/score_page.sh' > '$LOG' 2>&1"
```

Record the job ID and wait for successful completion. The candidate page files
are `$OUTPUT_ROOT/results.json` and `$OUTPUT_ROOT/frequency_error.json`.
The first four cases carry a `recbir.legacy_rir_1s.*` protocol ID because
their page scores use the historical Rec-BIR/FiNS protocol. The last two carry
the SURE pipeline ID from their report.

## 6. Review the candidate result before publishing

```bash
python3 -m json.tool "$OUTPUT_ROOT/results.json" >/dev/null
python3 -m json.tool "$OUTPUT_ROOT/frequency_error.json" >/dev/null
python3 "$EXAMPLE_ROOT/example/test_example.py"
node --check "$EXAMPLE_ROOT/app.js"
git -C "$EXAMPLE_ROOT" diff --check
```

The checked-in page data combines a fixed-SNR monaural/binaural run with a
four-microphone run. A fresh six-scenario run can differ numerically, so compare
the candidate scores with the published JSON before replacing it:

```bash
python3 "$EXAMPLE_ROOT/scripts/compare_page_results.py" \
  --published "$EXAMPLE_ROOT/data/results.json" \
  --candidate "$OUTPUT_ROOT/results.json"
```

After reviewing the differences, publish the two candidate JSON files
together:

```bash
install -m 644 "$OUTPUT_ROOT/results.json" "$EXAMPLE_ROOT/data/results.json"
install -m 644 "$OUTPUT_ROOT/frequency_error.json" "$EXAMPLE_ROOT/data/frequency_error.json"
git -C "$EXAMPLE_ROOT" diff --check
```

The reference arrays and prediction WAVs remain outside the public repository.

## Harness-only fixture

The separate [`harness-run/`](harness-run/README.md) fixture is a small
20-row MCP contract test. It is useful for Harness CI, but it is not the data
source for the six browser scenarios and is not a substitute for this complete
reproduction flow.
