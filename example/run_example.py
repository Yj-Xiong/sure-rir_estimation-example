"""Run pinned Rec-RIR inference through MCP and SURE's locked RIR evaluation backend."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixture"
SURE_COMMIT = "73975931da1353c3b97a422e796612d8b363fe3b"
ENGINE_COMMIT = "8041b1249c5d0ce39a96c72cab01e49b09cc87e9"
MODEL_COMMIT = "6914eea792f0117e39f87510ffbda7cd04dffbbb"
CHECKPOINT_SHA256 = "afe36e477f6fb3656d162d906a47da2d40a789634b476564266fc1ba36037478"
METRICS = "rir_nmse,rir_corr,rt60_mae"
DATASET = "rir_smoke__unversioned__rir"


def git_head(root):
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(label, command, output, environment, *, cwd):
    completed = subprocess.run([str(part) for part in command], cwd=cwd, env=environment, text=True, capture_output=True)
    (output / f"{label}.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"{label} failed ({completed.returncode}); see {output / (label + '.log')}")
    return completed.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="Pinned PigeonDan1/sure checkout")
    parser.add_argument("--model-repo", type=Path, required=True, help="Pinned Audio-WestlakeU/Rec-RIR checkout")
    parser.add_argument("--checkpoint", type=Path, required=True, help="Official epoch35 checkpoint")
    parser.add_argument("--model-python", type=Path, required=True, help="Python with the Rec-RIR model dependencies")
    parser.add_argument("--model-pythonpath", type=Path, help="Optional model-only dependency overlay")
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory for all inference and evaluation artifacts")
    parser.add_argument("--resume", action="store_true", help="Resume scoring from this run's verified real-model predictions")
    parser.add_argument("--device", default="cpu", help="Rec-RIR device, e.g. cpu or cuda:0")
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve()
    model_repo = args.model_repo.expanduser().resolve()
    engine = repo / "sure/external/sure-evaluation"
    checkpoint = args.checkpoint.expanduser().resolve()
    model_python = args.model_python.expanduser().absolute()
    output = args.output_dir.expanduser().resolve()
    for name, root, expected in (("SURE", repo, SURE_COMMIT), ("evaluation engine", engine, ENGINE_COMMIT), ("Rec-RIR", model_repo, MODEL_COMMIT)):
        if git_head(root) != expected:
            parser.error(f"{name} must be checked out at {expected}")
        if subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip():
            parser.error(f"{name} worktree is not clean")
    if digest(checkpoint) != CHECKPOINT_SHA256:
        parser.error("checkpoint SHA-256 does not match the official epoch35 file")
    if not model_python.is_file():
        parser.error("--model-python does not exist")
    manifest_path = Path(sys.prefix) / "runtime-manifest.json"
    if not manifest_path.is_file():
        parser.error("run this script with the SURE bootstrap Harness Runtime Python")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("lock_sha256") != digest(repo / "sure/runtime/harness/requirements.lock.txt"):
        parser.error("Harness Runtime does not match the pinned SURE dependency lock")
    rows = [json.loads(line) for line in (FIXTURE / "gt.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 20 or len({row["sample_id"] for row in rows}) != 20:
        parser.error("expected 20 unique fixture rows")
    hashes = {entry["path"]: entry["sha256"] for entry in json.loads((FIXTURE / "sha256.json").read_text(encoding="utf-8"))["files"]}
    if hashes.get("gt.jsonl") != digest(FIXTURE / "gt.jsonl"):
        parser.error("fixture gt.jsonl does not match its SHA-256 manifest")
    for row in rows:
        for field in ("input_audio", "reference_rir"):
            relative = row[field]
            path = FIXTURE / relative
            if path.is_symlink() or not path.is_file() or hashes.get(relative) != digest(path):
                parser.error(f"fixture {field} is absent or changed: {relative}")
    if args.resume:
        if not (output / "infer-contract.json").is_file() or not (output / "infer-mcp.log").is_file():
            parser.error("--resume needs an existing run with real MCP inference evidence")
    else:
        if output.exists():
            parser.error("--output-dir must not already exist")
        output.mkdir(parents=True)
    environment = {
        **os.environ,
        "HARNESS_PYTHON_BIN": sys.executable,
        "SURE_HARNESS_RUNTIME_ROOT": sys.prefix,
        "SURE_HARNESS_RUNTIME_ID": manifest["runtime_id"],
        "SURE_HARNESS_LOCK_SHA256": manifest["lock_sha256"],
        "SURE_HARNESS_MANIFEST_PATH": str(manifest_path),
        "SURE_RIR_MODEL_ROOT": str(model_repo),
        "SURE_RIR_CHECKPOINT": str(checkpoint),
        "SURE_RIR_DEVICE": args.device,
    }
    model_environment = dict(environment)
    if args.model_pythonpath:
        overlay = args.model_pythonpath.expanduser().resolve()
        if not overlay.is_dir():
            parser.error("--model-pythonpath must be an existing directory")
        model_environment["PYTHONPATH"] = str(overlay)
    model_probe = (
        "import importlib.metadata as m,json,platform,torch;"
        "names=['torch','torchaudio','mamba-ssm','causal-conv1d','numpy','soundfile','toml','tqdm','jsonargparse','matplotlib'];"
        "print(json.dumps({'python':platform.python_version(),'torch_build':torch.__version__,"
        "'torch_cuda':torch.version.cuda,'packages':{name:m.version(name) for name in names}}))"
    )
    write_json(output / "model_environment.json", json.loads(run(
        "model_environment", [model_python, "-c", model_probe], output, model_environment, cwd=HERE)))
    sys.path.insert(0, str(repo / "sure/skills/sure_infer/scripts"))
    from evaluate_predictions import _write_external_audio_samples_jsonl
    from generate_predictions_via_server import _extract_response_payload, _normalize_prediction_payload, _write_prediction_snapshots
    import yaml

    predictions = output / "predictions"
    predictions.mkdir(exist_ok=args.resume)
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    for index, row in enumerate(rows, 3):
        requests.append({"jsonrpc": "2.0", "id": index, "method": "tools/call", "params": {
            "name": "estimate_rir", "arguments": {
                "audio_path": str(FIXTURE / row["input_audio"]),
                "output_path": str(predictions / f"{row['sample_id']}.wav"),
            },
        }})
    requests.append({"jsonrpc": "2.0", "id": len(requests) + 1, "method": "shutdown", "params": {}})
    responses = {}
    previous = {}
    if args.resume:
        prior_entries = json.loads((output / "infer-contract.json").read_text(encoding="utf-8"))
        previous = {entry["sample_id"]: entry for entry in prior_entries}
        if len(prior_entries) != len(rows) or len(previous) != len(rows):
            parser.error("--resume inference manifest must have one entry for each fixture row")
        responses[2] = {"result": {"tools": [{"name": "estimate_rir"}]}}
        for index, row in enumerate(rows, 3):
            expected = predictions / f"{row['sample_id']}.wav"
            entry = previous.get(row["sample_id"])
            if not entry or entry.get("rir_path") != str(expected) or not expected.is_file() or digest(expected) != entry.get("sha256"):
                parser.error(f"--resume prediction is absent or changed: {row['sample_id']}")
            responses[index] = {"result": {"content": [{"type": "text", "text": json.dumps({
                "rir_path": str(expected), "sample_rate": 16000, "channel_layout": "mono"})}]}}
        print("Resuming from 20 verified real-model predictions", flush=True)
    else:
        print("Running real Rec-RIR MCP inference", flush=True)
        completed = subprocess.run(
            [str(model_python), str(HERE / "adapter/server.py")],
            input="".join(json.dumps(request) + "\n" for request in requests),
            text=True, capture_output=True, cwd=HERE / "adapter", env=model_environment, timeout=36000,
        )
        (output / "infer-mcp.log").write_text(completed.stderr, encoding="utf-8")
        if completed.returncode:
            raise RuntimeError("MCP server failed; see infer-mcp.log")
        for line in completed.stdout.splitlines():
            response = json.loads(line)
            if response.get("id") is not None:
                responses[response["id"]] = response
        if responses.get(1, {}).get("result", {}).get("protocolVersion") != "2024-11-05":
            raise RuntimeError("MCP initialize response did not match id 1")
        if "result" not in responses.get(requests[-1]["id"], {}):
            raise RuntimeError("MCP shutdown response is missing")
    if "estimate_rir" not in [tool["name"] for tool in responses.get(2, {}).get("result", {}).get("tools", [])]:
        raise RuntimeError("MCP server did not advertise estimate_rir")
    structured = {}
    infer_contract = []
    for index, row in enumerate(rows, 3):
        payload = _extract_response_payload(responses[index])
        path, prediction = _normalize_prediction_payload(payload, task="RIR")
        expected = predictions / f"{row['sample_id']}.wav"
        if Path(path) != expected or expected.is_symlink() or not expected.is_file():
            raise RuntimeError(f"invalid prediction path for {row['sample_id']}")
        structured[row["sample_id"]] = {"prediction": prediction}
        infer_contract.append({"sample_id": row["sample_id"], "rir_path": str(expected), "sha256": digest(expected)})
    info_probe = (
        "import json,soundfile as sf,sys;"
        "infos=[sf.info(path) for path in sys.argv[1:]];"
        "print(json.dumps([[info.samplerate,info.channels,info.frames] for info in infos]))"
    )
    audio_infos = json.loads(run("prediction_audio", [model_python, "-c", info_probe,
        *(entry["rir_path"] for entry in infer_contract)], output, model_environment, cwd=HERE))
    if len(audio_infos) != len(rows) or any(rate != 16000 or channels != 1 or frames == 0
                                            for rate, channels, frames in audio_infos):
        raise RuntimeError("Rec-RIR returned invalid mono 16 kHz RIR audio")
    write_json(output / "infer-contract.json", infer_contract)
    samples = [{"key": row["sample_id"], "reference_rir": str(FIXTURE / row["reference_rir"]),
                "sample_rate": row["sample_rate"], "channel_layout": "mono", "metadata": row["metadata"]} for row in rows]
    samples_path = output / "samples.jsonl"
    _write_external_audio_samples_jsonl(
        task="RIR", dataset_jsonl_path=FIXTURE / "gt.jsonl", samples=samples,
        structured_predictions=structured, structured_prediction_path=output / "infer-contract.json",
        output_path=samples_path, required_roles=set(),
    )
    run("evaluation_runtime", [sys.executable, repo / "sure/skills/sure_infer/scripts/evaluation_runtime.py",
        "--prepare", "--engine-root", engine, "--output", output / "evaluation_runtime.json"], output, environment, cwd=repo)
    binding = json.loads((output / "evaluation_runtime.json").read_text(encoding="utf-8"))
    dataset_root = output / "dataset"
    references = dataset_root / "sure_benchmark/jsonl"
    references.mkdir(parents=True, exist_ok=args.resume)
    dataset_rows = [{"key": sample["key"], "task": "RIR", "path": str(FIXTURE / row["input_audio"]),
                     "reference_rir": sample["reference_rir"], "sample_rate": 16000,
                     "channel_layout": "mono", "metadata": sample["metadata"]}
                    for sample, row in zip(samples, rows)]
    (references / f"{DATASET}.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in dataset_rows), encoding="utf-8")
    harness_eval = output / "harness-evaluation"
    harness_eval.mkdir(exist_ok=True)
    prediction_root = harness_eval / "predictions"
    prediction_root.mkdir(exist_ok=args.resume)
    _write_prediction_snapshots(
        samples=dataset_rows, prediction_path=prediction_root / f"{DATASET}.txt",
        structured_prediction_path=prediction_root / f"{DATASET}.jsonl",
        prediction_map={row["sample_id"]: str(predictions / f"{row['sample_id']}.wav") for row in rows},
        structured_map={key: {"key": key, "dataset": DATASET, "task": "RIR",
                              "prediction": value["prediction"]} for key, value in structured.items()},
        canonical_dataset=DATASET, sample_task="RIR", sample_language="any",
    )
    config = output / "evaluation.yaml"
    config.write_text(yaml.safe_dump({"data": {"datasets": str(dataset_root)}}), encoding="utf-8")
    run("harness_evaluate", [sys.executable, repo / "sure/skills/sure_infer/scripts/evaluate_predictions.py",
        "--dataset", DATASET, "--pred-dir", prediction_root, "--config", config,
        "--evaluation-backend", "external", "--evaluation-engine-root", engine,
        "--device", "cpu", "--metric", "rir_nmse", "--metric", "rir_corr",
        "--metric", "rt60_mae", "--run-dir", harness_eval,
        "--output", harness_eval / "payload.json"], output, environment, cwd=repo)
    harness_payload = json.loads((harness_eval / "payload.json").read_text(encoding="utf-8"))
    if len(harness_payload.get("results", [])) != 3 or any(
        result.get("evaluation_backend") != "external" or result.get("num_samples") != 20
        for result in harness_payload["results"]
    ):
        raise RuntimeError("Harness external evaluation did not produce three complete RIR results")
    eval_environment = {**environment, "PYTHONPATH": str(engine / "src")}
    sure_eval = [binding["python_executable"], "-c", "from sure_eval.cli import app; app()"]
    pipeline = output / "pipeline.json"
    run("describe", [*sure_eval, "metric", "describe", "rir", "--metrics", METRICS,
        "--output", pipeline, "--json"], output, eval_environment, cwd=engine)
    report_dir = output / "evaluation"
    run("score", [*sure_eval, "metric", "run", "--pipeline", pipeline, "--samples-jsonl", samples_path,
        "--output-dir", report_dir, "--device", "cpu", "--validate-env", "--json"], output, eval_environment, cwd=engine)
    description = json.loads((report_dir / "pipeline_description.json").read_text(encoding="utf-8"))
    report = json.loads((report_dir / "report.json").read_text(encoding="utf-8"))
    if description["pipeline_id"] != report["pipeline_id"] or description["computation_node_ids"] != report["computation_node_ids"]:
        raise RuntimeError("describe/run/report pipeline identity mismatch")
    metrics = {node["details"]["result"]["metric_name"]: node["details"]["result"]["score"]
               for node in report["pipeline_trace"] if "result" in node.get("details", {})}
    harness_scores = {result["metric"]: result["result"]["score"] for result in harness_payload["results"]}
    if set(metrics) != set(METRICS.split(",")) or set(harness_scores) != set(metrics) or any(
        abs(metrics[name] - harness_scores[name]) > 1e-9 for name in metrics
    ):
        raise RuntimeError("Harness metric scores differ from the versioned bundle report")
    if any(len(node["details"]["result"].get("per_sample", [])) != len(rows)
           for node in report["pipeline_trace"] if "result" in node.get("details", {})):
        raise RuntimeError("bundle report does not contain every fixture sample")
    write_json(output / "summary.json", {
        "status": "completed", "scope": "Rec-RIR channel-0 Harness backend reproduction",
        "sure_commit": SURE_COMMIT, "engine_commit": ENGINE_COMMIT, "model_commit": MODEL_COMMIT,
        "checkpoint_sha256": CHECKPOINT_SHA256, "harness_runtime_id": manifest["runtime_id"],
        "evaluation_runtime_id": binding["runtime_id"], "model_environment": "model_environment.json",
        "sample_count": len(rows), "resumed_scoring": args.resume,
        "pipeline_id": report["pipeline_id"], "metrics": metrics,
        "harness_payload": "harness-evaluation/payload.json",
        "report": "evaluation/report.json", "pipeline_description": "evaluation/pipeline_description.json",
    })
    print(output / "summary.json")


if __name__ == "__main__":
    main()
