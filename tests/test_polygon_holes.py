import pytest
from shapely.geometry import MultiPolygon, Polygon

from src.mesh import extrude_polygon_simple, make_building_meshes


def test_extrude_polygon_with_hole_matches_expected_volume():
    outer = [(0, 0), (12, 0), (12, 12), (0, 12)]
    hole = [(2, 2), (2, 10), (10, 10), (10, 2)]
    polygon = Polygon(shell=outer, holes=[hole])

    mesh = extrude_polygon_simple(polygon, bottom_z=1.5, top_z=6.5, origin_x=0.0, origin_y=0.0)

    assert mesh.is_watertight
    assert mesh.volume == pytest.approx(polygon.area * (6.5 - 1.5))
    assert mesh.bounds[0][2] == pytest.approx(1.5)
    assert mesh.bounds[1][2] == pytest.approx(6.5)


def test_make_building_meshes_splits_multipolygon_parts():
    part_a = Polygon([(0, 0), (4, 0), (4, 4), (0, 4)])
    part_b = Polygon([(10, 10), (13, 10), (13, 13), (10, 13)])
    geom = MultiPolygon([part_a, part_b])

    meshes = make_building_meshes([(geom, 3.0, 0.0, 0.0, 0.0)])

    assert len(meshes) == 2
    assert all(mesh.is_watertight for mesh in meshes)
    assert sum(mesh.volume for mesh in meshes) == pytest.approx((part_a.area + part_b.area) * 3.0)

