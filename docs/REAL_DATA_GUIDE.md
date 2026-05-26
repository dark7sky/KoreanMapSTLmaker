# Real Data Guide

This guide is for replacing the sample files with real Korean DEM and building data.

## Recommended Offline-First Path

Use downloaded files first. It is easier to reproduce, does not depend on per-request API limits, and works well with the current CLI.

1. Draw or prepare an area polygon.
2. Download DEM as a local raster.
3. Download building footprints as SHP/GPKG/GeoJSON.
4. Inspect all inputs before generating a model.
5. Register reusable datasets in `datasets.json`.

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
- The online-assisted building fetcher is planned, not complete yet.
- After download, inspect fields with:

```powershell
.\.venv\Scripts\python.exe scripts\inspect_data.py `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --buildings data\buildings\gis_buildings.shp `
  --dem data\dem\dem.tif
```

Choose the height field with `--height-field` if a measured height field exists. If only floor count exists, pass it with `--floor-field` and tune `--default-floor-height`.

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
