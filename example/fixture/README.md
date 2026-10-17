# Fixture metadata

This directory contains metadata only. `variable_mspacing_selection.json`
selects two scenes at each of ten microphone spacings; the upstream manifest
resolves the actual mixture and reference RIR paths at run time.

`model_examples.yaml` describes the four model adapters and their channel
transforms. `provenance.json` records the source and redistribution boundary.
No audio, checkpoint, generated RIR, cache, report, or machine-specific path is
committed.
