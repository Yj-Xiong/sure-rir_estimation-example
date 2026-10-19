"""Rec-RIR channel-0 adapter using the pinned upstream PIM inference entrypoint."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4


class ModelWrapper:
    def __init__(self, config=None):
        self.config = config or {}

    def load(self):
        self.model_root = Path(os.environ["SURE_RIR_MODEL_ROOT"]).expanduser().resolve()
        self.checkpoint = Path(os.environ["SURE_RIR_CHECKPOINT"]).expanduser().resolve()
        if not (self.model_root / "inference.py").is_file():
            raise FileNotFoundError(self.model_root / "inference.py")
        if not self.checkpoint.is_file():
            raise FileNotFoundError(self.checkpoint)

    def predict(self, input_data):
        import numpy as np
        import soundfile as sf

        if not isinstance(input_data, dict) or not input_data.get("audio_path"):
            raise ValueError("audio_path is required")
        source = Path(input_data["audio_path"]).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        samples, rate = sf.read(source, always_2d=True, dtype="float32")
        if rate != 16000 or samples.size == 0 or not np.isfinite(samples).all():
            raise ValueError("Expected nonempty finite 16 kHz input audio")
        target = Path(input_data.get("output_path") or Path(tempfile.gettempdir()) / "sure-rir" / f"{uuid4().hex}.wav").expanduser().resolve()
        if target.suffix.lower() != ".wav" or target == source or target.exists():
            raise ValueError("output_path must name a new WAV distinct from the input")
        if not hasattr(self, "model_root"):
            self.load()
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="sure-rec-rir-") as temporary:
            root = Path(temporary)
            input_dir = root / "input"
            input_dir.mkdir()
            sf.write(input_dir / "sample.wav", samples[:, 0], rate, subtype="FLOAT")
            output_dir = root / "output"
            command = [
                sys.executable, str(self.model_root / "inference.py"),
                "--config", str(Path(__file__).with_name("config.toml")),
                "--ckpt", str(self.checkpoint),
                "--input_path", str(input_dir), "--output_path", str(output_dir),
                "--device", os.environ.get("SURE_RIR_DEVICE", "cpu"),
            ]
            subprocess.run(command, cwd=self.model_root, stdout=sys.stderr, stderr=sys.stderr, check=True, timeout=1800)
            generated = output_dir / "rir" / "sample.wav"
            rir, output_rate = sf.read(generated, always_2d=True, dtype="float32")
            if output_rate != 16000 or rir.shape[1] != 1 or rir.shape[0] == 0 or not np.isfinite(rir).all():
                raise RuntimeError("Rec-RIR returned an invalid mono 16 kHz RIR")
            shutil.copyfile(generated, target)
        return {"rir_path": str(target), "sample_rate": 16000, "channel_layout": "mono"}

    def healthcheck(self):
        return {"status": "ready" if hasattr(self, "model_root") else "loading"}
