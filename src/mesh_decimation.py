from dataclasses import dataclass

import trimesh


@dataclass(frozen=True)
class DecimationResult:
    requested: bool
    applied: bool
    skipped_reason: str | None
    backend: str | None
    original_faces: int
    target_faces: int | None
    result_faces: int


def maybe_decimate_mesh(mesh: trimesh.Trimesh, max_faces: int | None) -> tuple[trimesh.Trimesh, DecimationResult]:
    original_faces = int(len(mesh.faces))
    if max_faces is None:
        return mesh, DecimationResult(
            requested=False,
            applied=False,
            skipped_reason="not_requested",
            backend=None,
            original_faces=original_faces,
            target_faces=None,
            result_faces=original_faces,
        )

    if max_faces <= 0:
        return mesh, DecimationResult(
            requested=True,
            applied=False,
            skipped_reason="invalid_target_faces",
            backend=None,
            original_faces=original_faces,
            target_faces=max_faces,
            result_faces=original_faces,
        )

    if mesh.is_empty:
        return mesh, DecimationResult(
            requested=True,
            applied=False,
            skipped_reason="empty_mesh",
            backend=None,
            original_faces=original_faces,
            target_faces=max_faces,
            result_faces=original_faces,
        )

    if original_faces <= max_faces:
        return mesh, DecimationResult(
            requested=True,
            applied=False,
            skipped_reason="within_target",
            backend=None,
            original_faces=original_faces,
            target_faces=max_faces,
            result_faces=original_faces,
        )

    try:
        simplified = mesh.simplify_quadric_decimation(face_count=max_faces)
    except Exception:
        return mesh, DecimationResult(
            requested=True,
            applied=False,
            skipped_reason="backend_unavailable_or_failed",
            backend=None,
            original_faces=original_faces,
            target_faces=max_faces,
            result_faces=original_faces,
        )

    if simplified is None or simplified.is_empty:
        return mesh, DecimationResult(
            requested=True,
            applied=False,
            skipped_reason="empty_result",
            backend="quadric_decimation",
            original_faces=original_faces,
            target_faces=max_faces,
            result_faces=original_faces,
        )

    result_faces = int(len(simplified.faces))
    if result_faces <= 0 or result_faces > original_faces:
        return mesh, DecimationResult(
            requested=True,
            applied=False,
            skipped_reason="invalid_result",
            backend="quadric_decimation",
            original_faces=original_faces,
            target_faces=max_faces,
            result_faces=original_faces,
        )

    return simplified, DecimationResult(
        requested=True,
        applied=True,
        skipped_reason=None,
        backend="quadric_decimation",
        original_faces=original_faces,
        target_faces=max_faces,
        result_faces=result_faces,
    )
