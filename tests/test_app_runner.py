from pathlib import Path

from app.runner import run_build
from src.pipeline import BuildOptions


def _sample_options() -> BuildOptions:
    return BuildOptions(
        area_path=Path("data/sample/area.geojson"),
        buildings_path=Path("data/sample/buildings.geojson"),
        dem_path=Path("data/sample/dem.tif"),
        out_path=Path("output/model.stl"),
        target_crs="EPSG:5179",
        area_crs=None,
        building_crs=None,
        dem_crs=None,
        terrain_resolution=10.0,
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
        preview=False,
        height_fields=None,
        floor_fields=None,
        building_base_mode="representative",
        export_formats=("stl",),
        z_scale=1.0,
    )


def test_run_build_success():
    options = _sample_options()

    def fake_build(passed: BuildOptions) -> dict:
        assert passed is options
        return {"output": "output/model.stl", "building_count": 2}

    result = run_build(options, build_fn=fake_build)

    assert result.ok is True
    assert result.summary == {"output": "output/model.stl", "building_count": 2}
    assert result.error is None
    assert result.elapsed_seconds >= 0


def test_run_build_error():
    options = _sample_options()

    def fake_build(_: BuildOptions) -> dict:
        raise RuntimeError("boom")

    result = run_build(options, build_fn=fake_build)

    assert result.ok is False
    assert result.summary is None
    assert result.error == "boom"
    assert result.elapsed_seconds >= 0
