from src.export import export_preview_html


def test_preview_html_includes_structured_summary_panel(tmp_path):
    stl_path = tmp_path / "model.stl"
    stl_path.write_bytes(b"solid sample\nendsolid sample\n")
    summary = {
        "output": str(stl_path),
        "building_count": 3,
        "vertices": 120,
        "faces": 220,
        "min_elevation_m": 14.25,
        "terrain_resolution_m": 10.0,
        "outputs": {"stl": str(stl_path)},
    }

    preview_path = export_preview_html(stl_path, summary)
    html = preview_path.read_text(encoding="utf-8")

    assert "<h2>Preview Summary</h2>" in html
    assert '["Buildings", summary.building_count ?? 0]' in html
    assert '["Vertices", summary.vertices ?? 0]' in html
    assert '["Terrain resolution", `${summary.terrain_resolution_m ?? 0} m`]' in html
    assert "escapeHtml(value)" in html
    assert "escapeAttribute(toFileHref(String(pathValue)))" in html
    assert '.filter(([key]) => key === "obj" || key === "glb" || key === "gltf" || key.endsWith("_stl"))' in html


def test_preview_html_lists_clickable_obj_and_separate_stl_outputs(tmp_path):
    stl_path = tmp_path / "model.stl"
    stl_path.write_bytes(b"solid sample\nendsolid sample\n")
    summary = {
        "output": str(stl_path),
        "building_count": 2,
        "vertices": 42,
        "faces": 50,
        "min_elevation_m": 1.0,
        "terrain_resolution_m": 5.0,
        "outputs": {
            "stl": str(stl_path),
            "obj": str(tmp_path / "model.obj"),
            "glb": str(tmp_path / "model.glb"),
            "gltf": str(tmp_path / "model.gltf"),
            "terrain_stl": str(tmp_path / "model_terrain.stl"),
            "buildings_stl": str(tmp_path / "model_buildings.stl"),
        },
    }

    preview_path = export_preview_html(stl_path, summary)
    html = preview_path.read_text(encoding="utf-8")

    assert "Output files" in html
    assert "model.obj" in html
    assert "model.glb" in html
    assert "model.gltf" in html
    assert "model_terrain.stl" in html
    assert "model_buildings.stl" in html
    assert "file:///" in html
    assert "model.stl</a>" not in html
    assert "const hasSeparatedStl = Boolean(terrainStlBase64) || Boolean(buildingsStlBase64);" in html
    assert "addMeshFromStl(terrainStlBase64" in html
    assert "addMeshFromStl(buildingsStlBase64" in html
    assert "color: 0xc4a484" in html
    assert "color: 0xbec0c8" in html


def test_preview_html_escapes_summary_values(tmp_path):
    stl_path = tmp_path / "model.stl"
    stl_path.write_bytes(b"solid sample\nendsolid sample\n")
    summary = {
        "output": "<script>alert(1)</script>",
        "building_count": 1,
        "vertices": 2,
        "faces": 3,
        "min_elevation_m": 4.0,
        "terrain_resolution_m": 5.0,
        "outputs": {"obj": str(tmp_path / 'bad"name.obj')},
    }

    preview_path = export_preview_html(stl_path, summary)
    html = preview_path.read_text(encoding="utf-8")

    assert "function escapeHtml" in html
    assert "function escapeAttribute" in html
    assert "<script>alert(1)</script>" not in html
    assert "\\u003cscript\\u003ealert(1)\\u003c/script\\u003e" in html


def test_preview_html_uses_default_single_mesh_branch_without_separate_stl(tmp_path):
    stl_path = tmp_path / "model.stl"
    stl_path.write_bytes(b"solid sample\nendsolid sample\n")
    summary = {
        "output": str(stl_path),
        "outputs": {"stl": str(stl_path)},
    }

    preview_path = export_preview_html(stl_path, summary)
    html = preview_path.read_text(encoding="utf-8")

    assert 'const terrainStlBase64 = "";' in html
    assert 'const buildingsStlBase64 = "";' in html
    assert "const hasSeparatedStl = Boolean(terrainStlBase64) || Boolean(buildingsStlBase64);" in html
    assert "addMeshFromStl(stlBase64" in html
    assert "color: 0xd8d2c4" in html


def test_preview_html_supports_local_module_paths_from_summary_options(tmp_path):
    stl_path = tmp_path / "model.stl"
    stl_path.write_bytes(b"solid sample\nendsolid sample\n")
    summary = {
        "output": str(stl_path),
        "outputs": {"stl": str(stl_path)},
        "options": {
            "preview_assets": {
                "three": "./vendor/three.module.js",
                "orbit_controls": "./vendor/OrbitControls.js",
                "stl_loader": "./vendor/STLLoader.js",
            }
        },
    }

    preview_path = export_preview_html(stl_path, summary)
    html = preview_path.read_text(encoding="utf-8")

    assert 'import * as THREE from "./vendor/three.module.js";' in html
    assert 'import { OrbitControls } from "./vendor/OrbitControls.js";' in html
    assert 'import { STLLoader } from "./vendor/STLLoader.js";' in html
