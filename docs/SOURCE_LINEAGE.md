# Source lineage

`manifests/source_lineage_v1_3.csv` records every refactored authoritative source and copied aggregate source with original relative path, original SHA-256, candidate path, candidate SHA-256, refactor status, scientific purpose and public-safety level. It also records the V1.2-to-V1.3 license-finalization lineage for changed public files.

The scientific modules consolidate the original versioned scripts into an installable package:

- pure contracts and I/O → `src/wce/contracts/`;
- nested prepared-input training and prediction → `src/wce/pipeline/`;
- four-cell operators → `src/wce/stencil/`;
- aggregate metrics → `src/wce/metrics/`;
- public figures → `src/wce/plotting/`;
- permission-controlled schema only → `src/wce/external_interface/`.

Original scripts were not modified. The candidate contains no legacy executable. The locked feature configuration was mechanically derived from the completed formal outer-fold model configurations and contains only feature names, parameters and source hashes—no model material or row-level data.
