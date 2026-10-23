#!/usr/bin/env python3
"""Materialize the published 60-row monaural/binaural selection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "data/legacy_demo_selection.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    dataset_root = args.dataset_root.resolve()
    manifest = dataset_root / "test_manifest.jsonl"
    source = {
        row["sample_id"]: row
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in (json.loads(line),)
    }
    rows = []
    for snr_db in selection["snr_db"]:
        for spacing_cm in selection["microphone_spacing_cm"]:
            for scene_id in selection["scene_ids"]:
                sample_id = f"{scene_id}_mic{spacing_cm:02d}cm_snr{snr_db}dB"
                item = source[sample_id]
                if (int(item["snr_db"]), int(item["mic_spacing_cm"]), item["scene_id"]) != (
                    snr_db, spacing_cm, scene_id
                ):
                    raise ValueError(f"selection metadata mismatch: {sample_id}")
                paths = {}
                for role in ("mixture", "rir"):
                    original = Path(item[role])
                    relative = original.relative_to(dataset_root)
                    resolved = dataset_root / relative
                    if not resolved.is_file():
                        raise FileNotFoundError(resolved)
                    paths[role] = str(resolved)
                rows.append({
                    "sample_id": sample_id,
                    "scene_id": scene_id,
                    "snr_db": snr_db,
                    "mic_spacing_cm": spacing_cm,
                    **paths,
                })
    if len(rows) != selection["sample_count"]:
        raise ValueError(f"expected {selection['sample_count']} rows, got {len(rows)}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    print(json.dumps({"selection": str(args.output), "samples": len(rows)}))


if __name__ == "__main__":
    main()
