# SURE RIR Estimation Example

**[Open the GitHub Pages demo](https://yj-xiong.github.io/sure-rir_estimation-example/)** · [Reproduction notes](example/README.md)

This example covers SURE's channel-aware RIR evaluation contract:

- Rec-RIR and NeuBIRE -> monaural inference, scoring channel 0;
- Rec-RIR and NeuBIRE -> binaural inference, with IACC and channel-0-relative spatial metrics;
- Rec-RIR and NeuBIRE -> four-channel inference, with two-channel model passes merged into four paths.

The **RIR estimation** task and its metrics are implemented in
[`sure-evaluation`](https://github.com/PigeonDan1/sure-evaluation):

- The bundles include `rir_npm`, `rt30_mae`, `rt60_mae`, `rir_drr_mae`,
  `rir_c50_mae`, `rir_c80_mae`, and `rir_edc_mae`;
- binaural adds IACC, ITD, ILD, and IPD;
- four-channel adds channel-0-relative ITD, ILD, IPD, and DOA.

The default RIR bundle uses NPM and RT60 before optional spatial metrics. Scores are comparable only when the
canonical metric, channel branch, sample-rate/window policy, and pipeline ID
match; mono reports must not be mixed with binaural spatial reports. The small
browser preview uses 60 direct RIR rows from the fixed-SNR set: 10/20/30 dB,
scenes `scene_0000` and `scene_0025`, and ten microphone spacings.

The Harness reproduction in [`example/README.md`](example/README.md) pins SURE
and Rec-RIR, calls an `estimate_rir` MCP adapter on the 20-row fixture, then
uses the Harness RIR bridge and the locked Evaluation Runtime to produce reports.
The merge-check fixture covers every metric in the submitted bundles. The 20-row report is in
[`example/harness-run/`](example/harness-run/README.md).

The merge-check fixture is documented in
[`example/minimal/README.md`](example/minimal/README.md). It covers acoustic,
binaural, and four-channel spatial metrics with three small synthetic cases.

The page is a static GitHub Pages artifact. It loads six real 60-row direct-RIR
result cases. Model checkpoints and private paths stay outside the repository;
the browser data contains only bounded waveform samples and scores.
The exact source dataset, sample selection, checkpoints, preprocessing, and
scoring protocol are recorded in [`data/provenance.json`](data/provenance.json).
The four-microphone 60-row selection is recorded in
[`data/four_mic_demo_selection.json`](data/four_mic_demo_selection.json); it is
organized as 10/20/30 dB × 10 adjacent spacings × 2 rows. The page also shows
RT60, C50, and EDC error distributions across six frequency bands; regenerate
them with `python3 scripts/compute_frequency_error.py` after setting
`SURE_RIR_RAW_RUN` to the local raw-output directory.

Repository layout follows the SURE example convention:

```text
index.html / styles.css / app.js   GitHub Pages demo
data/results.json                   actual six-case report summary
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
