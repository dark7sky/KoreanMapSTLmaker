# Data Sources and Automation Plan

This project currently works best with local files:

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

If a DEM source is not GeoTIFF, convert it with QGIS/GDAL before modeling, or use the planned `import_dem.py` helper once implemented.

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

## Planned CLI Commands

### Fetch buildings

```powershell
.\.venv\Scripts\python.exe scripts\fetch_buildings.py `
  --area data\areas\my_area.geojson `
  --area-crs EPSG:4326 `
  --provider vworld-gis-building `
  --out data\buildings\my_area_buildings.geojson `
  --cache-dir .cache\data_sources
```

Configuration:

```powershell
$env:VWORLD_API_KEY = "..."
```

The command should fail clearly when a key is required but missing, and should never require a key for existing local files.

### Import DEM

```powershell
.\.venv\Scripts\python.exe scripts\import_dem.py `
  --source downloads\dem_source_file `
  --out data\dem\my_region_dem.tif `
  --target-crs EPSG:5179 `
  --registry datasets.json
```

The helper should preserve source metadata and write a sidecar JSON file.

## Implementation Tasks

1. Create `src/data_sources/` package.
2. Add provider interfaces for `fetch_buildings(bounds, crs)` and `register_dem(path)`.
3. Add VWorld building provider with mocked tests first.
4. Add local response cache and metadata sidecars.
5. Add CRS/bounds validation after every fetch/import.
6. Add dataset registry write/update helpers.
7. Add Streamlit data-prep tab.
8. Add docs for online and offline workflows.

## Official Source Notes

Public Data Portal currently lists VWorld WebGL/3D map APIs as key-required, and GIS Building Integrated Information as JSON/XML linked API data. Public listings also note that traffic limits can vary by provider policy.

Therefore, the project should keep two paths:

- offline-first: user downloads/registers files, no API key required
- online-assisted: optional key enables fetching building data for selected bounds
