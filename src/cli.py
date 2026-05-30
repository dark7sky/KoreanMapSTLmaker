import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create terrain/building STL models from local GIS data.")
    parser.add_argument("--area", required=True, type=Path, help="Area polygon file, e.g. GeoJSON/SHP/GPKG.")
    parser.add_argument("--buildings", type=Path, help="Building footprints file.")
    parser.add_argument("--dem", required=True, type=Path, help="DEM GeoTIFF.")
    parser.add_argument("--out", required=True, type=Path, help="Output model path. STL uses this path; OBJ/GLB use the same stem.")
    parser.add_argument("--target-crs", default="EPSG:5179", help="Metric CRS used for modeling.")
    parser.add_argument("--area-crs", help="Fallback CRS when area data has none.")
    parser.add_argument("--building-crs", help="Fallback CRS when building data has none.")
    parser.add_argument("--dem-crs", help="Fallback CRS when DEM raster data has none.")
    parser.add_argument("--terrain-resolution", type=_positive_float, default=10.0, help="Terrain spacing in meters.")
    parser.add_argument(
        "--terrain-resampling",
        choices=("nearest", "bilinear"),
        default="nearest",
        help="DEM sampling method for terrain elevation lookup.",
    )
    parser.add_argument(
        "--terrain-boundary-mode",
        choices=("grid", "polygon"),
        default="grid",
        help="Terrain boundary handling: grid keeps full-cell edges; polygon clips exactly to selected area boundary.",
    )
    parser.add_argument(
        "--terrain-smoothing-iterations",
        type=_non_negative_int,
        default=0,
        help="Number of terrain smoothing passes after DEM normalization.",
    )
    parser.add_argument(
        "--terrain-smoothing-factor",
        type=_unit_float,
        default=0.5,
        help="Blend factor per terrain smoothing pass, from 0 to 1.",
    )
    parser.add_argument(
        "--interpolate-nodata",
        action="store_true",
        help="Fill nodata gaps inside the selected area from neighboring DEM samples.",
    )
    parser.add_argument("--base-thickness", type=_non_negative_float, default=2.0, help="Base thickness in meters.")
    parser.add_argument("--default-floor-height", type=_positive_float, default=3.0, help="Meters per floor fallback.")
    parser.add_argument("--default-building-height", type=_positive_float, default=6.0, help="Default building height.")
    parser.add_argument("--z-scale", type=_positive_float, default=1.0, help="Vertical exaggeration scale factor.")
    parser.add_argument("--min-building-area", type=_non_negative_float, default=4.0, help="Drop smaller buildings, sqm.")
    parser.add_argument(
        "--simplify-tolerance",
        type=_non_negative_float,
        default=0.0,
        help="Simplify building footprints in meters after clipping (0 disables simplification).",
    )
    parser.add_argument("--model-scale", type=_positive_float, default=1.0, help="Uniformly scale the final model.")
    parser.add_argument(
        "--decimate-max-faces",
        type=_non_negative_int,
        help="Optional target max face count for final mesh decimation (opt-in).",
    )
    parser.add_argument(
        "--base-plate-thickness",
        type=_non_negative_float,
        default=0.0,
        help="Add a rectangular base plate below the model with this thickness in model units.",
    )
    parser.add_argument(
        "--base-plate-margin",
        type=_non_negative_float,
        default=0.0,
        help="XY margin around the model when --base-plate-thickness is greater than 0.",
    )
    parser.add_argument("--max-area-km2", type=_positive_float, default=4.0, help="Safety limit for selected area.")
    parser.add_argument(
        "--building-diagnostics-limit",
        type=_non_negative_int,
        default=200,
        help="Maximum number of per-building diagnostic records in the summary JSON.",
    )
    parser.add_argument("--separate", action="store_true", help="Also export terrain and buildings separately.")
    parser.add_argument(
        "--export-format",
        action="append",
        choices=("stl", "obj", "glb", "gltf"),
        help="Export format. Repeat to export multiple formats (default: stl).",
    )
    parser.add_argument("--preview", action="store_true", help="Generate a self-contained preview HTML file.")
    parser.add_argument("--height-field", action="append", help="Preferred building height field. Can be repeated.")
    parser.add_argument("--floor-field", action="append", help="Preferred floor-count field. Can be repeated.")
    parser.add_argument(
        "--building-base-mode",
        choices=("representative", "min", "mean", "min-corners"),
        default="representative",
        help="How to sample terrain elevation under each building footprint.",
    )
    args = parser.parse_args()

    from src.pipeline import BuildOptions, build_model

    export_formats = _normalize_export_formats(args.export_format)

    options = BuildOptions(
        area_path=args.area,
        buildings_path=args.buildings,
        dem_path=args.dem,
        out_path=args.out,
        target_crs=args.target_crs,
        area_crs=args.area_crs,
        building_crs=args.building_crs,
        dem_crs=args.dem_crs,
        terrain_resolution=args.terrain_resolution,
        terrain_resampling=args.terrain_resampling,
        terrain_boundary_mode=getattr(args, "terrain_boundary_mode", "grid"),
        terrain_smoothing_iterations=args.terrain_smoothing_iterations,
        terrain_smoothing_factor=args.terrain_smoothing_factor,
        interpolate_nodata=args.interpolate_nodata,
        base_thickness=args.base_thickness,
        default_floor_height=args.default_floor_height,
        default_building_height=args.default_building_height,
        min_building_area=args.min_building_area,
        simplify_tolerance=args.simplify_tolerance,
        model_scale=args.model_scale,
        base_plate_thickness=args.base_plate_thickness,
        base_plate_margin=args.base_plate_margin,
        max_area_km2=args.max_area_km2,
        building_diagnostics_limit=args.building_diagnostics_limit,
        separate=args.separate,
        preview=args.preview,
        height_fields=tuple(args.height_field or ()),
        floor_fields=tuple(args.floor_field or ()),
        building_base_mode=args.building_base_mode,
        z_scale=getattr(args, "z_scale", 1.0),
        export_formats=export_formats,
        decimate_max_faces=getattr(args, "decimate_max_faces", None),
    )
    summary = build_model(options)
    print(f"Output: {summary['output']}")
    print(f"Buildings: {summary['building_count']}")
    print(f"Faces: {summary['faces']}")
    if "preview" in summary:
        print(f"Preview: {summary['preview']}")


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def _non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be 0 or greater")
    return parsed


def _unit_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0 or parsed > 1:
        raise argparse.ArgumentTypeError("must be between 0 and 1")
    return parsed


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be 0 or greater")
    return parsed


def _normalize_export_formats(values: list[str] | None) -> tuple[str, ...]:
    formats = values or ["stl"]
    # Keep order while deduplicating repeated flags.
    return tuple(dict.fromkeys(formats))
