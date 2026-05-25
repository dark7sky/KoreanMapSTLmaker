import json
from pathlib import Path

import pytest

from scripts import blender_import


def test_model_paths_from_inputs_accepts_model_files():
    paths = blender_import.model_paths_from_inputs([Path("model.stl"), Path("model.gltf"), Path("model.stl")])

    assert paths == [Path("model.stl"), Path("model.gltf")]


def test_model_paths_from_summary_collects_supported_outputs(tmp_path):
    summary_path = tmp_path / "model_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "outputs": {
                    "stl": "model.stl",
                    "obj": "model.obj",
                    "preview": "model_preview.html",
                    "glb": str(tmp_path / "model.glb"),
                }
            }
        ),
        encoding="utf-8",
    )

    paths = blender_import.model_paths_from_summary(summary_path)

    assert paths == [
        tmp_path / "model.stl",
        tmp_path / "model.obj",
        tmp_path / "model.glb",
    ]


def test_model_paths_from_summary_rejects_missing_outputs(tmp_path):
    summary_path = tmp_path / "model_summary.json"
    summary_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="outputs object"):
        blender_import.model_paths_from_summary(summary_path)
