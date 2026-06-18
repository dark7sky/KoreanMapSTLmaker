from pathlib import Path

from scripts import list_datasets
from scripts.auto_build import auto_build


def test_sample_registry_has_existing_paths():
    summary = list_datasets.summarize_registry(Path("datasets.sample.json"))

    assert summary["exists"] is True
    assert summary["dataset_count"] == 1
    dataset = summary["datasets"][0]
    assert dataset["name"] == "sample_block"
    assert dataset["missing_paths"] == []


def test_sample_registry_supports_auto_build_dry_run():
    report = auto_build(
        area_path=Path("data/sample/area.geojson"),
        registry_path=Path("datasets.sample.json"),
        dry_run=True,
    )

    assert report["status"] == "validated"
    assert report["dataset"]["name"] == "sample_block"
    assert report["validation"]["ok"] is True
    assert "make_model.py" in report["command"]
