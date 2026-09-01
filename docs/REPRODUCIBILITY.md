# Reproducibility guide

## Public result reproduction

The default route is self-contained and uses only aggregate files included in this repository:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -B workflows/validate_installation.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -B workflows/reproduce_public_results.py --output-root reproduced_outputs
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -v
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -B tools/security_scan.py --root .
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -B tools/verify_reference_outputs.py
```

The reproduction creates tables, six aggregate-only figure sets and a full-precision numeric verification report. It cannot access the originating research project because all inputs are resolved inside this repository.

## Full pipeline from authorized prepared inputs

This is an advanced opt-in route, not the default:

```bash
PYTHONPATH=src python -B workflows/run_full_pipeline.py \
  --execute \
  --config configs/full_pipeline_config_template_v1.json \
  --input-root /path/to/authorized-prepared-inputs \
  --output-root /path/to/new-empty-output
```

Before use, fill only the authorized prepared-input paths in a copy of the config and supply the required input contract. The locked feature and LightGBM settings are in `configs/locked_feature_config_v1.json`. The command refuses an existing output directory and produces strict component OOF models/predictions, overall/monthly/representativeness/station metrics, paired station-cluster component bootstrap, primary WCT and its bootstrap, piecewise sensitivity, and direct-WCT comparisons for all stations and with the mismatch cohort excluded. Station-level, row-level and bootstrap-replicate products remain under the user-selected local output root and are never copied into this repository.

The route performs no download, never calls the permission-controlled external endpoint, never trains production/external models, never retrains direct WCT and never produces a complete regional grid.

This scope is `FULL_PIPELINE_FROM_AUTHORIZED_PREPARED_INPUTS`; it is not a claim of one-command raw-data acquisition and complete-study reproduction.

## Clean-room verification

`tools/clean_room_test.py` copies the repository into a filesystem-isolated temporary directory, blocks outbound socket connections in child Python processes, runs installation validation, aggregate reproduction, unit tests, the security scan and reference-output verification, and then removes the temporary directory. It uses the caller's preinstalled Python dependency environment; it does not claim to recreate the Conda environment. All public inputs used in the clean room are internal to the copied repository.
