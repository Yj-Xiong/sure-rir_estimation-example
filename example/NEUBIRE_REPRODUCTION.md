# NeuBIRE RIR reproduction

This guide describes the NeuBIRE direct-RIR inference used by the four-channel
branch in the [demo](https://yj-xiong.github.io/sure-rir_estimation-example/).
The complete six-branch page reproduction, including monaural and binaural
Rec-RIR/NeuBIRE runs, is in [`README.md`](README.md).

The checkpoint, NeuBIRE workspace, and source test audio are not distributed
here. Reproduction requires access to the matching `Rec-BIR` workspace and its
`NeuSIRI/data/four_mic_fixed_v2` dataset. The current inference script also
runs Rec-RIR as the comparison baseline, so its config and checkpoint must be
available. The [Rec-RIR implementation](https://github.com/Audio-WestlakeU/Rec-RIR)
and [paper](https://arxiv.org/abs/2509.15628) are public.

The four-channel selection contains 60 rows: SNR 10, 20, and 30 dB; ten
adjacent microphone spacings from 0.02 to 0.20 m; and two rows per SNR-spacing
pair. The list is [`../data/four_mic_demo_selection.json`](../data/four_mic_demo_selection.json).
The RIR task evaluates saved RIR estimates directly; it does not run MINT
inverse filtering, speech reconstruction, or speech-quality scoring.

## 1. Set the workspace paths

Run inference in the project environment that provides `torch`, `torchaudio`,
`soundfile`, `toml`, the Rec-BIR model modules, and the NeuBIRE checkpoint.
Set these paths on a cluster-accessible shared filesystem:

```bash
export RECBIR_ROOT="/path/to/Rec-BIR"
export EXAMPLE_ROOT="/path/to/sure-rir_estimation-example"
export MODEL_PYTHON="/path/to/python-with-neubire-dependencies"
export RUN_ROOT="$RECBIR_ROOT/NeuSIRI/data/four_mic_demo_runs/neubire_reproduction"

NEUBIRE_DIR="$RECBIR_ROOT/eval_results/variable_mspacing_fixedsnr_delta01_260922_bestnpm1_260929/checkpoint_snapshot"
NEUBIRE_CONFIG="$NEUBIRE_DIR/config.toml"
NEUBIRE_CHECKPOINT="$NEUBIRE_DIR/best_npm_1.tar"

test -f "$RECBIR_ROOT/scripts/run_demo_recrir_neubire_three_cases.py"
test -f "$EXAMPLE_ROOT/data/four_mic_demo_selection.json"
test -f "$NEUBIRE_CONFIG"
test -f "$NEUBIRE_CHECKPOINT"
sha256sum "$NEUBIRE_CHECKPOINT"
```

The checkpoint SHA-256 for this result is
`6ce20499d9c470336785d68549052b481c1d204f46c2b78f4164a66cc6b1ffd5`.
The inference script loads this config and checkpoint directly. Keep the
selection JSON and `NeuSIRI` dataset-relative file layout unchanged because
the script resolves the listed mixture and RIR paths from `RECBIR_ROOT`.
The Rec-RIR side of the comparison also needs its config at
`../fins-main/configs/recrir/first_channel/original_recrir_1ch_2chrender_ch0_dataset30mm_noise92_full50_bs2x2.toml`
and checkpoint at
`$RECBIR_ROOT/eval_results/unified_10testsets_recrir_1ch_baselines_with_iacc_260805/checkpoint_snapshots/official_recrir_epoch35.tar`.
The Rec-RIR config is at
`$RECBIR_ROOT/../fins-main/configs/recrir/first_channel/original_recrir_1ch_2chrender_ch0_dataset30mm_noise92_full50_bs2x2.toml`.
The runner currently resolves these from the sibling `fins-main` and `Rec-BIR`
workspace layout; update its path constants if your checkout is arranged
differently. Use a new `RUN_ROOT` for each attempt so incomplete outputs are
not mistaken for a finished run.

## 2. Submit the inference run

Inference processes six model/channel combinations over 60 samples. Submit it
to the GPU queue; do not launch it on a debug machine. The command below uses
the 4090 partition and writes the job log and model outputs under `RECBIR_ROOT`.

```bash
JOB="rir_demo_neubire_reproduction_$(date +%Y%m%d_%H%M%S)"
LOG="$RECBIR_ROOT/NeuSIRI/logs/demo/${JOB}.JOB.log"
mkdir -p "$RECBIR_ROOT/NeuSIRI/logs/demo" "$(dirname "$RUN_ROOT")"

vc submit --nopassenv --enable-rdma 1 \
  --image docker.v2.aispeech.com/hpc/ai_on_device_base-nsp:1.1.1 \
  --partition pdgpu-4090 \
  --gpu-per-task 1 --mem-per-task 32G --cpu-per-task 8 \
  --project neusiri --job "$JOB" \
  --env "HOME=$HOME" \
  JOB=1:1 "$LOG" \
  --cmd "cd '$RECBIR_ROOT' && export PYTHONPATH='$RECBIR_ROOT:$RECBIR_ROOT/independent_use':\${PYTHONPATH:-} && '$MODEL_PYTHON' scripts/run_demo_recrir_neubire_three_cases.py --selection '$EXAMPLE_ROOT/data/four_mic_demo_selection.json' --output '$RUN_ROOT' --device cuda:0"
```

The run script is `Rec-BIR/scripts/run_demo_recrir_neubire_three_cases.py`.
For NeuBIRE it uses the first two mixture channels for the binaural estimate.
For the four-channel estimate it runs channels 0/1 and 2/3 in two passes and
reuses the first pass's channel-0 crop anchor. The PIM sine sweep and inverse
filter convert the model CTF output to time-domain RIRs. The script writes a
`samples.jsonl`, prediction WAVs, and reference WAVs under each model and
channel-mode directory in `RUN_ROOT`.

Check the job state with the cluster job tools and wait for a successful
completion before scoring. The output directories are:

```text
$RUN_ROOT/rec_rir/monaural/
$RUN_ROOT/rec_rir/binaural/
$RUN_ROOT/rec_rir/four_channel/
$RUN_ROOT/neubire/monaural/
$RUN_ROOT/neubire/binaural/
$RUN_ROOT/neubire/four_channel/
```

Each `samples.jsonl` should contain 60 rows. Four-channel prediction WAVs must
have four channels at 16 kHz.

## 3. Prepare one-second scoring inputs

The SURE RIR metrics use the first 16,000 samples at 16 kHz. The preparation
script pads shorter arrays and truncates longer arrays to this window, while
preserving sample IDs and metadata:

```bash
"$MODEL_PYTHON" "$RECBIR_ROOT/scripts/prepare_recrir_neubire_demo_scoring.py" \
  --run "$RUN_ROOT"
```

The script creates `scoring/samples.jsonl` for every model and channel mode.
Each row contains `prediction_rir`, `reference_rir`, `sample_rate`,
`channel_layout`, and source metadata used by the RIR metrics.

## 4. Install the pinned SURE evaluation engine

The reports use the RIR task implementation in the personal SURE evaluation
fork. This reproduction guide pins the branch commit used by the Harness
runtime; the task documents atomic single-metric routes as well as bundles.

```bash
SURE_EVAL_ROOT="$PWD/sure-evaluation"
git clone --branch feat/rir-estimation-openbench-v2 \
  https://github.com/Yj-Xiong/sure-evaluation.git "$SURE_EVAL_ROOT"
git -C "$SURE_EVAL_ROOT" checkout 39b4146
python3 -m venv "$SURE_EVAL_ROOT/.venv-rir"
"$SURE_EVAL_ROOT/.venv-rir/bin/python" -m pip install -e "${SURE_EVAL_ROOT}[audio]"
SURE_EVAL="$SURE_EVAL_ROOT/.venv-rir/bin/sure-eval"
"$SURE_EVAL" --version
```

## 5. Score each model and channel mode

The base bundle reports NPM, RT30, RT60, DRR, C50, C80, and EDC. The binaural
bundle adds the three IACC windows and channel-0-relative ITD, ILD, IPD, and
DOA. The four-channel bundle adds the same channel-0-relative spatial
metrics, without IACC because IACC requires exactly two channels.

```bash
BASE_METRICS="rir_npm,rt30_mae,rt60_mae,rir_drr_mae,rir_c50_mae,rir_c80_mae,rir_edc_mae"
BINAURAL_METRICS="$BASE_METRICS,rir_iacc_full_mae,rir_iacc_early_mae,rir_iacc_late_mae,rir_itd_mae,rir_ild_mae,rir_ipd_mae,rir_doa_mae"
MULTICHANNEL_METRICS="$BASE_METRICS,rir_itd_mae,rir_ild_mae,rir_ipd_mae,rir_doa_mae"

score_case() {
  local model="$1" mode="$2" metrics="$3"
  local case_dir="$RUN_ROOT/$model/$mode"
  local pipeline="$case_dir/scoring/pipeline.json"
  mkdir -p "$case_dir/scoring/evaluation"
  "$SURE_EVAL" metric describe rir --metrics "$metrics" \
    --output "$pipeline" --json
  "$SURE_EVAL" metric run --pipeline "$pipeline" \
    --samples-jsonl "$case_dir/scoring/samples.jsonl" \
    --output-dir "$case_dir/scoring/evaluation" --json
}

for model in rec_rir neubire; do
  score_case "$model" monaural "$BASE_METRICS"
  score_case "$model" binaural "$BINAURAL_METRICS"
  score_case "$model" four_channel "$MULTICHANNEL_METRICS"
done
```

Reports are written to each case's `scoring/evaluation/report.json`. Confirm
that every report has 60 per-sample results for each requested metric. In
multichannel reports, ITD, ILD, IPD, and DOA include one pair for each
`chN` relative to `ch0`; the aggregate score is the mean over those pairs.

The complete page assembly is described in [`README.md`](README.md): build the
fresh legacy report, build the fresh four-channel report, then run
`scripts/assemble_demo_results.py` to require all six branches and 60 rows per
branch before publishing `data/results.json`.

## 6. Compare with the browser data

The page shows normalized waveform traces for inspection and metric values
from the scoring reports. It does not derive the reported metric values from
the displayed traces. The fixed four-channel selection is shared between the
NeuBIRE and Rec-RIR estimates, and the demo page records its sample list and
checkpoint hash in [`../data/provenance.json`](../data/provenance.json).

The test manifest, raw mixtures, reference arrays, checkpoints, and full
prediction WAVs stay in the model workspace. They are not copied into the
public example repository.
