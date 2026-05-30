import numpy as np
import trimesh
from shapely.geometry import box

from src import pipeline, terrain
from src.mesh_decimation import maybe_decimate_mesh


def test_decimation_is_disabled_by_default():
    mesh = trimesh.creation.box(extents=(1.0, 1.0, 1.0))

    result_mesh, summary = maybe_decimate_mesh(mesh, None)

    assert result_mesh is mesh
    assert summary.requested is False
    assert summary.applied is False
    assert summary.skipped_reason == "not_requested"
    assert summary.target_faces is None
    assert summary.original_faces == len(mesh.faces)
    assert summary.result_faces == len(mesh.faces)


def test_decimation_requested_but_backend_unavailable(monkeypatch):
    mesh = trimesh.creation.box(extents=(1.0, 1.0, 1.0))

    def fail(*_args, **_kwargs):
        raise RuntimeError("no backend")

    monkeypatch.setattr(mesh, "simplify_quadric_decimation", fail)

    result_mesh, summary = maybe_decimate_mesh(mesh, 4)

    assert result_mesh is mesh
    assert summary.requested is True
    assert summary.applied is False
    assert summary.skipped_reason == "backend_unavailable_or_failed"
    assert summary.target_faces == 4
    assert summary.original_faces == len(mesh.faces)
    assert summary.result_faces == len(mesh.faces)


def test_decimation_requested_and_applied(monkeypatch):
    mesh = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    target_faces = 6

    simplified = mesh.copy()
    simplified.update_faces(np.arange(target_faces))
    simplified.remove_unreferenced_vertices()

    monkeypatch.setattr(mesh, "simplify_quadric_decimation", lambda face_count: simplified)

    result_mesh, summary = maybe_decimate_mesh(mesh, target_faces)

    assert result_mesh is simplified
    assert summary.requested is True
    assert summary.applied is True
    assert summary.skipped_reason is None
    assert summary.backend == "quadric_decimation"
    assert summary.original_faces == len(mesh.faces)
    assert summary.target_faces == target_faces
    assert summary.result_faces == len(simplified.faces)


def test_pipeline_summary_includes_decimation_status(monkeypatch, tmp_path):
    area = box(0.0, 0.0, 1.0, 1.0)
    fake_mesh = trimesh.creation.box(extents=(1.0, 1.0, 1.0))

    monkeypatch.setattr(pipeline, "load_area", lambda *_: (area, 0.1))
    monkeypatch.setattr(
        pipeline,
        "sample_terrain",
        lambda *_args, **_kwargs: terrain.TerrainGrid(
            xs=np.array([0.0, 1.0]),
            ys=np.array([0.0, 1.0]),
            elevations=np.array([[0.0, 1.0], [2.0, 3.0]]),
            valid=np.ones((2, 2), dtype=bool),
            min_elevation=10.0,
            origin_x=0.0,
            origin_y=0.0,
        ),
    )
    monkeypatch.setattr(pipeline, "make_terrain_mesh", lambda *_, **__: fake_mesh)
    monkeypatch.setattr(
        pipeline,
        "prepare_buildings",
        lambda *_args, **_kwargs: type(
            "B",
            (),
            {
                "buildings": [],
                "height_counts": {},
                "source_feature_count": 0,
                "intersect_feature_count": 0,
                "clipped_polygon_count": 0,
                "skipped_small_count": 0,
                "skipped_no_elevation_count": 0,
                "fields": [],
            },
        )(),
    )
    monkeypatch.setattr(pipeline, "make_building_meshes", lambda *_: [])
    monkeypatch.setattr(pipeline, "merge_meshes", lambda parts: fake_mesh)
    monkeypatch.setattr(
        pipeline,
        "get_dem_info",
        lambda *_: terrain.DemInfo("EPSG:3857", [0, 0, 1, 1], [0, 0, 1, 1], 2, 2, None, [1.0, 1.0]),
    )
    monkeypatch.setattr(pipeline, "mesh_summary", lambda *_: {})
    monkeypatch.setattr(pipeline, "export_summary", lambda *_: tmp_path / "summary.json")
    monkeypatch.setattr(pipeline, "export_stl", lambda *_: None)
    monkeypatch.setattr(
        pipeline,
        "maybe_decimate_mesh",
        lambda mesh, max_faces: (
            mesh,
            type(
                "D",
                (),
                {
                    "requested": True,
                    "applied": False,
                    "skipped_reason": "backend_unavailable_or_failed",
                    "backend": None,
                    "original_faces": len(mesh.faces),
                    "target_faces": max_faces,
                    "result_faces": len(mesh.faces),
                },
            )(),
        ),
    )

    area_path = tmp_path / "area.geojson"
    dem_path = tmp_path / "dem.tif"
    area_path.write_text("{}")
    dem_path.write_text("dem")
    options = pipeline.BuildOptions(
        area_path=area_path,
        buildings_path=None,
        dem_path=dem_path,
        out_path=tmp_path / "out.stl",
        target_crs="EPSG:3857",
        area_crs=None,
        building_crs=None,
        dem_crs=None,
        terrain_resolution=1.0,
        terrain_smoothing_iterations=0,
        terrain_smoothing_factor=0.5,
        interpolate_nodata=False,
        base_thickness=2.0,
        default_floor_height=3.0,
        default_building_height=6.0,
        min_building_area=0.0,
        simplify_tolerance=0.0,
        model_scale=1.0,
        base_plate_thickness=0.0,
        base_plate_margin=0.0,
        max_area_km2=10.0,
        building_diagnostics_limit=200,
        separate=False,
        preview=False,
        height_fields=(),
        floor_fields=(),
        building_base_mode="representative",
        export_formats=("stl",),
        decimate_max_faces=500,
    )

    summary = pipeline.build_model(options)

    assert summary["mesh_decimation"]["requested"] is True
    assert summary["mesh_decimation"]["applied"] is False
    assert summary["mesh_decimation"]["skipped_reason"] == "backend_unavailable_or_failed"
    assert summary["mesh_decimation"]["target_faces"] == 500
