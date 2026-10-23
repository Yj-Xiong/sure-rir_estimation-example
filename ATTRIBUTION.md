# Sources and attribution

## Evaluation contract

The RIR task, JSONL contract, route IDs, and scoring nodes are provided by
[SURE](https://github.com/Yj-Xiong/sure) and its
[sure-evaluation](https://github.com/Yj-Xiong/sure-evaluation) engine.
This repository contains the browser example, fixtures, and reproduction
instructions.

## Data

The optional 20-row selection uses `VariableMSpacingTest`, with two scenes at
each of the 3, 6, 9, 12, 15, 18, 21, 24, 27, and 30 cm microphone spacings.
The dataset and its source licenses remain external to this example. This
bounded subset includes the selected source mixture WAVs, reference RIR arrays,
metadata, and four generated prediction sets. Checkpoints and private absolute
paths are not redistributed; file hashes are recorded in
`example/fixture/sha256.json`.

## Models

[Rec-RIR](https://github.com/Audio-WestlakeU/Rec-RIR) is an upstream model
baseline; see its [paper](https://arxiv.org/abs/2509.15628). NeuBIRE inference
uses the implementation and checkpoint recorded in
[`data/provenance.json`](data/provenance.json). Model weights and private
workspace files are not included in this example repository. See the
[NeuBIRE reproduction guide](example/NEUBIRE_REPRODUCTION.md) for the exact
workspace paths and run steps.
