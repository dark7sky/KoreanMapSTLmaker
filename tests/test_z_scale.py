from collections import Counter
from types import SimpleNamespace

import numpy as np
from shapely.geometry import box

from src import cli, pipeline, terrain


class _StubSampler:
    def __init__(self, dem_path: str, target_crs: str, dem_crs: str | None = None):
        self.dem_path = dem_path
        self.target_crs = target_crs
        self.dem_crs = "EPSG:3857"
        self.nodata = None

    def close(self) -> None:
        return None

    def bounds_in_target_crs(self) -> list[float]:
        return [0.0, 0.0, 1.0, 1.0]

    def sample_many(self, points: list[tuple[float, float]]) -> np.ndarray:
        return np.array([10.0, 12.0, 14.0, 16.0], dtype=float)


def test_sample_terrain_applies_z_scale_after_min_normalization(monkeypatch):
    monkeypatch.setattr(terrain, "ElevationSampler", _StubSampler)
    grid = terrain.sample_terrain(box(0.0, 0.0, 1.0, 1.0), "dem.tif", "EPSG:3857", 1.0, z_scale=2.0)

    np.testing.assert_allclose(grid.elevations, np.array([[0.0, 4.0], [8.0, 12.0]]))
    assert grid.min_elevation == 10.0


def test_sample_terrain_applies_smoothing_to_valid_samples(monkeypatch):
    class SmoothingSampler(_StubSampler):
        def bounds_in_target_crs(self) -> list[float]:
            return [0.0, 0.0, 2.0, 2.0]

        def sample_many(self, points: list[tuple[float, float]]) -> np.ndarray:
            return np.array([10.0, 10.0, 10.0, 10.0, 30.0, 10.0, 10.0, 10.0, 10.0], dtype=float)

    monkeypatch.setattr(terrain, "ElevationSampler", SmoothingSampler)

    grid = terrain.sample_terrain(
        box(0.0, 0.0, 2.0, 2.0),
        "dem.tif",
        "EPSG:3857",
        1.0,
        smoothing_iterations=1,
        smoothing_factor=1.0,
    )

    assert grid.elevations[1, 1] < 20.0
    assert grid.elevations[0, 0] > 0.0


def test_sample_terrain_interpolates_nodata_inside_area(monkeypatch):
    class NodataSampler(_StubSampler):
        nodata = -9999.0

        def bounds_in_target_crs(self) -> list[float]:
            return [0.0, 0.0, 2.0, 2.0]

        def sample_many(self, points: list[tuple[float, float]]) -> np.ndarray:
            return np.array([10.0, 10.0, 10.0, 10.0, np.nan, 14.0, 10.0, 10.0, 10.0], dtype=float)

    monkeypatch.setattr(terrain, "ElevationSampler", NodataSampler)

    grid = terrain.sample_terrain(
        box(0.0, 0.0, 2.0, 2.0),
        "dem.tif",
        "EPSG:3857",
        1.0,
        interpolate_nodata=True,
    )

    assert grid.valid.all()
    assert grid.filled_nodata_samples == 1
    assert np.isfinite(grid.elevations[1, 1])


