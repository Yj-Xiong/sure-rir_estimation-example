#!/usr/bin/env bash
set -euo pipefail

for name in EXAMPLE_ROOT RECBIR_ROOT LEGACY_RUN FOUR_RUN SCORING_PYTHON SURE_EVAL OUTPUT_ROOT; do
    test -n "${!name:-}" || { printf 'set %s\n' "$name" >&2; exit 2; }
done
test -f "$LEGACY_RUN/rec_rir/monaural/samples.jsonl"
test -f "$LEGACY_RUN/neubire/binaural/samples.jsonl"
test -f "$FOUR_RUN/rec_rir/four_channel/samples.jsonl"
test -f "$FOUR_RUN/neubire/four_channel/samples.jsonl"
test ! -e "$OUTPUT_ROOT"
scoring_extra=${SCORING_EXTRA_PYTHONPATH:-}

job="rir_page_report_$(date +%Y%m%d_%H%M%S)"
log="$RECBIR_ROOT/NeuSIRI/logs/demo/$job.JOB.log"
record="$RECBIR_ROOT/NeuSIRI/logs/demo/$job.submit.log"
mkdir -p "$(dirname "$log")"
vc submit --nopassenv \
    --image docker.v2.aispeech.com/hpc/ai_on_device_base-nsp:1.1.1 \
    --partition pdcpu --mem-per-task 32G --cpu-per-task 8 \
    --project neusiri --job "$job" JOB=1:1 "$log" \
    --cmd "EXAMPLE_ROOT='$EXAMPLE_ROOT' RECBIR_ROOT='$RECBIR_ROOT' LEGACY_RUN='$LEGACY_RUN' FOUR_RUN='$FOUR_RUN' SCORING_PYTHON='$SCORING_PYTHON' SURE_EVAL='$SURE_EVAL' OUTPUT_ROOT='$OUTPUT_ROOT' SCORING_EXTRA_PYTHONPATH='$scoring_extra' bash '$EXAMPLE_ROOT/example/score_page.sh' > '$log' 2>&1" \
    2>&1 | tee "$record"
printf 'queue=pdcpu device=cpu project=neusiri job=%s log=%s output=%s submission=%s\n' \
    "$job" "$log" "$OUTPUT_ROOT" "$record"
