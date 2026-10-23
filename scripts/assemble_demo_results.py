#!/usr/bin/env python3
"""Assemble fresh legacy and four-channel reports into six page scenarios."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


CASE_ORDER = (
    "rec_rir_single", "neubire_v1_single", "rec_rir_separate", "neubire_v1_native",
    "rec_rir_four_channel", "neubire_v1_four_channel",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy", type=Path, required=True)
    parser.add_argument("--four-channel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    legacy = json.loads(args.legacy.read_text(encoding="utf-8"))
    four_channel = json.loads(args.four_channel.read_text(encoding="utf-8"))
    cases = {**legacy.get("cases", {}), **four_channel.get("cases", {})}
    missing = [case for case in CASE_ORDER if case not in cases]
    if missing:
        raise ValueError(f"missing page result scenarios: {missing}")
    counts = {case: len(cases[case].get("samples", [])) for case in CASE_ORDER}
    if set(counts.values()) != {60}:
        raise ValueError(f"each page scenario must contain 60 samples: {counts}")
    payload = {
        "schema": "sure.rir.demo.results.v6",
        "status": "fresh_reproduction",
        "source": "fresh legacy VariableMSpacingFixedSNR run plus fresh four-microphone run",
        "sample_count": 60,
        "cases": {case: cases[case] for case in CASE_ORDER},
        "not_run": [],
        "inference_provenance": {
            "legacy_selection": "data/legacy_demo_selection.json",
            "four_channel_selection": "data/four_mic_demo_selection.json",
            "legacy_runner": "scripts/run_legacy_demo_inference.py",
            "four_channel_runner": "Rec-BIR/scripts/run_demo_recrir_neubire_three_cases.py",
            "sample_rate_hz": 16000,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "cases": list(payload["cases"]), "samples_per_case": 60}))


if __name__ == "__main__":
    main()
