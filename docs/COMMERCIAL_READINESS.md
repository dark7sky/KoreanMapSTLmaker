# Commercial Readiness

This project is close to a publishable local tool, but commercial release should be treated as a product process, not only a code milestone.

## Current Release Gate

Run:

```powershell
.\.venv\Scripts\python.exe scripts\release_check.py
```

For a quicker check while iterating:

```powershell
.\.venv\Scripts\python.exe scripts\release_check.py --skip-tests
```

The release check verifies:

- required user-facing docs and sample registry files exist
- the master plan has only the two external real-data validation items remaining
- `datasets.sample.json` points to existing sample files
- `scripts\auto_build.py` can validate the sample registry
- optional `output\real_data_acceptance.json` evidence is valid when present
- pytest passes, unless `--skip-tests` is used

## GUI Readiness

Commercial users should start from the Streamlit GUI, not from raw CLI commands:

```powershell
.\.venv\Scripts\streamlit.exe run app\streamlit_app.py
```

The GUI exposes:

- `빠른 제작` for coordinate-based area creation, file upload, model build, and STL download
- `Auto Build` for area + registry based validation/build
- `Manual Build` for advanced path and field control
- `Data Prep` for command generation around fetch/import/inspect workflows

Before a paid release, run at least one real dataset through `Auto Build` with `Validate only` enabled, then rerun with model generation enabled and verify STL download plus preview output.

## Final Real-Data Acceptance

The last two master-plan items should only be closed after validating non-sample external data. Generate the reports:

```powershell
.\.venv\Scripts\python.exe scripts\validate_real_dataset.py `
  --area data\areas\real_area.geojson `
  --buildings data\buildings\real_buildings.shp `
  --dem data\dem\real_dem.tif `
  --json-out output\real_dataset_validation.json

.\.venv\Scripts\python.exe scripts\validate_real_dem.py `
  --dem data\dem\real_dem.tif `
  --area data\areas\real_area.geojson `
  --json-out output\real_dem_validation.json
```

Then create acceptance evidence:

```powershell
.\.venv\Scripts\python.exe scripts\real_data_acceptance.py `
  --dataset-report output\real_dataset_validation.json `
  --dem-report output\real_dem_validation.json `
  --out output\real_data_acceptance.json
```

The acceptance script rejects committed sample fixture paths by default. Once `REAL_DATA_ACCEPTANCE PASS` appears, the remaining two master-plan items can be checked off with real evidence.

## Product Requirements Before Public Sale

- The repository now includes a proprietary `LICENSE`; replace or expand it with counsel-reviewed customer terms before paid distribution.
- Verify third-party Python package licenses against your intended distribution model.
- Verify VWorld, NGII, Public Data Portal, and any other source-data licenses for commercial use.
- Validate at least one real VWorld/GIS building dataset and one real DEM dataset, then archive the validation reports.
- Decide whether generated model outputs can be redistributed, sold, or only used privately under each data source license.
- Add versioned release artifacts and a changelog before publishing outside private use.

## Support Boundary

The code can automate local modeling when data is available and licensed. It does not bypass portal approval, login, payment, API key, or license obligations.
