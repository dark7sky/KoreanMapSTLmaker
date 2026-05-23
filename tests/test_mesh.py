from shapely.geometry import Polygon

from src.mesh import extrude_polygon_simple


def test_extrude_polygon_simple_creates_mesh():
    polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    mesh = extrude_polygon_simple(polygon, 0, 5, 0, 0)
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    assert mesh.bounds[0][2] == 0
    assert mesh.bounds[1][2] == 5


def test_extrude_polygon_with_holes_creates_valid_mesh():
    outer = [(0, 0), (10, 0), (10, 10), (0, 10)]
    inner = [(3, 3), (3, 7), (7, 7), (7, 3)]
    polygon = Polygon(shell=outer, holes=[inner])
    
    mesh = extrude_polygon_simple(polygon, 0.0, 5.0, 0.0, 0.0)
    
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    assert mesh.is_watertight is True
    # Volume of outer box (100 * 5 = 500) minus inner hole (16 * 5 = 80) = 420
    import pytest
    assert mesh.volume == pytest.approx(420.0)

