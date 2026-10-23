#!/usr/bin/env python3
"""Compute normalized octave-band acoustic parameter errors for the demo."""

from __future__ import annotations

import json
import argparse
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data/results.json"
OUTPUT = ROOT / "data/frequency_error.json"
BANDS = ((125, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000))
SAMPLE_RATE = 16000
EPSILON = 1e-12


def normalize(signal: np.ndarray) -> np.ndarray:
    signal = np.asarray(signal, dtype=np.float64)
    peak = float(np.max(np.abs(signal))) if signal.size else 0.0
    return signal / peak if peak > EPSILON else signal


def bandpass(signal: np.ndarray, low: float, high: float) -> np.ndarray:
    nyquist = SAMPLE_RATE / 2.0
    low = max(20.0, float(low))
    high = min(nyquist * 0.98, float(high))
    if not 0.0 < low < high < nyquist or signal.size < 64:
        return np.full_like(signal, np.nan, dtype=np.float64)
    sections = butter(4, (low, high), btype="bandpass", fs=SAMPLE_RATE, output="sos")
    return sosfilt(sections, signal)


def edc_db(signal: np.ndarray) -> np.ndarray:
    energy = np.square(np.asarray(signal, dtype=np.float64))
    curve = np.cumsum(energy[::-1])[::-1]
    maximum = float(curve.max()) if curve.size else 0.0
    if maximum <= EPSILON:
        return np.full(curve.shape, np.nan, dtype=np.float64)
    return 10.0 * np.log10(np.maximum(curve / maximum, EPSILON))


def rt60(signal: np.ndarray) -> float:
    curve = edc_db(signal)
    for decay in (30.0, 20.0, 10.0):
        upper = np.flatnonzero(curve <= -5.0)
        lower = np.flatnonzero(curve <= -(5.0 + decay))
        if not upper.size or not lower.size:
            continue
        start, end = int(upper[0]), int(lower[0])
        if end - start < 4:
            continue
        times = np.arange(start, end + 1, dtype=np.float64) / SAMPLE_RATE
        slope, _ = np.polyfit(times, curve[start : end + 1], 1)
        if slope < 0.0:
            return float(-60.0 / slope)
    return float("nan")


def c50(signal: np.ndarray) -> float:
    signal = np.asarray(signal, dtype=np.float64)
    if not signal.size:
        return float("nan")
    peak = int(np.argmax(np.abs(signal)))
    start = max(0, peak - int(round(SAMPLE_RATE * 0.0025)))
    signal = signal[start:]
    peak = int(np.argmax(np.abs(signal)))
    early_end = min(signal.size, peak + int(round(SAMPLE_RATE * 0.050)) + 1)
    if early_end >= signal.size:
        return float("nan")
    early = float(np.sum(signal[peak:early_end] ** 2))
    late = float(np.sum(signal[early_end:] ** 2))
    if early <= EPSILON or late <= EPSILON:
        return float("nan")
    return float(10.0 * np.log10(early / late))


def edc_error(reference: np.ndarray, estimate: np.ndarray) -> float:
    ref = edc_db(reference)
    pred = edc_db(estimate)
    valid = np.isfinite(ref) & np.isfinite(pred)
    return float(np.mean(np.abs(ref[valid] - pred[valid]))) if np.any(valid) else float("nan")


def distribution(values: list[float], unit: str) -> dict[str, float | int | str | None]:
    valid = np.asarray([value for value in values if np.isfinite(value)], dtype=np.float64)
    if valid.size == 0:
        return {"mean": None, "p25": None, "median": None, "p75": None, "count": 0, "unit": unit}
    return {"mean": float(np.mean(valid)), "p25": float(np.percentile(valid, 25)),
            "median": float(np.percentile(valid, 50)), "p75": float(np.percentile(valid, 75)),
            "count": int(valid.size), "unit": unit}


