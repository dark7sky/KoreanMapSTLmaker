import json
import subprocess
import sys
from pathlib import Path

from shapely.geometry import box

from scripts import select_dataset


def write_registry(path: Path, registry: object) -> None:
    path.write_text(json.dumps(registry), encoding="utf-8")


def test_select_datasets_ranks_overlapping_coverage(monkeypatch, tmp_path):
    registry_path = tmp_path / "datasets.json"
    write_registry(
        registry_path,
        {
            "datasets": [
                {
                    "name": "partial",
                    "area": "areas/partial.geojson",
                    "dem": "dem/partial.tif",
                    "buildings": "buildings/partial.geojson",
                    "coverage_bounds": [5.0, 0.0, 15.0, 10.0],
                },
                {
                    "name": "full",
                    "area": "areas/full.geojson",
                    "dem": "dem/full.tif",
                    "buildings": "buildings/full.geojson",
                    "coverage_bounds": [0.0, 0.0, 10.0, 10.0],
                    "source_date": "2024-11-01",
                    "license": "sample",
                },
                {
                    "name": "missing_bounds",
                    "area": "areas/missing.geojson",
                    "dem": "dem/missing.tif",
                    "buildings": "buildings/missing.geojson",
                },
            ]
        },
    )
    monkeypatch.setattr(select_dataset, "load_area", lambda *args, **kwargs: (box(0.0, 0.0, 10.0, 10.0), 0.01))

    result = select_dataset.select_datasets(
        registry_path=registry_path,
        area_path=tmp_path / "area.geojson",
        target_crs="EPSG:5179",
    )

    assert [match["name"] for match in result["matches"]] == ["full", "partial"]
    assert result["matches"][0]["area_overlap_ratio"] == 1.0
    assert result["matches"][0]["metadata"] == {"source_date": "2024-11-01", "license": "sample"}
    assert result["skipped"] == [{"name": "missing_bounds", "reason": "missing coverage_bounds"}]


def test_select_datasets_honors_limit(monkeypatch, tmp_path):
    registry_path = tmp_path / "datasets.json"
    write_registry(
        registry_path,
        {
            "datasets": [
                {"name": "a", "area": "a.geojson", "dem": "a.tif", "buildings": "a.gpkg", "coverage_bounds": [0, 0, 5, 5]},
                {"name": "b", "area": "b.geojson", "dem": "b.tif", "buildings": "b.gpkg", "coverage_bounds": [0, 0, 4, 4]},
            ]
        },
    )
    monkeypatch.setattr(select_dataset, "load_area", lambda *args, **kwargs: (box(0.0, 0.0, 10.0, 10.0), 0.01))

    result = select_dataset.select_datasets(
        registry_path=registry_path,
        area_path=tmp_path / "area.geojson",
        target_crs="EPSG:5179",
        limit=1,
    )

    assert result["match_count"] == 1
    assert result["matches"][0]["name"] == "a"


def test_print_commands_for_best_match(monkeypatch, tmp_path, capsys):
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
                    "coverage_bounds": [0, 0, 10, 10],
                    "height_fields": ["HEIGHT"],
                    "floor_fields": ["GRND_FLR"],
                }
            ]
        },
    )

    select_dataset.print_commands_for_match(
        registry_path,
        tmp_path / "drawn.geojson",
        {"name": "sample"},
    )

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 2
    assert "scripts\\inspect_data.py" in lines[0]
    assert "make_model.py" in lines[1]
    assert "--area" in lines[1]
    assert "drawn.geojson" in lines[1]
    assert "--height-field HEIGHT" in lines[1]
    assert "--floor-field GRND_FLR" in lines[1]


def test_cli_prints_json(monkeypatch, tmp_path):
    registry_path = tmp_path / "datasets.json"
    area_path = tmp_path / "area.geojson"
    area_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    write_registry(
        registry_path,
        {
            "datasets": [
                {
                    "name": "sample",
                    "area": "area.geojson",
                    "dem": "dem.tif",
                    "buildings": "buildings.geojson",
                    "coverage_bounds": [0, 0, 10, 10],
                }
            ]
        },
    )
    monkeypatch.setattr(select_dataset, "load_area", lambda *args, **kwargs: (box(0.0, 0.0, 10.0, 10.0), 0.01))

    result = subprocess.run(
        [
            sys.executable,
            str(Path("scripts") / "select_dataset.py"),
            "--registry",
            str(registry_path),
            "--area",
            str(area_path),
            "--target-crs",
            "EPSG:4326",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["matches"][0]["name"] == "sample"
