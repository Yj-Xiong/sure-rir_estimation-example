# SURE RIR Estimation Example

**[Open the demo](https://yj-xiong.github.io/sure-rir_estimation-example/)** ·
[Example repository](https://github.com/Yj-Xiong/sure-rir_estimation-example) ·
[Reproduce all six branches](example/README.md) ·
[NeuBIRE four-channel details](example/NEUBIRE_REPRODUCTION.md)

This example covers SURE's channel-aware RIR evaluation contract:

- Rec-RIR monaural inference and NeuBIRE channel-0 projection from a native pair;
- Rec-RIR and NeuBIRE -> binaural inference, with IACC full/early/late and channel-0-relative spatial metrics;
- Rec-RIR and NeuBIRE -> four-channel inference, with two-channel model passes merged into four paths.

The **RIR estimation** task and its metrics are implemented in
[`sure-evaluation`](https://github.com/Yj-Xiong/sure-evaluation):

- The bundles include `rir_npm`, `rt30_mae`, `rt60_mae`, `rir_drr_mae`,
  `rir_c50_mae`, `rir_c80_mae`, and `rir_edc_mae`;
- binaural adds IACC full/early/late, ITD, ILD, IPD, and DOA;
- four-channel adds channel-0-relative ITD, ILD, IPD, and DOA.

The shared acoustic bundle uses NPM, RT30, RT60, DRR, C50, C80, and EDC before
optional spatial metrics. Scores are comparable only when the canonical
metric, channel branch, sample-rate/window policy, and pipeline ID
match; mono reports must not be mixed with binaural spatial reports. Each
browser branch contains 60 rows. The monaural and binaural branches use
`VariableMSpacingFixedSNR` scenes `scene_0000` and `scene_0025` at 10/20/30 dB
and ten spacings. Four-channel branches use the separate
`four_mic_fixed_v2` selection, with two rows per SNR-spacing pair.

The complete six-branch workflow is in [`example/README.md`](example/README.md).
The focused NeuBIRE four-channel details are in
[`example/NEUBIRE_REPRODUCTION.md`](example/NEUBIRE_REPRODUCTION.md). The
separate 20-row Harness fixture is retained under
[`example/harness-run/`](example/harness-run/README.md) for CI contract checks.

The merge-check fixture is documented in
[`example/minimal/README.md`](example/minimal/README.md). It covers acoustic,
binaural, and four-channel spatial metrics with three small synthetic cases.

The page is a static GitHub Pages artifact. It loads six real 60-row direct-RIR
result cases. Model checkpoints and private paths stay outside the repository;
the browser data contains only bounded waveform samples and scores.
The exact source dataset, sample selection, checkpoints, preprocessing, and
scoring protocol are recorded in [`data/provenance.json`](data/provenance.json).
Rec-RIR is described in “Monaural Blind Room Impulse Response Identification
via DNN-based Reverberant Speech Reconstruction in STFT Domain”
([paper](https://arxiv.org/abs/2509.15628)) and released at
[Audio-WestlakeU/Rec-RIR](https://github.com/Audio-WestlakeU/Rec-RIR).
The four-microphone 60-row selection is recorded in
[`data/four_mic_demo_selection.json`](data/four_mic_demo_selection.json); it is
organized as 10/20/30 dB × 10 adjacent spacings × 2 rows. The page also shows
RT60, C50, and EDC error distributions across six frequency bands; the full
reproduction workflow computes them from the native RIR WAVs in both run roots.

Repository layout follows the SURE example convention:

```text
index.html / styles.css / app.js   GitHub Pages demo
data/results.json                   actual six-case report summary
example/fixture/                    original data, predictions and provenance
example/README.md                   complete six-branch reproduction
example/NEUBIRE_REPRODUCTION.md     NeuBIRE four-channel inference details
example/submit_*.sh                cluster inference and scoring entry points
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
