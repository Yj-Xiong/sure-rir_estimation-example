#!/usr/bin/env python3
"""Validate all six result scenarios and their frequency-band records."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


CASE_CHANNELS = {
    "rec_rir_single": 1,
    "neubire_v1_single": 1,
    "rec_rir_separate": 2,
    "neubire_v1_native": 2,
    "rec_rir_four_channel": 4,
    "neubire_v1_four_channel": 4,
}
CHANNEL_LAYOUTS = {1: "monaural", 2: "binaural", 4: "four_channel"}
COVERAGE_FILE = json.loads(
    (Path(__file__).resolve().parent.parent / "example/minimal/pipeline_coverage.json").read_text(encoding="utf-8")
)
COVERAGE = COVERAGE_FILE.get("page_samples", COVERAGE_FILE["samples"])


def check_results(results: dict, legacy_ids: list[str], four_ids: list[str]) -> None:
    cases = results["cases"]
    if set(cases) != set(CASE_CHANNELS):
        raise ValueError(f"expected six scenarios, got {sorted(cases)}")
    for case_id, channels in CASE_CHANNELS.items():
        case = cases[case_id]
        samples = case["samples"]
        expected_ids = four_ids if channels == 4 else legacy_ids
        if [sample["sample_id"] for sample in samples] != expected_ids:
            raise ValueError(f"sample selection or order differs: {case_id}")
        metrics = set(case["metrics"])
        if metrics != set(case["means"]):
            raise ValueError(f"metric summary differs from case metrics: {case_id}")
        if channels == 4:
            pipeline_metrics = metrics
        else:
            mapping = case.get("pipeline_metric_map", {})
            if set(mapping.values()) != metrics - {"rir_l1_mae"}:
                raise ValueError(f"legacy metric mapping differs from displayed metrics: {case_id}")
            pipeline_metrics = set(mapping)
            sources = case.get("metric_pipeline_ids", {})
            supplemental = case.get("supplemental_pipeline_id")
            if not supplemental or set(sources) != metrics:
                raise ValueError(f"metric pipeline provenance is incomplete: {case_id}")
            expected_supplemental = {"rt30_mae", "rir_c80_mae"}
            if channels == 2:
                expected_supplemental.add("rir_doa_mae")
            for name in metrics:
                expected_source = supplemental if name in expected_supplemental else case["pipeline_id"]
                if sources[name] != expected_source:
                    raise ValueError(f"metric pipeline provenance differs for {case_id}/{name}")
        expected_metrics = set(COVERAGE[CHANNEL_LAYOUTS[channels]]["metrics"])
        if pipeline_metrics != expected_metrics:
            raise ValueError(f"pipeline metric coverage differs for {case_id}: {sorted(pipeline_metrics)}")
        for sample in samples:
            if set(sample["scores"]) != metrics:
                raise ValueError(f"metric set differs for {case_id}/{sample['sample_id']}")
            if any(not math.isfinite(value) for value in sample["scores"].values()):
                raise ValueError(f"nonfinite score for {case_id}/{sample['sample_id']}")
            for role in ("reference_waveforms", "estimate_waveforms"):
                traces = sample[role]
                if len(traces) != channels or any(len(trace) != 180 for trace in traces):
                    raise ValueError(f"waveform shape differs for {case_id}/{sample['sample_id']}")
        for metric in metrics:
            average = sum(sample["scores"][metric] for sample in samples) / len(samples)
            if not math.isclose(average, case["means"][metric], abs_tol=1e-8, rel_tol=1e-8):
                raise ValueError(f"metric mean differs for {case_id}/{metric}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--frequency", type=Path, required=True)
    parser.add_argument("--legacy-selection", type=Path, required=True)
    parser.add_argument("--four-selection", type=Path, required=True)
    args = parser.parse_args()
    results = json.loads(args.results.read_text(encoding="utf-8"))
    frequency = json.loads(args.frequency.read_text(encoding="utf-8"))
    legacy_ids = [json.loads(line)["sample_id"] for line in args.legacy_selection.read_text(encoding="utf-8").splitlines()]
    four_ids = [row["sample_id"] for row in json.loads(args.four_selection.read_text(encoding="utf-8"))["rows"]]
    if len(legacy_ids) != 60 or len(four_ids) != 60:
        raise ValueError("both selections must contain 60 samples")
    check_results(results, legacy_ids, four_ids)
    if set(frequency["cases"]) != set(CASE_CHANNELS) or len(frequency["bands"]) != 6:
        raise ValueError("frequency analysis must contain six cases and six bands")
    if "native RIR WAVs" not in frequency["source"]:
        raise ValueError("frequency analysis must use native RIR WAVs")
    print("validated six result scenarios, 360 model rows, and six frequency bands")


if __name__ == "__main__":
    main()
