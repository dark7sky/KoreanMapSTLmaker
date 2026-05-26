# Data Preparation Guide

This project does not require a live map API for the local workflow. Prepare local files first, then pass them to `make_model.py`.

## 1. Area Polygon

Recommended format: `GeoJSON`

The area file should contain one `Polygon` or `MultiPolygon`.

Example path:

```text
data/areas/my_area.geojson
```

If the file has no CRS metadata, pass it explicitly:

```powershell
--area-crs EPSG:4326
```

For Korean projected meter coordinates, the internal modeling CRS defaults to:

```text
EPSG:5179
```

## 2. DEM / Terrain

Recommended format: GeoTIFF DEM.

Example path:

```text
data/dem/my_region_dem.tif
```

Requirements:

- CRS must be present in the raster.
- Elevation unit should be meters.
- The DEM bounds must overlap the selected area.
- Use a coarse `--terrain-resolution` first, such as `10` or `20`, then lower it after the result is sane.

Example:

```powershell
--dem data/dem/my_region_dem.tif
--terrain-resolution 10
```

## 3. Building Footprints

Recommended format: SHP, GeoPackage, or GeoJSON.

Example path:

```text
data/buildings/my_region_buildings.shp
```

For VWorld / national GIS building master data, useful fields commonly include:

```text
HEIGHT    building height in meters
GRND_FLR  above-ground floor count
```

The tool automatically tries common ASCII field names. If your file uses a different field, pass it explicitly:

```powershell
--height-field HEIGHT
--floor-field GRND_FLR
```

The options can be repeated:

```powershell
--height-field HEIGHT --height-field BLD_HEIGHT
--floor-field GRND_FLR --floor-field FLOOR_CNT
```

Height fallback order:

```text
1. First positive value from height fields
2. First positive value from floor fields * --default-floor-height
3. --default-building-height
```

## 4. First Real-Data Run

Inspect the files first:

```powershell
.\.venv\Scripts\python.exe scripts\inspect_data.py `
  --area data/areas/my_area.geojson `
  --buildings data/buildings/my_region_buildings.shp `
  --dem data/dem/my_region_dem.tif
```

Confirm:

- area/building CRS values are sensible
- area/building/DEM bounds overlap
- building fields include a usable height or floor-count field

Start with a small area.

```powershell
.\.venv\Scripts\python.exe make_model.py `
  --area data/areas/my_area.geojson `
  --buildings data/buildings/my_region_buildings.shp `
  --dem data/dem/my_region_dem.tif `
  --out output/my_area.stl `
  --terrain-resolution 10 `
  --height-field HEIGHT `
  --floor-field GRND_FLR `
  --separate `
  --preview
```

Check:

- `output/my_area_summary.json`
- `output/my_area_preview.html`
- `output/my_area.stl`

## 5. Common Problems

### CRS is missing

Use:

```powershell
--area-crs EPSG:4326
--building-crs EPSG:5179
```

### No DEM samples found

Likely causes:

- DEM does not overlap the selected area.
- Area CRS is wrong.
- DEM CRS metadata is wrong or missing.

### No buildings found

Likely causes:

- Building file does not overlap the area.
- Building CRS is wrong.
- Buildings are smaller than `--min-building-area`.

### STL is too large

Increase terrain resolution:

```powershell
--terrain-resolution 20
```

Then reduce gradually.

## 6. Data Source Notes

For building data, look for GIS building integrated/master information from VWorld or national spatial data portals. Public references describe `HEIGHT` as building height in meters and `GRND_FLR` as above-ground floor count.

For terrain, use a DEM/DTM source that can be downloaded as GeoTIFF or converted to GeoTIFF.

## 7. Online-Assisted Data Preparation

The current program does not automatically download real public data yet. The planned online-assisted path is documented in:

```text
docs/DATA_SOURCES_AUTOMATION.md
```

Short version:

- Buildings are the best first target for automation through VWorld/Public Data Portal linked GIS building APIs.
- DEM should remain offline-first at first: download/register local DEM files, then convert/register them for the model workflow.
- API keys, portal login, and traffic limits should be treated as optional external setup, not as a hard requirement for the core CLI.
