#!/usr/bin/env python3
"""Score the published monaural and binaural branches from fresh RIR WAVs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from scripts.compute_variable_mspacing_acoustic_errors import acoustic_errors_from_arrays
from scripts.evaluate_fins_rir50_only_260713 import (
    _iacc_values,
    c50,
    drr,
    edc_db,
    preprocess_rir,
    rt60,
)
from scripts.evaluate_variable_mspacing_bci import npm_db
from scripts.waveform_alignment import shared_ch0_peak_crop


SAMPLE_RATE = 16000
DISPLAY_TAPS = 180
CASE_MAP = {
    "rec_rir_single": ("rec_rir", "monaural", "Rec-RIR", "single_channel"),
    "neubire_v1_single": ("neubire", "monaural", "NeuBIRE", "single_channel"),
    "rec_rir_separate": ("rec_rir", "binaural", "Rec-RIR separate", "binaural"),
    "neubire_v1_native": ("neubire", "binaural", "NeuBIRE", "binaural"),
}
BASE_METRICS = ("rir_l1_mae", "rir_npm", "rt60_1s_mae", "drr_1s_mae", "c50_1s_mae", "edc_1s_mae")
SPATIAL_METRICS = (
    "iacc_full_1s_mae", "iacc_early_1s_mae", "iacc_late_1s_mae",
    "itd_1s_mae", "ild_1s_mae", "ipd_1s_mae",
)
BASE_PROTOCOL = "recbir.legacy_rir_1s.acoustic.v1"
SPATIAL_PROTOCOL = "recbir.legacy_rir_1s.binaural.v1"


def fit_length(signal: np.ndarray) -> np.ndarray:
    sliced = signal[:, :SAMPLE_RATE]
    return np.pad(sliced, ((0, 0), (0, max(0, SAMPLE_RATE - sliced.shape[1]))))


def match_reference_peaks(reference: np.ndarray, estimate: np.ndarray) -> np.ndarray:
    reference_peaks = np.max(np.abs(reference), axis=1, keepdims=True)
    estimate_peaks = np.max(np.abs(estimate), axis=1, keepdims=True)
    if np.any(estimate_peaks <= 1e-12):
        raise ValueError("estimated RIR has a silent channel")
    return estimate * (reference_peaks / estimate_peaks)


def normalized_crop(signal: np.ndarray) -> np.ndarray:
    cropped, _, _ = shared_ch0_peak_crop(signal, target_length=SAMPLE_RATE)
    peak = np.max(np.abs(cropped), axis=1, keepdims=True)
    return cropped / np.maximum(peak, 1e-12)


def display_waveforms(signal: np.ndarray) -> list[list[float]]:
    cropped = normalized_crop(signal)
    original_times = np.linspace(0.0, 1.0, cropped.shape[1])
    display_times = np.linspace(0.0, 1.0, DISPLAY_TAPS)
    return [np.interp(display_times, original_times, channel).round(8).tolist() for channel in cropped]


def spectral_values(signal: np.ndarray) -> tuple[float, float]:
    spectrum = np.fft.rfft(signal, axis=1)
    magnitude = np.abs(spectrum)
    valid = np.all(magnitude > 1e-12, axis=0)
    if not np.any(valid):
        raise ValueError("no valid binaural spectral bins")
    ratio = spectrum[0, valid] / spectrum[1, valid]
    level = 20.0 * np.log10(magnitude[0, valid] / magnitude[1, valid])
    return float(np.mean(level)), float(np.mean(np.angle(ratio)))


def spectral_errors(reference: np.ndarray, estimate: np.ndarray) -> tuple[float, float]:
    reference_fft = np.fft.rfft(reference, axis=1)
    estimate_fft = np.fft.rfft(estimate, axis=1)
    reference_magnitude = np.abs(reference_fft)
    estimate_magnitude = np.abs(estimate_fft)
    valid = np.all(reference_magnitude > 1e-12, axis=0) & np.all(estimate_magnitude > 1e-12, axis=0)
    if not np.any(valid):
        raise ValueError("no shared valid binaural spectral bins")
    reference_ratio = reference_fft[0, valid] / reference_fft[1, valid]
    estimate_ratio = estimate_fft[0, valid] / estimate_fft[1, valid]
    level_error = np.abs(20.0 * np.log10(np.abs(estimate_ratio)) - 20.0 * np.log10(np.abs(reference_ratio)))
    phase_error = np.abs(np.angle(np.exp(1j * (np.angle(estimate_ratio) - np.angle(reference_ratio)))))
    return float(np.mean(level_error)), float(np.mean(phase_error))


def side_metrics(signal: np.ndarray) -> dict:
    signal = fit_length(signal)
    metrics = {name: [] for name in (
        "peak", "direct_peak_sample", "energy", "rt60_1s", "drr_1s", "c50_1s", "edc_1s_db"
    )}
    for channel in signal:
        prepared = preprocess_rir(channel, SAMPLE_RATE)
        metrics["peak"].append(float(np.max(np.abs(channel))))
        metrics["direct_peak_sample"].append(int(np.argmax(np.abs(channel))))
        metrics["energy"].append(float(np.sum(channel * channel)))
        for name, function in (("rt60_1s", rt60), ("drr_1s", drr), ("c50_1s", c50)):
            value = float(function(prepared, SAMPLE_RATE))
            metrics[name].append(value if np.isfinite(value) else None)
        curve = edc_db(prepared)
        metrics["edc_1s_db"].append(np.interp(
            np.linspace(0.0, 1.0, DISPLAY_TAPS), np.linspace(0.0, 1.0, curve.size), curve
        ).tolist())
    if signal.shape[0] == 2:
        iacc = _iacc_values(signal, SAMPLE_RATE)
        for window in ("full", "early", "late"):
            value = float(iacc[f"iacc_{window}"])
            metrics[f"iacc_{window}_1s"] = value if np.isfinite(value) else None
        peaks = np.argmax(np.abs(signal), axis=1)
        metrics["itd_1s_ms"] = float((peaks[1] - peaks[0]) * 1000 / SAMPLE_RATE)
        metrics["ild_1s_db"], metrics["ipd_1s_rad"] = spectral_values(signal)
    return metrics


def score_sample(reference: np.ndarray, estimate: np.ndarray) -> dict[str, float]:
    reference_window = fit_length(reference)
    estimate_window = fit_length(estimate)
    normalized_reference = normalized_crop(reference)
    normalized_estimate = normalized_crop(estimate)
    scores = {
        "rir_l1_mae": float(np.mean(np.abs(normalized_reference - normalized_estimate))),
        "rir_npm": float(npm_db(
            np.repeat(reference_window, 2, axis=0) if reference.shape[0] == 1 else reference_window,
            np.repeat(estimate_window, 2, axis=0) if estimate.shape[0] == 1 else estimate_window,
        )),
    }
    acoustic_reference = np.repeat(reference, 2, axis=0) if reference.shape[0] == 1 else reference
    acoustic_estimate = np.repeat(estimate, 2, axis=0) if estimate.shape[0] == 1 else estimate
    acoustic = acoustic_errors_from_arrays(acoustic_reference, acoustic_estimate)
    for metric in ("rt60", "drr", "c50", "edc"):
        scores[f"{metric}_1s_mae"] = float(np.mean([
            acoustic[f"{metric}_1s_ch{channel}_abs_err"] for channel in range(reference.shape[0])
        ]))
    if reference.shape[0] == 2:
        for window in ("full", "early", "late"):
            scores[f"iacc_{window}_1s_mae"] = float(acoustic[f"iacc_{window}_1s_abs_err"])
        scores["itd_1s_mae"] = float(acoustic["interchannel_delay_1s_abs_err"] * 1000 / SAMPLE_RATE)
        scores["ild_1s_mae"], scores["ipd_1s_mae"] = spectral_errors(reference_window, estimate_window)
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = {}
    for case_id, (model, mode, label, branch) in CASE_MAP.items():
        manifest = args.run / model / mode / "samples.jsonl"
        rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not rows:
            raise ValueError(f"empty case manifest: {manifest}")
        rendered = []
        for row in rows:
            reference, reference_rate = sf.read(row["reference_rir"], always_2d=True, dtype="float64")
            estimate, estimate_rate = sf.read(row["prediction_rir"], always_2d=True, dtype="float64")
            channels = 1 if mode == "monaural" else 2
            if reference_rate != SAMPLE_RATE or estimate_rate != SAMPLE_RATE:
                raise ValueError(f"invalid sample rate: {row['sample_id']}")
            if reference.shape[1] != channels or estimate.shape[1] != channels:
                raise ValueError(f"invalid channel count: {row['sample_id']}")
            reference, estimate = reference.T, estimate.T
            estimate = match_reference_peaks(reference, estimate)
            rendered.append({
                "sample_id": row["sample_id"],
                "scene_id": row["metadata"]["scene_id"],
                "spacing_cm": row["metadata"]["mic_spacing_cm"],
                "snr_db": row["metadata"]["snr_db"],
                "scores": score_sample(reference, estimate),
                "reference_waveforms": display_waveforms(reference),
                "estimate_waveforms": display_waveforms(estimate),
                "reference_metrics": side_metrics(reference),
                "prediction_metrics": side_metrics(estimate),
            })
        metric_names = BASE_METRICS + (SPATIAL_METRICS if mode == "binaural" else ())
        cases[case_id] = {
            "status": "direct_rir_protocol_report",
            "model": label,
            "branch": branch,
            "channel_layout": "mono" if mode == "monaural" else "binaural_lr",
            "pipeline_id": SPATIAL_PROTOCOL if mode == "binaural" else BASE_PROTOCOL,
            "metrics": metric_names,
            "means": {name: float(np.mean([sample["scores"][name] for sample in rendered])) for name in metric_names},
            "samples": rendered,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "schema": "sure.rir.demo.legacy_results.v1",
        "source": "VariableMSpacingFixedSNR 60-row monaural and binaural direct RIR run",
        "sample_count": len(next(iter(cases.values()))["samples"]),
        "cases": cases,
    }, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "cases": list(cases)}))


if __name__ == "__main__":
    main()
