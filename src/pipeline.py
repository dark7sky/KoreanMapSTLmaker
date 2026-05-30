from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.buildings import prepare_buildings
from src.export import (
    cleanup_normals,
    export_glb,
    export_glb_scene,
    export_gltf,
    export_gltf_scene,
    export_obj,
    export_obj_scene,
    export_preview_html,
    export_stl,
    export_summary,
    make_visual_scene,
)
from src.io import load_area
from src.mesh import add_base_plate, make_building_meshes, make_terrain_mesh, merge_meshes, scale_mesh
from src.mesh_decimation import maybe_decimate_mesh
from src.mesh_quality import mesh_summary
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
    dem_crs: Optional[str]
    terrain_resolution: float
    terrain_smoothing_iterations: int
    terrain_smoothing_factor: float
    interpolate_nodata: bool
    base_thickness: float
    default_floor_height: float
    default_building_height: float
    min_building_area: float
    simplify_tolerance: float
    model_scale: float
    base_plate_thickness: float
    base_plate_margin: float
    max_area_km2: float
    building_diagnostics_limit: int
    separate: bool
    preview: bool
    height_fields: Optional[tuple[str, ...]]
    floor_fields: Optional[tuple[str, ...]]
    building_base_mode: str
    export_formats: tuple[str, ...]
    terrain_resampling: str = "nearest"
    terrain_boundary_mode: str = "grid"
    z_scale: float = 1.0
    decimate_max_faces: int | None = None


