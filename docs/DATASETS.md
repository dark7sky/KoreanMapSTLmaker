# Dataset Registry

Use `datasets.json` to keep local area, DEM, and building footprint paths together. The registry is optional; when it is not present, the listing command prints an empty JSON summary.

Example `datasets.json` at the project root:

```json
{
  "datasets": [
    {
      "name": "sample_block",
      "area": "data/areas/sample_block.geojson",
      "dem": "data/dem/sample_block_dem.tif",
      "buildings": "data/buildings/sample_block_buildings.geojson",
      "target_crs": "EPSG:32652",
      "area_crs": "EPSG:4326",
      "building_crs": "EPSG:5186",
      "height_fields": ["height_m", "height"],
      "floor_fields": ["floors", "stories"],
      "building_base_mode": "min",
      "coverage_bounds": [126.9, 37.4, 127.2, 37.7],
      "source_date": "2024-11-01",
      "license": "ODC-BY-1.0",
      "source_url": "https://example.com/datasets/sample_block",
      "notes": "Optional dataset-specific hints."
    }
  ]
}
```

This repository also includes `datasets.sample.json`, a ready-to-run registry for the committed sample area, DEM, and building fixture. Use it to test the registry and auto-build workflow before preparing real data:

```powershell
.\.venv\Scripts\python.exe scripts\auto_build.py `
  --area data\sample\area.geojson `
  --registry datasets.sample.json `
  --dry-run
```

List registered datasets:

```powershell
.\.venv\Scripts\python.exe scripts\list_datasets.py
```

Use a different registry file:

```powershell
.\.venv\Scripts\python.exe scripts\list_datasets.py --registry data\datasets.json
```

Generate command templates for a named dataset:

```powershell
.\.venv\Scripts\python.exe scripts\command_from_dataset.py sample_block
```

Select datasets that overlap a drawn area:

```powershell
.\.venv\Scripts\python.exe scripts\select_dataset.py `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --registry datasets.json
```

Print inspect/model commands for the best overlapping dataset:

```powershell
.\.venv\Scripts\python.exe scripts\select_dataset.py `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --registry datasets.json `
  --commands
```

Run the best overlapping dataset end to end:

```powershell
.\.venv\Scripts\python.exe scripts\auto_build.py `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --registry datasets.json `
  --output-name my_area `
  --dry-run `
  --summary-out output\my_area_auto_build.json
```

Remove `--dry-run` after the selected dataset and validation report look correct.

The script prints two PowerShell command templates:

- `scripts\inspect_data.py` with `--area`, `--buildings`, `--dem`, and optional `--area-crs` / `--building-crs`
- `make_model.py` through `.venv\Scripts\python.exe` with `--area`, `--buildings`, `--dem`, `--out`, plus optional metadata flags (`--target-crs`, repeated `--height-field`, repeated `--floor-field`, and `--building-base-mode`)

The command validates that:

- the registry is valid JSON
- the top-level value is an object with a `datasets` list
- every dataset has a unique non-empty `name`
- every dataset has non-empty string paths for `area`, `dem`, and `buildings`
- optional `target_crs`, `area_crs`, `building_crs`, and `notes` are non-empty strings when present
- optional `building_base_mode` is one of `representative`, `min`, `mean`, or `min-corners`
- optional `height_fields` and `floor_fields` are non-empty lists of non-empty strings when present
- optional `coverage_bounds` is a list of four numeric values in `[minx, miny, maxx, maxy]` order when present
- optional `source_date`, `license`, and `source_url` are non-empty strings when present

The JSON summary reports the resolved path for each dataset input, lists any missing path fields in `missing_paths`, and includes a `metadata` object when optional fields are present.
Dataset selection expects `coverage_bounds` to use the same CRS as `--target-crs`.

After a dataset is selected, add run-specific generation options such as `--export-format gltf`, `--interpolate-nodata`, smoothing, scale, and base plate flags to the printed `make_model.py` command as needed.

## Build Dataset Index

Generate an index for DEM rasters or building vectors so you can review coverage and metadata before creating registry entries.

```powershell
.\.venv\Scripts\python.exe scripts\build_dataset_index.py `
  --root data\dem `
  --kind dem `
  --out output\dem_dataset_index.json `
  --target-crs EPSG:5179
```

```powershell
.\.venv\Scripts\python.exe scripts\build_dataset_index.py `
  --root data\buildings `
  --kind buildings `
  --out output\building_dataset_index.json `
  --target-crs EPSG:5179
```

Behavior:

- recursively scans `--root`
- DEM extensions: `.tif`, `.tiff`
- building extensions: `.shp`, `.gpkg`, `.geojson`, `.json`
- writes JSON with `type`, `path`, `crs`, `bounds`, `coverage_bounds`, and basic `metadata`
- stores `path` relative to `--root` for registry-friendly copying
