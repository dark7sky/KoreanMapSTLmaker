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
- pytest passes, unless `--skip-tests` is used

## Product Requirements Before Public Sale

- Choose and write an explicit software license or commercial EULA.
- Verify third-party Python package licenses against your intended distribution model.
- Verify VWorld, NGII, Public Data Portal, and any other source-data licenses for commercial use.
- Validate at least one real VWorld/GIS building dataset and one real DEM dataset, then archive the validation reports.
- Decide whether generated model outputs can be redistributed, sold, or only used privately under each data source license.
- Add versioned release artifacts and a changelog before publishing outside private use.

## Support Boundary

The code can automate local modeling when data is available and licensed. It does not bypass portal approval, login, payment, API key, or license obligations.
