import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.dem_registry import find_dem_tiles
from src.io import load_area


def main() -> None:
    parser = argparse.ArgumentParser(description="Find DEM registry entries overlapping an area or explicit bounds.")
    parser.add_argument("--registry", type=Path, default=Path("datasets.json"), help="Registry JSON path.")
    parser.add_argument("--target-crs", default="EPSG:5179", help="CRS used for --area and --bounds.")
    parser.add_argument("--area", type=Path, help="Area polygon file used for overlap query.")
    parser.add_argument("--area-crs", help="Fallback CRS when the area file has none.")
    parser.add_argument("--bounds", nargs=4, type=float, metavar=("MINX", "MINY", "MAXX", "MAXY"))
    parser.add_argument("--limit", type=int, default=10, help="Maximum matches to return.")
    args = parser.parse_args()

    if bool(args.area) == bool(args.bounds):
        raise SystemExit("Provide exactly one of --area or --bounds.")

    query_bounds = _resolve_query_bounds(args.area, args.area_crs, args.bounds, args.target_crs)
    result = find_dem_tiles(
        registry_path=args.registry,
        query_bounds=query_bounds,
        query_crs=args.target_crs,
        limit=args.limit,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


def _resolve_query_bounds(
    area_path: Path | None,
    area_crs: str | None,
    bounds: list[float] | None,
    target_crs: str,
) -> list[float]:
    if bounds is not None:
        return [float(value) for value in bounds]
    if area_path is None:
        raise SystemExit("Provide either --area or --bounds.")
    area, _ = load_area(area_path, target_crs, area_crs)
    return [float(value) for value in area.bounds]


if __name__ == "__main__":
    main()
