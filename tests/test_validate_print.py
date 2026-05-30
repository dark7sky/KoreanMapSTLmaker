import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import validate_print


def _summary(mesh_quality: dict) -> dict:
    return {"mesh_quality": mesh_quality}


def test_validate_summary_passes_with_defaults():
    report = validate_print.validate_summary(
        _summary(
            {
                "is_watertight": False,
                "non_manifold_edge_count": 0,
                "degenerate_face_count": 0,
                "bounds": [[0, 0, 0], [10, 20, 5]],
                "volume": 100.0,
            }
        ),
        require_watertight=False,
        max_non_manifold_edges=0,
        max_degenerate_faces=0,
        min_dimension=None,
        max_dimension=None,
        min_volume=None,
    )

    assert report["passed"] is True
    assert report["profile"] == "default"
    assert [check["name"] for check in report["checks"]] == [
        "max_non_manifold_edges",
        "max_degenerate_faces",
    ]


def test_validate_summary_fails_thresholds():
    report = validate_print.validate_summary(
        _summary(
            {
                "is_watertight": False,
                "non_manifold_edge_count": 3,
                "degenerate_face_count": 2,
                "bounds": [[0, 0, 0], [20, 30, 2]],
                "volume": 0.5,
            }
        ),
        require_watertight=True,
        max_non_manifold_edges=1,
        max_degenerate_faces=0,
        min_dimension=3.0,
        max_dimension=25.0,
        min_volume=1.0,
    )

    assert report["passed"] is False
    failures = [check["name"] for check in report["checks"] if not check["passed"]]
    assert failures == [
        "watertight",
        "max_non_manifold_edges",
        "max_degenerate_faces",
        "min_dimension",
        "max_dimension",
        "min_volume",
    ]


def test_validate_summary_requires_mesh_quality():
    with pytest.raises(ValueError, match="mesh_quality object"):
        validate_print.validate_summary(
            {},
            require_watertight=False,
            max_non_manifold_edges=0,
            max_degenerate_faces=0,
            min_dimension=None,
            max_dimension=None,
            min_volume=None,
        )


def test_cli_json_output_and_exit_code(tmp_path):
    summary_path = tmp_path / "model_summary.json"
    summary_path.write_text(
        json.dumps(
            _summary(
                {
                    "is_watertight": True,
                    "non_manifold_edge_count": 0,
                    "degenerate_face_count": 0,
                    "bounds": [[0, 0, 0], [10, 10, 10]],
                    "volume": 1000.0,
                }
            )
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(Path("scripts") / "validate_print.py"), str(summary_path), "--require-watertight"],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["passed"] is True


def test_cli_text_output_fails_with_nonzero_exit(tmp_path):
    summary_path = tmp_path / "model_summary.json"
    summary_path.write_text(
        json.dumps(
            _summary(
                {
                    "is_watertight": False,
                    "non_manifold_edge_count": 4,
                    "degenerate_face_count": 0,
                    "bounds": [[0, 0, 0], [1, 1, 1]],
                    "volume": 0.1,
                }
            )
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(Path("scripts") / "validate_print.py"),
            str(summary_path),
            "--require-watertight",
            "--max-non-manifold-edges",
            "0",
            "--min-volume",
            "1.0",
            "--format",
            "text",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "PASS=False" in result.stdout
    assert "FAIL Mesh is watertight" in result.stdout
    assert "Repair open boundaries before slicing" in result.stdout


def test_cli_strict_uses_fdm_profile(tmp_path):
    summary_path = tmp_path / "model_summary.json"
    summary_path.write_text(
        json.dumps(
            _summary(
                {
                    "is_watertight": True,
                    "non_manifold_edge_count": 0,
                    "degenerate_face_count": 0,
                    "bounds": [[0, 0, 0], [4.0, 4.0, 2.0]],
                    "volume": 0.5,
                }
            )
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(Path("scripts") / "validate_print.py"), str(summary_path), "--strict", "--format", "text"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "PROFILE=fdm" in result.stdout
    assert "FAIL Smallest bbox dimension above minimum" in result.stdout
    assert "FAIL Volume above minimum" in result.stdout


def test_validate_summary_uses_wall_and_base_hints():
    report = validate_print.validate_summary(
        {
            "mesh_quality": {
                "is_watertight": True,
                "non_manifold_edge_count": 0,
                "degenerate_face_count": 0,
                "bounds": [[0, 0, 0], [10, 10, 5]],
                "volume": 20.0,
            },
            "base_thickness_hint": 0.6,
            "wall_thickness_hint": 0.3,
        },
        profile_name="resin",
        require_watertight=True,
        max_non_manifold_edges=0,
        max_degenerate_faces=0,
        min_dimension=3.0,
        max_dimension=140.0,
        min_volume=0.2,
        min_base_thickness=0.8,
        min_wall_thickness=0.4,
    )

    assert report["passed"] is False
    by_name = {check["name"]: check for check in report["checks"]}
    assert by_name["min_base_thickness"]["passed"] is False
    assert by_name["min_wall_thickness"]["passed"] is False


def test_slicer_check_template_includes_model_when_present(tmp_path):
    summary_path = tmp_path / "my_area_summary.json"
    model_path = tmp_path / "my_area.stl"
    summary_path.write_text("{}", encoding="utf-8")
    model_path.write_text("solid test", encoding="utf-8")

    context = validate_print._build_slicer_context(summary_path, None)
    template = validate_print.slicer_check_template(context)

    assert str(model_path.resolve()) in template


def test_run_slicer_check_reports_error_without_model_placeholder_value(tmp_path):
    summary_path = tmp_path / "my_area_summary.json"
    summary_path.write_text("{}", encoding="utf-8")
    context = validate_print._build_slicer_context(summary_path, None)

    report = validate_print.run_slicer_check(
        "fake-slicer --check {model}",
        context=context,
        timeout_seconds=1.0,
    )

    assert report["passed"] is False
    assert "model path is required for {model}" in report["error"]


def test_run_slicer_check_uses_subprocess_result(monkeypatch, tmp_path):
    summary_path = tmp_path / "my_area_summary.json"
    model_path = tmp_path / "my_area.stl"
    summary_path.write_text("{}", encoding="utf-8")
    model_path.write_text("solid test", encoding="utf-8")
    context = validate_print._build_slicer_context(summary_path, model_path)

    def fake_run(args, capture_output, text, timeout, check):
        assert args[0] == "fake-slicer"
        assert capture_output is True
        assert text is True
        assert timeout == 2.5
        assert check is False
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(validate_print.subprocess, "run", fake_run)
    report = validate_print.run_slicer_check(
        "fake-slicer --check {model}",
        context=context,
        timeout_seconds=2.5,
    )

    assert report["passed"] is True
    assert report["returncode"] == 0
    assert report["stdout"] == "ok"


def test_cli_json_includes_slicer_template(tmp_path):
    summary_path = tmp_path / "model_summary.json"
    summary_path.write_text(
        json.dumps(
            _summary(
                {
                    "is_watertight": True,
                    "non_manifold_edge_count": 0,
                    "degenerate_face_count": 0,
                    "bounds": [[0, 0, 0], [10, 10, 10]],
                    "volume": 1000.0,
                }
            )
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(Path("scripts") / "validate_print.py"),
            str(summary_path),
            "--include-slicer-template",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert "slicer_check_template" in payload
