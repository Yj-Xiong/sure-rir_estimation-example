#!/usr/bin/env python3
"""Run the ISO 3382 EDT/JND routes on synthetic 1/2/4-channel RIRs."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np


ISO_METRICS = (
    "rir_edt_m_mae",
    "rir_edt_broadband_mae",
    "rir_edt_jnd_mae",
    "rir_c80_jnd_mae",
    "rir_d50_jnd_mae",
    "rir_ts_jnd_mae",
)
JND_METRICS = ("rir_edt_jnd_mae", "rir_c80_jnd_mae", "rir_d50_jnd_mae", "rir_ts_jnd_mae")
BASE_METRICS = ("rir_npm", "rt30_mae", "rt60_mae", "rir_drr_mae", "rir_c50_mae", "rir_c80_mae", "rir_edc_mae")
SPATIAL_METRICS = ("rir_itd_mae", "rir_ild_mae", "rir_ipd_mae", "rir_doa_mae")


def write_pair(root: Path, channels: int) -> Path:
    length = 16384
    t = np.arange(length - 32, dtype=np.float64)
    tail = np.exp(-t / 7000.0)
    tone = np.sin(2.0 * np.pi * 500.0 * t / 16000.0) * np.exp(-t / 12000.0)
    reference = np.zeros((length, channels), dtype=np.float64)
    prediction = np.zeros_like(reference)
    for channel in range(channels):
        scale = 1.0 - channel * 0.05
        reference[32, channel] = scale
        reference[32:, channel] += (0.1 + channel * 0.005) * tail + 0.02 * tone
        prediction[32, channel] = scale * 0.98
        prediction[32:, channel] += (0.095 + channel * 0.005) * tail + 0.018 * tone
    ref_path = root / f"reference_{channels}ch.npy"
    pred_path = root / f"prediction_{channels}ch.npy"
    np.save(ref_path, reference)
    np.save(pred_path, prediction)
    rows = [{
        "sample_id": f"minimal-{channels}ch",
        "prediction_rir": pred_path.name,
        "reference_rir": ref_path.name,
        "sample_rate": 16000,
        "channel_layout": "mono" if channels == 1 else "binaural_lr" if channels == 2 else "multi_channel",
        "metadata": {"microphone_spacing_m": 0.08},
    }]
    manifest = root / f"samples_{channels}ch.jsonl"
    manifest.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return manifest


def run_case(sure_eval: str, root: Path, channels: int) -> dict:
    manifest = write_pair(root, channels)
    metrics = BASE_METRICS + ISO_METRICS + (() if channels == 1 else SPATIAL_METRICS)
    pipeline = root / f"pipeline_{channels}ch.json"
    output = root / f"report_{channels}ch"
    subprocess.run(
        [sure_eval, "metric", "describe", "rir", "--metrics", ",".join(metrics), "--output", str(pipeline), "--json"],
        check=True,
        text=True,
        capture_output=True,
    )
    subprocess.run(
        [sure_eval, "metric", "run", "--pipeline", str(pipeline), "--samples-jsonl", str(manifest), "--output-dir", str(output), "--json"],
        check=True,
        text=True,
        capture_output=True,
    )
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    results = report["details"]["results"]
    missing = sorted(set(metrics) - set(results))
    if missing:
        raise RuntimeError(f"{channels}-channel report is missing metrics: {missing}")
    for metric in JND_METRICS:
        if "within_one_jnd_percent" not in results[metric]:
            raise RuntimeError(f"{metric} has no metric-level JND pass rate")
    return {"channels": channels, "pipeline_id": report["pipeline_id"], "metrics": list(results)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sure-eval", required=True, help="path to the sure-eval CLI from the ISO metric branch")
    parser.add_argument("--output", type=Path, default=Path(".sure-rir-iso3382-minimal"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    reports = [run_case(args.sure_eval, args.output, channels) for channels in (1, 2, 4)]
    (args.output / "summary.json").write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
