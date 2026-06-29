# Real Data Guide

This guide is for replacing the sample files with real Korean DEM and building data.

## Recommended Offline-First Path (Keyless)

Use downloaded files first. It is easier to reproduce, does not depend on per-request API limits, and works well with the current CLI.

1. Draw or prepare an area polygon.
2. Download DEM as a local raster.
3. Download building footprints as SHP/GPKG/GeoJSON.
4. Inspect all inputs before generating a model.
5. Register reusable datasets in `datasets.json`.

No API key is required for this path.

## Phase 1 Offline Real-Data Preflight

Before running `make_model.py` with real files, run the offline validation script:

```powershell
.\.venv\Scripts\python.exe scripts\validate_real_dataset.py `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --buildings data\buildings\gis_buildings.shp `
  --dem data\dem\dem.tif `
  --target-crs EPSG:5179 `
  --format text `
  --json-out output\real_data_validation.json `
  --manifest-out output\real_data_manifest.json
```

What this checks without network/API access:

- required files exist and can be opened
- reproducibility manifest with resolved file paths, sizes, and SHA-256 hashes
- required SHP sidecars for building data: `.shp`, `.shx`, `.dbf`, `.prj`
- area/buildings feature counts, geometry types, and CRS presence
- likely building `height`/`floor` fields based on name matching
- DEM CRS/bounds/size/band sanity
- overlap of area vs buildings and area vs DEM in `--target-crs`

Treat any `FAIL` as a blocker before Phase 1 model generation. `WARN` means usable but review recommended.

The validation is complete only for the local files passed to the command. This repo cannot certify a real
VWorld/Public Data download unless you point `--buildings` at that downloaded dataset and the command passes.

Archive both outputs with the generated model:

- `real_data_validation.json`: full machine-readable validation report
- `real_data_manifest.json`: exact local fixture/data manifest for repeatable reruns

When both building/area/DEM validation and DEM-only validation pass on non-sample external files, write final acceptance evidence:

```powershell
.\.venv\Scripts\python.exe scripts\real_data_acceptance.py `
  --dataset-report output\real_data_validation.json `
  --dem-report output\real_dem_validation.json `
  --out output\real_data_acceptance.json
```

### Real Building Data Checklist

Use this checklist when preparing VWorld/GIS Building Integrated Information files:

- Download file-based building data when available instead of relying on a live API call.
- Keep all SHP sidecars in one directory: `.shp`, `.shx`, `.dbf`, `.prj`; keep `.cpg` too if provided.
- Keep the original downloaded archive or a note with portal URL, download date, license, and query/coverage area.
- Run `scripts\validate_real_dataset.py` against the downloaded building file, selected area, and DEM.
- Confirm `buildings_feature_count`, `buildings_crs_present`, `buildings_geometry_type`, and `area_buildings_overlap` pass.
- Review `buildings_height_field_candidates` and `buildings_floor_field_candidates`; pass the selected fields to `make_model.py`.
- Save `output\real_data_validation.json` and `output\real_data_manifest.json` next to generated STL/GLTF outputs.

## Building Data

Primary candidate:

- VWorld / Public Data Portal GIS Building Integrated Information
- Typical formats: SHP for bulk file data, WMS/WFS or JSON/XML through linked API entries
- Useful because it combines building geometry with building-register attributes

Public references:

- Public Data Portal GIS Building Integrated Information API listing: <https://www.data.go.kr/data/15123970/openapi.do>
- Public Data Portal standard dataset listing: <https://www.data.go.kr/data/15029175/standard.do>
- VWorld linked data/API pages: <https://www.vworld.kr>

Notes:

- Prefer file download for this project when possible.
- API use may require an application/key, and traffic limits may vary by provider policy.
- For fully offline runs, skip live API fetch and use downloaded files.
- API key issuance/login flows are external to this repo and may require separate portal approval.
- Do not use `LT_C_UQ111` for buildings; it is not a GIS building layer. Obtain the current GIS building data ID from the VWorld API detail page.
- After download, inspect fields with:

```powershell
.\.venv\Scripts\python.exe scripts\inspect_data.py `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --buildings data\buildings\gis_buildings.shp `
  --dem data\dem\dem.tif
```

Choose the height field with `--height-field` if a measured height field exists. If only floor count exists, pass it with `--floor-field` and tune `--default-floor-height`.

Optional online-assisted fetch (key required):

```powershell
Set-Content .env "VWORLD_API_KEY=your-issued-key"
Add-Content .env "VWORLD_BUILDING_DATA_NAME=your-current-building-data-id"
.\.venv\Scripts\python.exe scripts\fetch_buildings.py `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --provider vworld-gis-building `
  --data-name your-current-building-data-id `
  --out data\buildings\area_buildings.geojson `
  --cache-dir .cache\data_sources `
  --validate-area data\areas\area.geojson `
  --validate-area-crs EPSG:4326 `
  --env-file .env
```

