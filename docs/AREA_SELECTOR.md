# Area Selector

`tools/area_selector.html` is a small local map tool for creating an `area.geojson` file.

## Use

Open:

```text
tools/area_selector.html
```

Draw one rectangle or polygon, then click `Download`.

The exported file is in `EPSG:4326`, so place it under `data/areas/` and pass the CRS when using it.

The panel creates two PowerShell command templates. Update the paths, choose `Inspect data`, then use `Copy Command`:

```powershell
.\.venv\Scripts\python.exe scripts\inspect_data.py `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --buildings data\buildings\my_region_buildings.shp `
  --dem data\dem\my_region_dem.tif
```

Confirm the CRS and bounds overlap, then choose `Make model` and copy the model command:

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

## Notes

- The map uses OpenStreetMap tiles through Leaflet.
- No VWorld API key is required.
- The generated area file contains longitude/latitude coordinates.
- Use `Inspect data` first to confirm area, building, and DEM overlap.
- Keep the first real test area small, then expand after DEM/building overlap is confirmed.
