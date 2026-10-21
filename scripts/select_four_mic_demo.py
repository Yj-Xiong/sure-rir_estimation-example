#!/usr/bin/env python3
"""Select the deterministic 60-row four-microphone demo subset."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


DEFAULT_MANIFEST = Path("../../Rec-BIR/NeuSIRI/data/four_mic_fixed_v2/test/test_manifest.jsonl")
SNR_VALUES = (10, 20, 30)
ROWS_PER_SPACING = 2


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def select(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[int, float], list[dict]] = defaultdict(list)
    for row in rows:
        snr = int(row["snr_db"])
        spacing = float(row["adjacent_spacing_m"])
        if snr in SNR_VALUES:
            grouped[(snr, spacing)].append(row)
    spacings = sorted({spacing for _, spacing in grouped})
    expected = len(SNR_VALUES) * len(spacings) * ROWS_PER_SPACING
    selected = []
    for snr in SNR_VALUES:
        for spacing in spacings:
            candidates = sorted(grouped[(snr, spacing)], key=lambda row: row["sample_id"])
            if len(candidates) < ROWS_PER_SPACING:
                raise ValueError(f"need {ROWS_PER_SPACING} rows for SNR {snr}, spacing {spacing}")
            selected.extend(candidates[:ROWS_PER_SPACING])
    if len(selected) != expected or len({row["sample_id"] for row in selected}) != expected:
        raise ValueError("selection does not contain the expected unique rows")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=Path("data/four_mic_demo_selection.json"))
    args = parser.parse_args()
    rows = select(read_rows(args.manifest))
    output = {
        "schema": "sure.rir.four_mic_demo_selection.v1",
        "source_manifest": "Rec-BIR/NeuSIRI/data/four_mic_fixed_v2/test/test_manifest.jsonl",
        "sample_rate_hz": 16000,
        "snr_db": list(SNR_VALUES),
        "rows_per_snr_spacing": ROWS_PER_SPACING,
        "spacing_m": sorted({float(row["adjacent_spacing_m"]) for row in rows}),
        "sample_count": len(rows),
        "rows": [
            {
                "sample_id": row["sample_id"],
                "snr_db": int(row["snr_db"]),
                "adjacent_spacing_m": float(row["adjacent_spacing_m"]),
                "array_aperture_m": float(row["array_aperture_m"]),
                "rir": row["rir"].split("/Rec-BIR/", 1)[-1],
                "mixture": row["mixture"].split("/Rec-BIR/", 1)[-1],
            }
            for row in rows
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sample_count": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
