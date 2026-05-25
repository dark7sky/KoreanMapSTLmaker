from dataclasses import dataclass

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.warp import transform_bounds
from rasterio.crs import CRS
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry


@dataclass
class TerrainGrid:
    xs: np.ndarray
    ys: np.ndarray
    elevations: np.ndarray
    valid: np.ndarray
    min_elevation: float
    origin_x: float
    origin_y: float
    filled_nodata_samples: int = 0


@dataclass
class DemInfo:
    crs: str
    bounds: list[float]
    bounds_in_target_crs: list[float]
    width: int
    height: int
    nodata: float | None
    resolution: list[float]


@dataclass
class TerrainDiagnostics:
    area_bounds: list[float]
    dem_bounds_in_target_crs: list[float]
    bbox_overlap: bool
    grid_samples: int
    samples_inside_area: int
    finite_dem_samples: int


class ElevationSampler:
    def __init__(self, dem_path: str, target_crs: str):
        self.dataset = rasterio.open(dem_path)
        self.nodata = self.dataset.nodata
        dem_crs = self.dataset.crs
        if dem_crs is None:
            raise ValueError(f"DEM has no CRS: {dem_path}. Provide a GeoTIFF with a defined CRS.")
        self.dem_crs = dem_crs
        self.target_crs = target_crs
        self.transformer = Transformer.from_crs(CRS.from_string(target_crs), dem_crs, always_xy=True)

    def close(self) -> None:
        self.dataset.close()

    def sample_one(self, x: float, y: float) -> float:
        dx, dy = self.transformer.transform(x, y)
        value = next(self.dataset.sample([(dx, dy)]))[0]
        if self._is_nodata(value):
            return float("nan")
        return float(value)

    def sample_many(self, points: list[tuple[float, float]]) -> np.ndarray:
        transformed = [self.transformer.transform(x, y) for x, y in points]
        values = np.array([v[0] for v in self.dataset.sample(transformed)], dtype=float)
        if self.nodata is not None:
            values[np.isclose(values, self.nodata)] = np.nan
        return values

    def _is_nodata(self, value: float) -> bool:
        if self.nodata is None:
            return False
        return bool(np.isclose(value, self.nodata))

    def bounds_in_target_crs(self) -> list[float]:
        bounds = self.dataset.bounds
        transformed = transform_bounds(self.dem_crs, CRS.from_string(self.target_crs), *bounds)
        return [float(value) for value in transformed]


def sample_terrain(
    area: BaseGeometry,
    dem_path: str,
    target_crs: str,
    resolution: float,
    z_scale: float = 1.0,
    smoothing_iterations: int = 0,
    smoothing_factor: float = 0.5,
    interpolate_nodata: bool = False,
) -> TerrainGrid:
    sampler = ElevationSampler(dem_path, target_crs)
    try:
        minx, miny, maxx, maxy = area.bounds
        area_bounds = [float(minx), float(miny), float(maxx), float(maxy)]
        dem_bounds = sampler.bounds_in_target_crs()
        if not _bounds_overlap(area_bounds, dem_bounds):
            raise ValueError(
                "Selected area does not overlap the DEM in the target CRS. "
                f"target_crs={target_crs}; area_bounds={area_bounds}; "
                f"dem_bounds_in_target_crs={dem_bounds}; dem_crs={sampler.dem_crs}"
            )

        xs = np.arange(minx, maxx + resolution, resolution)
        ys = np.arange(miny, maxy + resolution, resolution)
        if xs.size < 2 or ys.size < 2:
            raise ValueError("Area is too small for the requested terrain resolution.")

        points = [(float(x), float(y)) for y in ys for x in xs]
        values = sampler.sample_many(points).reshape((ys.size, xs.size))
        finite_dem_samples = int(np.isfinite(values).sum())

        inside = np.zeros(values.shape, dtype=bool)
        samples_inside_area = 0
        for row, y in enumerate(ys):
            for col, x in enumerate(xs):
                inside_area = area.covers(Point(float(x), float(y)))
                if inside_area:
                    samples_inside_area += 1
                inside[row, col] = inside_area

        filled_nodata_samples = 0
        if interpolate_nodata:
            values, filled_nodata_samples = interpolate_missing_inside_area(values, inside)

        valid = inside & np.isfinite(values)

        if not valid.any():
            diagnostics = TerrainDiagnostics(
                area_bounds=area_bounds,
                dem_bounds_in_target_crs=dem_bounds,
                bbox_overlap=True,
                grid_samples=int(values.size),
                samples_inside_area=samples_inside_area,
                finite_dem_samples=finite_dem_samples,
            )
            raise ValueError(
                "No valid DEM samples found inside selected area. "
                f"target_crs={target_crs}; dem_crs={sampler.dem_crs}; nodata={sampler.nodata}; "
                f"diagnostics={diagnostics}"
            )

        min_elevation = float(np.nanmin(values[valid]))
        normalized = values - min_elevation
        if z_scale != 1.0:
            normalized = normalized * z_scale
        normalized = smooth_elevations(
            normalized,
            valid,
            iterations=smoothing_iterations,
            factor=smoothing_factor,
        )

        return TerrainGrid(
            xs=xs,
            ys=ys,
            elevations=normalized,
            valid=valid,
            min_elevation=min_elevation,
            origin_x=float(minx),
            origin_y=float(miny),
            filled_nodata_samples=filled_nodata_samples,
        )
    finally:
        sampler.close()


