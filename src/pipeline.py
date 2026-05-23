from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.buildings import prepare_buildings
from src.export import export_preview_html, export_stl, export_summary
from src.io import load_area
from src.mesh import make_building_meshes, make_terrain_mesh, merge_meshes
from src.terrain import bounds_overlap, get_dem_info, sample_terrain


@dataclass
class BuildOptions:
    area_path: Path
    buildings_path: Optional[Path]
    dem_path: Path
    out_path: Path
    target_crs: str
    area_crs: Optional[str]
    building_crs: Optional[str]
    terrain_resolution: float
    base_thickness: float
    default_floor_height: float
    default_building_height: float
    min_building_area: float
    max_area_km2: float
    separate: bool
    preview: bool
    height_fields: Optional[tuple[str, ...]]
    floor_fields: Optional[tuple[str, ...]]


def build_model(options: BuildOptions) -> dict:
    _check_inputs(options)
    area, area_km2 = load_area(options.area_path, options.target_crs, options.area_crs)
    if area_km2 > options.max_area_km2:
        raise ValueError(f"Selected area {area_km2:.2f} km2 exceeds limit {options.max_area_km2:.2f} km2.")

    terrain_grid = sample_terrain(area, str(options.dem_path), options.target_crs, options.terrain_resolution)
    terrain_mesh = make_terrain_mesh(terrain_grid, options.base_thickness)
    dem_info = get_dem_info(str(options.dem_path), options.target_crs)

    building_result = prepare_buildings(
        options.buildings_path,
        area,
        options.dem_path,
        options.target_crs,
        options.building_crs,
        terrain_grid.min_elevation,
        options.default_floor_height,
        options.default_building_height,
        options.min_building_area,
        options.height_fields,
        options.floor_fields,
    )
    prepared_buildings = building_result.buildings
    building_meshes = make_building_meshes(
        [
            (b.polygon, b.height, b.base_z, terrain_grid.origin_x, terrain_grid.origin_y)
            for b in prepared_buildings
        ]
    )
    buildings_mesh = merge_meshes(building_meshes)
    combined_mesh = merge_meshes([terrain_mesh, buildings_mesh])

    export_stl(combined_mesh, options.out_path)
    if options.separate:
        export_stl(terrain_mesh, options.out_path.with_name(f"{options.out_path.stem}_terrain.stl"))
        if not buildings_mesh.is_empty:
            export_stl(buildings_mesh, options.out_path.with_name(f"{options.out_path.stem}_buildings.stl"))

    area_bounds = [float(value) for value in area.bounds]
    bounds = combined_mesh.bounds.tolist() if not combined_mesh.is_empty else []
    summary = {
        "area_km2": area_km2,
        "area_bounds": area_bounds,
        "target_crs": options.target_crs,
        "dem": {
            "crs": dem_info.crs,
            "bounds": dem_info.bounds,
            "bounds_in_target_crs": dem_info.bounds_in_target_crs,
            "bbox_overlaps_area": bounds_overlap(area_bounds, dem_info.bounds_in_target_crs),
            "width": dem_info.width,
            "height": dem_info.height,
            "resolution": dem_info.resolution,
            "nodata": dem_info.nodata,
        },
        "terrain_resolution_m": options.terrain_resolution,
        "terrain_samples": [int(terrain_grid.elevations.shape[1]), int(terrain_grid.elevations.shape[0])],
        "terrain_valid_samples": int(terrain_grid.valid.sum()),
        "min_elevation_m": terrain_grid.min_elevation,
        "building_count": len(prepared_buildings),
        "building_diagnostics": {
            "source_feature_count": building_result.source_feature_count,
            "intersect_feature_count": building_result.intersect_feature_count,
            "clipped_polygon_count": building_result.clipped_polygon_count,
            "skipped_small_count": building_result.skipped_small_count,
            "skipped_no_elevation_count": building_result.skipped_no_elevation_count,
            "fields": building_result.fields,
        },
        "building_height_source": dict(Counter(building_result.height_counts)),
        "height_fields": list(options.height_fields or ()),
        "floor_fields": list(options.floor_fields or ()),
        "vertices": int(len(combined_mesh.vertices)),
        "faces": int(len(combined_mesh.faces)),
        "bounds": bounds,
        "output": str(options.out_path),
    }
    summary_path = export_summary(summary, options.out_path)
    summary["summary"] = str(summary_path)
    if options.preview:
        preview_path = export_preview_html(options.out_path, summary)
        summary["preview"] = str(preview_path)
        export_summary(summary, options.out_path)
    return summary


def _check_inputs(options: BuildOptions) -> None:
    if not options.area_path.exists():
        raise FileNotFoundError(options.area_path)
    if not options.dem_path.exists():
        raise FileNotFoundError(options.dem_path)
    if options.buildings_path is not None and not options.buildings_path.exists():
        raise FileNotFoundError(options.buildings_path)
