import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.dem_registry import find_dem_tiles, load_dem_registry


def test_load_dem_registry_defaults_when_missing(tmp_path):
    registry = load_dem_registry(tmp_path / "missing.json")
    assert registry == {"dem_datasets": []}


def test_load_dem_registry_rejects_invalid_dem_datasets(tmp_path):
    registry_path = tmp_path / "datasets.json"
    registry_path.write_text(json.dumps({"dem_datasets": {}}), encoding="utf-8")

    with pytest.raises(ValueError, match="dem_datasets must be a list"):
        load_dem_registry(registry_path)


def test_find_dem_tiles_matches_and_sorts(tmp_path):
    registry_path = tmp_path / "datasets.json"
    registry_path.write_text(
        json.dumps(
            {
                "dem_datasets": [
                    {"name": "partial", "dem": "data/dem/partial.tif", "crs": "EPSG:5179", "bounds": [5, 0, 15, 10]},
                    {"name": "full", "dem": "data/dem/full.tif", "crs": "EPSG:5179", "bounds": [0, 0, 10, 10]},
                    {"name": "bad", "dem": "data/dem/bad.tif", "crs": "EPSG:5179"},
                ]
            }
        ),
        encoding="utf-8",
    )

    result = find_dem_tiles(
        registry_path=registry_path,
        query_bounds=[0, 0, 10, 10],
        query_crs="EPSG:5179",
        limit=10,
    )

    assert result["match_count"] == 2
    assert [item["name"] for item in result["matches"]] == ["full", "partial"]
    assert result["matches"][0]["query_overlap_ratio"] == 1.0
    assert result["skipped"] == [{"name": "bad", "reason": "missing or invalid bounds"}]


def test_find_dem_tiles_cli_with_bounds(tmp_path):
    registry_path = tmp_path / "datasets.json"
    registry_path.write_text(
        json.dumps(
            {
                "dem_datasets": [
                    {"name": "match", "dem": "data/dem/match.tif", "crs": "EPSG:5179", "bounds": [0, 0, 10, 10]},
                    {"name": "miss", "dem": "data/dem/miss.tif", "crs": "EPSG:5179", "bounds": [20, 20, 30, 30]},
                ]
            }
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(Path("scripts") / "find_dem_tiles.py"),
            "--registry",
            str(registry_path),
            "--target-crs",
            "EPSG:5179",
            "--bounds",
            "0",
            "0",
            "8",
            "8",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["match_count"] == 1
    assert payload["matches"][0]["name"] == "match"
