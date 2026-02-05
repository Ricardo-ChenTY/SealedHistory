# Demo sealed datasets (synthetic)

This folder contains small sealed micro-history datasets used for offline smoke tests.

- `*.sealed.jsonl`: demo sealed records
- `*.sealed.codebook.json`: **synthetic demo mappings** (for examples/tests only)

Real dataset builds write private codebooks under `runs/exports/{dataset_version}/private/mapping_key/`.
Do not publish or commit real codebooks from exports.

