import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import rasterio
from rasterio.warp import transform_bounds


DEM_EXTENSIONS = {".tif", ".tiff"}
BUILDING_EXTENSIONS = {".shp", ".gpkg", ".geojson", ".json"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a dataset index for DEM or building datasets.")
    parser.add_argument("--root", type=Path, required=True, help="Root directory to recursively scan.")
    parser.add_argument("--kind", choices=("dem", "buildings"), required=True, help="Dataset kind to index.")
    parser.add_argument("--out", type=Path, required=True, help="Output JSON index path.")
    parser.add_argument("--target-crs", default="EPSG:5179", help="CRS used for coverage_bounds.")
    args = parser.parse_args()

    index = build_index(root=args.root, kind=args.kind, target_crs=args.target_crs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def build_index(root: Path, kind: str, target_crs: str) -> dict[str, Any]:
    root = root.resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Root path does not exist or is not a directory: {root}")

    datasets = []
    for path in scan_paths(root, kind):
        entry = build_entry(path=path, root=root, kind=kind, target_crs=target_crs)
        datasets.append(entry)

    datasets.sort(key=lambda value: value["path"])
    return {
        "root": str(root),
        "kind": kind,
        "target_crs": target_crs,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_count": len(datasets),
        "datasets": datasets,
    }


def scan_paths(root: Path, kind: str) -> list[Path]:
    extensions = DEM_EXTENSIONS if kind == "dem" else BUILDING_EXTENSIONS
    return [path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in extensions]


def build_entry(path: Path, root: Path, kind: str, target_crs: str) -> dict[str, Any]:
    if kind == "dem":
        return inspect_dem(path=path, root=root, target_crs=target_crs)
    return inspect_buildings(path=path, root=root, target_crs=target_crs)


def inspect_dem(path: Path, root: Path, target_crs: str) -> dict[str, Any]:
    with rasterio.open(path) as dataset:
        bounds = [float(dataset.bounds.left), float(dataset.bounds.bottom), float(dataset.bounds.right), float(dataset.bounds.top)]
        dataset_crs = None if dataset.crs is None else str(dataset.crs)
        coverage_bounds = bounds
        if dataset.crs is not None and str(dataset.crs) != target_crs:
            coverage = transform_bounds(dataset.crs, target_crs, *dataset.bounds, densify_pts=21)
            coverage_bounds = [float(coverage[0]), float(coverage[1]), float(coverage[2]), float(coverage[3])]
        return {
            "type": "dem",
            "path": relative_posix(path, root),
            "crs": dataset_crs,
            "bounds": bounds,
            "coverage_bounds": coverage_bounds,
            "metadata": {
                "width": int(dataset.width),
                "height": int(dataset.height),
                "count": int(dataset.count),
                "resolution": [float(abs(dataset.res[0])), float(abs(dataset.res[1]))],
                "nodata": None if dataset.nodata is None else float(dataset.nodata),
                "dtypes": [str(dtype) for dtype in dataset.dtypes],
            },
        }


def inspect_buildings(path: Path, root: Path, target_crs: str) -> dict[str, Any]:
    gdf = gpd.read_file(path)
    dataset_crs = None if gdf.crs is None else str(gdf.crs)
    if gdf.empty:
        bounds: list[float] = []
        coverage_bounds: list[float] = []
    else:
        bounds = [float(value) for value in gdf.total_bounds]
        coverage_bounds = bounds
        if gdf.crs is not None and str(gdf.crs) != target_crs:
            projected = gdf.to_crs(target_crs)
            coverage_bounds = [float(value) for value in projected.total_bounds]

    geometry_types: list[str] = []
    if not gdf.empty:
        geometry_types = sorted(str(value) for value in gdf.geometry.geom_type.dropna().unique())

    return {
        "type": "buildings",
        "path": relative_posix(path, root),
        "crs": dataset_crs,
        "bounds": bounds,
        "coverage_bounds": coverage_bounds,
        "metadata": {
            "feature_count": int(len(gdf)),
            "geometry_types": geometry_types,
            "fields": [str(column) for column in gdf.columns if column != "geometry"],
        },
    }


def relative_posix(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


if __name__ == "__main__":
    main()
