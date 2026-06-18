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

If you already maintain a `datasets.json` registry with DEM/building coverage bounds, the quickest path is the auto builder:

```powershell
.\.venv\Scripts\python.exe scripts\auto_build.py `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --registry datasets.json `
  --output-name my_area `
  --terrain-resolution 10 `
  --terrain-boundary-mode polygon `
  --export-format stl `
  --export-format glb `
  --preview `
  --summary-out output\my_area_auto_build.json
```

Start with `--dry-run` to select the best overlapping dataset and run validation without creating geometry. If validation passes, remove `--dry-run` and rerun the same command. The auto builder writes the selected dataset, validation report, equivalent `make_model.py` command, and build summary into the JSON report.

Use the manual inspect/build steps below when you are preparing a new dataset, debugging CRS/overlap problems, or running without a registry.

For a first smoke test with committed fixtures, use `datasets.sample.json`:

```powershell
.\.venv\Scripts\python.exe scripts\auto_build.py `
  --area data\sample\area.geojson `
  --registry datasets.sample.json `
  --dry-run
```

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

If bounds do not overlap, stop and fix CRS/path inputs before generation. If the area selector GeoJSON reports a missing CRS, keep `--area-crs EPSG:4326` in both the inspect and generate commands. If a building SHP reports a missing CRS, first check that the `.prj` file stayed beside the `.shp`; otherwise pass `--building-crs` with the source CRS.

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
  --export-format glb `
  --export-format gltf `
  --terrain-resolution 10 `
  --interpolate-nodata `
  --terrain-smoothing-iterations 1 `
  --terrain-smoothing-factor 0.4 `
  --z-scale 1.5 `
  --model-scale 1.0 `
  --base-plate-thickness 1.0 `
  --base-plate-margin 3.0 `
  --building-diagnostics-limit 200 `
  --building-base-mode representative `
  --height-field HEIGHT `
  --floor-field GRND_FLR `
  --separate `
  --preview
```

Start with `--terrain-resolution 10` or `20`. Lower the value after the geometry looks correct. Add `--interpolate-nodata` when small DEM gaps produce holes inside the selected terrain. Use terrain smoothing sparingly to reduce noisy DEM spikes. Use `--z-scale` only when the terrain relief needs visual exaggeration; building heights remain in real units. Use `--model-scale` for final print scaling, and add a base plate when the model needs a larger flat bottom for slicing.

## 7. Review Output

Open:

```text
output/my_area_preview.html
```

Also check:

```text
output/my_area_summary.json
```

The summary contains DEM bounds, valid terrain samples, interpolated nodata sample counts, building counts, skipped buildings, per-building diagnostics up to `--building-diagnostics-limit`, height source statistics, mesh quality, selected building base mode, and an `options` block for reproducing the run.
Mesh quality currently includes watertight status, Euler number, volume, bounding box, non-manifold edge count, and degenerate face count.

Validate print thresholds from the summary:

```powershell
.\.venv\Scripts\python.exe scripts\validate_print.py output\my_area_summary.json `
  --require-watertight `
  --max-non-manifold-edges 0 `
  --max-degenerate-faces 0 `
  --min-dimension 5 `
  --max-dimension 300 `
  --min-volume 1.0 `
  --format text
```

The command exits non-zero when any threshold fails, so it can be used in CI checks or batch post-validation.

Optional: include a slicer command template in the validation report:

```powershell
.\.venv\Scripts\python.exe scripts\validate_print.py output\my_area_summary.json `
  --include-slicer-template `
  --format text
```

Optional: run an external slicer dry-run/check command (only when you provide it):

```powershell
.\.venv\Scripts\python.exe scripts\validate_print.py output\my_area_summary.json `
  --slicer-check-cmd "prusa-slicer-console.exe --export-gcode --load printer_config.ini --output output\my_area.gcode {model}" `
  --model-path output\my_area.stl `
  --format text
```

`{summary}` and `{model}` placeholders are supported. If `--model-path` is omitted, the validator tries `<summary_stem>.stl` next to `*_summary.json`.

Print a rerun command from a saved model summary:

```powershell
.\.venv\Scripts\python.exe scripts\command_from_summary.py output\my_area_summary.json
```

Import generated model outputs into Blender for visual review:

```powershell
blender --python scripts\blender_import.py -- output\my_area_summary.json --clear-scene --set-metric-units
```

## 8. Optional Cached Re-run

If you frequently rerun the same inputs/options, use the cached runner to skip rebuilds on repeated jobs.

Create `job.json` (same schema as one `scripts\run_batch.py` job object), then run:

```powershell
.\.venv\Scripts\python.exe scripts\cache_model.py `
  --job job.json `
  --cache-dir .cache\model_runner
```

The script prints `Cache: hit` when outputs were restored from cache, or `Cache: miss` when it rebuilt and stored a new cache entry.

## 8.1 Optional Web Service Storage

The optional local web service keeps each job inside the active workspace under:

```text
.web_api/jobs/<job_id>/
```

Uploaded inputs are stored under `uploads/`, generated files under `artifacts/`, and all registered paths are checked so they cannot escape the workspace or job directory.

## 9. Dataset Registry

For repeated work with the same source data, maintain a dataset registry that names each DEM and building dataset and records the details needed to select it reliably.

Current registry fields:

- Dataset name.
- Area path.
- DEM path.
- Building path.
- Optional CRS hints.
- Optional height and floor field preferences.
- Optional building base mode.
- Optional coverage bounds.
- Optional source date.
- Optional license.
- Optional source URL.
- Optional notes.

Run:

```powershell
.\.venv\Scripts\python.exe scripts\list_datasets.py
```

Generate inspect/model command templates from a named dataset:

```powershell
.\.venv\Scripts\python.exe scripts\command_from_dataset.py sample_block
```

Or select a dataset by overlap with your drawn area:

```powershell
.\.venv\Scripts\python.exe scripts\select_dataset.py `
  --area data\areas\area.geojson `
  --area-crs EPSG:4326 `
  --registry datasets.json `
  --commands
```

## 10. Run Batch Jobs (JSON)

For sequential multi-area processing, prepare a JSON file with top-level `jobs`.

Example:

```json
{
  "jobs": [
    {
      "name": "sample_a",
      "area": "data/areas/a.geojson",
      "area_crs": "EPSG:4326",
      "buildings": "data/buildings/a.shp",
      "dem": "data/dem/a.tif",
      "out": "output/a.stl",
      "export_format": ["stl", "obj"],
      "terrain_resolution": 10,
      "interpolate_nodata": true,
      "z_scale": 1.2
    }
  ]
}
```

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_batch.py `
  --batch batch_jobs.json `
  --summary-out output\batch_summary.json `
  --retries 1 `
  --workers 2
```

The script runs jobs using the same model pipeline as `make_model.py`. Use `--workers` for parallel jobs. Failures are recorded in the batch summary, each failed job can be retried with `--retries`, and the process exits non-zero only after all jobs finish.
