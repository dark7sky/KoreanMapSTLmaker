import json
from pathlib import Path

from scripts import cache_model


def test_cache_key_is_stable_and_ignores_out_path(tmp_path):
    area = tmp_path / "area.geojson"
    dem = tmp_path / "dem.tif"
    area.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")
    dem.write_bytes(b"dem-data")

    job_one = {"area": str(area), "dem": str(dem), "out": str(tmp_path / "one.stl"), "terrain_resolution": 10.0}
    job_two = {"area": str(area), "dem": str(dem), "out": str(tmp_path / "two.stl"), "terrain_resolution": 10.0}

    key_one = cache_model.compute_cache_key(job_one, workspace=tmp_path)
    key_two = cache_model.compute_cache_key(job_two, workspace=tmp_path)

    assert key_one == key_two


def test_cache_key_changes_when_input_changes(tmp_path):
    area = tmp_path / "area.geojson"
    dem = tmp_path / "dem.tif"
    area.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")
    dem.write_bytes(b"dem-data-v1")
    job = {"area": str(area), "dem": str(dem), "out": str(tmp_path / "model.stl")}

    key_before = cache_model.compute_cache_key(job, workspace=tmp_path)
    dem.write_bytes(b"dem-data-v2")
    key_after = cache_model.compute_cache_key(job, workspace=tmp_path)

    assert key_before != key_after


def test_run_cached_job_reports_miss_then_hit(tmp_path, monkeypatch):
    area = tmp_path / "area.geojson"
    dem = tmp_path / "dem.tif"
    area.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")
    dem.write_bytes(b"dem-data")

    out_path = tmp_path / "output" / "model.stl"
    cache_dir = tmp_path / ".cache"
    job = {"area": str(area), "dem": str(dem), "out": str(out_path), "export_format": ["stl"]}
    calls = {"count": 0}

    def fake_build_model(options):
        calls["count"] += 1
        options.out_path.parent.mkdir(parents=True, exist_ok=True)
        options.out_path.write_text("mesh", encoding="utf-8")
        summary_path = options.out_path.with_name(f"{options.out_path.stem}_summary.json")
        summary = {
            "output": str(options.out_path),
            "outputs": {"stl": str(options.out_path)},
            "export_formats": ["stl"],
            "summary": str(summary_path),
            "options": {"out": str(options.out_path)},
        }
        summary_path.write_text(json.dumps(summary), encoding="utf-8")
        return summary

    monkeypatch.setattr(cache_model, "build_model", fake_build_model)

    first = cache_model.run_cached_job(job, cache_dir=cache_dir, workspace=tmp_path)
    assert first["status"] == "miss"
    assert calls["count"] == 1
    assert out_path.exists()

    out_path.unlink()
    out_path.with_name("model_summary.json").unlink()

    second = cache_model.run_cached_job(job, cache_dir=cache_dir, workspace=tmp_path)
    assert second["status"] == "hit"
    assert calls["count"] == 1
    assert out_path.read_text(encoding="utf-8") == "mesh"
    restored = json.loads(out_path.with_name("model_summary.json").read_text(encoding="utf-8"))
    assert restored["output"] == str(out_path)


def test_cache_hit_regenerates_preview_with_rewritten_summary(tmp_path, monkeypatch):
    area = tmp_path / "area.geojson"
    dem = tmp_path / "dem.tif"
    area.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")
    dem.write_bytes(b"dem-data")

    out_path = tmp_path / "first" / "model.stl"
    second_out_path = tmp_path / "second" / "model.stl"
    cache_dir = tmp_path / ".cache"
    job = {"area": str(area), "dem": str(dem), "out": str(out_path), "export_format": ["stl"], "preview": True}
    preview_calls = []

    def fake_build_model(options):
        options.out_path.parent.mkdir(parents=True, exist_ok=True)
        options.out_path.write_text("mesh", encoding="utf-8")
        summary_path = options.out_path.with_name(f"{options.out_path.stem}_summary.json")
        preview_path = options.out_path.with_name(f"{options.out_path.stem}_preview.html")
        preview_path.write_text("old preview", encoding="utf-8")
        summary = {
            "output": str(options.out_path),
            "outputs": {"stl": str(options.out_path)},
            "export_formats": ["stl"],
            "summary": str(summary_path),
            "preview": str(preview_path),
            "options": {"out": str(options.out_path)},
        }
        summary_path.write_text(json.dumps(summary), encoding="utf-8")
        return summary

    monkeypatch.setattr(cache_model, "build_model", fake_build_model)
    monkeypatch.setattr(cache_model, "export_preview_html", lambda stl, summary: preview_calls.append((stl, summary)))

    first = cache_model.run_cached_job(job, cache_dir=cache_dir, workspace=tmp_path)
    assert first["status"] == "miss"

    second_job = dict(job)
    second_job["out"] = str(second_out_path)
    second = cache_model.run_cached_job(second_job, cache_dir=cache_dir, workspace=tmp_path)

    assert second["status"] == "hit"
    assert preview_calls == [(second_out_path, second["summary"])]
    assert second["summary"]["preview"] == str(second_out_path.with_name("model_preview.html"))
