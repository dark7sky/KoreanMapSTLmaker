import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import command_from_dataset


def write_registry(path: Path, registry: object) -> None:
    path.write_text(json.dumps(registry), encoding="utf-8")


def test_build_commands_with_required_fields_only(tmp_path):
    registry_path = tmp_path / "datasets.json"
    write_registry(
        registry_path,
        {
            "datasets": [
                {
                    "name": "sample",
                    "area": "data/area.geojson",
                    "dem": "data/dem.tif",
                    "buildings": "data/buildings.geojson",
                }
            ]
        },
    )

    inspect_command, make_model_command = command_from_dataset.build_commands(registry_path, "sample")

    area = str((tmp_path / "data" / "area.geojson").resolve())
    dem = str((tmp_path / "data" / "dem.tif").resolve())
    buildings = str((tmp_path / "data" / "buildings.geojson").resolve())
    output_stl = str((Path("output") / "sample.stl").resolve())

    assert inspect_command == (
        f".\\.venv\\Scripts\\python.exe scripts\\inspect_data.py --area '{area}' "
        f"--buildings '{buildings}' --dem '{dem}'"
    )
    assert make_model_command == (
        f".\\.venv\\Scripts\\python.exe make_model.py --area '{area}' "
        f"--buildings '{buildings}' --dem '{dem}' --out '{output_stl}'"
    )


def test_build_commands_include_optional_metadata(tmp_path):
    registry_path = tmp_path / "datasets.json"
    write_registry(
        registry_path,
        {
            "datasets": [
                {
                    "name": "sample",
                    "area": "data/area.geojson",
                    "dem": "data/dem.tif",
                    "buildings": "data/buildings.geojson",
                    "target_crs": "EPSG:32652",
                    "area_crs": "EPSG:4326",
                    "building_crs": "EPSG:5186",
                    "height_fields": ["height_m", "height"],
                    "floor_fields": ["floors", "stories"],
                    "building_base_mode": "min",
                }
            ]
        },
    )

    inspect_command, make_model_command = command_from_dataset.build_commands(registry_path, "sample")

    assert "--area-crs EPSG:4326" in inspect_command
    assert "--building-crs EPSG:5186" in inspect_command
    assert "--target-crs EPSG:32652" in make_model_command
    assert "--area-crs EPSG:4326" in make_model_command
    assert "--building-crs EPSG:5186" in make_model_command
    assert "--building-base-mode min" in make_model_command
    assert "--height-field height_m --height-field height" in make_model_command
    assert "--floor-field floors --floor-field stories" in make_model_command


def test_build_commands_tolerates_extended_registry_metadata(tmp_path):
    registry_path = tmp_path / "datasets.json"
    write_registry(
        registry_path,
        {
            "datasets": [
                {
                    "name": "sample",
                    "area": "data/area.geojson",
                    "dem": "data/dem.tif",
                    "buildings": "data/buildings.geojson",
                    "coverage_bounds": [126.9, 37.4, 127.2, 37.7],
                    "source_date": "2024-11-01",
                    "license": "ODC-BY-1.0",
                    "source_url": "https://example.com/datasets/sample",
                }
            ]
        },
    )

    inspect_command, make_model_command = command_from_dataset.build_commands(registry_path, "sample")

    assert "scripts\\inspect_data.py" in inspect_command
    assert "make_model.py" in make_model_command
    assert "--source-url" not in inspect_command
    assert "--source-url" not in make_model_command


def test_build_commands_rejects_unknown_dataset(tmp_path):
    registry_path = tmp_path / "datasets.json"
    write_registry(registry_path, {"datasets": []})

    with pytest.raises(ValueError, match="was not found"):
        command_from_dataset.build_commands(registry_path, "missing")


def test_cli_prints_two_commands(tmp_path):
    registry_path = tmp_path / "datasets.json"
    write_registry(
        registry_path,
        {
            "datasets": [
                {
                    "name": "sample",
                    "area": "area.geojson",
                    "dem": "dem.tif",
                    "buildings": "buildings.geojson",
                }
            ]
        },
    )

    result = subprocess.run(
        [
            sys.executable,
            str(Path("scripts") / "command_from_dataset.py"),
            "sample",
            "--registry",
            str(registry_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 2
    assert "scripts\\inspect_data.py" in lines[0]
    assert ".\\.venv\\Scripts\\python.exe make_model.py" in lines[1]
