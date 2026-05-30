from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_sources import Bounds, VWorldGISBuildingProvider, fetch_buildings_geojson
from src.data_sources.config import load_env_file, load_optional_env_file
from src.data_sources.validation import validate_area_overlaps_vector


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch building footprints from online providers or fixture responses.")
    parser.add_argument("--area", type=Path, help="Area polygon file used to derive fetch bounds.")
    parser.add_argument("--area-crs", help="Fallback CRS when area data has none.")
    parser.add_argument("--bounds", nargs=4, type=float, metavar=("MIN_X", "MIN_Y", "MAX_X", "MAX_Y"))
    parser.add_argument("--provider", default="vworld-gis-building", choices=("vworld-gis-building",))
    parser.add_argument("--base-url", default="https://api.vworld.kr/req/data", help="Provider request base URL.")
    parser.add_argument("--data-name", default="LT_C_UQ111", help="VWorld data layer name.")
    parser.add_argument("--crs", default="EPSG:4326", help="Coordinate reference system used for request bounds.")
    parser.add_argument("--out", required=True, type=Path, help="Output GeoJSON path.")
    parser.add_argument(
        "--validate-area",
        type=Path,
        help="Optional area file used to validate overlap against fetched buildings.",
    )
    parser.add_argument(
        "--validate-area-crs",
        help="Fallback CRS when --validate-area has no CRS metadata.",
    )
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/data_sources"))
    parser.add_argument("--fixture-response", type=Path, help="Local JSON response for offline test/simulation mode.")
    parser.add_argument("--env-file", type=Path, help="Optional .env file to load before reading API keys.")
    args = parser.parse_args()

    project_env_path = Path(__file__).resolve().parents[1] / ".env"
    if args.env_file:
        load_env_file(args.env_file)
    else:
        load_optional_env_file(project_env_path)

    bounds = resolve_bounds(args.area, args.area_crs, args.bounds)
    fixture_response = None
    if args.fixture_response:
        fixture_response = json.loads(args.fixture_response.read_text(encoding="utf-8"))

    api_key = os.environ.get("VWORLD_API_KEY")
    if args.provider != "vworld-gis-building":
        raise ValueError(f"Unsupported provider: {args.provider}")
    provider = VWorldGISBuildingProvider(api_key=api_key, base_url=args.base_url, data_name=args.data_name)

    if fixture_response is None and not api_key:
        raise SystemExit(
            "VWORLD_API_KEY is required for live fetches. Set VWORLD_API_KEY or pass --fixture-response for offline mode."
        )

    result = fetch_buildings_geojson(
        provider=provider,
        bounds=bounds,
        crs=args.crs,
        out_path=args.out,
        cache_dir=args.cache_dir,
        fixture_response=fixture_response,
    )

    validate_area = args.validate_area or args.area
    if validate_area:
        validation = validate_area_overlaps_vector(
            area_path=validate_area,
            vector_path=args.out,
            target_crs=args.crs,
            area_crs=args.validate_area_crs or args.area_crs,
            vector_crs=args.crs,
            source_label="building",
        )
        if not validation.overlaps:
            raise SystemExit(
                "Fetched buildings do not overlap the validation area. "
                f"target_crs={validation.target_crs}; area_bounds={validation.area_bounds}; "
                f"building_bounds={validation.source_bounds}; "
                "check --validate-area/--validate-area-crs and fetch bounds/CRS."
            )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def resolve_bounds(
    area_path: Path | None,
    area_crs: str | None,
    bounds_values: list[float] | None,
) -> Bounds:
    if bounds_values is not None:
        return Bounds(*bounds_values)
    if area_path is None:
        raise SystemExit("Either --bounds or --area must be provided.")
    if not area_path.exists():
        raise FileNotFoundError(area_path)
    gdf = gpd.read_file(area_path)
    if gdf.crs is None:
        if not area_crs:
            raise SystemExit("Area CRS is missing. Pass --area-crs, or provide --bounds directly.")
        gdf = gdf.set_crs(area_crs)
    if gdf.empty:
        raise SystemExit(f"Area file has no features: {area_path}")
    min_x, min_y, max_x, max_y = gdf.total_bounds
    return Bounds(float(min_x), float(min_y), float(max_x), float(max_y))


if __name__ == "__main__":
    main()
