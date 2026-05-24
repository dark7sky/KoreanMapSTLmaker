"""Basic mesh repair helpers using trimesh with API-safe fallbacks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import trimesh

from src.mesh_quality import degenerate_face_count, mesh_summary


def load_mesh(path: Path) -> Any:
    """Load a mesh from STL/OBJ and coerce scene-like inputs to a single mesh."""
    loader = getattr(trimesh, "load_mesh", None) or getattr(trimesh, "load", None)
    if loader is None:
        raise RuntimeError("trimesh loader API is unavailable")

    loaded = loader(str(path), force="mesh")
    if isinstance(loaded, trimesh.Scene):
        if not loaded.geometry:
            raise ValueError(f"input mesh has no geometry: {path}")
        as_mesh = loaded.to_mesh()
        if as_mesh is None:
            raise ValueError(f"failed to convert scene to mesh: {path}")
        loaded = as_mesh
    return loaded


def repair_mesh(mesh: Any, *, try_fill_holes: bool = True) -> tuple[Any, dict[str, Any]]:
    """Apply safe baseline repairs, tolerating trimesh API differences."""
    before = mesh_summary(mesh)

    operations: dict[str, Any] = {
        "removed_duplicate_faces": False,
        "removed_degenerate_faces": False,
        "fixed_normals": False,
        "filled_holes": False,
    }

    removed_dupes = _remove_duplicate_faces(mesh)
    operations["removed_duplicate_faces"] = removed_dupes

    removed_degenerate = _remove_degenerate_faces(mesh)
    operations["removed_degenerate_faces"] = removed_degenerate

    operations["fixed_normals"] = _fix_normals(mesh)
    operations["filled_holes"] = _fill_holes(mesh) if try_fill_holes else False

    after = mesh_summary(mesh)
    summary = {
        "before": before,
        "after": after,
        "operations": operations,
    }
    return mesh, summary


def repair_mesh_file(
    input_path: Path,
    output_path: Path,
    *,
    try_fill_holes: bool = True,
) -> dict[str, Any]:
    """Load, repair, export, and return a JSON-serializable summary."""
    mesh = load_mesh(input_path)
    repaired_mesh, summary = repair_mesh(mesh, try_fill_holes=try_fill_holes)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    repaired_mesh.export(str(output_path))

    summary["input"] = str(input_path)
    summary["output"] = str(output_path)
    summary["format"] = output_path.suffix.lower().lstrip(".")
    return summary


def _remove_duplicate_faces(mesh: Any) -> bool:
    before = _face_count(mesh)
    if before == 0:
        return False

    remover = getattr(mesh, "remove_duplicate_faces", None)
    if callable(remover):
        try:
            remover()
            return _face_count(mesh) < before
        except Exception:
            pass

    unique_faces = getattr(mesh, "unique_faces", None)
    update_faces = getattr(mesh, "update_faces", None)
    if callable(unique_faces) and callable(update_faces):
        try:
            mask = unique_faces()
            update_faces(mask)
            return _face_count(mesh) < before
        except Exception:
            return False
    return False


def _remove_degenerate_faces(mesh: Any) -> bool:
    before = _face_count(mesh)
    if before == 0:
        return False

    remover = getattr(mesh, "remove_degenerate_faces", None)
    if callable(remover):
        try:
            remover()
            return _face_count(mesh) < before
        except Exception:
            pass

    nondegenerate = getattr(mesh, "nondegenerate_faces", None)
    update_faces = getattr(mesh, "update_faces", None)
    if callable(update_faces) and nondegenerate is not None:
        try:
            mask = nondegenerate() if callable(nondegenerate) else nondegenerate
            update_faces(mask)
            return _face_count(mesh) < before
        except Exception:
            pass

    before_degenerate = degenerate_face_count(mesh)
    if before_degenerate in (None, 0):
        return False
    return degenerate_face_count(mesh) == 0


def _fix_normals(mesh: Any) -> bool:
    fixer = getattr(mesh, "fix_normals", None)
    if callable(fixer):
        try:
            fixer()
            return True
        except Exception:
            return False

    repair_module = getattr(trimesh, "repair", None)
    if repair_module is None:
        return False
    fixer = getattr(repair_module, "fix_normals", None)
    if callable(fixer):
        try:
            fixer(mesh)
            return True
        except Exception:
            return False
    return False


def _fill_holes(mesh: Any) -> bool:
    filler = getattr(mesh, "fill_holes", None)
    if callable(filler):
        try:
            result = filler()
            return bool(result) or result is None
        except Exception:
            pass

    repair_module = getattr(trimesh, "repair", None)
    if repair_module is None:
        return False
    filler = getattr(repair_module, "fill_holes", None)
    if callable(filler):
        try:
            result = filler(mesh)
            return bool(result) or result is None
        except Exception:
            return False
    return False


def _face_count(mesh: Any) -> int:
    try:
        faces = getattr(mesh, "faces", ())
        return int(len(faces))
    except Exception:
        return 0
