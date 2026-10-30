#!/usr/bin/env bash
set -euo pipefail

: "${EXAMPLE_ROOT:?set EXAMPLE_ROOT}"
: "${RECBIR_ROOT:?set RECBIR_ROOT}"
: "${LEGACY_RUN:?set LEGACY_RUN}"
: "${FOUR_RUN:?set FOUR_RUN}"
: "${SCORING_PYTHON:?set SCORING_PYTHON}"
: "${SURE_EVAL:?set SURE_EVAL}"
: "${OUTPUT_ROOT:?set OUTPUT_ROOT}"

mkdir -p "$OUTPUT_ROOT"
"$SCORING_PYTHON" "$EXAMPLE_ROOT/scripts/prepare_four_scoring.py" --run "$FOUR_RUN"
"$SCORING_PYTHON" "$EXAMPLE_ROOT/scripts/prepare_legacy_supplemental.py" \
    --run "$LEGACY_RUN" --output "$OUTPUT_ROOT/legacy_sure"

base=rir_npm,rt30_mae,rt60_mae,rir_drr_mae,rir_c50_mae,rir_c80_mae,rir_edc_mae,rir_edt_m_mae,rir_edt_broadband_mae,rir_edt_jnd_mae,rir_c80_jnd_mae,rir_d50_jnd_mae,rir_ts_jnd_mae
multi="$base,rir_itd_mae,rir_ild_mae,rir_ipd_mae,rir_doa_mae"
for model in rec_rir neubire; do
    for mode in monaural binaural; do
        case_dir="$OUTPUT_ROOT/legacy_sure/$model/$mode"
        metrics=rt30_mae,rir_c80_mae,rir_edt_m_mae,rir_edt_broadband_mae,rir_edt_jnd_mae,rir_c80_jnd_mae,rir_d50_jnd_mae,rir_ts_jnd_mae
        if [[ "$mode" == binaural ]]; then
            metrics="$metrics,rir_doa_mae"
        fi
        mkdir -p "$case_dir/evaluation"
        "$SURE_EVAL" metric describe rir --metrics "$metrics" \
            --output "$case_dir/pipeline.json" --json
        "$SURE_EVAL" metric run --pipeline "$case_dir/pipeline.json" \
            --samples-jsonl "$case_dir/samples.jsonl" \
            --output-dir "$case_dir/evaluation" --json
    done
done
for model in rec_rir neubire; do
    case_dir="$FOUR_RUN/$model/four_channel"
    mkdir -p "$case_dir/scoring/evaluation"
    "$SURE_EVAL" metric describe rir --metrics "$multi" \
        --output "$case_dir/scoring/pipeline.json" --json
    "$SURE_EVAL" metric run --pipeline "$case_dir/scoring/pipeline.json" \
        --samples-jsonl "$case_dir/scoring/samples.jsonl" \
        --output-dir "$case_dir/scoring/evaluation" --json
done

PYTHONPATH="${SCORING_EXTRA_PYTHONPATH:+$SCORING_EXTRA_PYTHONPATH:}$RECBIR_ROOT:$RECBIR_ROOT/../fins-main${PYTHONPATH:+:$PYTHONPATH}" \
    "$SCORING_PYTHON" "$EXAMPLE_ROOT/scripts/build_legacy_demo_results.py" \
    --run "$LEGACY_RUN" --supplemental-root "$OUTPUT_ROOT/legacy_sure" \
    --output "$OUTPUT_ROOT/legacy_results.json"
"$SCORING_PYTHON" "$EXAMPLE_ROOT/scripts/build_demo_results_from_reports.py" \
    --run "$FOUR_RUN" --cases rec_rir_four_channel neubire_v1_four_channel \
    --output "$OUTPUT_ROOT/four_channel_results.json"
"$SCORING_PYTHON" "$EXAMPLE_ROOT/scripts/assemble_demo_results.py" \
    --legacy "$OUTPUT_ROOT/legacy_results.json" \
    --four-channel "$OUTPUT_ROOT/four_channel_results.json" \
    --output "$OUTPUT_ROOT/results.json"
PYTHONPATH="${SCORING_EXTRA_PYTHONPATH:+$SCORING_EXTRA_PYTHONPATH:}${PYTHONPATH:-}" \
    "$SCORING_PYTHON" "$EXAMPLE_ROOT/scripts/compute_frequency_error.py" \
    --results "$OUTPUT_ROOT/results.json" --output "$OUTPUT_ROOT/frequency_error.json" \
    --legacy-run "$LEGACY_RUN" --four-channel-run "$FOUR_RUN"
"$SCORING_PYTHON" "$EXAMPLE_ROOT/scripts/check_reproduced_results.py" \
    --results "$OUTPUT_ROOT/results.json" \
    --frequency "$OUTPUT_ROOT/frequency_error.json" \
    --legacy-selection "$EXAMPLE_ROOT/data/legacy_demo_selection.jsonl" \
    --four-selection "$EXAMPLE_ROOT/data/four_mic_demo_selection.json"

printf 'Complete page reproduction: %s\n' "$OUTPUT_ROOT"
