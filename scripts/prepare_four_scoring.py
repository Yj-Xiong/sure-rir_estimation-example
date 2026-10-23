#!/usr/bin/env python3
"""Prepare one-second four-channel RIR pairs for SURE scoring."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf


TAPS = 16000


def fit_length(samples: np.ndarray) -> np.ndarray:
    clipped = samples[:TAPS]
    return np.pad(clipped, ((0, max(0, TAPS - clipped.shape[0])), (0, 0)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    for model in ("rec_rir", "neubire"):
        root = args.run / model / "four_channel"
        source = root / "samples.jsonl"
        rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(rows) != 60:
            raise ValueError(f"expected 60 four-channel rows for {model}, got {len(rows)}")
        scoring = root / "scoring"
        records = []
        for row in rows:
            prediction, pred_rate = sf.read(row["prediction_rir"], always_2d=True, dtype="float32")
            reference, ref_rate = sf.read(row["reference_rir"], always_2d=True, dtype="float32")
            if pred_rate != 16000 or ref_rate != 16000 or prediction.shape[1] != 4 or reference.shape[1] != 4:
                raise ValueError(f"invalid four-channel RIR pair: {model}/{row['sample_id']}")
            paths = {}
            for role, signal in (("prediction_rir", prediction), ("reference_rir", reference)):
                subdir = "predictions" if role == "prediction_rir" else "references"
                target = scoring / subdir / f"{row['sample_id']}.wav"
                target.parent.mkdir(parents=True, exist_ok=True)
                sf.write(str(target), fit_length(signal), 16000, subtype="FLOAT")
                if not target.is_file():
                    raise OSError(f"RIR WAV was not retained: {target}")
                paths[role] = str(target)
            records.append({**row, **paths})
        (scoring / "samples.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8"
        )
        print(f"{model}/four_channel: {len(records)} scoring rows")


if __name__ == "__main__":
    main()