def band_metric_errors(reference: list[float], estimate: list[float], low: float, high: float) -> dict[str, float]:
    length = min(len(reference), len(estimate))
    if length < 64:
        return {"rt60": float("nan"), "c50": float("nan"), "edc": float("nan")}
    ref = bandpass(normalize(np.asarray(reference[:length])), low, high)
    pred = bandpass(normalize(np.asarray(estimate[:length])), low, high)
    if not np.isfinite(ref).all() or not np.isfinite(pred).all():
        return {"rt60": float("nan"), "c50": float("nan"), "edc": float("nan")}
    pred_rt60, ref_rt60 = rt60(pred), rt60(ref)
    pred_c50, ref_c50 = c50(pred), c50(ref)
    return {
        "rt60": abs(pred_rt60 - ref_rt60) if np.isfinite(pred_rt60) and np.isfinite(ref_rt60) else float("nan"),
        "c50": abs(pred_c50 - ref_c50) if np.isfinite(pred_c50) and np.isfinite(ref_c50) else float("nan"),
        "edc": edc_error(ref, pred),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--legacy-run", type=Path)
    parser.add_argument("--four-channel-run", type=Path)
    args = parser.parse_args()
    if bool(args.legacy_run) != bool(args.four_channel_run):
        parser.error("both --legacy-run and --four-channel-run are required for native WAV analysis")
    source = json.loads(args.results.read_text(encoding="utf-8"))
    metric_units = {"rt60": "s", "c50": "dB", "edc": "dB"}
    cases = {}
    for case_id, case in source["cases"].items():
        values = {metric: {str(index): [] for index in range(len(BANDS))} for metric in metric_units}
        raw_manifest = None
        if args.legacy_run is not None:
            raw_case = {"rec_rir_single": (args.legacy_run, "rec_rir", "monaural"),
                        "neubire_v1_single": (args.legacy_run, "neubire", "monaural"),
                        "rec_rir_separate": (args.legacy_run, "rec_rir", "binaural"),
                        "neubire_v1_native": (args.legacy_run, "neubire", "binaural"),
                        "rec_rir_four_channel": (args.four_channel_run, "rec_rir", "four_channel"),
                        "neubire_v1_four_channel": (args.four_channel_run, "neubire", "four_channel")}.get(case_id)
            if raw_case is None:
                raise ValueError(f"unknown case for raw RIR analysis: {case_id}")
            manifest = raw_case[0] / raw_case[1] / raw_case[2] / "samples.jsonl"
            raw_manifest = {row["sample_id"]: row for line in manifest.read_text(encoding="utf-8").splitlines()
                            if line.strip() for row in (json.loads(line),)}
        for sample in case["samples"]:
            if raw_manifest is not None:
                if sample["sample_id"] not in raw_manifest:
                    raise ValueError(f"missing raw RIR for {case_id}/{sample['sample_id']}")
                raw = raw_manifest[sample["sample_id"]]
                ref_audio, _ = sf.read(raw["reference_rir"], always_2d=True, dtype="float64")
                pred_audio, _ = sf.read(raw["prediction_rir"], always_2d=True, dtype="float64")
                references = ref_audio.T.tolist()
                estimates = pred_audio.T.tolist()
            else:
                references = sample.get("reference_waveforms") or []
                estimates = sample.get("estimate_waveforms") or []
            for reference, estimate in zip(references, estimates):
                for index, (low, high) in enumerate(BANDS):
                    result = band_metric_errors(reference, estimate, low, high)
                    for metric in metric_units:
                        values[metric][str(index)].append(result[metric])
        cases[case_id] = {"model": case["model"], "branch": case["branch"], "bands": {
            str(index): {metric: distribution(values[metric][str(index)], metric_units[metric]) for metric in metric_units}
            for index in range(len(BANDS))
        }}
    payload = {
        "schema": "sure.rir.demo_frequency_acoustic_error.v2",
        "source": "native RIR WAVs from all six branches, normalized per channel before causal Butterworth octave-band filtering",
        "sample_rate_hz": SAMPLE_RATE,
        "metrics": [{"id": "rt60", "label": "RT60 MAE", "unit": "s"},
                    {"id": "c50", "label": "C50 MAE", "unit": "dB"},
                    {"id": "edc", "label": "EDC MAE", "unit": "dB"}],
        "bands": [{"label": f"{low / 1000:g}-{high / 1000:g} kHz", "low_hz": low, "high_hz": high} for low, high in BANDS],
        "cases": cases,
    }
    payload["source"] = (
        "native RIR WAVs from all six branches, normalized per channel before causal Butterworth octave-band filtering"
        if args.legacy_run else "downsampled browser traces, normalized per channel before causal Butterworth octave-band filtering"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "cases": len(cases), "bands": len(BANDS)}, indent=2))


if __name__ == "__main__":
    main()
