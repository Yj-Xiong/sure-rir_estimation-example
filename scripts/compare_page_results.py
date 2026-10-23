#!/usr/bin/env python3
"""Summarize score changes between a published page and a fresh run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--published", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    published = json.loads(args.published.read_text(encoding="utf-8"))["cases"]
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))["cases"]
    if set(published) != set(candidate):
        raise ValueError("candidate and published case IDs differ")
    print("case,metric,mean_delta,max_sample_abs_delta,matched_samples")
    for case_id in published:
        old = {sample["sample_id"]: sample for sample in published[case_id]["samples"]}
        new = {sample["sample_id"]: sample for sample in candidate[case_id]["samples"]}
        if set(old) != set(new):
            raise ValueError(f"candidate and published sample IDs differ for {case_id}")
        common_metrics = set(published[case_id]["metrics"]) & set(candidate[case_id]["metrics"])
        for metric in sorted(common_metrics):
            deltas = [new[sample_id]["scores"][metric] - old[sample_id]["scores"][metric] for sample_id in old]
            print(f"{case_id},{metric},{sum(deltas) / len(deltas):.6g},{max(map(abs, deltas)):.6g},{len(deltas)}")
        removed = set(published[case_id]["metrics"]) - common_metrics
        added = set(candidate[case_id]["metrics"]) - common_metrics
        if removed or added:
            print(f"{case_id},metric-set-changed,removed={sorted(removed)},added={sorted(added)},0")


if __name__ == "__main__":
    main()
