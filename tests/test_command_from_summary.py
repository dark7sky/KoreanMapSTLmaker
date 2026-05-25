import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import command_from_summary


def test_build_command_from_summary_options(tmp_path):
    summary_path = tmp_path / "model_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "options": {
                    "area": "data/area.geojson",
                    "buildings": "data/buildings.geojson",
                    "dem": "data/dem.tif",
                    "out": "output/model.stl",
                    "target_crs": "EPSG:5179",
                    "area_crs": "EPSG:4326",
                    "building_crs": None,
                    "terrain_resolution": 20.0,
                    "terrain_smoothing_iterations": 2,
                    "terrain_smoothing_factor": 0.25,
                    "base_thickness": 2.0,
                    "default_floor_height": 3.0,
                    "default_building_height": 6.0,
                    "min_building_area": 4.0,
                    "simplify_tolerance": 0.1,
                    "model_scale": 0.5,
                    "base_plate_thickness": 1.0,
                    "base_plate_margin": 2.0,
                    "max_area_km2": 4.0,
                    "building_diagnostics_limit": 12,
                    "separate": True,
                    "preview": False,
                    "height_fields": ["HEIGHT"],
                    "floor_fields": ["GRND_FLR"],
                    "building_base_mode": "representative",
                    "export_formats": ["stl", "obj"],
                    "z_scale": 1.5,
                }
            }
        ),
        encoding="utf-8",
    )

    command = command_from_summary.build_command(summary_path)

    assert command.startswith(".\\.venv\\Scripts\\python.exe make_model.py")
    assert "--area data/area.geojson" in command
    assert "--buildings data/buildings.geojson" in command
    assert "--area-crs EPSG:4326" in command
    assert "--terrain-resolution 20.0" in command
    assert "--terrain-smoothing-iterations 2" in command
    assert "--terrain-smoothing-factor 0.25" in command
    assert "--simplify-tolerance 0.1" in command
    assert "--model-scale 0.5" in command
    assert "--base-plate-thickness 1.0" in command
    assert "--base-plate-margin 2.0" in command
    assert "--building-diagnostics-limit 12" in command
    assert "--z-scale 1.5" in command
    assert "--height-field HEIGHT" in command
    assert "--floor-field GRND_FLR" in command
    assert "--export-format stl --export-format obj" in command
    assert "--separate" in command
    assert "--preview" not in command


def test_build_command_requires_options(tmp_path):
    summary_path = tmp_path / "model_summary.json"
    summary_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="options object"):
        command_from_summary.build_command(summary_path)


def test_cli_prints_command(tmp_path):
    summary_path = tmp_path / "model_summary.json"
    summary_path.write_text(
        json.dumps({"options": {"area": "a.geojson", "dem": "d.tif", "out": "o.stl"}}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(Path("scripts") / "command_from_summary.py"), str(summary_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "make_model.py" in result.stdout
    assert "--area a.geojson" in result.stdout
