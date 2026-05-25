# Terrain Building STL

Local tool for creating a terrain-aware 3D model from:

- an area polygon (`GeoJSON`, `SHP`, `GPKG`, etc.)
- a DEM raster (`GeoTIFF`)
- building footprints with height attributes

The first target is a personal/local CLI workflow, with no web service or API dependency.

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
  --terrain-resolution 10 `
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

## Current Scope

Implemented:

- CLI skeleton
- area loading and CRS conversion
- DEM sampling over selected area
- terrain mesh generation with base thickness
- optional terrain smoothing
- vertical terrain exaggeration (`--z-scale`)
- print-ready model scale and optional base plate controls
- building footprint clipping
- optional building footprint simplification (`--simplify-tolerance`)
- building height fallback rules
- simple building extrusion
- combined STL export
- optional OBJ export (`--export-format obj`)
- optional GLB export (`--export-format glb`)
- summary JSON export
- self-contained preview HTML export
- mesh quality summary in the JSON output
- mesh quality includes non-manifold edge and degenerate face counts
- per-building diagnostics in the JSON output
- normal cleanup before export
- standalone mesh repair command for STL/OBJ (`scripts/repair_mesh.py`)
- building base elevation modes: representative, min, mean
- polygon holes are preserved during building extrusion
- dataset command generation from registry entries (`scripts/command_from_dataset.py`)

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
- `model_summary.json`
- `model_preview.html` when `--preview` is passed

Summary includes area, terrain resolution, minimum elevation, building count, height source counts, mesh quality, selected building base mode, generation options, vertices, and faces.
Use `scripts\command_from_summary.py output\model_summary.json` to print a rerun command from the saved options.
The preview panel also shows a compact summary and clickable local links for generated `obj` / separate `stl` outputs when those files are present in the summary.

## Master Backlog

See `docs/MASTER_PLAN.md`.

## Real Data

See `docs/DATA_PREP.md` for preparing DEM and building files.

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
