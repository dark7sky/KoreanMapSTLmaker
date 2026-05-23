from shapely.geometry import Polygon

from src.mesh import extrude_polygon_simple


def test_extrude_polygon_simple_creates_mesh():
    polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    mesh = extrude_polygon_simple(polygon, 0, 5, 0, 0)
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    assert mesh.bounds[0][2] == 0
    assert mesh.bounds[1][2] == 5
