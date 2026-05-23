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

## 4. Generate Model

Run:

```powershell
.\.venv\Scripts\python.exe make_model.py `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --buildings data\buildings\my_region_buildings.shp `
  --dem data\dem\my_region_dem.tif `
  --out output\my_area.stl `
  --terrain-resolution 10 `
  --height-field HEIGHT `
  --floor-field GRND_FLR `
  --separate `
  --preview
```

Start with `--terrain-resolution 10` or `20`. Lower the value after the geometry looks correct.

## 5. Review Output

Open:

```text
output/my_area_preview.html
```

Also check:

```text
output/my_area_summary.json
```

The summary contains DEM bounds, valid terrain samples, building counts, skipped buildings, and height source statistics.
