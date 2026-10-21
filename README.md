# SURE RIR Estimation Example

**[Open the GitHub Pages demo](https://yj-xiong.github.io/sure-rir_estimation-example/)** · [Reproduction notes](example/README.md)

This example covers SURE's channel-aware RIR evaluation contract:

- Rec-RIR -> monaural inference, scoring channel 0;
- Rec-RIR -> two independent mono inferences, merged as L/R;
- NeuBIRE -> channel 0 duplicated to both model inputs, scoring output channel 0;
- NeuBIRE -> multichannel inference with IACC and ITD.

The **RIR estimation** task and its metrics are implemented in
[`sure-evaluation`](https://github.com/PigeonDan1/sure-evaluation):

- `rir.any.rir_iacc_mae.rir_iacc_mae_v1`;
- `rir.any.rir_itd_mae.rir_itd_mae_v1`;
- the existing binaural ILD/IPD nodes remain independently selectable;
- the spatial multi-metric bundle keeps `rir_npm` and `rt60_mae` as the
  base scores before the spatial metrics.

The default RIR bundle uses NPM and RT60 before optional spatial metrics. Scores are comparable only when the
canonical metric, channel branch, sample-rate/window policy, and pipeline ID
match; mono reports must not be mixed with binaural spatial reports. The small
browser preview uses 60 direct RIR rows from the fixed-SNR set: 10/20/30 dB,
scenes `scene_0000` and `scene_0025`, and ten microphone spacings.

The Harness reproduction in [`example/README.md`](example/README.md) pins SURE
and Rec-RIR, calls an `estimate_rir` MCP adapter on the 20-row fixture, then
uses the Harness RIR bridge, `evaluate_predictions.py`, and the locked
Evaluation Runtime to produce reports. The script evaluates the Rec-RIR
channel-0 branch. It uses `rir_nmse`/`rir_corr`/`rt60_mae`; the browser data
uses NPM and a different dataset. The 20-row report is in
[`example/harness-run/`](example/harness-run/README.md).

The merge-check fixture is documented in
[`example/minimal/README.md`](example/minimal/README.md). It covers acoustic,
binaural, and four-channel spatial metrics with three small synthetic cases.

The page is a static GitHub Pages artifact. It loads four real 60-row direct-RIR
result cases. Model checkpoints and private paths stay outside the repository;
the browser data contains only bounded waveform samples and scores.
The exact source dataset, sample selection, checkpoints, preprocessing, and
scoring protocol are recorded in [`data/provenance.json`](data/provenance.json).
The four-microphone 60-row selection is recorded in
[`data/four_mic_demo_selection.json`](data/four_mic_demo_selection.json); it is
organized as 10/20/30 dB × 10 adjacent spacings × 2 rows. The page also shows
normalized waveform magnitude-spectrum error distributions for six frequency
bands; regenerate them with `python3 scripts/compute_frequency_error.py`.

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