def test_pipeline_scales_building_base_z_only(monkeypatch, tmp_path):
    area = box(0.0, 0.0, 1.0, 1.0)
    captured = {}

    monkeypatch.setattr(pipeline, "load_area", lambda *_: (area, 0.1))
    monkeypatch.setattr(
        pipeline,
        "sample_terrain",
        lambda *_args, **_kwargs: terrain.TerrainGrid(
            xs=np.array([0.0, 1.0]),
            ys=np.array([0.0, 1.0]),
            elevations=np.array([[0.0, 1.0], [2.0, 3.0]]),
            valid=np.ones((2, 2), dtype=bool),
            min_elevation=10.0,
            origin_x=0.0,
            origin_y=0.0,
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "prepare_buildings",
        lambda *_args, **_kwargs: SimpleNamespace(
            buildings=[SimpleNamespace(polygon=area, height=7.0, base_z=3.0, source="height")],
            height_counts=Counter({"height": 1}),
            source_feature_count=1,
            intersect_feature_count=1,
            clipped_polygon_count=1,
            skipped_small_count=0,
            skipped_no_elevation_count=0,
            fields=[],
        ),
    )
    monkeypatch.setattr(pipeline, "make_terrain_mesh", lambda *_: _FakeMesh())
    monkeypatch.setattr(
        pipeline,
        "make_building_meshes",
        lambda rows: _capture_rows(captured, rows),
    )
    monkeypatch.setattr(pipeline, "merge_meshes", lambda *_: _FakeMesh())
    monkeypatch.setattr(
        pipeline,
        "get_dem_info",
        lambda *_: terrain.DemInfo("EPSG:3857", [0, 0, 1, 1], [0, 0, 1, 1], 2, 2, None, [1.0, 1.0]),
    )
    monkeypatch.setattr(pipeline, "mesh_summary", lambda *_: {})
    monkeypatch.setattr(pipeline, "export_summary", lambda *_: tmp_path / "summary.json")
    monkeypatch.setattr(pipeline, "export_stl", lambda *_: None)

    area_path = tmp_path / "area.geojson"
    dem_path = tmp_path / "dem.tif"
    area_path.write_text("{}")
    dem_path.write_text("dem")
    options = pipeline.BuildOptions(
        area_path=area_path,
        buildings_path=None,
        dem_path=dem_path,
        out_path=tmp_path / "out.stl",
        target_crs="EPSG:3857",
        area_crs=None,
        building_crs=None,
        dem_crs=None,
        terrain_resolution=1.0,
        terrain_smoothing_iterations=0,
        terrain_smoothing_factor=0.5,
        interpolate_nodata=False,
        base_thickness=2.0,
        default_floor_height=3.0,
        default_building_height=6.0,
        min_building_area=0.0,
        simplify_tolerance=0.0,
        model_scale=1.0,
        base_plate_thickness=0.0,
        base_plate_margin=0.0,
        max_area_km2=10.0,
        building_diagnostics_limit=200,
        separate=False,
        preview=False,
        height_fields=(),
        floor_fields=(),
        building_base_mode="representative",
        export_formats=("stl",),
        z_scale=2.5,
    )

    pipeline.build_model(options)

    assert len(captured["rows"]) == 1
    _, height, base_z, _, _ = captured["rows"][0]
    assert height == 7.0
    assert base_z == 7.5


def test_cli_passes_default_and_custom_z_scale(monkeypatch, tmp_path, capsys):
    captured = []

    def _stub_build_model(options):
        captured.append(options.z_scale)
        return {"output": str(options.out_path), "building_count": 0, "faces": 0}

    monkeypatch.setattr(pipeline, "build_model", _stub_build_model)
    area_path = tmp_path / "area.geojson"
    dem_path = tmp_path / "dem.tif"
    area_path.write_text("{}")
    dem_path.write_text("dem")
    out_path = tmp_path / "out.stl"

    monkeypatch.setattr(
        "sys.argv",
        ["prog", "--area", str(area_path), "--dem", str(dem_path), "--out", str(out_path)],
    )
    cli.main()
    capsys.readouterr()

    monkeypatch.setattr(
        "sys.argv",
        [
            "prog",
            "--area",
            str(area_path),
            "--dem",
            str(dem_path),
            "--out",
            str(out_path),
            "--z-scale",
            "3.0",
        ],
    )
    cli.main()
    capsys.readouterr()

    assert captured == [1.0, 3.0]


class _FakeMesh:
    def __init__(self):
        self.vertices = np.zeros((1, 3), dtype=float)
        self.faces = np.zeros((1, 3), dtype=int)
        self.bounds = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]], dtype=float)
        self.is_empty = False


def _capture_rows(captured: dict, rows: list[tuple]) -> list[_FakeMesh]:
    captured["rows"] = rows
    return [_FakeMesh()]
