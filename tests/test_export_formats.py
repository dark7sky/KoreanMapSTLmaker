from argparse import Namespace
from pathlib import Path

import pytest

import src.cli
import src.pipeline


class _FakeBounds:
    def __init__(self, values):
        self._values = values

    def tolist(self):
        return list(self._values)


class _FakeMesh:
    def __init__(self, *, is_empty=False):
        self.is_empty = is_empty
        self.vertices = [0, 1, 2]
        self.faces = [0]
        self.bounds = _FakeBounds([0.0, 0.0, 0.0, 1.0, 1.0, 1.0])


class _FakePolygon:
    area = 12.5
    bounds = (1.0, 2.0, 3.0, 4.0)

    @staticmethod
    def representative_point():
        return type("Point", (), {"x": 2.0, "y": 3.0})()


def test_cli_default_export_format_is_stl(monkeypatch):
    captured = {}

    def fake_parse_args(self):
        return Namespace(
            area=Path("area.geojson"),
            buildings=None,
            dem=Path("dem.tif"),
            out=Path("model.stl"),
            target_crs="EPSG:5179",
            area_crs=None,
            building_crs=None,
            dem_crs=None,
            terrain_resolution=10.0,
            terrain_resampling="nearest",
            terrain_smoothing_iterations=0,
            terrain_smoothing_factor=0.5,
            interpolate_nodata=False,
            base_thickness=2.0,
            default_floor_height=3.0,
            default_building_height=6.0,
            min_building_area=4.0,
            simplify_tolerance=0.0,
            model_scale=1.0,
            base_plate_thickness=0.0,
            base_plate_margin=0.0,
            max_area_km2=4.0,
            building_diagnostics_limit=200,
            separate=False,
            export_format=None,
            preview=False,
            height_field=None,
            floor_field=None,
            building_base_mode="representative",
        )

    def fake_build_model(options):
        captured["formats"] = options.export_formats
        return {"output": "model.stl", "building_count": 0, "faces": 0}

    monkeypatch.setattr(src.cli.argparse.ArgumentParser, "parse_args", fake_parse_args)
    monkeypatch.setattr("src.pipeline.build_model", fake_build_model)

    src.cli.main()

    assert captured["formats"] == ("stl",)
    assert src.cli._normalize_export_formats(["stl", "obj", "glb", "gltf", "stl"]) == ("stl", "obj", "glb", "gltf")


def test_cli_passes_simplify_tolerance(monkeypatch):
    captured = {}

    def fake_parse_args(self):
        return Namespace(
            area=Path("area.geojson"),
            buildings=None,
            dem=Path("dem.tif"),
            out=Path("model.stl"),
            target_crs="EPSG:5179",
            area_crs=None,
            building_crs=None,
            dem_crs=None,
            terrain_resolution=10.0,
            terrain_resampling="nearest",
            terrain_smoothing_iterations=0,
            terrain_smoothing_factor=0.5,
            interpolate_nodata=False,
            base_thickness=2.0,
            default_floor_height=3.0,
            default_building_height=6.0,
            min_building_area=4.0,
            simplify_tolerance=1.25,
            model_scale=1.0,
            base_plate_thickness=0.0,
            base_plate_margin=0.0,
            max_area_km2=4.0,
            building_diagnostics_limit=200,
            separate=False,
            export_format=None,
            preview=False,
            height_field=None,
            floor_field=None,
            building_base_mode="representative",
        )

    def fake_build_model(options):
        captured["simplify_tolerance"] = options.simplify_tolerance
        return {"output": "model.stl", "building_count": 0, "faces": 0}

    monkeypatch.setattr(src.cli.argparse.ArgumentParser, "parse_args", fake_parse_args)
    monkeypatch.setattr("src.pipeline.build_model", fake_build_model)

    src.cli.main()

    assert captured["simplify_tolerance"] == 1.25


