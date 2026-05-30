import numpy as np
from shapely.geometry import Polygon

from src.mesh import make_terrain_mesh
from src.terrain import TerrainGrid


def _grid() -> TerrainGrid:
    xs = np.array([0.0, 1.0, 2.0], dtype=float)
    ys = np.array([0.0, 1.0, 2.0], dtype=float)
    elevations = np.array(
        [
            [0.0, 1.0, 2.0],
            [1.0, 2.0, 3.0],
            [2.0, 3.0, 4.0],
        ],
        dtype=float,
    )
    valid = np.ones_like(elevations, dtype=bool)
    return TerrainGrid(
        xs=xs,
        ys=ys,
        elevations=elevations,
        valid=valid,
        min_elevation=0.0,
        origin_x=0.0,
        origin_y=0.0,
    )


def test_polygon_boundary_mode_clips_square_exactly():
    grid = _grid()
    area = Polygon([(0.25, 0.25), (1.75, 0.25), (1.75, 1.75), (0.25, 1.75)])

    mesh = make_terrain_mesh(grid, 1.5, terrain_boundary_mode="polygon", boundary_area=area)

    assert not mesh.is_empty
    assert mesh.bounds[0][0] == 0.25
    assert mesh.bounds[0][1] == 0.25
    assert mesh.bounds[1][0] == 1.75
    assert mesh.bounds[1][1] == 1.75
    assert mesh.bounds[0][2] == -1.5


def test_polygon_boundary_mode_clips_triangle_with_non_grid_vertices():
    grid = _grid()
    area = Polygon([(0.2, 0.2), (1.8, 0.2), (1.0, 1.7)])

    mesh = make_terrain_mesh(grid, 1.0, terrain_boundary_mode="polygon", boundary_area=area)

    assert not mesh.is_empty
    assert any(abs(float(vertex[0]) - 0.2) < 1e-6 for vertex in mesh.vertices)
    assert any(abs(float(vertex[1]) - 1.7) < 1e-6 for vertex in mesh.vertices)
    assert mesh.bounds[0][2] == -1.0
