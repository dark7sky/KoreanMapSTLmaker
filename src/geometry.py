from __future__ import annotations

from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

try:
    from shapely import make_valid as _make_valid
except ImportError:
    try:
        from shapely.validation import make_valid as _make_valid
    except ImportError:
        _make_valid = None


def repair_polygonal_geometry(geom: BaseGeometry) -> BaseGeometry:
    """Repair geometry and keep only polygonal components."""
    if geom is None or geom.is_empty:
        return geom
    if geom.is_valid:
        repaired = geom
    elif _make_valid is not None:
        repaired = _make_valid(geom)
    else:
        repaired = geom.buffer(0)
    return _extract_polygonal_components(repaired)


def _extract_polygonal_components(geom: BaseGeometry) -> BaseGeometry:
    if geom is None or geom.is_empty:
        return geom
    if isinstance(geom, (Polygon, MultiPolygon)):
        return geom
    if isinstance(geom, GeometryCollection):
        polygons = []
        for part in geom.geoms:
            polygonal = _extract_polygonal_components(part)
            if polygonal is None or polygonal.is_empty:
                continue
            if isinstance(polygonal, Polygon):
                polygons.append(polygonal)
            elif isinstance(polygonal, MultiPolygon):
                polygons.extend(list(polygonal.geoms))
        if not polygons:
            return Polygon()
        if len(polygons) == 1:
            return polygons[0]
        return unary_union(polygons)
    return Polygon()
