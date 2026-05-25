from pathlib import Path
from typing import Optional

import geopandas as gpd
from pyproj.exceptions import CRSError
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union


def load_area(path: Path, target_crs: str, fallback_crs: Optional[str]) -> tuple[BaseGeometry, float]:
    gdf = _read_vector(path, fallback_crs, "area", "--area-crs")
    if gdf.empty:
        raise ValueError(f"Area file has no features: {path}")
    gdf = _to_crs(gdf, target_crs, "area", path)
    geom = unary_union([_repair_geometry(g) for g in gdf.geometry if g is not None and not g.is_empty])
    if geom.is_empty:
        raise ValueError("Area geometry is empty after loading.")
    return geom, geom.area / 1_000_000.0


def load_buildings(path: Path, target_crs: str, fallback_crs: Optional[str]) -> gpd.GeoDataFrame:
    gdf = _read_vector(path, fallback_crs, "building", "--building-crs")
    if gdf.empty:
        return gdf
    gdf["geometry"] = gdf.geometry.map(_repair_geometry)
    return _to_crs(gdf, target_crs, "building", path)


def _read_vector(path: Path, fallback_crs: Optional[str], label: str, fallback_flag: str) -> gpd.GeoDataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        if not fallback_crs:
            raise ValueError(
                f"{label.capitalize()} CRS is missing for {path}. "
                f"Pass {fallback_flag} with the source CRS, for example {fallback_flag} EPSG:4326 "
                "for area-selector GeoJSON, or restore the missing .prj sidecar for SHP files."
            )
        try:
            gdf = gdf.set_crs(fallback_crs)
        except CRSError as error:
            raise ValueError(f"Invalid fallback CRS for {label} data: {fallback_crs}") from error
    return gdf


def _to_crs(gdf: gpd.GeoDataFrame, target_crs: str, label: str, path: Path) -> gpd.GeoDataFrame:
    try:
        return gdf.to_crs(target_crs)
    except CRSError as error:
        raise ValueError(
            f"Could not transform {label} data from {gdf.crs} to target CRS {target_crs}: {path}. "
            "Check --target-crs and the source CRS metadata."
        ) from error


def _repair_geometry(geom: BaseGeometry) -> BaseGeometry:
    if geom is None or geom.is_empty:
        return geom
    if geom.is_valid:
        return geom
    return geom.buffer(0)
