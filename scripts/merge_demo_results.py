#!/usr/bin/env python3
"""Restore the previous mono/binaural data and retain current four-channel data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


RESTORED_CASES = (
    "rec_rir_single",
    "neubire_v1_single",
    "rec_rir_separate",
    "neubire_v1_native",
)
CURRENT_CASES = ("rec_rir_four_channel", "neubire_v1_four_channel")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    previous = json.loads(args.previous.read_text(encoding="utf-8"))
    current = json.loads(args.current.read_text(encoding="utf-8"))
    cases = {name: previous["cases"][name] for name in RESTORED_CASES}
    cases.update({name: current["cases"][name] for name in CURRENT_CASES})
    payload = {
        "schema": "sure.rir.demo.results.v5",
        "status": "actual_sure_reports",
        "source": "previous VariableMSpacingFixedSNR mono/binaural results plus current four-mic results",
        "sample_count": 60,
        "cases": cases,
        "not_run": [],
        "inference_provenance": {
            "restored_cases": "data/results.json from demo commit d12e3c9",
            "current_cases": "four-channel branches from the old NeuBIRE checkpoint run",
            "sample_rate_hz": 16000,
        },
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "cases": list(cases), "samples_per_case": 60}, indent=2))


if __name__ == "__main__":
    main()
