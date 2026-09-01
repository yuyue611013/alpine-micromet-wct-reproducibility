# WCE microclimate-to-exposure reproducibility code

This candidate repository accompanies the manuscript **“Limits to translating environmental data into exposure metrics.”** It is an author-review snapshot of the `WCE_SCIENTIFIC_CORRECTION_V1` analysis.

The repository has three deliberately separate reproduction levels:

1. **Public result reproduction (default).** Recreates public tables, aggregate-only figures and a numeric verification report from files in `data/aggregate/` and `data/figure_source/`.
2. **Full pipeline from authorized prepared inputs (opt-in).** Exposes the strict nested station-grouped OOF contracts and requires explicit `--execute`, `--config`, `--input-root` and `--output-root`. It does not download data, run the permission-controlled external endpoint, or generate a complete Alpine grid.
3. **Permission-controlled external interface.** Publishes only a synthetic schema and design documentation. Real observations, locations, identities and hourly matched records are not included.

## Quick start

Use Python 3.11. For public/core validation and aggregate figure reproduction, install:

```bash
python -m pip install -e '.[plot]'
```

For the opt-in pipeline from authorized prepared inputs, install:

```bash
python -m pip install -e '.[full,plot]'
python workflows/validate_installation.py --full
```

The default public route is:

```bash
python workflows/validate_installation.py
python workflows/reproduce_public_results.py --output-root reproduced_outputs
python -m unittest discover -s tests -v
python tools/security_scan.py --root .
python tools/verify_reference_outputs.py
```

All writing commands are non-clobbering. Remove or choose a different output directory before repeating public reproduction.

## Scientific lock

- ERA5-Land accumulated surface solar radiation is converted from J m-2 to W m-2 by division by 3600 before feature derivation.
- Five outer station folds are used; held-out stations are never used for training or boosting-round selection.
- Four remaining original folds are used as station-grouped inner validation folds.
- The deterministic selected round is `floor((b2 + b3) / 2 + 0.5)` after sorting four inner best iterations.
- The final outer model uses fixed rounds and no validation set or early stopping.
- Station predictions use a four-cell grid stencil and bilinear interpolation.
- Dew point is constrained only after same-fold, same-key alignment with temperature.
- Wind is modelled as rotated Ralong/Rcross residuals and reconstructed to U/V; wind speed is vector magnitude.
- The paired station-cluster bootstrap uses 2,000 replicates and seed 20260825; model training seed is 20260127.
- Primary WCT uses observed temperature at or below 0 °C, the standard Celsius formula, wind converted to km h-1 and a 0.1 m s-1 numerical floor.
- Existing direct-WCT OOF predictions are an input and are never retrained by this repository.

## Boundaries

This candidate contains no station-hour tables, station identities, raw observations, provider/site identifiers, coordinates, model files, NetCDF, Parquet or full-grid outputs. The external result is a calendar-aligned cross-year operational stress test, not same-year validation. See `docs/RESTRICTED_DATA_POLICY.md` and `docs/DATA_AVAILABILITY.md`.

## Licensing and data restrictions

- **Code:** MIT License; see `LICENSE`. Copyright (c) 2026 Yu Yue, Yannis P. Pitsiladis, and contributors.
- **Public-safe aggregate data:** CC BY 4.0, limited to the paths expressly listed in `DATA_LICENSE.md`.
- **Third-party and restricted data:** excluded; see `THIRD_PARTY_DATA.md` and `docs/RESTRICTED_DATA_POLICY.md`.

The licenses do not state or imply that all raw data are public. This repository does not contain and cannot execute the permission-controlled external endpoint without separately authorized inputs. It contains no raw ERA5-Land NetCDF, raw station/provider observations, Olympic venue hourly records, identities, coordinates, provider IDs, models, row-level predictions or complete grids.

## Final figure mapping

Public reproduction writes `Figure_1_workflow`, `Figure_2_component_RMSE`, `Figure_3_monthly_representativeness`, `Figure_4_primary_WCT`, `Figure_5_direct_external` and `Supplementary_Figure_2_direct_heterogeneity` as PNG/PDF/manifest sets. Supplementary Figure 1 (study domain) requires author handling because its coordinate-bearing source is not public. Supplementary Figure 3 (representative external time series) is frozen and excluded with its generator and row-level source data.
