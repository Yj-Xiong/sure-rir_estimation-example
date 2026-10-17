# Sources and attribution

## Evaluation contract

The RIR task, JSONL contract, route IDs, and scoring nodes are provided by
[SURE](https://github.com/PigeonDan1/sure) and its
[sure-evaluation](https://github.com/PigeonDan1/sure-evaluation) engine.
The live evaluation path remains in `sure-harness`; this repository contains
the visual example and reproduction pointers.

## Data

The optional 20-row selection uses `VariableMSpacingTest`, with two scenes at
each of the 3, 6, 9, 12, 15, 18, 21, 24, 27, and 30 cm microphone spacings.
The dataset and its source licenses remain external to this example. This
bounded subset includes the selected source mixture WAVs, reference RIR arrays,
metadata, and four generated prediction sets. Checkpoints and private absolute
paths are not redistributed; file hashes are recorded in
`example/fixture/sha256.json`.

## Models

Rec-RIR and NeuBIRE-MINT are referenced as evaluation model adapters. Their
weights and runtime licenses are governed by their respective upstream model
repositories and are not included here.
