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
            terrain_resolution=10.0,
            base_thickness=2.0,
            default_floor_height=3.0,
            default_building_height=6.0,
            min_building_area=4.0,
            simplify_tolerance=0.0,
            model_scale=1.0,
            base_plate_thickness=0.0,
            base_plate_margin=0.0,
            max_area_km2=4.0,
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
    assert src.cli._normalize_export_formats(["stl", "obj", "stl"]) == ("stl", "obj")


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
            terrain_resolution=10.0,
            base_thickness=2.0,
            default_floor_height=3.0,
            default_building_height=6.0,
            min_building_area=4.0,
            simplify_tolerance=1.25,
            model_scale=1.0,
            base_plate_thickness=0.0,
            base_plate_margin=0.0,
            max_area_km2=4.0,
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
            terrain_resolution=10.0,
            base_thickness=2.0,
            default_floor_height=3.0,
            default_building_height=6.0,
            min_building_area=4.0,
            simplify_tolerance=0.0,
            model_scale=0.5,
            base_plate_thickness=1.2,
            base_plate_margin=3.4,
            max_area_km2=4.0,
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
        return {"output": "model.stl", "building_count": 0, "faces": 0}

    monkeypatch.setattr(src.cli.argparse.ArgumentParser, "parse_args", fake_parse_args)
    monkeypatch.setattr("src.pipeline.build_model", fake_build_model)

    src.cli.main()

    assert captured == {
        "model_scale": 0.5,
        "base_plate_thickness": 1.2,
        "base_plate_margin": 3.4,
    }


def test_pipeline_exports_requested_formats_and_keeps_separate_stl_only(monkeypatch, tmp_path):
    terrain_mesh = _FakeMesh()
    buildings_mesh = _FakeMesh()
    combined_mesh = _FakeMesh()
    export_stl_calls = []
    export_obj_calls = []
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
    monkeypatch.setattr(src.pipeline, "mesh_summary", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(src.pipeline, "bounds_overlap", lambda *args, **kwargs: True)
    monkeypatch.setattr(src.pipeline, "export_summary", lambda *args, **kwargs: tmp_path / "summary.json")
    monkeypatch.setattr(src.pipeline, "export_stl", lambda mesh, path: export_stl_calls.append(path))
    monkeypatch.setattr(src.pipeline, "export_obj", lambda mesh, path: export_obj_calls.append(path))

    options = src.pipeline.BuildOptions(
        area_path=tmp_path / "area.geojson",
        buildings_path=None,
        dem_path=tmp_path / "dem.tif",
        out_path=tmp_path / "model.stl",
        target_crs="EPSG:5179",
        area_crs=None,
        building_crs=None,
        terrain_resolution=10.0,
        base_thickness=2.0,
        default_floor_height=3.0,
        default_building_height=6.0,
        min_building_area=4.0,
        simplify_tolerance=0.0,
        model_scale=1.0,
        base_plate_thickness=0.0,
        base_plate_margin=0.0,
        max_area_km2=4.0,
        separate=True,
        preview=False,
        height_fields=(),
        floor_fields=(),
        building_base_mode="representative",
        export_formats=("obj",),
    )
    options.area_path.write_text("{}", encoding="utf-8")
    options.dem_path.write_text("dem", encoding="utf-8")

    summary = src.pipeline.build_model(options)

    assert export_stl_calls == []
    assert export_obj_calls == [tmp_path / "model.obj"]
    assert summary["output"] == str(tmp_path / "model.obj")
    assert summary["outputs"] == {"obj": str(tmp_path / "model.obj")}
    assert summary["options"]["out"] == str(tmp_path / "model.stl")
    assert summary["options"]["export_formats"] == ["obj"]
    assert summary["options"]["simplify_tolerance"] == 0.0


def test_pipeline_rejects_preview_without_stl_before_processing(monkeypatch, tmp_path):
    options = src.pipeline.BuildOptions(
        area_path=tmp_path / "area.geojson",
        buildings_path=None,
        dem_path=tmp_path / "dem.tif",
        out_path=tmp_path / "model.stl",
        target_crs="EPSG:5179",
        area_crs=None,
        building_crs=None,
        terrain_resolution=10.0,
        base_thickness=2.0,
        default_floor_height=3.0,
        default_building_height=6.0,
        min_building_area=4.0,
        simplify_tolerance=0.0,
        model_scale=1.0,
        base_plate_thickness=0.0,
        base_plate_margin=0.0,
        max_area_km2=4.0,
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
