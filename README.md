# SURE RIR Estimation Example

**[Open the GitHub Pages demo](https://yj-xiong.github.io/sure-rir_estimation-example/)** · [Reproduction notes](example/README.md)

This example follows the public structure of `sure-se-example`, and covers
SURE's channel-aware RIR evaluation contract:

- Rec-RIR -> single-channel inference, scoring channel 0;
- Rec-RIR -> two independent mono inferences, merged as L/R;
- NeuBIRE -> channel 0 duplicated to both model inputs, scoring output channel 0;
- NeuBIRE -> multichannel inference with IACC and ITD.

This repository is the Example contribution only. The evaluation Pipeline
contribution belongs in `PigeonDan1/sure-evaluation`; the later Harness
integration belongs in `PigeonDan1/sure` after the engine PR is merged. The
three repositories must keep their own PRs and pipeline identities separate.

## Open-Bench contribution mapping

The engine change adds the **RIR estimation** task and its metrics:

- `rir.any.rir_iacc_mae.rir_iacc_mae_v1`;
- `rir.any.rir_itd_mae.rir_itd_mae_v1`;
- the existing binaural ILD/IPD nodes remain independently selectable;
- the spatial multi-metric bundle keeps `rir_npm` and `rt60_mae` as the
  base scores before the spatial metrics.

The engine PR contains only versioned nodes, task contracts, routes, tests,
task documentation, and regenerated catalog assets. This repository contains
no node implementation and no replacement for an existing `pipeline_id`.

The default RIR bundle uses NPM and RT60 before optional spatial metrics. Scores are comparable only when the
canonical metric, channel branch, sample-rate/window policy, and pipeline ID
match; mono reports must not be mixed with binaural spatial reports. The small
browser preview uses 60 direct RIR rows from the fixed-SNR set: 10/20/30 dB,
scenes `scene_0000` and `scene_0025`, and ten microphone spacings.

The page is a static GitHub Pages artifact. It loads four real 60-row direct-RIR
result cases. Model checkpoints and private paths stay outside the repository;
the browser data contains only bounded waveform samples and scores.
The exact source dataset, sample selection, checkpoints, preprocessing, and
scoring protocol are recorded in [`data/provenance.json`](data/provenance.json).

Repository layout follows the SURE example convention:

```text
index.html / styles.css / app.js   GitHub Pages demo
data/results.json                   actual four-case report summary
example/fixture/                    original data, predictions and provenance
example/README.md                   reproducible SURE evaluation commands
example/expected.json               pipeline identity and metric expectations
```

## Local preview

```bash
python3 -m http.server 8000
```

Open `http://localhost:8000`.

The included `.github/workflows/pages.yml` publishes the repository root with
GitHub Pages on pushes to `main`. Enable `GitHub Actions` as the Pages source
in repository settings.
