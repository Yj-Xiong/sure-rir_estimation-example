#!/usr/bin/env bash
set -euo pipefail

: "${EXAMPLE_ROOT:?set EXAMPLE_ROOT}"
: "${RECBIR_ROOT:?set RECBIR_ROOT}"
: "${MODEL_PYTHON:?set MODEL_PYTHON}"
: "${FOUR_RUN:?set FOUR_RUN}"
model_extra=${MODEL_EXTRA_PYTHONPATH:-}

selection="$EXAMPLE_ROOT/data/four_mic_demo_selection.json"
test -f "$selection"
test -f "$RECBIR_ROOT/scripts/run_demo_recrir_neubire_three_cases.py"
test ! -e "$FOUR_RUN"

job="rir_four_channel_60_$(date +%Y%m%d_%H%M%S)"
log="$RECBIR_ROOT/NeuSIRI/logs/demo/$job.JOB.log"
record="$RECBIR_ROOT/NeuSIRI/logs/demo/$job.submit.log"
mkdir -p "$(dirname "$log")"
vc submit --nopassenv \
    --image docker.v2.aispeech.com/hpc/ai_on_device_base-nsp:1.1.1 \
    --partition pdgpu-4090 --gpu-per-task 1 --mem-per-task 32G --cpu-per-task 8 \
    --project neusiri --job "$job" JOB=1:1 "$log" \
    --cmd "cd '$RECBIR_ROOT' && export PYTHONPATH='${model_extra:+$model_extra:}$RECBIR_ROOT:$RECBIR_ROOT/independent_use':\${PYTHONPATH:-} && '$MODEL_PYTHON' scripts/run_demo_recrir_neubire_three_cases.py --selection '$selection' --output '$FOUR_RUN' --device cuda:0 > '$log' 2>&1" \
    2>&1 | tee "$record"
printf 'queue=pdgpu-4090 device=4090 project=neusiri job=%s log=%s output=%s submission=%s\n' \
    "$job" "$log" "$FOUR_RUN" "$record"
