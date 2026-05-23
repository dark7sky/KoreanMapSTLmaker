import argparse
import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import rasterio


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect local GIS inputs before generating STL.")
    parser.add_argument("--area", type=Path, help="Area vector file.")
    parser.add_argument("--buildings", type=Path, help="Building vector file.")
    parser.add_argument("--dem", type=Path, help="DEM raster file.")
    parser.add_argument("--area-crs", help="Fallback area CRS when missing.")
    parser.add_argument("--building-crs", help="Fallback building CRS when missing.")
    args = parser.parse_args()

    result: dict[str, Any] = {}
    if args.area:
        result["area"] = inspect_vector(args.area, args.area_crs)
    if args.buildings:
        result["buildings"] = inspect_vector(args.buildings, args.building_crs)
    if args.dem:
        result["dem"] = inspect_raster(args.dem)

    print(json.dumps(result, indent=2, ensure_ascii=False))


def inspect_vector(path: Path, fallback_crs: str | None) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    gdf = gpd.read_file(path)
    crs_was_missing = gdf.crs is None
    if crs_was_missing and fallback_crs:
        gdf = gdf.set_crs(fallback_crs)

    geometry_types = []
    if not gdf.empty:
        geometry_types = sorted(str(value) for value in gdf.geometry.geom_type.dropna().unique())

    return {
        "path": str(path),
        "exists": True,
        "feature_count": int(len(gdf)),
        "crs": None if gdf.crs is None else str(gdf.crs),
        "crs_was_missing": crs_was_missing,
        "bounds": [] if gdf.empty else [float(value) for value in gdf.total_bounds],
        "geometry_types": geometry_types,
        "fields": [str(column) for column in gdf.columns if column != "geometry"],
    }


def inspect_raster(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    with rasterio.open(path) as dataset:
        bounds = dataset.bounds
        return {
            "path": str(path),
            "exists": True,
            "crs": None if dataset.crs is None else str(dataset.crs),
            "bounds": [float(bounds.left), float(bounds.bottom), float(bounds.right), float(bounds.top)],
            "width": int(dataset.width),
            "height": int(dataset.height),
            "count": int(dataset.count),
            "resolution": [float(abs(dataset.res[0])), float(abs(dataset.res[1]))],
            "nodata": None if dataset.nodata is None else float(dataset.nodata),
            "dtypes": list(dataset.dtypes),
        }


if __name__ == "__main__":
    main()
