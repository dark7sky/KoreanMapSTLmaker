from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import rasterio
from pyproj import CRS
from rasterio.warp import transform_bounds
from shapely.geometry import box


@dataclass(frozen=True)
class OverlapValidationResult:
    target_crs: str
    area_bounds: list[float]
    source_bounds: list[float]
    overlaps: bool


def validate_area_overlaps_vector(
    *,
    area_path: Path,
    vector_path: Path,
    target_crs: str,
    area_crs: str | None = None,
    vector_crs: str | None = None,
    source_label: str = "vector",
) -> OverlapValidationResult:
    area_bounds = _load_vector_bounds(area_path, target_crs, fallback_crs=area_crs, label="area")
    source_bounds = _load_vector_bounds(vector_path, target_crs, fallback_crs=vector_crs, label=source_label)
    overlaps = box(*area_bounds).intersects(box(*source_bounds))
    return OverlapValidationResult(
        target_crs=target_crs,
        area_bounds=area_bounds,
        source_bounds=source_bounds,
        overlaps=overlaps,
    )


def validate_area_overlaps_dem(
    *,
    area_path: Path,
    dem_path: Path,
    target_crs: str,
    area_crs: str | None = None,
) -> OverlapValidationResult:
    area_bounds = _load_vector_bounds(area_path, target_crs, fallback_crs=area_crs, label="area")
    source_bounds = _load_dem_bounds(dem_path, target_crs)
    overlaps = box(*area_bounds).intersects(box(*source_bounds))
    return OverlapValidationResult(
        target_crs=target_crs,
        area_bounds=area_bounds,
        source_bounds=source_bounds,
        overlaps=overlaps,
    )


def _load_vector_bounds(path: Path, target_crs: str, *, fallback_crs: str | None, label: str) -> list[float]:
    target = path.resolve()
    if not target.exists():
        raise FileNotFoundError(target)
    gdf = gpd.read_file(target)
    if gdf.empty:
        raise ValueError(f"{label.capitalize()} file has no features: {target}")
    if gdf.crs is None:
        if not fallback_crs:
            raise ValueError(
                f"{label.capitalize()} CRS is missing for {target}. "
                f"Pass an explicit CRS with --validate-area-crs or a source-specific CRS option."
            )
        gdf = gdf.set_crs(fallback_crs)
    gdf = gdf.to_crs(CRS.from_user_input(target_crs))
    minx, miny, maxx, maxy = gdf.total_bounds
    return [float(minx), float(miny), float(maxx), float(maxy)]


def _load_dem_bounds(path: Path, target_crs: str) -> list[float]:
    target = path.resolve()
    if not target.exists():
        raise FileNotFoundError(target)
    with rasterio.open(target) as dataset:
        if dataset.crs is None:
            raise ValueError(f"DEM CRS is missing for {target}")
        bounds = dataset.bounds
        transformed = transform_bounds(dataset.crs, CRS.from_user_input(target_crs), *bounds)
    return [float(value) for value in transformed]
