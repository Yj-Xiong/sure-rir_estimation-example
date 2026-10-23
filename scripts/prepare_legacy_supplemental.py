#!/usr/bin/env python3
"""Prepare peak-calibrated one-second legacy RIR pairs for SURE metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf


SAMPLE_RATE = 16000


def one_second(signal: np.ndarray) -> np.ndarray:
    clipped = signal[:SAMPLE_RATE]
    return np.pad(clipped, ((0, max(0, SAMPLE_RATE - clipped.shape[0])), (0, 0)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    for model in ("rec_rir", "neubire"):
        for mode, channels in (("monaural", 1), ("binaural", 2)):
            manifest = args.run / model / mode / "samples.jsonl"
            rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
            if len(rows) != 60:
                raise ValueError(f"expected 60 rows in {manifest}, got {len(rows)}")
            case_dir = args.output / model / mode
            records = []
            for row in rows:
                reference, reference_rate = sf.read(row["reference_rir"], always_2d=True, dtype="float64")
                estimate, estimate_rate = sf.read(row["prediction_rir"], always_2d=True, dtype="float64")
                if (reference_rate != SAMPLE_RATE or estimate_rate != SAMPLE_RATE or
                        reference.shape[1] != channels or estimate.shape[1] != channels):
                    raise ValueError(f"invalid RIR pair: {model}/{mode}/{row['sample_id']}")
                reference_peak = np.max(np.abs(reference), axis=0, keepdims=True)
                estimate_peak = np.max(np.abs(estimate), axis=0, keepdims=True)
                if np.any(estimate_peak <= 1e-12):
                    raise ValueError(f"silent estimated channel: {row['sample_id']}")
                estimate = estimate * (reference_peak / estimate_peak)
                paths = {}
                for role, signal in (("reference_rir", reference), ("prediction_rir", estimate)):
                    subdir = "references" if role == "reference_rir" else "predictions"
                    target = case_dir / subdir / f"{row['sample_id']}.wav"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    sf.write(str(target), one_second(signal), SAMPLE_RATE, subtype="FLOAT")
                    if not target.is_file():
                        raise OSError(f"RIR WAV was not retained: {target}")
                    paths[role] = str(target)
                records.append({**row, **paths})
            (case_dir / "samples.jsonl").write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8"
            )
            print(f"{model}/{mode}: {len(records)} SURE scoring rows")


if __name__ == "__main__":
    main()
