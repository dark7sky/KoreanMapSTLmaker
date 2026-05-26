import json
import subprocess
import sys
from pathlib import Path

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
    assert "FAIL watertight" in result.stdout
