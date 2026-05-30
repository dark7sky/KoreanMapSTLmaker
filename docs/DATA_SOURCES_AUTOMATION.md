# Data Sources and Automation Plan

Phase 13 data acquisition supports two explicit modes:

- keyless offline mode: fully local files, no API key, no provider login
- key-required online-assisted mode: live building fetch with `VWORLD_API_KEY`, then local reuse

This project still works best with local files:

- area polygon: GeoJSON
- terrain: GeoTIFF DEM
- buildings: SHP, GeoPackage, or GeoJSON with height/floor attributes

The next data milestone is to automate as much of this as possible without making the local workflow fragile.

## Current Manual Preparation

### Area

Use `tools/area_selector.html` to draw a polygon and download `area.geojson`.

Expected location:

```text
data/areas/my_area.geojson
```

Area selector output is usually `EPSG:4326`, so pass:

```powershell
--area-crs EPSG:4326
```

### Buildings

Recommended source:

- VWorld / Public Data Portal GIS Building Integrated Information
- Bulk file data when available, or WFS/REST API when an API key is configured

Useful fields vary by source, but common candidates are:

```text
HEIGHT
BLD_HEIGHT
GRND_FLR
FLOOR_CNT
```

The app already inspects building fields and suggests likely height/floor fields.

### Terrain

Recommended source:

- NGII / National Geographic Information Institute DEM or terrain products
- Public Data Portal metadata can help identify DEM products, but direct model input should be a local GeoTIFF

Expected location:

```text
data/dem/my_region_dem.tif
```

If a DEM source is not GeoTIFF, convert it with QGIS/GDAL before modeling, or use `scripts/import_dem.py`.

## What Can Be Automated

### High-confidence automation

- Fetch building footprints/attributes from VWorld-style WFS/REST APIs for a selected bounding box.
- Save fetched data as local GeoJSON or GeoPackage.
- Cache API responses by provider, bounds, CRS, and timestamp.
- Inspect fetched fields and prefill height/floor options.
- Register imported building/DEM files into `datasets.json`.
- Validate CRS and overlap before model generation.

### Partial automation

- DEM registration and conversion can be automated after the user downloads source files.
- DEM tile selection can be automated if local metadata/index files are available.
- Full DEM download may still require manual login, approval, or portal interaction depending on the source.

### Not assumed automatic yet

- API key issuance.
- Portal login.
- Downloading datasets whose license or portal flow requires explicit user action.
- Using 3D tile/model services as printable building geometry, because licenses, formats, and access rules may differ from simple building footprints.

## Current CLI Workflows

### 1) Keyless offline mode (no API key required)

Use local area/building/DEM files only.

```powershell
.\.venv\Scripts\python.exe scripts\inspect_data.py `
  --area data\areas\my_area.geojson `
  --area-crs EPSG:4326 `
  --buildings data\buildings\my_area_buildings.geojson `
  --dem data\dem\my_region_dem.tif
```

If DEM candidate files are already indexed in `datasets.json`, find overlapping tiles:

```powershell
.\.venv\Scripts\python.exe scripts\find_dem_tiles.py `
  --registry datasets.json `
  --area data\areas\my_area.geojson `
  --area-crs EPSG:4326 `
  --target-crs EPSG:5179 `
  --limit 5
```

Import/register a downloaded DEM as local GeoTIFF and validate overlap:

```powershell
.\.venv\Scripts\python.exe scripts\import_dem.py `
  --source downloads\dem\raw_dem.tif `
  --out data\dem\my_region_dem.tif `
  --target-crs EPSG:5179 `
  --reproject `
  --registry datasets.json `
  --validate-area data\areas\my_area.geojson `
  --validate-area-crs EPSG:4326
```

Notes:

- `import_dem.py` does not download from portals. It imports local source files you already obtained.
- Source issuance/login/approval flows (NGII/Public Data portals) are external and not automated by this repo.

### 2) Key-required online-assisted mode (live building fetch)

```powershell
.\.venv\Scripts\python.exe scripts\fetch_buildings.py `
  --area data\areas\my_area.geojson `
  --area-crs EPSG:4326 `
  --provider vworld-gis-building `
  --out data\buildings\my_area_buildings.geojson `
  --cache-dir .cache\data_sources `
  --validate-area data\areas\my_area.geojson `
  --validate-area-crs EPSG:4326
```

Load key from `.env` (recommended):

```powershell
Set-Content .env "VWORLD_API_KEY=your-issued-key"
.\.venv\Scripts\python.exe scripts\fetch_buildings.py `
  --area data\areas\my_area.geojson `
  --area-crs EPSG:4326 `
  --provider vworld-gis-building `
  --out data\buildings\my_area_buildings.geojson `
  --env-file .env
```

Or set it only for current PowerShell session:

```powershell
$env:VWORLD_API_KEY = "your-issued-key"
```

Offline simulation without live API key (fixture response):

```powershell
.\.venv\Scripts\python.exe scripts\fetch_buildings.py `
  --bounds 126.9789 37.5660 126.9820 37.5682 `
  --crs EPSG:4326 `
  --out data\buildings\fixture_buildings.geojson `
  --fixture-response tests\fixtures\vworld_buildings_response.json
```

Behavior notes:

- Live mode requires `VWORLD_API_KEY`; missing key fails clearly.
- API key issuance and any provider account/login approval are external/manual steps.
- Live responses are cached in `.cache\data_sources` keyed by provider+bounds+CRS.
- The VWorld provider implementation applies paging and retry handling internally.
- `--validate-area` / `--validate-area-crs` runs overlap validation after fetch.

### 3) DEM import and registration (both modes)

```powershell
.\.venv\Scripts\python.exe scripts\import_dem.py `
  --source downloads\dem_source_file.tif `
  --out data\dem\my_region_dem.tif `
  --target-crs EPSG:5179 `
  --registry datasets.json `
  --validate-area data\areas\my_area.geojson `
  --validate-area-crs EPSG:4326
```

The command updates local DEM files and registry metadata. It does not perform portal login or dataset purchase/issuance flows.

## Implementation Tasks

1. Create `src/data_sources/` package.
2. Add provider interfaces for `fetch_buildings(bounds, crs)` and `register_dem(path)`.
3. Add VWorld building provider with mocked tests first.
4. Add local response cache and metadata sidecars.
5. Add CRS/bounds validation after every fetch/import.
6. Add dataset registry write/update helpers.
7. Add Streamlit data-prep tab.
8. Add docs for online and offline workflows. (done)

## Official Source Notes

Public Data Portal currently lists VWorld WebGL/3D map APIs as key-required, and GIS Building Integrated Information as JSON/XML linked API data. Public listings also note that traffic limits can vary by provider policy.

Therefore, the project should keep two paths:

- offline-first: user downloads/registers files, no API key required
- online-assisted: optional key enables fetching building data for selected bounds
