import json
from pathlib import Path

import trimesh

from scripts import repair_mesh
from src.mesh_repair import repair_mesh_file


def test_repair_mesh_file_removes_basic_bad_faces_and_exports(tmp_path):
    input_path = tmp_path / "broken.obj"
    output_path = tmp_path / "repaired.stl"

    # One duplicated face and one degenerate face.
    mesh = trimesh.Trimesh(
        vertices=[
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        faces=[
            [0, 1, 2],
            [0, 1, 2],
            [0, 0, 3],
        ],
        process=False,
    )
    mesh.export(input_path)

    summary = repair_mesh_file(input_path, output_path)

    assert output_path.exists()
    assert summary["input"] == str(input_path)
    assert summary["output"] == str(output_path)
    assert summary["after"]["face_count"] <= summary["before"]["face_count"]
    assert summary["after"]["degenerate_face_count"] in (0, None)


def test_repair_mesh_script_prints_json_summary(tmp_path, capsys):
    input_path = tmp_path / "source.stl"
    output_path = tmp_path / "result.obj"
    summary_path = tmp_path / "repair_summary.json"
    trimesh.creation.box().export(input_path)

    repair_mesh.main(
        [
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--summary-out",
            str(summary_path),
            "--skip-fill-holes",
        ]
    )

    captured = capsys.readouterr()
    summary = json.loads(captured.out)

    assert output_path.exists()
    assert summary_path.exists()
    assert summary["format"] == "obj"
    assert Path(summary["output"]) == output_path
    assert json.loads(summary_path.read_text(encoding="utf-8"))["output"] == str(output_path)
    assert "operations" in summary
    assert "before" in summary
    assert "after" in summary
