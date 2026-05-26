from app.result_summary import summarize_build_result


def test_summarize_build_result_extracts_outputs_preview_and_mesh_quality(tmp_path):
    stl = tmp_path / "model.stl"
    stl.write_text("solid sample\nendsolid sample\n", encoding="utf-8")
    obj = tmp_path / "model.obj"
    obj.write_text("# obj", encoding="utf-8")
    preview = tmp_path / "model_preview.html"
    preview.write_text("<html></html>", encoding="utf-8")

    summary = {
        "outputs": {"stl": str(stl), "obj": str(obj)},
        "preview": str(preview),
        "mesh_quality": {"is_watertight": True, "non_manifold_edge_count": 0, "degenerate_face_count": 0},
    }

    result = summarize_build_result(summary)

    assert result.mesh_quality["is_watertight"] is True
    assert [item.label for item in result.output_files] == ["stl", "obj"]
    assert result.preview is not None and result.preview.exists is True
    assert result.stl_download is not None
    assert result.stl_download.path == stl


def test_summarize_build_result_handles_missing_or_invalid_values(tmp_path):
    stl = tmp_path / "missing_model.stl"
    summary = {
        "output": str(stl),
        "mesh_quality": None,
        "outputs": {"stl": str(stl), "obj": ""},
        "preview": " ",
    }

    result = summarize_build_result(summary)

    assert result.mesh_quality == {}
    assert len(result.output_files) == 1
    assert result.output_files[0].exists is False
    assert result.preview is None
    assert result.stl_download is None
