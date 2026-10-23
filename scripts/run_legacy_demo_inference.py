#!/usr/bin/env python3
"""Run the two published 60-row monaural and binaural model branches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

WRITE_WAV = sf.write

from scripts.evaluate_air_itd_gccphat_260817 import RecRIR1chEstimator
from scripts.evaluate_recbir_dataset30mm_fixed_test import (
    RecBIRFixedTestEvaluator,
    _load_fixed_mixture_2ch,
)


def save_case(root: Path, model: str, mode: str, row: dict, estimate: np.ndarray, reference: np.ndarray) -> dict:
    directory = root / model / mode
    prediction_path = directory / "predictions" / f"{row['sample_id']}.wav"
    reference_path = directory / "references" / f"{row['sample_id']}.wav"
    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    reference_path.parent.mkdir(parents=True, exist_ok=True)
    WRITE_WAV(str(prediction_path), estimate.T, 16000, subtype="FLOAT")
    WRITE_WAV(str(reference_path), reference.T, 16000, subtype="FLOAT")
    if not prediction_path.is_file() or not reference_path.is_file():
        raise OSError(f"RIR WAV was not retained for {row['sample_id']}")
    return {
        "sample_id": row["sample_id"],
        "prediction_rir": str(prediction_path),
        "reference_rir": str(reference_path),
        "sample_rate": 16000,
        "channel_layout": "mono" if mode == "monaural" else "binaural_lr",
        "metadata": {
            "scene_id": row["scene_id"],
            "snr_db": row["snr_db"],
            "mic_spacing_cm": row["mic_spacing_cm"],
            "microphone_spacing_m": row["mic_spacing_cm"] / 100,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--recrir-config", type=Path, required=True)
    parser.add_argument("--recrir-checkpoint", type=Path, required=True)
    parser.add_argument("--neubire-config", type=Path, required=True)
    parser.add_argument("--neubire-checkpoint", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    for path in (
        args.selection, args.recrir_config, args.recrir_checkpoint,
        args.neubire_config, args.neubire_checkpoint,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output.exists():
        raise FileExistsError(f"output directory already exists: {args.output}")
    rows = [json.loads(line) for line in args.selection.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or len({row["sample_id"] for row in rows}) != len(rows):
        raise ValueError("selection must contain unique sample IDs")
    if args.limit:
        rows = rows[:args.limit]

    device = torch.device(args.device)
    if device.type == "cuda":
        torch.cuda.set_device(device)
    recrir = RecRIR1chEstimator(args.recrir_config, args.recrir_checkpoint, device)
    neubire = RecBIRFixedTestEvaluator(args.neubire_config, args.neubire_checkpoint, device)
    manifests = {(model, mode): [] for model in ("rec_rir", "neubire") for mode in ("monaural", "binaural")}
    for index, row in enumerate(rows, start=1):
        reference = np.asarray(np.load(row["rir"], allow_pickle=False), dtype=np.float32)
        if reference.ndim != 2 or reference.shape[0] != 2:
            raise ValueError(f"expected two reference channels: {row['sample_id']}")
        recrir_estimate = np.asarray(recrir.estimate(row), dtype=np.float32)
        mixture = _load_fixed_mixture_2ch(row["mixture"], neubire.sr, neubire.input_length).to(device)
        native_estimate, _ = neubire.estimate(mixture, rir_len=reference.shape[1])
        native_estimate = native_estimate[0].detach().cpu().numpy().astype(np.float32)
        estimates = {
            ("rec_rir", "monaural"): recrir_estimate[:1],
            ("rec_rir", "binaural"): recrir_estimate[:2],
            ("neubire", "monaural"): native_estimate[:1],
            ("neubire", "binaural"): native_estimate[:2],
        }
        for (model, mode), estimate in estimates.items():
            channels = 1 if mode == "monaural" else 2
            if estimate.shape[0] != channels or not np.isfinite(estimate).all():
                raise ValueError(f"invalid {model}/{mode} estimate: {row['sample_id']}")
            manifests[model, mode].append(save_case(
                args.output, model, mode, row, estimate, reference[:channels]
            ))
        if index % 10 == 0 or index == len(rows):
            print(f"legacy RIR inference: {index}/{len(rows)}", flush=True)

    for (model, mode), records in manifests.items():
        destination = args.output / model / mode / "samples.jsonl"
        destination.write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
            encoding="utf-8",
        )
    print(json.dumps({"output": str(args.output), "sample_count": len(rows), "case_count": len(manifests)}))


if __name__ == "__main__":
    main()