def build_model(options: BuildOptions) -> dict:
    _check_inputs(options)
    _check_options(options)
    area, area_km2 = load_area(options.area_path, options.target_crs, options.area_crs)
    if area_km2 > options.max_area_km2:
        raise ValueError(f"Selected area {area_km2:.2f} km2 exceeds limit {options.max_area_km2:.2f} km2.")

    terrain_grid = sample_terrain(
        area,
        str(options.dem_path),
        options.target_crs,
        options.terrain_resolution,
        resampling=options.terrain_resampling,
        z_scale=options.z_scale,
        smoothing_iterations=options.terrain_smoothing_iterations,
        smoothing_factor=options.terrain_smoothing_factor,
        interpolate_nodata=options.interpolate_nodata,
        dem_crs=options.dem_crs,
    )
    terrain_mesh = make_terrain_mesh(
        terrain_grid,
        options.base_thickness,
        terrain_boundary_mode=options.terrain_boundary_mode,
        boundary_area=area,
    )
    dem_info = get_dem_info(str(options.dem_path), options.target_crs, options.dem_crs)

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
        options.simplify_tolerance,
        options.height_fields,
        options.floor_fields,
        options.building_base_mode,
    )
    prepared_buildings = building_result.buildings
    if options.z_scale != 1.0:
        for building in prepared_buildings:
            building.base_z *= options.z_scale
    building_meshes = make_building_meshes(
        [
            (b.polygon, b.height, b.base_z, terrain_grid.origin_x, terrain_grid.origin_y)
            for b in prepared_buildings
        ]
    )
    buildings_mesh = merge_meshes(building_meshes)
    combined_mesh = merge_meshes([terrain_mesh, buildings_mesh])
    combined_mesh = add_base_plate(
        combined_mesh,
        margin=options.base_plate_margin,
        thickness=options.base_plate_thickness,
    )
    combined_mesh = scale_mesh(combined_mesh, options.model_scale)
    combined_mesh, decimation = maybe_decimate_mesh(combined_mesh, options.decimate_max_faces)
    normals_cleaned = cleanup_normals(combined_mesh)
    terrain_visual_mesh = None
    buildings_visual_mesh = None
    if options.separate:
        terrain_visual_mesh = scale_mesh(terrain_mesh, options.model_scale)
        cleanup_normals(terrain_visual_mesh)
        buildings_visual_mesh = scale_mesh(buildings_mesh, options.model_scale)
        cleanup_normals(buildings_visual_mesh)
    separate_visual_formats = options.separate and any(
        fmt in options.export_formats for fmt in ("obj", "glb", "gltf")
    )
    visual_scene = (
        make_visual_scene(terrain_visual_mesh, buildings_visual_mesh)
        if separate_visual_formats and terrain_visual_mesh is not None and buildings_visual_mesh is not None
        else None
    )

    output_paths: dict[str, str] = {}
    visual_separation: dict[str, bool] = {}
    if "stl" in options.export_formats:
        export_stl(combined_mesh, options.out_path)
        output_paths["stl"] = str(options.out_path)
        visual_separation["stl"] = False
    if "obj" in options.export_formats:
        obj_path = options.out_path.with_suffix(".obj")
        if visual_scene is not None:
            export_obj_scene(visual_scene, obj_path)
            visual_separation["obj"] = True
        else:
            export_obj(combined_mesh, obj_path)
            visual_separation["obj"] = False
        output_paths["obj"] = str(obj_path)
    if "glb" in options.export_formats:
        glb_path = options.out_path.with_suffix(".glb")
        if visual_scene is not None:
            export_glb_scene(visual_scene, glb_path)
            visual_separation["glb"] = True
        else:
            export_glb(combined_mesh, glb_path)
            visual_separation["glb"] = False
        output_paths["glb"] = str(glb_path)
    if "gltf" in options.export_formats:
        gltf_path = options.out_path.with_suffix(".gltf")
        if visual_scene is not None:
            export_gltf_scene(visual_scene, gltf_path)
            visual_separation["gltf"] = True
        else:
            export_gltf(combined_mesh, gltf_path)
            visual_separation["gltf"] = False
        output_paths["gltf"] = str(gltf_path)
    if options.separate and "stl" in options.export_formats:
        terrain_path = options.out_path.with_name(f"{options.out_path.stem}_terrain.stl")
        assert terrain_visual_mesh is not None
        export_stl(terrain_visual_mesh, terrain_path)
        output_paths["terrain_stl"] = str(terrain_path)
        if not buildings_mesh.is_empty:
            buildings_path = options.out_path.with_name(f"{options.out_path.stem}_buildings.stl")
            assert buildings_visual_mesh is not None
            export_stl(buildings_visual_mesh, buildings_path)
            output_paths["buildings_stl"] = str(buildings_path)

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
        "terrain_resampling": options.terrain_resampling,
        "terrain_smoothing_iterations": options.terrain_smoothing_iterations,
        "terrain_smoothing_factor": options.terrain_smoothing_factor,
        "terrain_boundary_mode": options.terrain_boundary_mode,
        "terrain_interpolate_nodata": options.interpolate_nodata,
        "terrain_samples": [int(terrain_grid.elevations.shape[1]), int(terrain_grid.elevations.shape[0])],
        "terrain_valid_samples": int(terrain_grid.valid.sum()),
        "terrain_filled_nodata_samples": int(getattr(terrain_grid, "filled_nodata_samples", 0)),
        "min_elevation_m": terrain_grid.min_elevation,
        "building_count": len(prepared_buildings),
        "building_base_mode": options.building_base_mode,
        "building_diagnostics": {
            "source_feature_count": building_result.source_feature_count,
            "intersect_feature_count": building_result.intersect_feature_count,
            "clipped_polygon_count": building_result.clipped_polygon_count,
            "skipped_small_count": building_result.skipped_small_count,
            "skipped_no_elevation_count": building_result.skipped_no_elevation_count,
            "fields": building_result.fields,
            "per_building_limit": options.building_diagnostics_limit,
            "per_building_omitted_count": max(0, len(prepared_buildings) - options.building_diagnostics_limit),
            "per_building": _building_diagnostics(prepared_buildings, options.building_diagnostics_limit),
        },
        "building_height_source": dict(Counter(building_result.height_counts)),
        "height_fields": list(options.height_fields or ()),
        "floor_fields": list(options.floor_fields or ()),
        "vertices": int(len(combined_mesh.vertices)),
        "faces": int(len(combined_mesh.faces)),
        "mesh_quality": mesh_summary(combined_mesh),
        "mesh_decimation": {
            "requested": decimation.requested,
            "applied": decimation.applied,
            "skipped_reason": decimation.skipped_reason,
            "backend": decimation.backend,
            "original_faces": decimation.original_faces,
            "target_faces": decimation.target_faces,
            "result_faces": decimation.result_faces,
        },
        "normal_cleanup_applied": normals_cleaned,
        "bounds": bounds,
        "output": output_paths[options.export_formats[0]],
        "outputs": output_paths,
        "export_formats": list(options.export_formats),
        "visual_separation": visual_separation,
        "options": _summary_options(options),
    }
    summary_path = export_summary(summary, options.out_path)
    summary["summary"] = str(summary_path)
    if options.preview:
        preview_path = export_preview_html(options.out_path, summary)
        summary["preview"] = str(preview_path)
        export_summary(summary, options.out_path)
    return summary


