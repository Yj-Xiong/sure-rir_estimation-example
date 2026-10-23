#!/usr/bin/env python3
"""Build the browser data from the six checked-in RIR pipeline reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf


CASE_MAP = {
    "rec_rir_single": ("rec_rir", "monaural", "Rec-RIR", "single_channel"),
    "neubire_v1_single": ("neubire", "monaural", "NeuBIRE", "single_channel"),
    "rec_rir_separate": ("rec_rir", "binaural", "Rec-RIR", "binaural"),
    "neubire_v1_native": ("neubire", "binaural", "NeuBIRE", "binaural"),
    "rec_rir_four_channel": ("rec_rir", "four_channel", "Rec-RIR", "four_channel"),
    "neubire_v1_four_channel": ("neubire", "four_channel", "NeuBIRE", "four_channel"),
}
DISPLAY_TAPS = 180
SAMPLE_RATE = 16000


def display_trace(reference: np.ndarray, estimate: np.ndarray) -> tuple[list[list[float]], list[list[float]]]:
    anchor = max(0, int(np.argmax(np.abs(reference[:, 0]))) - int(round(SAMPLE_RATE * 0.0025)))
    ref = reference[:, anchor : anchor + SAMPLE_RATE]
    pred = estimate[:, anchor : anchor + SAMPLE_RATE]
    length = min(ref.shape[1], pred.shape[1])
    ref, pred = ref[:, :length], pred[:, :length]
    x_old = np.linspace(0.0, 1.0, max(length, 1))
    x_new = np.linspace(0.0, 1.0, DISPLAY_TAPS)
    refs, preds = [], []
    for channel in range(ref.shape[0]):
        ref_ch = ref[channel] / max(float(np.max(np.abs(ref[channel]))), 1e-12)
        pred_ch = pred[channel] / max(float(np.max(np.abs(pred[channel]))), 1e-12)
        refs.append(np.interp(x_new, x_old, ref_ch).round(8).tolist())
        preds.append(np.interp(x_new, x_old, pred_ch).round(8).tolist())
    return refs, preds


def report_scores(report: dict) -> tuple[list[str], dict[str, dict[str, float]], dict[str, float]]:
    metric_names, per_metric, means = [], {}, {}
    for node in report.get("pipeline_trace", []):
        result = node.get("details", {}).get("result")
        if not result:
            continue
        name = result["metric_name"]
        metric_names.append(name)
        per_metric[name] = {str(row["sample_id"]): float(row["score"]) for row in result["per_sample"]}
        means[name] = float(result["score"])
    return metric_names, per_metric, means


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", nargs="*", choices=tuple(CASE_MAP), default=list(CASE_MAP))
    args = parser.parse_args()
    cases, sample_count = {}, None
    for case_id in args.cases:
        model, branch, model_label, branch_label = CASE_MAP[case_id]
        root = args.run / model / branch
        samples = [json.loads(line) for line in (root / "samples.jsonl").read_text(encoding="utf-8").splitlines()]
        report = json.loads((root / "scoring" / "evaluation" / "report.json").read_text(encoding="utf-8"))
        metric_names, per_metric, means = report_scores(report)
        rendered = []
        for row in samples:
            reference, _ = sf.read(row["reference_rir"], always_2d=True, dtype="float64")
            estimate, _ = sf.read(row["prediction_rir"], always_2d=True, dtype="float64")
            refs, preds = display_trace(reference.T, estimate.T)
            spacing_cm = int(round(float(row["metadata"]["adjacent_spacing_m"]) * 100))
            rendered.append({
                "sample_id": row["sample_id"], "scene_id": row["sample_id"],
                "spacing_cm": spacing_cm, "snr_db": int(row["metadata"]["snr_db"]),
                "scores": {name: per_metric[name][row["sample_id"]] for name in metric_names},
                "reference_waveforms": refs, "estimate_waveforms": preds,
                "reference_metrics": {}, "prediction_metrics": {},
            })
        sample_count = len(rendered) if sample_count is None else sample_count
        cases[case_id] = {
            "status": "actual_sure_report", "model": model_label, "branch": branch_label,
            "channel_layout": "mono" if branch == "monaural" else ("binaural_lr" if branch == "binaural" else "multi_channel"),
            "pipeline_id": report["pipeline_id"], "metrics": metric_names, "means": means,
            "samples": rendered,
        }
    payload = {
        "schema": "sure.rir.demo.results.v4", "status": "actual_sure_reports",
        "source": "four_mic_fixed_v2 test manifest: SNR 10/20/30 dB, 10 spacings, 60 rows",
        "sample_count": sample_count, "cases": cases, "not_run": [],
        "inference_provenance": {"models": ["Rec-RIR", "NeuBIRE"], "raw_run": str(args.run), "sample_rate_hz": SAMPLE_RATE},
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "cases": len(cases), "samples_per_case": sample_count}, indent=2))


if __name__ == "__main__":
    main()
