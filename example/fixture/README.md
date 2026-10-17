# Fixture metadata

This directory is the bounded Harness smoke fixture, separate from the 60-row
fixed-SNR dataset used to publish `data/results.json`. It contains 20 original
mixture WAVs, 20 original two-channel reference RIR arrays, metadata,
channel-0 reference arrays, and predictions from Rec-RIR and NeuBIRE v1.
`variable_mspacing_selection.json` selects two scenes at each of ten microphone
spacings. `case_manifest.json` maps the four input/output channel transforms to
their SURE reports.

`model_examples.yaml` describes the four model adapters and their channel
transforms. `provenance.json` and `sha256.json` record the source and file
integrity. Checkpoints, caches, private absolute paths, and unrelated dataset
rows are not committed.