def test_cli_passes_decimate_max_faces(monkeypatch):
    captured = {}

    def fake_parse_args(self):
        return Namespace(
            area=Path("area.geojson"),
            buildings=None,
            dem=Path("dem.tif"),
            out=Path("model.stl"),
            target_crs="EPSG:5179",
            area_crs=None,
            building_crs=None,
            dem_crs=None,
            terrain_resolution=10.0,
            terrain_resampling="nearest",
            terrain_smoothing_iterations=0,
            terrain_smoothing_factor=0.5,
            interpolate_nodata=False,
            base_thickness=2.0,
            default_floor_height=3.0,
            default_building_height=6.0,
            min_building_area=4.0,
            simplify_tolerance=0.0,
            model_scale=1.0,
            decimate_max_faces=2500,
            base_plate_thickness=0.0,
            base_plate_margin=0.0,
            max_area_km2=4.0,
            building_diagnostics_limit=200,
            separate=False,
            export_format=None,
            preview=False,
            height_field=None,
            floor_field=None,
            building_base_mode="representative",
        )

    def fake_build_model(options):
        captured["decimate_max_faces"] = options.decimate_max_faces
        return {"output": "model.stl", "building_count": 0, "faces": 0}

    monkeypatch.setattr(src.cli.argparse.ArgumentParser, "parse_args", fake_parse_args)
    monkeypatch.setattr("src.pipeline.build_model", fake_build_model)

    src.cli.main()

    assert captured["decimate_max_faces"] == 2500


def test_cli_passes_print_ready_options(monkeypatch):
    captured = {}

    def fake_parse_args(self):
        return Namespace(
            area=Path("area.geojson"),
            buildings=None,
            dem=Path("dem.tif"),
            out=Path("model.stl"),
            target_crs="EPSG:5179",
            area_crs=None,
            building_crs=None,
            dem_crs=None,
            terrain_resolution=10.0,
            terrain_resampling="bilinear",
            terrain_smoothing_iterations=2,
            terrain_smoothing_factor=0.25,
            interpolate_nodata=True,
            base_thickness=2.0,
            default_floor_height=3.0,
            default_building_height=6.0,
            min_building_area=4.0,
            simplify_tolerance=0.0,
            model_scale=0.5,
            base_plate_thickness=1.2,
            base_plate_margin=3.4,
            max_area_km2=4.0,
            building_diagnostics_limit=12,
            separate=False,
            export_format=None,
            preview=False,
            height_field=None,
            floor_field=None,
            building_base_mode="representative",
        )

    def fake_build_model(options):
        captured["model_scale"] = options.model_scale
        captured["base_plate_thickness"] = options.base_plate_thickness
        captured["base_plate_margin"] = options.base_plate_margin
        captured["terrain_smoothing_iterations"] = options.terrain_smoothing_iterations
        captured["terrain_smoothing_factor"] = options.terrain_smoothing_factor
        captured["interpolate_nodata"] = options.interpolate_nodata
        captured["building_diagnostics_limit"] = options.building_diagnostics_limit
        return {"output": "model.stl", "building_count": 0, "faces": 0}

    monkeypatch.setattr(src.cli.argparse.ArgumentParser, "parse_args", fake_parse_args)
    monkeypatch.setattr("src.pipeline.build_model", fake_build_model)

    src.cli.main()

    assert captured == {
        "model_scale": 0.5,
        "base_plate_thickness": 1.2,
        "base_plate_margin": 3.4,
        "terrain_smoothing_iterations": 2,
        "terrain_smoothing_factor": 0.25,
        "interpolate_nodata": True,
        "building_diagnostics_limit": 12,
    }


