import pytest
import trimesh
import numpy as np

from src.mesh_quality import (
    bounds,
    euler_number,
    face_count,
    is_empty,
    is_watertight,
    mesh_summary,
    vertex_count,
    volume,
    non_manifold_edge_count,
    degenerate_face_count,
)


def test_mesh_summary_reports_box_quality_values():
    mesh = trimesh.creation.box(extents=(2.0, 3.0, 4.0))

    summary = mesh_summary(mesh)

    assert summary == {
        "vertex_count": 8,
        "face_count": 12,
        "bounds": ((-1.0, -1.5, -2.0), (1.0, 1.5, 2.0)),
        "is_empty": False,
        "is_watertight": True,
        "euler_number": 2,
        "volume": pytest.approx(24.0),
        "non_manifold_edge_count": 0,
        "degenerate_face_count": 0,
    }


def test_individual_helpers_report_empty_mesh_safely():
    mesh = trimesh.Trimesh()

    assert vertex_count(mesh) == 0
    assert face_count(mesh) == 0
    assert bounds(mesh) is None
    assert is_empty(mesh) is True
    assert is_watertight(mesh) is False
    assert euler_number(mesh) == 0
    assert volume(mesh) == 0.0
    assert non_manifold_edge_count(mesh) == 0
    assert degenerate_face_count(mesh) == 0


def test_optional_quality_values_can_be_missing():
    class MinimalMesh:
        vertices = [(0.0, 0.0, 0.0)]
        faces = []

    summary = mesh_summary(MinimalMesh())

    assert summary == {
        "vertex_count": 1,
        "face_count": 0,
        "bounds": None,
        "is_empty": True,
        "is_watertight": False,
        "euler_number": None,
        "volume": None,
        "non_manifold_edge_count": 0,
        "degenerate_face_count": 0,
    }


def test_optional_quality_properties_that_raise_are_ignored():
    class FragileMesh:
        vertices = [(0.0, 0.0, 0.0)]
        faces = [(0, 0, 0)]

        @property
        def bounds(self):
            raise ValueError("bounds unavailable")

        @property
        def is_empty(self):
            raise ValueError("empty unavailable")

        @property
        def is_watertight(self):
            raise ValueError("watertight unavailable")

        @property
        def euler_number(self):
            raise ValueError("euler unavailable")

        @property
        def volume(self):
            raise ValueError("volume unavailable")

        @property
        def edges_unique_inverse(self):
            raise ValueError("edges_unique_inverse unavailable")

        @property
        def nondegenerate_faces(self):
            raise ValueError("nondegenerate_faces unavailable")

    summary = mesh_summary(FragileMesh())

    assert summary == {
        "vertex_count": 1,
        "face_count": 1,
        "bounds": None,
        "is_empty": False,
        "is_watertight": False,
        "euler_number": None,
        "volume": None,
        "non_manifold_edge_count": 0,
        "degenerate_face_count": 1,
    }


def test_mesh_quality_non_manifold_and_degenerate():
    # Construct a mesh with one degenerate face and one true non-manifold edge
    # (vertices share coordinates to form degenerate face and multiple face connections)
    vertices = np.array([[0,0,0], [1,0,0], [0,1,0], [0,0,0]], dtype=float)
    # Face 0: valid, Face 1: degenerate
    faces = np.array([[0,1,2], [0,0,3]], dtype=int)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

    assert degenerate_face_count(mesh) == 1
    assert non_manifold_edge_count(mesh) == 4


def test_non_manifold_edge_count_includes_boundary_edges():
    class OpenTriangleMesh:
        vertices = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        faces = [(0, 1, 2)]

    assert non_manifold_edge_count(OpenTriangleMesh()) == 3
