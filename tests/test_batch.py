import json
from pathlib import Path

import pytest

from scripts import run_batch


def test_load_jobs_requires_jobs_array(tmp_path):
    batch_path = tmp_path / "batch.json"
    batch_path.write_text(json.dumps({"jobs": {}}), encoding="utf-8")

    with pytest.raises(ValueError, match='top-level key "jobs"'):
        run_batch.load_jobs(batch_path)


def test_load_jobs_accepts_utf8_bom(tmp_path):
    batch_path = tmp_path / "batch.json"
    batch_path.write_text(json.dumps({"jobs": []}), encoding="utf-8-sig")

    assert run_batch.load_jobs(batch_path) == []


def test_build_options_from_job_maps_cli_like_fields():
    options = run_batch.build_options_from_job(
        {
            "area": "data/areas/a.geojson",
            "dem": "data/dem/a.tif",
            "buildings": "data/buildings/a.geojson",
            "out": "output/a.stl",
            "export_format": ["stl", "obj", "stl"],
            "height_field": ["HEIGHT", "height_m"],
            "floor_field": ["GRND_FLR"],
            "z_scale": 1.5,
            "separate": True,
        },
        0,
    )

    assert options.area_path == Path("data/areas/a.geojson")
    assert options.dem_path == Path("data/dem/a.tif")
    assert options.buildings_path == Path("data/buildings/a.geojson")
    assert options.out_path == Path("output/a.stl")
    assert options.export_formats == ("stl", "obj")
    assert options.height_fields == ("HEIGHT", "height_m")
    assert options.floor_fields == ("GRND_FLR",)
    assert options.z_scale == 1.5
    assert options.separate is True


def test_build_options_rejects_string_booleans():
    with pytest.raises(ValueError, match="must be a boolean"):
        run_batch.build_options_from_job(
            {"area": "a.geojson", "dem": "a.tif", "out": "a.stl", "preview": "false"},
            0,
        )


def test_build_options_rejects_invalid_numeric_and_list_fields():
    with pytest.raises(ValueError, match="must be numeric"):
        run_batch.build_options_from_job(
            {"area": "a.geojson", "dem": "a.tif", "out": "a.stl", "terrain_resolution": True},
            0,
        )

    with pytest.raises(ValueError, match="list of non-empty strings"):
        run_batch.build_options_from_job(
            {"area": "a.geojson", "dem": "a.tif", "out": "a.stl", "height_field": ["HEIGHT", ""]},
            0,
        )

    with pytest.raises(ValueError, match="non-empty strings"):
        run_batch.build_options_from_job(
            {"area": "a.geojson", "dem": "a.tif", "out": "a.stl", "export_format": ["stl", 123]},
            0,
        )


def test_run_jobs_records_failures_and_keeps_going(monkeypatch):
    calls = []

    def fake_build_model(options):
        calls.append(options.out_path.name)
        if options.out_path.name == "two.stl":
            raise RuntimeError("dem overlap failed")
        return {"output": str(options.out_path), "summary": str(options.out_path.with_suffix(".json"))}

    monkeypatch.setattr(run_batch, "build_model", fake_build_model)

    summary = run_batch.run_jobs(
        [
            {"name": "one", "area": "a.geojson", "dem": "a.tif", "out": "one.stl"},
            {"name": "two", "area": "b.geojson", "dem": "b.tif", "out": "two.stl"},
            {"name": "three", "area": "c.geojson", "dem": "c.tif", "out": "three.stl"},
        ]
    )

    assert calls == ["one.stl", "two.stl", "three.stl"]
    assert summary["job_count"] == 3
    assert summary["success_count"] == 2
    assert summary["failure_count"] == 1
    assert [job["status"] for job in summary["jobs"]] == ["ok", "failed", "ok"]
    assert summary["jobs"][1]["error"] == "dem overlap failed"


def test_run_jobs_retries_failed_jobs(monkeypatch):
    attempts = {"flaky.stl": 0}

    def fake_build_model(options):
        attempts[options.out_path.name] += 1
        if attempts[options.out_path.name] == 1:
            raise RuntimeError("temporary failure")
        return {"output": str(options.out_path), "summary": str(options.out_path.with_suffix(".json"))}

    monkeypatch.setattr(run_batch, "build_model", fake_build_model)

    summary = run_batch.run_jobs(
        [{"name": "flaky", "area": "a.geojson", "dem": "a.tif", "out": "flaky.stl"}],
        retries=1,
    )

    assert summary["success_count"] == 1
    assert summary["failure_count"] == 0
    assert summary["jobs"][0]["status"] == "ok"
    assert summary["jobs"][0]["attempts"] == 2


def test_run_jobs_records_all_retry_errors(monkeypatch):
    def fake_build_model(options):
        raise RuntimeError(f"failed {options.out_path.name}")

    monkeypatch.setattr(run_batch, "build_model", fake_build_model)

    summary = run_batch.run_jobs(
        [{"name": "bad", "area": "a.geojson", "dem": "a.tif", "out": "bad.stl"}],
        retries=2,
    )

    assert summary["failure_count"] == 1
    assert summary["jobs"][0]["attempts"] == 3
    assert summary["jobs"][0]["errors"] == ["failed bad.stl", "failed bad.stl", "failed bad.stl"]


def test_main_writes_summary_and_returns_non_zero_on_failures(tmp_path, monkeypatch):
    batch_path = tmp_path / "batch.json"
    summary_path = tmp_path / "batch_summary.json"
    batch_path.write_text(
        json.dumps(
            {
                "jobs": [
                    {"name": "ok", "area": "a.geojson", "dem": "a.tif", "out": "ok.stl"},
                    {"name": "bad", "area": "b.geojson", "dem": "b.tif", "out": "bad.stl"},
                ]
            }
        ),
        encoding="utf-8",
    )

    def fake_build_model(options):
        if options.out_path.name == "bad.stl":
            raise ValueError("invalid geometry")
        return {"output": str(options.out_path), "summary": str(options.out_path.with_suffix(".json"))}

    monkeypatch.setattr(run_batch, "build_model", fake_build_model)

    exit_code = run_batch.main(["--batch", str(batch_path), "--summary-out", str(summary_path)])

    assert exit_code == 1
    saved = json.loads(summary_path.read_text(encoding="utf-8"))
    assert saved["failure_count"] == 1
    assert saved["jobs"][1]["name"] == "bad"
    assert saved["jobs"][1]["status"] == "failed"


def test_main_rejects_batch_summary_that_collides_with_model_summary(tmp_path):
    batch_path = tmp_path / "batch.json"
    out_path = tmp_path / "model.stl"
    summary_path = tmp_path / "model_summary.json"
    batch_path.write_text(
        json.dumps({"jobs": [{"area": "a.geojson", "dem": "a.tif", "out": str(out_path)}]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="collides with model summary"):
        run_batch.main(["--batch", str(batch_path), "--summary-out", str(summary_path)])
