# dataset-v1

This release contains the audited nested ladder `S100 ⊂ S500 ⊂ S1000` generated with seed `20261006`.

- `random100_v1.json.gz`: 100 episodes
- `random500_v1.json.gz`: 500 episodes
- `random1000_v1.json.gz`: 1000 episodes
- `additional400_v1.json.gz`: `S500 - S100`
- `additional500_v1.json.gz`: `S1000 - S500`
- `*.manifest.json`: selected keys, source indices, input hashes, and output hashes
- `generation_plan.json`: source and frozen-parent provenance
- `SHA256SUMS`: hashes for the data, manifests, and generation plan

The source SHA-256 is `0e4fddca056d2e012ecc52f43a259ebddb1128503a7767b5da3b5af8ea8cf653`. The frozen S100 and S500 parent SHA-256 values are recorded in `generation_plan.json` and `datasets/manifests/source_registry.json`. The release was audited with the repository's `ladder audit` command. No S1000 navigation evaluation is included in this release.

Verify the published files with `(cd datasets/releases/dataset-v1 && sha256sum -c SHA256SUMS)`.
