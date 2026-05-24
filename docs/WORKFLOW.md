# Workflow

This is the recommended local workflow for real data.

## 1. Put Data in Place

Use these folders:

```text
data/areas/       selected area GeoJSON files
data/dem/         DEM GeoTIFF files
data/buildings/   building SHP/GPKG/GeoJSON files
data/raw/         original downloads and archives
output/           generated STL, preview HTML, and summary JSON
```

Large source data and generated output are ignored by git. The `.gitkeep` files only preserve the folder structure.

## 2. Draw Area

Open:

```text
tools/area_selector.html
```

Draw a polygon, download `area.geojson`, and place it under:

```text
data/areas/
```

The area selector also creates a PowerShell command template. Update the paths in the selector panel, then copy the command.

## 3. Preflight Inspect Inputs

Run `scripts\inspect_data.py` before generating the model, especially when you are using newly downloaded data or a freshly drawn area. The area selector command is for `make_model.py`; use the same paths in this inspect command first so path, CRS, and overlap issues show up before a longer STL run.

Run:

```powershell
.\.venv\Scripts\python.exe scripts\inspect_data.py `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --buildings data\buildings\my_region_buildings.shp `
  --dem data\dem\my_region_dem.tif
```

Check that:

- Each requested file reports `"exists": true`.
- CRS values are present, or the missing vector CRS is intentionally supplied with `--area-crs` or `--building-crs`.
- Area, building, and DEM bounds overlap in the same coordinate system.
- Building fields include `HEIGHT`, `GRND_FLR`, or custom equivalents that you will pass to `make_model.py`.
- DEM width, height, band count, resolution, and nodata look plausible for the selected area.

If bounds do not overlap, stop and fix CRS/path inputs before generation. If the area selector GeoJSON reports a missing CRS, keep `--area-crs EPSG:4326` in both the inspect and generate commands.

## 4. Choose Building Fields

Use the field list from `inspect_data.py` to choose the best height and floor attributes before generation.

Recommended order:

- Prefer a measured height field when one exists.
- Use a floor count field as a fallback with the default floor height.
- Leave a selector blank only when the dataset does not provide that attribute.

Current CLI flags:

```text
--height-field HEIGHT
--floor-field GRND_FLR
```

Next-stage UI workflow: the local app should read the inspected building attributes, show searchable height and floor field selectors, preview how many buildings each selector covers, and pass the selected fields into `make_model.py`.

## 5. Choose Building Base Mode

Building base elevation controls how footprints sit on sloped terrain. Choose a base mode:

```text
representative   sample terrain at a representative point
min              use the minimum sampled terrain elevation under the footprint
mean             use the mean sampled terrain elevation under the footprint
```

Use `representative` for fast checks and small buildings. Use `min` or `mean` when sloped sites need more predictable placement.

Current CLI flag:

```text
--building-base-mode representative
```

## 6. Generate Model

Run:

```powershell
.\.venv\Scripts\python.exe make_model.py `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --buildings data\buildings\my_region_buildings.shp `
  --dem data\dem\my_region_dem.tif `
  --out output\my_area.stl `
  --export-format stl `
  --export-format obj `
  --terrain-resolution 10 `
  --z-scale 1.5 `
  --building-base-mode representative `
  --height-field HEIGHT `
  --floor-field GRND_FLR `
  --separate `
  --preview
```

Start with `--terrain-resolution 10` or `20`. Lower the value after the geometry looks correct. Use `--z-scale` only when the terrain relief needs visual exaggeration; building heights remain in real units.

## 7. Review Output

Open:

```text
output/my_area_preview.html
```

Also check:

```text
output/my_area_summary.json
```

The summary contains DEM bounds, valid terrain samples, building counts, skipped buildings, height source statistics, mesh quality, and the selected building base mode.
Mesh quality currently includes watertight status, Euler number, volume, bounding box, non-manifold edge count, and degenerate face count.

## 8. Dataset Registry

For repeated work with the same source data, maintain a dataset registry that names each DEM and building dataset and records the details needed to select it reliably.

Current registry fields:

- Dataset name.
- Area path.
- DEM path.
- Building path.
- Optional CRS hints.
- Optional height and floor field preferences.
- Optional building base mode.
- Optional notes.

Run:

```powershell
.\.venv\Scripts\python.exe scripts\list_datasets.py
```

Generate inspect/model command templates from a named dataset:

```powershell
.\.venv\Scripts\python.exe scripts\command_from_dataset.py sample_block
```

Future registry fields should add coverage bounds, download date, and license notes.
