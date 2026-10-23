#!/usr/bin/env bash
set -euo pipefail

: "${EXAMPLE_ROOT:?set EXAMPLE_ROOT}"
: "${RECBIR_ROOT:?set RECBIR_ROOT}"
: "${MODEL_PYTHON:?set MODEL_PYTHON}"
: "${LEGACY_RUN:?set LEGACY_RUN}"
model_extra=${MODEL_EXTRA_PYTHONPATH:-}
device=${RIR_GPU_DEVICE:-4090}
case "$device" in 4090|v100) ;; *) printf 'unsupported RIR_GPU_DEVICE: %s\n' "$device" >&2; exit 2 ;; esac
partition="pdgpu-$device"

selection="$EXAMPLE_ROOT/data/legacy_demo_selection.jsonl"
recrir_config="$RECBIR_ROOT/../fins-main/configs/recrir/first_channel/original_recrir_1ch_2chrender_ch0_dataset30mm_noise92_full50_bs2x2.toml"
recrir_checkpoint="$RECBIR_ROOT/eval_results/unified_10testsets_recrir_1ch_baselines_with_iacc_260805/checkpoint_snapshots/official_recrir_epoch35.tar"
neubire_dir="$RECBIR_ROOT/eval_results/variable_mspacing_fixedsnr_delta01_260922_bestnpm1_260929/checkpoint_snapshot"
for path in "$selection" "$recrir_config" "$recrir_checkpoint" "$neubire_dir/config.toml" "$neubire_dir/best_npm_1.tar"; do
    test -f "$path"
done
test ! -e "$LEGACY_RUN"

job="rir_legacy_60_$(date +%Y%m%d_%H%M%S)"
log="$RECBIR_ROOT/NeuSIRI/logs/demo/$job.JOB.log"
record="$RECBIR_ROOT/NeuSIRI/logs/demo/$job.submit.log"
mkdir -p "$(dirname "$log")"
vc submit --nopassenv \
    --image docker.v2.aispeech.com/hpc/ai_on_device_base-nsp:1.1.1 \
    --partition "$partition" --gpu-per-task 1 --mem-per-task 32G --cpu-per-task 8 \
    --project neusiri --job "$job" JOB=1:1 "$log" \
    --cmd "cd '$RECBIR_ROOT' && export PYTHONPATH='${model_extra:+$model_extra:}$RECBIR_ROOT:$RECBIR_ROOT/independent_use':\${PYTHONPATH:-} && '$MODEL_PYTHON' '$EXAMPLE_ROOT/scripts/run_legacy_demo_inference.py' --selection '$selection' --output '$LEGACY_RUN' --recrir-config '$recrir_config' --recrir-checkpoint '$recrir_checkpoint' --neubire-config '$neubire_dir/config.toml' --neubire-checkpoint '$neubire_dir/best_npm_1.tar' --device cuda:0 > '$log' 2>&1" \
    2>&1 | tee "$record"
printf 'queue=%s device=%s project=neusiri job=%s log=%s output=%s submission=%s\n' \
    "$partition" "$device" "$job" "$log" "$LEGACY_RUN" "$record"