def _check_options(options: BuildOptions) -> None:
    if not options.export_formats:
        raise ValueError("At least one export format is required.")
    if options.preview and "stl" not in options.export_formats:
        raise ValueError("--preview requires STL export. Include --export-format stl.")
    if options.model_scale <= 0:
        raise ValueError("model_scale must be greater than 0.")
    if options.base_plate_thickness < 0:
        raise ValueError("base_plate_thickness must be 0 or greater.")
    if options.base_plate_margin < 0:
        raise ValueError("base_plate_margin must be 0 or greater.")
    if options.terrain_smoothing_iterations < 0:
        raise ValueError("terrain_smoothing_iterations must be 0 or greater.")
    if options.terrain_resampling not in {"nearest", "bilinear"}:
        raise ValueError("terrain_resampling must be one of: nearest, bilinear.")
    if options.terrain_boundary_mode not in {"grid", "polygon"}:
        raise ValueError("terrain_boundary_mode must be one of: grid, polygon.")
    if not 0 <= options.terrain_smoothing_factor <= 1:
        raise ValueError("terrain_smoothing_factor must be between 0 and 1.")
    if options.building_diagnostics_limit < 0:
        raise ValueError("building_diagnostics_limit must be 0 or greater.")


def _check_inputs(options: BuildOptions) -> None:
    if not options.area_path.exists():
        raise FileNotFoundError(options.area_path)
    if not options.dem_path.exists():
        raise FileNotFoundError(options.dem_path)
    if options.buildings_path is not None and not options.buildings_path.exists():
        raise FileNotFoundError(options.buildings_path)


def _summary_options(options: BuildOptions) -> dict[str, object]:
    return {
        "area": str(options.area_path),
        "buildings": str(options.buildings_path) if options.buildings_path is not None else None,
        "dem": str(options.dem_path),
        "out": str(options.out_path),
        "target_crs": options.target_crs,
        "area_crs": options.area_crs,
        "building_crs": options.building_crs,
        "dem_crs": options.dem_crs,
        "terrain_resolution": options.terrain_resolution,
        "terrain_resampling": options.terrain_resampling,
        "terrain_boundary_mode": options.terrain_boundary_mode,
        "terrain_smoothing_iterations": options.terrain_smoothing_iterations,
        "terrain_smoothing_factor": options.terrain_smoothing_factor,
        "interpolate_nodata": options.interpolate_nodata,
        "base_thickness": options.base_thickness,
        "default_floor_height": options.default_floor_height,
        "default_building_height": options.default_building_height,
        "min_building_area": options.min_building_area,
        "simplify_tolerance": options.simplify_tolerance,
        "model_scale": options.model_scale,
        "base_plate_thickness": options.base_plate_thickness,
        "base_plate_margin": options.base_plate_margin,
        "max_area_km2": options.max_area_km2,
        "building_diagnostics_limit": options.building_diagnostics_limit,
        "separate": options.separate,
        "preview": options.preview,
        "height_fields": list(options.height_fields or ()),
        "floor_fields": list(options.floor_fields or ()),
        "building_base_mode": options.building_base_mode,
        "export_formats": list(options.export_formats),
        "z_scale": options.z_scale,
        "decimate_max_faces": options.decimate_max_faces,
    }


def _building_diagnostics(buildings: list, limit: int) -> list[dict[str, object]]:
    diagnostics = []
    for index, building in enumerate(buildings[:limit]):
        polygon = building.polygon
        point = polygon.representative_point()
        diagnostics.append(
            {
                "index": index,
                "height": float(building.height),
                "base_z": float(building.base_z),
                "source": building.source,
                "area": float(polygon.area),
                "bounds": [float(value) for value in polygon.bounds],
                "representative_point": [float(point.x), float(point.y)],
            }
        )
    return diagnostics
