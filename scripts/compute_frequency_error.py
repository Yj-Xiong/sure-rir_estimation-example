#!/usr/bin/env python3
"""Compute normalized RIR spectral error distributions for the demo."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data/results.json"
OUTPUT = ROOT / "data/frequency_error.json"
BANDS = (
    (125, 250),
    (250, 500),
    (500, 1000),
    (1000, 2000),
    (2000, 4000),
    (4000, 8000),
)
EPSILON = 1e-8


def band_error(reference: list[float], estimate: list[float], sample_rate: int, low: float, high: float) -> float:
    length = min(len(reference), len(estimate))
    if length < 4:
        return float("nan")
    ref = np.asarray(reference[:length], dtype=np.float64)
    pred = np.asarray(estimate[:length], dtype=np.float64)
    ref_spectrum = np.abs(np.fft.rfft(ref))
    pred_spectrum = np.abs(np.fft.rfft(pred))
    frequencies = np.fft.rfftfreq(length, 1.0 / sample_rate)
    selected = (frequencies >= low) & (frequencies < high)
    if not np.any(selected):
        return float("nan")
    ref_db = 20.0 * np.log10(np.maximum(ref_spectrum[selected], EPSILON))
    pred_db = 20.0 * np.log10(np.maximum(pred_spectrum[selected], EPSILON))
    return float(np.mean(np.abs(pred_db - ref_db)))


def distribution(values: list[float]) -> dict[str, float | int]:
    valid = np.asarray([value for value in values if np.isfinite(value)], dtype=np.float64)
    if valid.size == 0:
        return {"mean_db": None, "p25_db": None, "median_db": None, "p75_db": None, "count": 0}
    return {
        "mean_db": float(np.mean(valid)),
        "p25_db": float(np.percentile(valid, 25)),
        "median_db": float(np.percentile(valid, 50)),
        "p75_db": float(np.percentile(valid, 75)),
        "count": int(valid.size),
    }


def main() -> None:
    source = json.loads(RESULTS.read_text(encoding="utf-8"))
    cases = {}
    for case_id, case in source["cases"].items():
        model_bands: dict[str, list[float]] = {str(index): [] for index in range(len(BANDS))}
        for sample in case["samples"]:
            references = sample.get("reference_waveforms") or []
            estimates = sample.get("estimate_waveforms") or []
            for reference, estimate in zip(references, estimates):
                for index, (low, high) in enumerate(BANDS):
                    model_bands[str(index)].append(
                        band_error(reference, estimate, 16000, low, high)
                    )
        cases[case_id] = {
            "model": case["model"],
            "branch": case["branch"],
            "bands": {
                str(index): distribution(values) for index, values in model_bands.items()
            },
        }
    payload = {
        "schema": "sure.rir.demo_frequency_error.v1",
        "source": "data/results.json normalized waveform traces",
        "sample_rate_hz": 16000,
        "error": "mean absolute magnitude-spectrum error in dB per band",
        "bands": [
            {"label": f"{low / 1000:g}-{high / 1000:g} kHz", "low_hz": low, "high_hz": high}
            for low, high in BANDS
        ],
        "cases": cases,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "cases": len(cases), "bands": len(BANDS)}, indent=2))


if __name__ == "__main__":
    main()
