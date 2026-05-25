import trimesh

from src.export import cleanup_normals


def test_cleanup_normals_falls_back_without_optional_graph_dependencies(monkeypatch):
    mesh = trimesh.creation.box()

    def fail_fix_normals(*args, **kwargs):
        raise ModuleNotFoundError("No module named 'networkx'")

    monkeypatch.setattr(mesh, "fix_normals", fail_fix_normals)
    monkeypatch.setattr(trimesh.repair, "fix_normals", fail_fix_normals)

    assert cleanup_normals(mesh) is True
