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

## Generate Sample Data

The sample area is committed as GeoJSON. Generate the sample DEM and buildings:

```powershell
.\.venv\Scripts\python.exe scripts\create_sample_data.py
```

Then run an end-to-end sample:

```powershell
.\.venv\Scripts\python.exe make_model.py `
  --area data/sample/area.geojson `
  --buildings data/sample/buildings.geojson `
  --dem data/sample/dem.tif `
  --out output/sample_model.stl `
  --terrain-resolution 10 `
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

## Current Scope

Implemented:

- CLI skeleton
- area loading and CRS conversion
- DEM sampling over selected area
- terrain mesh generation with base thickness
- building footprint clipping
- building height fallback rules
- simple building extrusion
- combined STL export
- summary JSON export
- self-contained preview HTML export

MVP limitations:

- Terrain is sampled on a regular grid.
- Building polygons with holes are simplified to exterior rings for extrusion.
- Building base elevation uses a representative point by default.
- Large areas should use coarse terrain resolution first.

## Output

The tool writes:

- `model.stl`
- `model_summary.json`
- `model_preview.html` when `--preview` is passed

Summary includes area, terrain resolution, minimum elevation, building count, height source counts, vertices, and faces.

## Master Backlog

See `docs/MASTER_PLAN.md`.

## Real Data

See `docs/DATA_PREP.md` for preparing DEM and building files.

## Draw an Area

Open `tools/area_selector.html` to draw a polygon and download `area.geojson`.

See `docs/AREA_SELECTOR.md` for details.

## End-to-End Workflow

See `docs/WORKFLOW.md` for the recommended real-data sequence.