Offline simulation with fixture JSON (no key):

```powershell
.\.venv\Scripts\python.exe scripts\fetch_buildings.py `
  --bounds 126.9789 37.5660 126.9820 37.5682 `
  --crs EPSG:4326 `
  --out data\buildings\fixture_buildings.geojson `
  --fixture-response tests\fixtures\vworld_buildings_response.json
```

## DEM Data

Primary candidates:

- NGII / National Geographic Information Institute DEM or terrain products
- Public Data Portal NGII listings and metadata for DEM, numerical map, and national imagery products

Public references:

- NGII / National Geographic Information Platform entry point: <https://map.ngii.go.kr>
- Public Data Portal NGII numerical map listing: <https://www.data.go.kr/data/15015482/fileData.do>
- Public Data Portal NGII imagery/DEM-related listing: <https://www.data.go.kr/data/15015483/fileData.do>

Notes:

- The project expects a GeoTIFF DEM.
- If the downloaded DEM is another raster format, convert it to GeoTIFF in QGIS/GDAL before running `make_model.py`.
- Keep the DEM CRS embedded in the file. A missing raster CRS is treated as an error unless a safe explicit fallback is supported by the command.
- If small nodata holes appear inside the selected area, add `--interpolate-nodata`.

Run the DEM-only offline metadata checklist before import/registration:

```powershell
.\.venv\Scripts\python.exe scripts\validate_real_dem.py `
  --dem downloads\dem\ngii_dem.tif `
  --target-crs EPSG:5179 `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --source-name "NGII/Public Data DEM" `
  --source-date 2026-01-15 `
  --license "Public Data Portal terms" `
  --source-url "https://www.data.go.kr/..." `
  --format text `
  --json-out output\real_dem_validation.json
```

The JSON report is designed to be kept with the imported DEM. It records:

- source/product/date/license/URL fields supplied on the command line
- raster driver, CRS, bounds, shape, resolution, transform, nodata, and dtypes
- first-band elevation min/max/mean and valid/nodata cell counts
- pass/warn/fail checks for GeoTIFF readability, CRS, target CRS match, numeric data, nodata coverage, and optional area overlap
- next-step guidance for reprojection, CRS repair, overlap fixes, or nodata review

Register/import downloaded DEM and validate overlap:

```powershell
.\.venv\Scripts\python.exe scripts\import_dem.py `
  --source downloads\dem\dem_source.tif `
  --out data\dem\dem.tif `
  --target-crs EPSG:5179 `
  --reproject `
  --registry datasets.json `
  --validate-area data\areas\area.geojson `
  --validate-area-crs EPSG:4326
```

Find candidate DEM tiles from registry before import:

```powershell
.\.venv\Scripts\python.exe scripts\find_dem_tiles.py `
  --registry datasets.json `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --target-crs EPSG:5179 `
  --limit 5
```

## CRS Checklist

The default modeling CRS is `EPSG:5179`.

- Area selector GeoJSON usually uses `EPSG:4326`; pass `--area-crs EPSG:4326` if the file has no CRS metadata.
- Building files often include CRS metadata, but SHP sidecar files can be lost. Keep `.shp`, `.shx`, `.dbf`, and `.prj` together.
- DEM should carry its CRS in the raster metadata.
- If `inspect_data.py` says bounds do not overlap, fix CRS assumptions before changing modeling options.

## Minimal Real-Data Command

```powershell
.\.venv\Scripts\python.exe make_model.py `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --buildings data\buildings\gis_buildings.shp `
  --dem data\dem\dem.tif `
  --out output\real_area.stl `
  --export-format stl `
  --export-format gltf `
  --terrain-resolution 20 `
  --interpolate-nodata `
  --building-base-mode representative `
  --preview
```

After geometry is confirmed, lower `--terrain-resolution`, add `--height-field` / `--floor-field`, and add print-specific scale or base plate options.

## Reusable Dataset Registry

For each reusable DEM/building bundle, add a `datasets.json` entry with:

- `coverage_bounds` in the same CRS as `target_crs`
- `source_date`
- `license`
- `source_url`
- preferred `height_fields` and `floor_fields`

Then select a matching dataset for a new area:

```powershell
.\.venv\Scripts\python.exe scripts\select_dataset.py `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --registry datasets.json `
  --commands
```

## Online-Assisted Future

See `docs/DATA_SOURCES_AUTOMATION.md`.

The intended direction is:

- keep local/offline files as the reliable default
- optionally fetch building data when a VWorld/Public Data key is configured
- import/register DEM files after the user downloads them from NGII/Public Data sources
- use fixture responses for repeatable offline testing of fetch logic
