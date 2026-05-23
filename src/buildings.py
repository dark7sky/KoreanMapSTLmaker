from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

from src.height import choose_building_height
from src.io import load_buildings
from src.terrain import ElevationSampler


@dataclass
class PreparedBuilding:
    polygon: Polygon
    height: float
    base_z: float
    source: str


@dataclass
class BuildingPreparationResult:
    buildings: list[PreparedBuilding]
    height_counts: Counter
    source_feature_count: int
    intersect_feature_count: int
    clipped_polygon_count: int
    skipped_small_count: int
    skipped_no_elevation_count: int
    fields: list[str]


def prepare_buildings(
    buildings_path: Optional[Path],
    area: BaseGeometry,
    dem_path: Path,
    target_crs: str,
    building_crs: Optional[str],
    min_elevation: float,
    default_floor_height: float,
    default_building_height: float,
    min_building_area: float,
    height_fields: Optional[tuple[str, ...]] = None,
    floor_fields: Optional[tuple[str, ...]] = None,
) -> BuildingPreparationResult:
    if buildings_path is None:
        return BuildingPreparationResult([], Counter(), 0, 0, 0, 0, 0, [])

    gdf = load_buildings(buildings_path, target_crs, building_crs)
    fields = [str(column) for column in gdf.columns if column != "geometry"]
    if gdf.empty:
        return BuildingPreparationResult([], Counter(), 0, 0, 0, 0, 0, fields)

    source_feature_count = int(len(gdf))
    gdf = gdf[gdf.intersects(area)].copy()
    if gdf.empty:
        return BuildingPreparationResult([], Counter(), source_feature_count, 0, 0, 0, 0, fields)

    sampler = ElevationSampler(str(dem_path), target_crs)
    buildings: list[PreparedBuilding] = []
    counts: Counter = Counter()
    clipped_polygon_count = 0
    skipped_small_count = 0
    skipped_no_elevation_count = 0
    try:
        for _, row in gdf.iterrows():
            clipped = row.geometry.intersection(area)
            for polygon in _iter_polygons(clipped):
                clipped_polygon_count += 1
                if polygon.area < min_building_area:
                    skipped_small_count += 1
                    continue
                height_result = choose_building_height(
                    row.to_dict(),
                    default_floor_height=default_floor_height,
                    default_building_height=default_building_height,
                    height_fields=height_fields,
                    floor_fields=floor_fields,
                )
                point = polygon.representative_point()
                elevation = sampler.sample_one(point.x, point.y)
                if elevation != elevation:
                    skipped_no_elevation_count += 1
                    continue
                base_z = elevation - min_elevation
                buildings.append(PreparedBuilding(polygon, height_result.value, base_z, height_result.source))
                counts[height_result.source] += 1
    finally:
        sampler.close()

    return BuildingPreparationResult(
        buildings=buildings,
        height_counts=counts,
        source_feature_count=source_feature_count,
        intersect_feature_count=int(len(gdf)),
        clipped_polygon_count=clipped_polygon_count,
        skipped_small_count=skipped_small_count,
        skipped_no_elevation_count=skipped_no_elevation_count,
        fields=fields,
    )


def _iter_polygons(geometry: BaseGeometry):
    if geometry.is_empty:
        return
    if isinstance(geometry, Polygon):
        yield geometry
    elif isinstance(geometry, MultiPolygon):
        yield from geometry.geoms
