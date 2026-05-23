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