def interpolate_missing_inside_area(values: np.ndarray, inside: np.ndarray) -> tuple[np.ndarray, int]:
    filled = values.copy()
    missing = inside & ~np.isfinite(filled)
    if not missing.any():
        return filled, 0
    if not (inside & np.isfinite(filled)).any():
        return filled, 0

    filled_count = 0
    rows, cols = filled.shape
    max_passes = rows + cols
    for _ in range(max_passes):
        updates: list[tuple[int, int, float]] = []
        missing_positions = np.argwhere(inside & ~np.isfinite(filled))
        if missing_positions.size == 0:
            break
        for row, col in missing_positions:
            neighbors = []
            for nrow in range(max(0, row - 1), min(rows, row + 2)):
                for ncol in range(max(0, col - 1), min(cols, col + 2)):
                    if nrow == row and ncol == col:
                        continue
                    if inside[nrow, ncol] and np.isfinite(filled[nrow, ncol]):
                        neighbors.append(float(filled[nrow, ncol]))
            if neighbors:
                updates.append((int(row), int(col), float(np.mean(neighbors))))
        if not updates:
            break
        for row, col, value in updates:
            filled[row, col] = value
        filled_count += len(updates)
    return filled, filled_count


def smooth_elevations(elevations: np.ndarray, valid: np.ndarray, *, iterations: int, factor: float) -> np.ndarray:
    if iterations <= 0 or factor <= 0:
        return elevations
    factor = min(float(factor), 1.0)
    smoothed = elevations.copy()
    for _ in range(iterations):
        next_values = smoothed.copy()
        rows, cols = smoothed.shape
        for row in range(rows):
            for col in range(cols):
                if not valid[row, col]:
                    continue
                neighbors = []
                for nrow in range(max(0, row - 1), min(rows, row + 2)):
                    for ncol in range(max(0, col - 1), min(cols, col + 2)):
                        if valid[nrow, ncol]:
                            neighbors.append(smoothed[nrow, ncol])
                if neighbors:
                    neighbor_mean = float(np.mean(neighbors))
                    next_values[row, col] = (smoothed[row, col] * (1.0 - factor)) + (neighbor_mean * factor)
        smoothed = next_values
    return smoothed


def get_dem_info(dem_path: str, target_crs: str) -> DemInfo:
    with rasterio.open(dem_path) as dataset:
        if dataset.crs is None:
            raise ValueError(f"DEM has no CRS: {dem_path}. Provide a GeoTIFF with a defined CRS.")
        bounds = dataset.bounds
        target_bounds = transform_bounds(dataset.crs, CRS.from_string(target_crs), *bounds)
        return DemInfo(
            crs=str(dataset.crs),
            bounds=[float(bounds.left), float(bounds.bottom), float(bounds.right), float(bounds.top)],
            bounds_in_target_crs=[float(value) for value in target_bounds],
            width=int(dataset.width),
            height=int(dataset.height),
            nodata=None if dataset.nodata is None else float(dataset.nodata),
            resolution=[float(abs(dataset.res[0])), float(abs(dataset.res[1]))],
        )


def bounds_overlap(area_bounds: list[float], dem_bounds_in_target_crs: list[float]) -> bool:
    return _bounds_overlap(area_bounds, dem_bounds_in_target_crs)


def _bounds_overlap(left: list[float], right: list[float]) -> bool:
    left_minx, left_miny, left_maxx, left_maxy = left
    right_minx, right_miny, right_maxx, right_maxy = right
    return not (
        left_maxx < right_minx
        or right_maxx < left_minx
        or left_maxy < right_miny
        or right_maxy < left_miny
    )
