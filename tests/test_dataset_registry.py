import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import list_datasets


def write_registry(path: Path, registry: object) -> None:
    path.write_text(json.dumps(registry), encoding="utf-8")


def test_summarize_registry_reports_missing_registry(tmp_path):
    registry_path = tmp_path / "datasets.json"

    summary = list_datasets.summarize_registry(registry_path)

    assert summary == {
        "registry": str(registry_path.resolve()),
        "exists": False,
        "dataset_count": 0,
        "datasets": [],
    }


def test_summarize_registry_validates_and_reports_paths(tmp_path):
    area_path = tmp_path / "data" / "areas" / "sample.geojson"
    dem_path = tmp_path / "data" / "dem" / "sample.tif"
    buildings_path = tmp_path / "data" / "buildings" / "sample.geojson"
    area_path.parent.mkdir(parents=True)
    dem_path.parent.mkdir(parents=True)
    buildings_path.parent.mkdir(parents=True)
    area_path.write_text("{}", encoding="utf-8")
    dem_path.write_text("dem", encoding="utf-8")
    buildings_path.write_text("{}", encoding="utf-8")
    registry_path = tmp_path / "datasets.json"
    write_registry(
        registry_path,
        {
            "datasets": [
                {
                    "name": "sample",
                    "area": "data/areas/sample.geojson",
                    "dem": "data/dem/sample.tif",
                    "buildings": "data/buildings/sample.geojson",
                }
            ]
        },
    )

    summary = list_datasets.summarize_registry(registry_path)

    assert summary["exists"] is True
    assert summary["dataset_count"] == 1
    assert summary["datasets"] == [
        {
            "name": "sample",
            "paths": {
                "area": str(area_path.resolve()),
                "dem": str(dem_path.resolve()),
                "buildings": str(buildings_path.resolve()),
            },
            "missing_paths": [],
        }
    ]


def test_summarize_registry_includes_optional_metadata_when_present(tmp_path):
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
                    "target_crs": "EPSG:32652",
                    "area_crs": "EPSG:4326",
                    "building_crs": "EPSG:5186",
                    "height_fields": ["height_m", "hgt"],
                    "floor_fields": ["floors", "stories"],
                    "building_base_mode": "min",
                    "coverage_bounds": [126.9, 37.4, 127.2, 37.7],
                    "source_date": "2024-11-01",
                    "license": "ODC-BY-1.0",
                    "source_url": "https://example.com/datasets/sample",
                    "notes": "prefers rooftop height over eave height",
                }
            ]
        },
    )

    summary = list_datasets.summarize_registry(registry_path)

    assert summary["datasets"][0]["metadata"] == {
        "target_crs": "EPSG:32652",
        "area_crs": "EPSG:4326",
        "building_crs": "EPSG:5186",
        "height_fields": ["height_m", "hgt"],
        "floor_fields": ["floors", "stories"],
        "building_base_mode": "min",
        "coverage_bounds": [126.9, 37.4, 127.2, 37.7],
        "source_date": "2024-11-01",
        "license": "ODC-BY-1.0",
        "source_url": "https://example.com/datasets/sample",
        "notes": "prefers rooftop height over eave height",
    }


def test_load_registry_accepts_utf8_bom(tmp_path):
    registry_path = tmp_path / "datasets.json"
    registry_path.write_text(
        json.dumps(
            {
                "datasets": [
                    {
                        "name": "sample",
                        "area": "area.geojson",
                        "dem": "dem.tif",
                        "buildings": "buildings.geojson",
                    }
                ]
            }
        ),
        encoding="utf-8-sig",
    )

    registry = list_datasets.load_registry(registry_path)

    assert registry["datasets"][0]["name"] == "sample"


