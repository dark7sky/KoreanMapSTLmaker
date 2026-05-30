import json
import subprocess
import sys
from pathlib import Path

import rasterio
import geopandas as gpd
from shapely.geometry import box


def test_import_dem_cli_copies_and_writes_sidecar(tmp_path):
    source = Path("data/sample/dem.tif").resolve()
    output = tmp_path / "copied_dem.tif"

    subprocess.run(
        [
            sys.executable,
            str(Path("scripts") / "import_dem.py"),
            "--source",
            str(source),
            "--out",
            str(output),
            "--source-date",
            "2026-01-15",
            "--license",
            "Public",
            "--source-url",
            "https://example.test/dem",
        ],
        check=True,
    )

    assert output.exists()
    sidecar = output.with_suffix(".tif.json")
    assert sidecar.exists()

    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["source_path"] == str(source)
    assert payload["output_path"] == str(output.resolve())
    assert payload["crs"] == "EPSG:5179"
    assert len(payload["bounds"]) == 4
    assert payload["width"] > 0
    assert payload["height"] > 0
    assert payload["dtypes"]
    assert payload["source_date"] == "2026-01-15"
    assert payload["license"] == "Public"
    assert payload["source_url"] == "https://example.test/dem"


def test_import_dem_cli_fails_on_crs_mismatch_without_reproject(tmp_path):
    source = Path("data/sample/dem.tif").resolve()
    output = tmp_path / "mismatch_dem.tif"

    completed = subprocess.run(
        [
            sys.executable,
            str(Path("scripts") / "import_dem.py"),
            "--source",
            str(source),
            "--out",
            str(output),
            "--target-crs",
            "EPSG:4326",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "Source CRS does not match --target-crs" in completed.stderr


def test_import_dem_cli_updates_registry_dem_datasets(tmp_path):
    source = Path("data/sample/dem.tif").resolve()
    output = tmp_path / "registered_dem.tif"
    registry = tmp_path / "datasets.json"

    subprocess.run(
        [
            sys.executable,
            str(Path("scripts") / "import_dem.py"),
            "--source",
            str(source),
            "--out",
            str(output),
            "--registry",
            str(registry),
            "--name",
            "sample-dem",
        ],
        check=True,
    )

    saved = json.loads(registry.read_text(encoding="utf-8"))
    assert "dem_datasets" in saved
    assert isinstance(saved["dem_datasets"], list)
    assert len(saved["dem_datasets"]) == 1
    entry = saved["dem_datasets"][0]
    assert entry["name"] == "sample-dem"
    assert entry["dem"] == "registered_dem.tif"
    assert entry["crs"] == "EPSG:5179"
    assert len(entry["bounds"]) == 4
    assert entry["shape"][0] > 0 and entry["shape"][1] > 0

    with rasterio.open(output) as dataset:
        assert entry["shape"] == [dataset.height, dataset.width]


def test_import_dem_cli_validate_area_fails_when_no_overlap(tmp_path):
    source = Path("data/sample/dem.tif").resolve()
    output = tmp_path / "validated_dem.tif"
    area_path = tmp_path / "far_area.geojson"
    gpd.GeoDataFrame({"id": [1]}, geometry=[box(2000.0, 2000.0, 2100.0, 2100.0)], crs="EPSG:5179").to_file(
        area_path,
        driver="GeoJSON",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(Path("scripts") / "import_dem.py"),
            "--source",
            str(source),
            "--out",
            str(output),
            "--validate-area",
            str(area_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "Imported DEM does not overlap the validation area" in completed.stderr
