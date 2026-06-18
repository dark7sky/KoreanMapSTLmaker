# Terrain Building STL

Local tool for creating a terrain-aware 3D model from:

- an area polygon (`GeoJSON`, `SHP`, `GPKG`, etc.)
- a DEM raster (`GeoTIFF`)
- building footprints with height attributes

The first target is a personal/local CLI workflow. There is also an optional local Docker/FastAPI scaffold for future service work, but the repo does not depend on it for the main build path.

## MVP Command

```powershell
python make_model.py `
  --area data/sample/area.geojson `
  --buildings data/sample/buildings.geojson `
  --dem data/sample/dem.tif `
  --out output/model.stl
```

## Local venv

This repository is set up to run from a project-local virtual environment.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe make_model.py --help
```

If pip installation is difficult on a machine because of GDAL wheels, Conda is the fallback:

```powershell
conda create -n terrain-stl python=3.11
conda activate terrain-stl
conda install -c conda-forge geopandas rasterio shapely pyproj trimesh numpy pytest
```

## Tests

Run tests from the local virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run only the Streamlit scaffold helper tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_app_ui_state.py tests\test_app_runner.py
```

Pytest is configured to use a workspace-local temporary base directory (`.pytest_tmp`) for more reliable execution on Windows.

## Generate Sample Data

The sample area is committed as GeoJSON. Generate the sample DEM and buildings:

```powershell
.\.venv\Scripts\python.exe scripts\create_sample_data.py
```

Or run the full sample workflow:

```powershell
.\scripts\run_sample.ps1
```

## Local Streamlit App (Scaffold)

Launch the local single-page app:

```powershell
.\.venv\Scripts\streamlit.exe run app\streamlit_app.py
```

## Optional Local Web Service Scaffold

See [`docs/WEB_SERVICE.md`](docs/WEB_SERVICE.md) for the containerized FastAPI run path, mount points, and environment variables.

The scaffold is intentionally local-first and includes health, synchronous build/job, and workspace-local upload/artifact endpoints.
An optional static browser console lives at `web_frontend/index.html`; open it directly after starting the web service to check `/health` and prepare or submit a `/build` JSON payload. It does not require Node or npm for tests.

Then run an end-to-end sample:

```powershell
.\.venv\Scripts\python.exe make_model.py `
  --area data/sample/area.geojson `
  --buildings data/sample/buildings.geojson `
  --dem data/sample/dem.tif `
  --out output/sample_model.stl `
  --export-format stl `
  --export-format obj `
  --export-format glb `
  --export-format gltf `
  --terrain-resolution 10 `
  --interpolate-nodata `
  --terrain-smoothing-iterations 1 `
  --terrain-smoothing-factor 0.4 `
  --z-scale 1.5 `
  --model-scale 1.0 `
  --base-plate-thickness 1.0 `
  --base-plate-margin 3.0 `
  --building-diagnostics-limit 200 `
  --building-base-mode representative `
  --separate `
  --preview
```

Inspect sample inputs:

```powershell
.\.venv\Scripts\python.exe scripts\inspect_data.py `
  --area data/sample/area.geojson `
  --buildings data/sample/buildings.geojson `
  --dem data/sample/dem.tif
```

Repair an existing mesh (STL/OBJ):

```powershell
.\.venv\Scripts\python.exe scripts\repair_mesh.py `
  --input output/sample_model.stl `
  --output output/sample_model_repaired.stl `
  --summary-out output/sample_model_repair_summary.json
```

Import generated outputs into Blender:

```powershell
blender --python scripts\blender_import.py -- output\sample_model_summary.json --clear-scene --set-metric-units
```

Reuse generated outputs from a local cache (same inputs/options => cache hit):

```powershell
.\.venv\Scripts\python.exe scripts\cache_model.py `
  --job job.json `
  --cache-dir .cache\model_runner
```

`job.json` uses the same keys as a `scripts\run_batch.py` job object.

## Current Scope

Implemented:

- CLI skeleton
- area loading and CRS conversion
- DEM sampling over selected area
- terrain mesh generation with base thickness
- optional terrain smoothing
- optional DEM nodata interpolation inside the selected area (`--interpolate-nodata`)
- vertical terrain exaggeration (`--z-scale`)
- print-ready model scale and optional base plate controls
- building footprint clipping
- optional building footprint simplification (`--simplify-tolerance`)
- building height fallback rules
- simple building extrusion
- combined STL export
- optional OBJ export (`--export-format obj`)
- optional GLB export (`--export-format glb`)
- optional GLTF export (`--export-format gltf`)
- scene-based terrain/building visual separation for OBJ/GLB/GLTF when `--separate` is used
- summary JSON export
- self-contained preview HTML export
- mesh quality summary in the JSON output
- mesh quality includes non-manifold edge and degenerate face counts
- per-building diagnostics in the JSON output
- normal cleanup before export
- standalone mesh repair command for STL/OBJ (`scripts/repair_mesh.py`)
- robust polygonal geometry repair for invalid area/building inputs
- building base elevation modes: representative, min, mean
- polygon holes are preserved during building extrusion
- dataset command generation from registry entries (`scripts/command_from_dataset.py`)
- DEM/building dataset index generation (`scripts/build_dataset_index.py`)
- cached model re-run helper (`scripts/cache_model.py`)
- master plan progress report (`scripts/progress_report.py`)
- Blender import helper (`scripts/blender_import.py`)

MVP limitations:

- Terrain is sampled on a regular grid.
- Building base elevation uses a representative point by default.
- Large areas should use coarse terrain resolution first.
- Z-scale changes terrain and building base elevations; building heights stay in real units.

Next-stage features:

- Richer mesh repair checks for non-manifold edges and degenerate faces.
- Area overlap selection from named datasets.

## Output

The tool writes:

- `model.stl`
- `model.obj` when `--export-format obj` is passed
- `model.glb` when `--export-format glb` is passed
- `model.gltf` when `--export-format gltf` is passed
- `model_summary.json`
- `model_preview.html` when `--preview` is passed

Summary includes area, terrain resolution, minimum elevation, valid and interpolated terrain sample counts, building count, height source counts, mesh quality, selected building base mode, generation options, vertices, and faces.
Use `scripts\command_from_summary.py output\model_summary.json` to print a rerun command from the saved options.
The preview panel also shows a compact summary and clickable local links for generated `obj` / `glb` / `gltf` / separate `stl` outputs when those files are present in the summary.

## Master Backlog

See `docs/MASTER_PLAN.md`.

Show current backlog progress:

```powershell
.\.venv\Scripts\python.exe scripts\progress_report.py
```

## Real Data

See `docs/DATA_PREP.md` for preparing DEM and building files.
See `docs/REAL_DATA_GUIDE.md` for public Korean building/DEM source candidates and a real-data checklist.
See `docs/DATA_SOURCES_AUTOMATION.md` for the planned optional data-fetch/import workflow.

## Draw an Area

Open `tools/area_selector.html` to draw a polygon and download `area.geojson`.

See `docs/AREA_SELECTOR.md` for details.

## End-to-End Workflow

See `docs/WORKFLOW.md` for the recommended real-data sequence.

The workflow also describes the height/floor field selector, building base mode choice, mesh quality review, and dataset registry.

## Dataset Registry

See `docs/DATASETS.md` for the optional `datasets.json` format and listing command.

Generate inspect/model command templates for a named dataset:

```powershell
.\.venv\Scripts\python.exe scripts\command_from_dataset.py sample_block
```
