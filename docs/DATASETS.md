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
      "building_base_mode": "dem_min",
      "notes": "Optional dataset-specific hints."
    }
  ]
}
```

List registered datasets:

```powershell
.\.venv\Scripts\python.exe scripts\list_datasets.py
```

Use a different registry file:

```powershell
.\.venv\Scripts\python.exe scripts\list_datasets.py --registry data\datasets.json
```

The command validates that:

- the registry is valid JSON
- the top-level value is an object with a `datasets` list
- every dataset has a unique non-empty `name`
- every dataset has non-empty string paths for `area`, `dem`, and `buildings`
- optional `target_crs`, `area_crs`, `building_crs`, `building_base_mode`, and `notes` are non-empty strings when present
- optional `height_fields` and `floor_fields` are non-empty lists of non-empty strings when present

The JSON summary reports the resolved path for each dataset input, lists any missing path fields in `missing_paths`, and includes a `metadata` object when optional fields are present.
