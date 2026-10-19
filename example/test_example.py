"""Fast adapter contract checks; the full run_example.py uses the real checkpoint."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf

from adapter.model import ModelWrapper


HERE = Path(__file__).resolve().parent


class RIRAdapterTests(unittest.TestCase):
    def test_fixture_hashes(self):
        root = HERE / "fixture"
        entries = json.loads((root / "sha256.json").read_text())["files"]
        for entry in entries:
            path = root / entry["path"]
            self.assertTrue(path.is_file(), entry["path"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry["sha256"], entry["path"])

    def test_published_report_identity(self):
        root = HERE / "harness-run"
        summary = json.loads((root / "summary.json").read_text())
        description = json.loads((root / "pipeline_description.json").read_text())
        report = json.loads((root / "report.json").read_text())
        fixture_rows = [json.loads(line) for line in (HERE / "fixture/gt.jsonl").read_text().splitlines() if line.strip()]
        sample_ids = {row["sample_id"] for row in fixture_rows}
        self.assertEqual(summary["sample_count"], 20)
        self.assertEqual(len(sample_ids), 20)
        self.assertEqual(summary["pipeline_id"], description["pipeline_id"])
        self.assertEqual(summary["pipeline_id"], report["pipeline_id"])
        self.assertEqual(description["computation_node_ids"], report["computation_node_ids"])
        self.assertEqual(set(summary["metrics"]), {"rir_nmse", "rir_corr", "rt60_mae"})
        for node in report["pipeline_trace"]:
            result = node["details"]["result"]
            self.assertEqual(len(result["per_sample"]), 20)
            self.assertEqual({row["sample_id"] for row in result["per_sample"]}, sample_ids)
            self.assertTrue(math.isclose(
                result["score"],
                sum(row["score"] for row in result["per_sample"]) / 20,
                rel_tol=1e-9,
                abs_tol=1e-9,
            ))
            self.assertAlmostEqual(result["score"], summary["metrics"][result["metric_name"]])

    def test_mcp_contract(self):
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 3, "method": "shutdown", "params": {}},
        ]
        result = subprocess.run(
            [sys.executable, str(HERE / "adapter/server.py")],
            input="".join(json.dumps(request) + "\n" for request in requests),
            text=True, capture_output=True, check=True, timeout=10,
        )
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(responses), 3)
        self.assertEqual([response["id"] for response in responses], [1, 2, 3])
        self.assertTrue(all(response["jsonrpc"] == "2.0" and "error" not in response for response in responses))
        self.assertEqual(responses[0]["result"]["protocolVersion"], "2024-11-05")
        self.assertEqual(responses[1]["result"]["tools"][0]["name"], "estimate_rir")

    def test_channel_zero_is_the_only_model_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model_root = root / "model"
            model_root.mkdir()
            (model_root / "inference.py").write_text("# test stub\n")
            checkpoint = root / "epoch35.tar"
            checkpoint.write_bytes(b"test checkpoint")
            source = root / "stereo.wav"
            left = np.full(1024, 0.25, dtype=np.float32)
            right = np.full(1024, -0.5, dtype=np.float32)
            sf.write(source, np.column_stack((left, right)), 16000, subtype="FLOAT")
            destination = root / "prediction.wav"

            def fake_inference(command, *, cwd, stdout, stderr, check, timeout):
                self.assertEqual(Path(command[1]), model_root / "inference.py")
                self.assertEqual(Path(command[command.index("--ckpt") + 1]), checkpoint)
                staged = Path(command[command.index("--input_path") + 1]) / "sample.wav"
                samples, rate = sf.read(staged, always_2d=True, dtype="float32")
                self.assertEqual(rate, 16000)
                self.assertEqual(samples.shape, (1024, 1))
                self.assertTrue(np.array_equal(samples[:, 0], left))
                output = Path(command[command.index("--output_path") + 1]) / "rir" / "sample.wav"
                output.parent.mkdir(parents=True)
                sf.write(output, samples, rate, subtype="FLOAT")
                return subprocess.CompletedProcess(command, 0)

            with patch.dict(os.environ, {"SURE_RIR_MODEL_ROOT": str(model_root),
                                      "SURE_RIR_CHECKPOINT": str(checkpoint)}), patch(
                                          "adapter.model.subprocess.run", side_effect=fake_inference):
                result = ModelWrapper().predict({"audio_path": str(source),
                                                 "output_path": str(destination),
                                                 "reference_rir": str(root / "hidden.npy")})
            self.assertEqual(result["rir_path"], str(destination))
            self.assertEqual(result["channel_layout"], "mono")
            self.assertTrue(destination.is_file())


if __name__ == "__main__":
    unittest.main()
