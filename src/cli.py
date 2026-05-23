import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create terrain/building STL models from local GIS data.")
    parser.add_argument("--area", required=True, type=Path, help="Area polygon file, e.g. GeoJSON/SHP/GPKG.")
    parser.add_argument("--buildings", type=Path, help="Building footprints file.")
    parser.add_argument("--dem", required=True, type=Path, help="DEM GeoTIFF.")
    parser.add_argument("--out", required=True, type=Path, help="Output STL path.")
    parser.add_argument("--target-crs", default="EPSG:5179", help="Metric CRS used for modeling.")
    parser.add_argument("--area-crs", help="Fallback CRS when area data has none.")
    parser.add_argument("--building-crs", help="Fallback CRS when building data has none.")
    parser.add_argument("--terrain-resolution", type=_positive_float, default=10.0, help="Terrain spacing in meters.")
    parser.add_argument("--base-thickness", type=_non_negative_float, default=2.0, help="Base thickness in meters.")
    parser.add_argument("--default-floor-height", type=_positive_float, default=3.0, help="Meters per floor fallback.")
    parser.add_argument("--default-building-height", type=_positive_float, default=6.0, help="Default building height.")
    parser.add_argument("--min-building-area", type=_non_negative_float, default=4.0, help="Drop smaller buildings, sqm.")
    parser.add_argument("--max-area-km2", type=_positive_float, default=4.0, help="Safety limit for selected area.")
    parser.add_argument("--separate", action="store_true", help="Also export terrain and buildings separately.")
    parser.add_argument("--preview", action="store_true", help="Generate a self-contained preview HTML file.")
    parser.add_argument("--height-field", action="append", help="Preferred building height field. Can be repeated.")
    parser.add_argument("--floor-field", action="append", help="Preferred floor-count field. Can be repeated.")
    args = parser.parse_args()

    from src.pipeline import BuildOptions, build_model

    options = BuildOptions(
        area_path=args.area,
        buildings_path=args.buildings,
        dem_path=args.dem,
        out_path=args.out,
        target_crs=args.target_crs,
        area_crs=args.area_crs,
        building_crs=args.building_crs,
        terrain_resolution=args.terrain_resolution,
        base_thickness=args.base_thickness,
        default_floor_height=args.default_floor_height,
        default_building_height=args.default_building_height,
        min_building_area=args.min_building_area,
        max_area_km2=args.max_area_km2,
        separate=args.separate,
        preview=args.preview,
        height_fields=tuple(args.height_field or ()),
        floor_fields=tuple(args.floor_field or ()),
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