def test_pipeline_exports_visual_formats_as_scene_when_separate(monkeypatch, tmp_path):
    terrain_mesh = _FakeMesh()
    buildings_mesh = _FakeMesh()
    combined_mesh = _FakeMesh()
    export_stl_calls = []
    export_obj_calls = []
    export_glb_calls = []
    export_gltf_calls = []
    export_obj_scene_calls = []
    export_glb_scene_calls = []
    export_gltf_scene_calls = []
    merge_call_count = {"count": 0}

    class _Area:
        bounds = (0.0, 0.0, 1.0, 1.0)

    class _TerrainGrid:
        min_elevation = 10.0
        elevations = type("E", (), {"shape": (2, 3)})()
        valid = type("V", (), {"sum": lambda self: 6})()
        origin_x = 0.0
        origin_y = 0.0

    class _BuildingResult:
        buildings = [
            type("Building", (), {"polygon": _FakePolygon(), "height": 10.0, "base_z": 1.5, "source": "HEIGHT"})(),
            type("Building", (), {"polygon": _FakePolygon(), "height": 6.0, "base_z": 0.5, "source": "default"})(),
        ]
        source_feature_count = 0
        intersect_feature_count = 0
        clipped_polygon_count = 0
        skipped_small_count = 0
        skipped_no_elevation_count = 0
        fields = []
        height_counts = []

    monkeypatch.setattr(src.pipeline, "load_area", lambda *args, **kwargs: (_Area(), 0.01))
    monkeypatch.setattr(src.pipeline, "sample_terrain", lambda *args, **kwargs: _TerrainGrid())
    monkeypatch.setattr(src.pipeline, "make_terrain_mesh", lambda *args, **kwargs: terrain_mesh)
    monkeypatch.setattr(
        src.pipeline,
        "get_dem_info",
        lambda *args, **kwargs: type(
            "DemInfo",
            (),
            {
                "crs": "EPSG:5179",
                "bounds": [0.0, 0.0, 1.0, 1.0],
                "bounds_in_target_crs": [0.0, 0.0, 1.0, 1.0],
                "width": 1,
                "height": 1,
                "resolution": [1.0, 1.0],
                "nodata": None,
            },
        )(),
    )
    monkeypatch.setattr(src.pipeline, "prepare_buildings", lambda *args, **kwargs: _BuildingResult())
    monkeypatch.setattr(src.pipeline, "make_building_meshes", lambda *args, **kwargs: [])

    def fake_merge_meshes(parts):
        merge_call_count["count"] += 1
        if merge_call_count["count"] == 1:
            return buildings_mesh
        return combined_mesh

    monkeypatch.setattr(src.pipeline, "merge_meshes", fake_merge_meshes)
    monkeypatch.setattr(src.pipeline, "mesh_summary", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(src.pipeline, "bounds_overlap", lambda *args, **kwargs: True)
    monkeypatch.setattr(src.pipeline, "export_summary", lambda *args, **kwargs: tmp_path / "summary.json")
    monkeypatch.setattr(src.pipeline, "scale_mesh", lambda mesh, *_args, **_kwargs: mesh)
    monkeypatch.setattr(src.pipeline, "cleanup_normals", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(src.pipeline, "make_visual_scene", lambda terrain, buildings: ("scene", terrain, buildings))
    monkeypatch.setattr(src.pipeline, "export_stl", lambda mesh, path: export_stl_calls.append(path))
    monkeypatch.setattr(src.pipeline, "export_obj", lambda mesh, path: export_obj_calls.append(path))
    monkeypatch.setattr(src.pipeline, "export_glb", lambda mesh, path: export_glb_calls.append(path))
    monkeypatch.setattr(src.pipeline, "export_gltf", lambda mesh, path: export_gltf_calls.append(path))
    monkeypatch.setattr(src.pipeline, "export_obj_scene", lambda scene, path: export_obj_scene_calls.append((scene, path)))
    monkeypatch.setattr(src.pipeline, "export_glb_scene", lambda scene, path: export_glb_scene_calls.append((scene, path)))
    monkeypatch.setattr(src.pipeline, "export_gltf_scene", lambda scene, path: export_gltf_scene_calls.append((scene, path)))

    options = src.pipeline.BuildOptions(
        area_path=tmp_path / "area.geojson",
        buildings_path=None,
        dem_path=tmp_path / "dem.tif",
        out_path=tmp_path / "model.stl",
        target_crs="EPSG:5179",
        area_crs=None,
        building_crs=None,
        dem_crs=None,
        terrain_resolution=10.0,
        terrain_resampling="nearest",
        terrain_smoothing_iterations=0,
        terrain_smoothing_factor=0.5,
        interpolate_nodata=True,
        base_thickness=2.0,
        default_floor_height=3.0,
        default_building_height=6.0,
        min_building_area=4.0,
        simplify_tolerance=0.0,
        model_scale=1.0,
        base_plate_thickness=0.0,
        base_plate_margin=0.0,
        max_area_km2=4.0,
        building_diagnostics_limit=1,
        separate=True,
        preview=False,
        height_fields=(),
        floor_fields=(),
        building_base_mode="representative",
        export_formats=("obj", "glb", "gltf"),
    )
    options.area_path.write_text("{}", encoding="utf-8")
    options.dem_path.write_text("dem", encoding="utf-8")

    summary = src.pipeline.build_model(options)

    assert export_stl_calls == []
    assert export_obj_calls == []
    assert export_glb_calls == []
    assert export_gltf_calls == []
    assert export_obj_scene_calls == [(("scene", terrain_mesh, buildings_mesh), tmp_path / "model.obj")]
    assert export_glb_scene_calls == [(("scene", terrain_mesh, buildings_mesh), tmp_path / "model.glb")]
    assert export_gltf_scene_calls == [(("scene", terrain_mesh, buildings_mesh), tmp_path / "model.gltf")]
    assert summary["output"] == str(tmp_path / "model.obj")
    assert summary["outputs"] == {
        "obj": str(tmp_path / "model.obj"),
        "glb": str(tmp_path / "model.glb"),
        "gltf": str(tmp_path / "model.gltf"),
    }
    assert summary["options"]["out"] == str(tmp_path / "model.stl")
    assert summary["options"]["export_formats"] == ["obj", "glb", "gltf"]
    assert summary["options"]["simplify_tolerance"] == 0.0
    assert summary["options"]["interpolate_nodata"] is True
    assert summary["terrain_interpolate_nodata"] is True
    assert summary["visual_separation"] == {"obj": True, "glb": True, "gltf": True}
    diagnostics = summary["building_diagnostics"]
    assert diagnostics["per_building_limit"] == 1
    assert diagnostics["per_building_omitted_count"] == 1
    assert diagnostics["per_building"] == [
        {
            "index": 0,
            "height": 10.0,
            "base_z": 1.5,
            "source": "HEIGHT",
            "area": 12.5,
            "bounds": [1.0, 2.0, 3.0, 4.0],
            "representative_point": [2.0, 3.0],
        }
    ]


def test_pipeline_rejects_preview_without_stl_before_processing(monkeypatch, tmp_path):
    options = src.pipeline.BuildOptions(
        area_path=tmp_path / "area.geojson",
        buildings_path=None,
        dem_path=tmp_path / "dem.tif",
        out_path=tmp_path / "model.stl",
        target_crs="EPSG:5179",
        area_crs=None,
        building_crs=None,
        dem_crs=None,
        terrain_resolution=10.0,
        terrain_resampling="nearest",
        terrain_smoothing_iterations=0,
        terrain_smoothing_factor=0.5,
        interpolate_nodata=False,
        base_thickness=2.0,
        default_floor_height=3.0,
        default_building_height=6.0,
        min_building_area=4.0,
        simplify_tolerance=0.0,
        model_scale=1.0,
        base_plate_thickness=0.0,
        base_plate_margin=0.0,
        max_area_km2=4.0,
        building_diagnostics_limit=200,
        separate=False,
        preview=True,
        height_fields=(),
        floor_fields=(),
        building_base_mode="representative",
        export_formats=("obj",),
    )
    options.area_path.write_text("{}", encoding="utf-8")
    options.dem_path.write_text("dem", encoding="utf-8")

    def fail_if_processing_starts(*args, **kwargs):
        raise AssertionError("build_model should validate preview/export formats before loading data")

    monkeypatch.setattr(src.pipeline, "load_area", fail_if_processing_starts)

    with pytest.raises(ValueError, match="preview requires STL"):
        src.pipeline.build_model(options)


def test_pipeline_keeps_single_mesh_visual_export_when_not_separate(monkeypatch, tmp_path):
    terrain_mesh = _FakeMesh()
    buildings_mesh = _FakeMesh()
    combined_mesh = _FakeMesh()
    export_obj_calls = []
    export_obj_scene_calls = []

    class _Area:
        bounds = (0.0, 0.0, 1.0, 1.0)

    class _TerrainGrid:
        min_elevation = 10.0
        elevations = type("E", (), {"shape": (2, 3)})()
        valid = type("V", (), {"sum": lambda self: 6})()
        origin_x = 0.0
        origin_y = 0.0

    class _BuildingResult:
        buildings = []
        source_feature_count = 0
        intersect_feature_count = 0
        clipped_polygon_count = 0
        skipped_small_count = 0
        skipped_no_elevation_count = 0
        fields = []
        height_counts = []

    monkeypatch.setattr(src.pipeline, "load_area", lambda *args, **kwargs: (_Area(), 0.01))
    monkeypatch.setattr(src.pipeline, "sample_terrain", lambda *args, **kwargs: _TerrainGrid())
    monkeypatch.setattr(src.pipeline, "make_terrain_mesh", lambda *args, **kwargs: terrain_mesh)
    monkeypatch.setattr(
        src.pipeline,
        "get_dem_info",
        lambda *args, **kwargs: type(
            "DemInfo",
            (),
            {
                "crs": "EPSG:5179",
                "bounds": [0.0, 0.0, 1.0, 1.0],
                "bounds_in_target_crs": [0.0, 0.0, 1.0, 1.0],
                "width": 1,
                "height": 1,
                "resolution": [1.0, 1.0],
                "nodata": None,
            },
        )(),
    )
    monkeypatch.setattr(src.pipeline, "prepare_buildings", lambda *args, **kwargs: _BuildingResult())
    monkeypatch.setattr(src.pipeline, "make_building_meshes", lambda *args, **kwargs: [])
    monkeypatch.setattr(src.pipeline, "merge_meshes", lambda parts: buildings_mesh if len(parts) == 0 else combined_mesh)
    monkeypatch.setattr(src.pipeline, "add_base_plate", lambda mesh, **kwargs: mesh)
    monkeypatch.setattr(src.pipeline, "scale_mesh", lambda mesh, *_args, **_kwargs: mesh)
    monkeypatch.setattr(src.pipeline, "cleanup_normals", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(src.pipeline, "mesh_summary", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(src.pipeline, "bounds_overlap", lambda *args, **kwargs: True)
    monkeypatch.setattr(src.pipeline, "export_summary", lambda *args, **kwargs: tmp_path / "summary.json")
    monkeypatch.setattr(src.pipeline, "export_obj", lambda mesh, path: export_obj_calls.append((mesh, path)))
    monkeypatch.setattr(src.pipeline, "export_obj_scene", lambda scene, path: export_obj_scene_calls.append((scene, path)))

    options = src.pipeline.BuildOptions(
        area_path=tmp_path / "area.geojson",
        buildings_path=None,
        dem_path=tmp_path / "dem.tif",
        out_path=tmp_path / "model.stl",
        target_crs="EPSG:5179",
        area_crs=None,
        building_crs=None,
        dem_crs=None,
        terrain_resolution=10.0,
        terrain_smoothing_iterations=0,
        terrain_smoothing_factor=0.5,
        interpolate_nodata=True,
        base_thickness=2.0,
        default_floor_height=3.0,
        default_building_height=6.0,
        min_building_area=4.0,
        simplify_tolerance=0.0,
        model_scale=1.0,
        base_plate_thickness=0.0,
        base_plate_margin=0.0,
        max_area_km2=4.0,
        building_diagnostics_limit=1,
        separate=False,
        preview=False,
        height_fields=(),
        floor_fields=(),
        building_base_mode="representative",
        export_formats=("obj",),
    )
    options.area_path.write_text("{}", encoding="utf-8")
    options.dem_path.write_text("dem", encoding="utf-8")

    summary = src.pipeline.build_model(options)

    assert export_obj_calls == [(combined_mesh, tmp_path / "model.obj")]
    assert export_obj_scene_calls == []
    assert summary["visual_separation"] == {"obj": False}


def test_pipeline_separate_stl_behavior_is_unchanged(monkeypatch, tmp_path):
    terrain_mesh = _FakeMesh()
    buildings_mesh = _FakeMesh()
    combined_mesh = _FakeMesh()
    export_stl_calls = []
    merge_call_count = {"count": 0}

    class _Area:
        bounds = (0.0, 0.0, 1.0, 1.0)

    class _TerrainGrid:
        min_elevation = 10.0
        elevations = type("E", (), {"shape": (2, 3)})()
        valid = type("V", (), {"sum": lambda self: 6})()
        origin_x = 0.0
        origin_y = 0.0

    class _BuildingResult:
        buildings = []
        source_feature_count = 0
        intersect_feature_count = 0
        clipped_polygon_count = 0
        skipped_small_count = 0
        skipped_no_elevation_count = 0
        fields = []
        height_counts = []

    monkeypatch.setattr(src.pipeline, "load_area", lambda *args, **kwargs: (_Area(), 0.01))
    monkeypatch.setattr(src.pipeline, "sample_terrain", lambda *args, **kwargs: _TerrainGrid())
    monkeypatch.setattr(src.pipeline, "make_terrain_mesh", lambda *args, **kwargs: terrain_mesh)
    monkeypatch.setattr(
        src.pipeline,
        "get_dem_info",
        lambda *args, **kwargs: type(
            "DemInfo",
            (),
            {
                "crs": "EPSG:5179",
                "bounds": [0.0, 0.0, 1.0, 1.0],
                "bounds_in_target_crs": [0.0, 0.0, 1.0, 1.0],
                "width": 1,
                "height": 1,
                "resolution": [1.0, 1.0],
                "nodata": None,
            },
        )(),
    )
    monkeypatch.setattr(src.pipeline, "prepare_buildings", lambda *args, **kwargs: _BuildingResult())
    monkeypatch.setattr(src.pipeline, "make_building_meshes", lambda *args, **kwargs: [])

    def fake_merge_meshes(parts):
        merge_call_count["count"] += 1
        if merge_call_count["count"] == 1:
            return buildings_mesh
        return combined_mesh

    monkeypatch.setattr(src.pipeline, "merge_meshes", fake_merge_meshes)
    monkeypatch.setattr(src.pipeline, "add_base_plate", lambda mesh, **kwargs: mesh)
    monkeypatch.setattr(src.pipeline, "scale_mesh", lambda mesh, *_args, **_kwargs: mesh)
    monkeypatch.setattr(src.pipeline, "cleanup_normals", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(src.pipeline, "mesh_summary", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(src.pipeline, "bounds_overlap", lambda *args, **kwargs: True)
    monkeypatch.setattr(src.pipeline, "export_summary", lambda *args, **kwargs: tmp_path / "summary.json")
    monkeypatch.setattr(src.pipeline, "export_stl", lambda mesh, path: export_stl_calls.append(path))
    monkeypatch.setattr(src.pipeline, "export_obj_scene", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected")))
    monkeypatch.setattr(src.pipeline, "export_glb_scene", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected")))
    monkeypatch.setattr(src.pipeline, "export_gltf_scene", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected")))

    options = src.pipeline.BuildOptions(
        area_path=tmp_path / "area.geojson",
        buildings_path=None,
        dem_path=tmp_path / "dem.tif",
        out_path=tmp_path / "model.stl",
        target_crs="EPSG:5179",
        area_crs=None,
        building_crs=None,
        dem_crs=None,
        terrain_resolution=10.0,
        terrain_smoothing_iterations=0,
        terrain_smoothing_factor=0.5,
        interpolate_nodata=True,
        base_thickness=2.0,
        default_floor_height=3.0,
        default_building_height=6.0,
        min_building_area=4.0,
        simplify_tolerance=0.0,
        model_scale=1.0,
        base_plate_thickness=0.0,
        base_plate_margin=0.0,
        max_area_km2=4.0,
        building_diagnostics_limit=1,
        separate=True,
        preview=False,
        height_fields=(),
        floor_fields=(),
        building_base_mode="representative",
        export_formats=("stl",),
    )
    options.area_path.write_text("{}", encoding="utf-8")
    options.dem_path.write_text("dem", encoding="utf-8")

    summary = src.pipeline.build_model(options)

    assert export_stl_calls == [
        tmp_path / "model.stl",
        tmp_path / "model_terrain.stl",
        tmp_path / "model_buildings.stl",
    ]
    assert summary["visual_separation"] == {"stl": False}
