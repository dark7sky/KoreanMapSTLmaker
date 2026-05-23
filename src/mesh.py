from collections import defaultdict
from typing import Iterable

import numpy as np
import trimesh
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import triangulate

from src.terrain import TerrainGrid


def make_terrain_mesh(grid: TerrainGrid, base_thickness: float) -> trimesh.Trimesh:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    top_index: dict[tuple[int, int], int] = {}
    bottom_index: dict[tuple[int, int], int] = {}

    def add_vertex(row: int, col: int, z: float) -> int:
        vertices.append((float(grid.xs[col] - grid.origin_x), float(grid.ys[row] - grid.origin_y), float(z)))
        return len(vertices) - 1

    rows, cols = grid.elevations.shape
    for row in range(rows):
        for col in range(cols):
            if grid.valid[row, col]:
                top_index[(row, col)] = add_vertex(row, col, grid.elevations[row, col])
                bottom_index[(row, col)] = add_vertex(row, col, -base_thickness)

    used_edges: defaultdict[tuple[int, int], int] = defaultdict(int)

    def add_face(a: int, b: int, c: int) -> None:
        faces.append((a, b, c))
        for u, v in ((a, b), (b, c), (c, a)):
            used_edges[tuple(sorted((u, v)))] += 1

    for row in range(rows - 1):
        for col in range(cols - 1):
            corners = [(row, col), (row, col + 1), (row + 1, col + 1), (row + 1, col)]
            if not all(c in top_index for c in corners):
                continue
            a, b, c, d = [top_index[p] for p in corners]
            add_face(a, b, c)
            add_face(a, c, d)

            ba, bb, bc, bd = [bottom_index[p] for p in corners]
            add_face(bc, bb, ba)
            add_face(bd, bc, ba)

    # Boundary side walls around valid cells.
    for row in range(rows - 1):
        for col in range(cols - 1):
            cell = [(row, col), (row, col + 1), (row + 1, col + 1), (row + 1, col)]
            if not all(p in top_index for p in cell):
                continue
            neighbors = {
                "top": row == 0 or not all((p in top_index) for p in [(row - 1, col), (row - 1, col + 1)]),
                "right": col == cols - 2 or not all((p in top_index) for p in [(row, col + 2), (row + 1, col + 2)]),
                "bottom": row == rows - 2 or not all((p in top_index) for p in [(row + 2, col), (row + 2, col + 1)]),
                "left": col == 0 or not all((p in top_index) for p in [(row, col - 1), (row + 1, col - 1)]),
            }
            edges = [
                ("top", cell[0], cell[1]),
                ("right", cell[1], cell[2]),
                ("bottom", cell[2], cell[3]),
                ("left", cell[3], cell[0]),
            ]
            for name, p1, p2 in edges:
                if not neighbors[name]:
                    continue
                t1, t2 = top_index[p1], top_index[p2]
                b1, b2 = bottom_index[p1], bottom_index[p2]
                faces.append((t1, b1, b2))
                faces.append((t1, b2, t2))

    return trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(faces), process=True)


def make_building_meshes(
    polygons: Iterable[tuple[Polygon, float, float, float, float]],
) -> list[trimesh.Trimesh]:
    meshes: list[trimesh.Trimesh] = []
    for polygon, height, base_z, origin_x, origin_y in polygons:
        for part in _iter_polygons(polygon):
            mesh = extrude_polygon_simple(part, base_z, base_z + height, origin_x, origin_y)
            if mesh.vertices.size and mesh.faces.size:
                meshes.append(mesh)
    return meshes


def extrude_polygon_simple(
    polygon: Polygon,
    bottom_z: float,
    top_z: float,
    origin_x: float,
    origin_y: float,
) -> trimesh.Trimesh:
    if polygon.is_empty or polygon.area <= 0:
        return trimesh.Trimesh()

    triangles = [t for t in triangulate(polygon) if polygon.contains(t.representative_point())]
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    vertex_map: dict[tuple[float, float, float], int] = {}

    def vertex_id(x: float, y: float, z: float) -> int:
        key = (round(x - origin_x, 6), round(y - origin_y, 6), round(z, 6))
        if key not in vertex_map:
            vertex_map[key] = len(vertices)
            vertices.append(key)
        return vertex_map[key]

    for tri in triangles:
        coords = list(tri.exterior.coords)[:3]
        top = [vertex_id(x, y, top_z) for x, y in coords]
        bottom = [vertex_id(x, y, bottom_z) for x, y in coords]
        faces.append((top[0], top[1], top[2]))
        faces.append((bottom[2], bottom[1], bottom[0]))

    # Create side walls for exterior boundary
    ring = list(polygon.exterior.coords)
    for (x1, y1), (x2, y2) in zip(ring[:-1], ring[1:]):
        t1 = vertex_id(x1, y1, top_z)
        t2 = vertex_id(x2, y2, top_z)
        b1 = vertex_id(x1, y1, bottom_z)
        b2 = vertex_id(x2, y2, bottom_z)
        faces.append((t1, b1, b2))
        faces.append((t1, b2, t2))

    # Create side walls for interior boundaries (holes)
    for interior in polygon.interiors:
        ring = list(interior.coords)
        for (x1, y1), (x2, y2) in zip(ring[:-1], ring[1:]):
            t1 = vertex_id(x1, y1, top_z)
            t2 = vertex_id(x2, y2, top_z)
            b1 = vertex_id(x1, y1, bottom_z)
            b2 = vertex_id(x2, y2, bottom_z)
            faces.append((t1, b1, b2))
            faces.append((t1, b2, t2))

    return trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(faces), process=True)


def merge_meshes(meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    meshes = [mesh for mesh in meshes if mesh.vertices.size and mesh.faces.size]
    if not meshes:
        return trimesh.Trimesh()
    return trimesh.util.concatenate(meshes)


def _iter_polygons(geometry):
    if isinstance(geometry, Polygon):
        yield geometry
    elif isinstance(geometry, MultiPolygon):
        yield from geometry.geoms
