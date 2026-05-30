from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import triangulate

from src.terrain import TerrainGrid


@dataclass
class _GridElevationSampler:
    grid: TerrainGrid

    def __post_init__(self) -> None:
        self._xs = np.asarray(self.grid.xs, dtype=float)
        self._ys = np.asarray(self.grid.ys, dtype=float)
        self._z = np.asarray(self.grid.elevations, dtype=float)
        finite = np.isfinite(self._z)
        points = np.argwhere(finite)
        self._finite_points = points
        if points.size:
            self._finite_xs = self._xs[points[:, 1]]
            self._finite_ys = self._ys[points[:, 0]]
            self._finite_zs = self._z[points[:, 0], points[:, 1]]
        else:
            self._finite_xs = np.array([], dtype=float)
            self._finite_ys = np.array([], dtype=float)
            self._finite_zs = np.array([], dtype=float)

    def sample(self, x: float, y: float) -> float:
        if self._xs.size < 2 or self._ys.size < 2:
            return float("nan")
        if x < self._xs[0] or x > self._xs[-1] or y < self._ys[0] or y > self._ys[-1]:
            return self._nearest_finite(x, y)

        col = int(np.searchsorted(self._xs, x, side="right") - 1)
        row = int(np.searchsorted(self._ys, y, side="right") - 1)
        col = min(max(col, 0), self._xs.size - 2)
        row = min(max(row, 0), self._ys.size - 2)

        x0 = float(self._xs[col])
        x1 = float(self._xs[col + 1])
        y0 = float(self._ys[row])
        y1 = float(self._ys[row + 1])
        if x1 == x0 or y1 == y0:
            return self._nearest_finite(x, y)

        z00 = float(self._z[row, col])
        z10 = float(self._z[row, col + 1])
        z01 = float(self._z[row + 1, col])
        z11 = float(self._z[row + 1, col + 1])
        corners = [(x0, y0, z00), (x1, y0, z10), (x0, y1, z01), (x1, y1, z11)]
        if all(np.isfinite(value) for _, _, value in corners):
            tx = (x - x0) / (x1 - x0)
            ty = (y - y0) / (y1 - y0)
            top = z00 * (1.0 - tx) + z10 * tx
            bottom = z01 * (1.0 - tx) + z11 * tx
            return float(top * (1.0 - ty) + bottom * ty)

        finite = [(cx, cy, cz) for cx, cy, cz in corners if np.isfinite(cz)]
        if finite:
            distances = [max((x - cx) ** 2 + (y - cy) ** 2, 1e-12) for cx, cy, _ in finite]
            weights = [1.0 / distance for distance in distances]
            weighted = sum(weight * value for weight, (_, _, value) in zip(weights, finite))
            return float(weighted / sum(weights))
        return self._nearest_finite(x, y)

    def _nearest_finite(self, x: float, y: float) -> float:
        if self._finite_points.size == 0:
            return float("nan")
        dx = self._finite_xs - x
        dy = self._finite_ys - y
        index = int(np.argmin((dx * dx) + (dy * dy)))
        return float(self._finite_zs[index])


def make_polygon_clipped_terrain_mesh(
    grid: TerrainGrid,
    *,
    area: BaseGeometry,
    base_thickness: float,
) -> trimesh.Trimesh:
    polygons = [poly for poly in _iter_polygons(area) if not poly.is_empty and poly.area > 0]
    if not polygons:
        return trimesh.Trimesh()

    sampler = _GridElevationSampler(grid)
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    vertex_map: dict[tuple[float, float, float], int] = {}

    def vertex_id(x: float, y: float, z: float) -> int:
        key = (
            round(float(x - grid.origin_x), 6),
            round(float(y - grid.origin_y), 6),
            round(float(z), 6),
        )
        if key not in vertex_map:
            vertex_map[key] = len(vertices)
            vertices.append(key)
        return vertex_map[key]

    for polygon in polygons:
        triangles = [
            tri
            for tri in triangulate(polygon)
            if not tri.is_empty and tri.area > 0 and polygon.covers(tri.representative_point())
        ]
        for tri in triangles:
            coords = list(tri.exterior.coords)[:3]
            top_ids: list[int] = []
            bottom_ids: list[int] = []
            skip_triangle = False
            for x, y in coords:
                top_z = sampler.sample(float(x), float(y))
                if not np.isfinite(top_z):
                    skip_triangle = True
                    break
                top_ids.append(vertex_id(float(x), float(y), top_z))
                bottom_ids.append(vertex_id(float(x), float(y), -base_thickness))
            if skip_triangle:
                continue
            faces.append((top_ids[0], top_ids[1], top_ids[2]))
            faces.append((bottom_ids[2], bottom_ids[1], bottom_ids[0]))

        _append_boundary_walls(polygon, sampler, vertex_id, faces, base_thickness)

    if not vertices or not faces:
        return trimesh.Trimesh()
    return trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(faces), process=True)


def _append_boundary_walls(
    polygon: Polygon,
    sampler: _GridElevationSampler,
    vertex_id,
    faces: list[tuple[int, int, int]],
    base_thickness: float,
) -> None:
    rings = [polygon.exterior, *polygon.interiors]
    for ring in rings:
        coords = list(ring.coords)
        for (x1, y1), (x2, y2) in zip(coords[:-1], coords[1:]):
            z1 = sampler.sample(float(x1), float(y1))
            z2 = sampler.sample(float(x2), float(y2))
            if not (np.isfinite(z1) and np.isfinite(z2)):
                continue
            t1 = vertex_id(float(x1), float(y1), z1)
            t2 = vertex_id(float(x2), float(y2), z2)
            b1 = vertex_id(float(x1), float(y1), -base_thickness)
            b2 = vertex_id(float(x2), float(y2), -base_thickness)
            faces.append((t1, b1, b2))
            faces.append((t1, b2, t2))


def _iter_polygons(geometry: BaseGeometry):
    if isinstance(geometry, Polygon):
        yield geometry
    elif isinstance(geometry, MultiPolygon):
        yield from geometry.geoms
