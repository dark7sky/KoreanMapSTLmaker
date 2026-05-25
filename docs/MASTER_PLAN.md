# Master Plan

This project should evolve in phases so another agent can resume work at any point.

## Phase 0 - Project Setup

- [x] Create repository structure.
- [x] Add dependency files.
- [x] Add CLI entrypoint.
- [x] Add master plan.
- [ ] Add real sample data guide.

## Phase 1 - Local CLI MVP

- [x] Load area polygon.
- [x] Convert area to target CRS.
- [x] Sample DEM over area.
- [x] Normalize terrain by minimum selected elevation.
- [x] Generate terrain mesh.
- [x] Load and clip building footprints.
- [x] Calculate building heights using height/floor/default fallback.
- [x] Extrude simple building meshes.
- [x] Merge terrain and building meshes.
- [x] Export STL.
- [x] Export summary JSON.
- [x] Add mesh quality summary to JSON output.
- [ ] Test against real VWorld/GIS building data.
- [ ] Test against real DEM data.

## Phase 2 - Data and CRS Robustness

- [ ] Add explicit `--dem-crs` fallback only if needed.
- [ ] Improve CRS error messages.
- [ ] Repair invalid geometries more thoroughly.
- [x] Add field mapping options for height and floor fields.
- [x] Add better no-overlap diagnostics.
- [x] Add area bounds report.
- [x] Add input inspection script.

## Phase 3 - Building Modeling

- [x] Support polygon holes.
- [x] Add footprint simplification option.
- [x] Add building base mode selector: representative/min/mean.
- [ ] Add sloped terrain policy for building base.
- [ ] Add per-building diagnostics.
- [x] Report selected base elevation mode in summary JSON.

## Phase 4 - Terrain Modeling

- [ ] Clip terrain boundary exactly to selected polygon.
- [ ] Add resampling method options.
- [ ] Add nodata interpolation.
- [ ] Add smoothing.
- [ ] Add mesh decimation.
- [ ] Add chunked processing for large areas.

## Phase 5 - Print-Ready STL

- [x] Add mesh repair command.
- [x] Check watertight/non-manifold edges.
- [x] Summarize basic mesh quality: watertight status, Euler number, volume, and bounding box.
- [x] Add non-manifold edge and degenerate face counts.
- [x] Add scale option.
- [x] Add base plate option.
- [x] Add normal cleanup.
- [ ] Validate in slicers.

## Phase 6 - Preview

- [x] Generate `preview.html`.
- [x] Add Three.js viewer.
- [ ] Add terrain/building color distinction.
- [x] Add summary panel.
- [ ] Add offline/local Three.js assets option.

## Phase 7 - Map Area Selection

- [x] Add simple HTML map.
- [x] Draw polygon.
- [x] Export `area.geojson`.
- [x] Show selected area size.
- [x] Connect selected area to CLI.
- [x] Add command template/copy flow.

## Phase 8 - Local App

- [ ] Streamlit UI.
- [ ] File pickers.
- [ ] Option form.
- [ ] Height/floor field selector based on inspected building attributes.
- [x] Building base mode selector.
- [ ] Mesh quality summary panel.
- [ ] Progress/log panel.
- [ ] STL download link.
- [ ] Preview integration.

## Phase 9 - Dataset Management

- [x] Dataset registry JSON with named area/DEM/building paths.
- [x] Generate inspect/model command templates from dataset registry entries.
- [x] Extend dataset registry with CRS hints, source notes, and default field mappings.
- [x] Extend dataset registry with coverage bounds, source dates, and license notes.
- [ ] DEM index.
- [ ] Building index.
- [ ] Automatic overlap selection.
- [x] Registry-backed defaults for height/floor fields in generated commands.
- [ ] Cache generated outputs.

## Phase 10 - Additional Formats

- [x] OBJ export.
- [ ] GLB/GLTF export.
- [ ] Material separation for visual formats.
- [ ] Blender import helper.

## Phase 11 - Batch Processing

- [x] Batch JSON format (`{"jobs":[...]}`).
- [x] Multiple area jobs.
- [x] Retry failed jobs.
- [x] Summary report.
- [ ] Parallel processing.

## Phase 12 - Optional Web Service

- [ ] FastAPI backend.
- [ ] Job API.
- [ ] Upload/download endpoints.
- [ ] React frontend.
- [ ] Local Docker packaging.
