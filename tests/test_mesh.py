from shapely.geometry import Polygon

from src.mesh import add_base_plate, extrude_polygon_simple, scale_mesh


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


def test_add_base_plate_expands_xy_and_extends_below_model():
    polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    mesh = extrude_polygon_simple(polygon, 0, 5, 0, 0)

    with_plate = add_base_plate(mesh, margin=2.0, thickness=1.5)

    assert with_plate.bounds[0][0] == -2.0
    assert with_plate.bounds[0][1] == -2.0
    assert with_plate.bounds[0][2] == -1.5
    assert with_plate.bounds[1][0] == 12.0
    assert with_plate.bounds[1][1] == 12.0
    assert with_plate.bounds[1][2] == 5.0


def test_scale_mesh_scales_bounds_without_mutating_original():
    polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    mesh = extrude_polygon_simple(polygon, 0, 5, 0, 0)

    scaled = scale_mesh(mesh, 2.0)

    assert mesh.bounds[1][2] == 5.0
    assert scaled.bounds[1][0] == 20.0
    assert scaled.bounds[1][1] == 20.0
    assert scaled.bounds[1][2] == 10.0