@pytest.mark.parametrize(
    ("registry", "message"),
    [
        ([], "must contain a JSON object"),
        ({}, "must contain a 'datasets' list"),
        ({"datasets": ["sample"]}, "datasets[0] must be an object"),
        ({"datasets": [{"name": "", "area": "a", "dem": "d", "buildings": "b"}]}, "datasets[0].name"),
        ({"datasets": [{"name": "sample", "area": "a", "dem": "d"}]}, "datasets[0].buildings"),
        (
            {
                "datasets": [
                    {"name": "sample", "area": "a", "dem": "d", "buildings": "b"},
                    {"name": "sample", "area": "a2", "dem": "d2", "buildings": "b2"},
                ]
            },
            "duplicates",
        ),
        (
            {"datasets": [{"name": "sample", "area": "a", "dem": "d", "buildings": "b", "target_crs": 32652}]},
            "datasets[0].target_crs",
        ),
        (
            {"datasets": [{"name": "sample", "area": "a", "dem": "d", "buildings": "b", "area_crs": ""}]},
            "datasets[0].area_crs",
        ),
        (
            {"datasets": [{"name": "sample", "area": "a", "dem": "d", "buildings": "b", "building_crs": 5186}]},
            "datasets[0].building_crs",
        ),
        (
            {
                "datasets": [
                    {"name": "sample", "area": "a", "dem": "d", "buildings": "b", "height_fields": "height"}
                ]
            },
            "datasets[0].height_fields",
        ),
        (
            {
                "datasets": [
                    {"name": "sample", "area": "a", "dem": "d", "buildings": "b", "floor_fields": ["", "floors"]}
                ]
            },
            "datasets[0].floor_fields",
        ),
        (
            {
                "datasets": [
                    {"name": "sample", "area": "a", "dem": "d", "buildings": "b", "building_base_mode": ""}
                ]
            },
            "datasets[0].building_base_mode",
        ),
        (
            {"datasets": [{"name": "sample", "area": "a", "dem": "d", "buildings": "b", "notes": 123}]},
            "datasets[0].notes",
        ),
        (
            {
                "datasets": [
                    {"name": "sample", "area": "a", "dem": "d", "buildings": "b", "building_base_mode": "dem_min"}
                ]
            },
            "datasets[0].building_base_mode",
        ),
        (
            {
                "datasets": [
                    {"name": "sample", "area": "a", "dem": "d", "buildings": "b", "coverage_bounds": [1, 2, 3]}
                ]
            },
            "datasets[0].coverage_bounds",
        ),
        (
            {
                "datasets": [
                    {"name": "sample", "area": "a", "dem": "d", "buildings": "b", "coverage_bounds": [1, "2", 3, 4]}
                ]
            },
            "datasets[0].coverage_bounds",
        ),
        (
            {
                "datasets": [
                    {"name": "sample", "area": "a", "dem": "d", "buildings": "b", "coverage_bounds": [1, True, 3, 4]}
                ]
            },
            "datasets[0].coverage_bounds",
        ),
        (
            {"datasets": [{"name": "sample", "area": "a", "dem": "d", "buildings": "b", "source_date": ""}]},
            "datasets[0].source_date",
        ),
        (
            {"datasets": [{"name": "sample", "area": "a", "dem": "d", "buildings": "b", "license": 123}]},
            "datasets[0].license",
        ),
        (
            {"datasets": [{"name": "sample", "area": "a", "dem": "d", "buildings": "b", "source_url": " "}]},
            "datasets[0].source_url",
        ),
    ],
)
def test_load_registry_rejects_invalid_structure(tmp_path, registry, message):
    registry_path = tmp_path / "datasets.json"
    write_registry(registry_path, registry)

    with pytest.raises(ValueError, match=re.escape(message)):
        list_datasets.load_registry(registry_path)


def test_cli_prints_json_summary(tmp_path):
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
            str(Path("scripts") / "list_datasets.py"),
            "--registry",
            str(registry_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(result.stdout)

    assert summary["dataset_count"] == 1
    assert summary["datasets"][0]["name"] == "sample"
    assert summary["datasets"][0]["missing_paths"] == ["area", "dem", "buildings"]
