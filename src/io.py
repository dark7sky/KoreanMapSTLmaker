from pathlib import Path
from typing import Optional

import geopandas as gpd
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union


def load_area(path: Path, target_crs: str, fallback_crs: Optional[str]) -> tuple[BaseGeometry, float]:
    gdf = _read_vector(path, fallback_crs)
    if gdf.empty:
        raise ValueError(f"Area file has no features: {path}")
    gdf = gdf.to_crs(target_crs)
    geom = unary_union([_repair_geometry(g) for g in gdf.geometry if g is not None and not g.is_empty])
    if geom.is_empty:
        raise ValueError("Area geometry is empty after loading.")
    return geom, geom.area / 1_000_000.0


def load_buildings(path: Path, target_crs: str, fallback_crs: Optional[str]) -> gpd.GeoDataFrame:
    gdf = _read_vector(path, fallback_crs)
    if gdf.empty:
        return gdf
    gdf["geometry"] = gdf.geometry.map(_repair_geometry)
    return gdf.to_crs(target_crs)


def _read_vector(path: Path, fallback_crs: Optional[str]) -> gpd.GeoDataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        if not fallback_crs:
            raise ValueError(f"CRS is missing for {path}. Pass a fallback CRS option.")
        gdf = gdf.set_crs(fallback_crs)
    return gdf


def _repair_geometry(geom: BaseGeometry) -> BaseGeometry:
    if geom is None or geom.is_empty:
        return geom
    if geom.is_valid:
        return geom
    return geom.buffer(0)
