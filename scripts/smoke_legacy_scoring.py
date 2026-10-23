#!/usr/bin/env python3
"""Check the legacy scorer against one saved NeuBIRE RIR pair."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import soundfile as sf

from build_legacy_demo_results import match_reference_peaks, score_sample


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--estimate", type=Path, required=True)
    parser.add_argument("--published", type=Path, required=True)
    parser.add_argument("--case", default="neubire_v1_native")
    parser.add_argument("--sample-id", default="scene_0000_mic03cm_snr10dB")
    args = parser.parse_args()
    reference = np.asarray(np.load(args.reference, allow_pickle=False), dtype=np.float64)
    estimate, rate = sf.read(args.estimate, always_2d=True, dtype="float64")
    if rate != 16000 or reference.shape[0] != estimate.shape[1]:
        raise ValueError("expected matching 16 kHz RIR channels")
    published = json.loads(args.published.read_text(encoding="utf-8"))
    expected = next(row["scores"] for row in published["cases"][args.case]["samples"]
                    if row["sample_id"] == args.sample_id)
    actual = score_sample(reference, match_reference_peaks(reference, estimate.T))
    for metric, value in actual.items():
        if not math.isfinite(value):
            raise ValueError(f"nonfinite {metric}")
        previous = expected.get(metric)
        delta = value - previous if previous is not None else None
        print(f"{metric}: computed={value:.6f} published={previous} delta={delta}")
    for metric in ("rt60_1s_mae", "drr_1s_mae", "c50_1s_mae", "edc_1s_mae",
                   "iacc_full_1s_mae", "iacc_early_1s_mae", "iacc_late_1s_mae",
                   "rir_npm", "ild_1s_mae"):
        if not math.isclose(actual[metric], expected[metric], abs_tol=1e-3):
            raise AssertionError(f"historical acoustic score differs for {metric}")


if __name__ == "__main__":
    main()
