"""Lightweight mesh quality and summary helpers."""

from __future__ import annotations

from typing import Any

import numpy as np


def vertex_count(mesh: Any) -> int:
    """Return the number of vertices in a trimesh-like mesh."""
    return int(len(getattr(mesh, "vertices", ())))


def face_count(mesh: Any) -> int:
    """Return the number of faces in a trimesh-like mesh."""
    return int(len(getattr(mesh, "faces", ())))


def bounds(mesh: Any) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    """Return mesh bounds as plain Python floats, or None when unavailable."""
    raw_bounds = _safe_getattr(mesh, "bounds")
    if raw_bounds is None:
        return None

    array = np.asarray(raw_bounds, dtype=float)
    if array.shape != (2, 3) or not np.isfinite(array).all():
        return None

    return tuple(tuple(float(value) for value in row) for row in array)  # type: ignore[return-value]


def is_empty(mesh: Any) -> bool:
    """Return whether a mesh has no usable geometry."""
    mesh_is_empty = _safe_getattr(mesh, "is_empty")
    if mesh_is_empty is not None:
        return bool(mesh_is_empty)
    return vertex_count(mesh) == 0 or face_count(mesh) == 0


def is_watertight(mesh: Any) -> bool:
    """Return whether the mesh is watertight when trimesh exposes that value."""
    return bool(_safe_getattr(mesh, "is_watertight", False))


def euler_number(mesh: Any) -> int | None:
    """Return the Euler number when available."""
    value = _safe_getattr(mesh, "euler_number")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def volume(mesh: Any) -> float | None:
    """Return mesh volume when available."""
    if vertex_count(mesh) == 0 and face_count(mesh) == 0:
        return 0.0

    value = _safe_getattr(mesh, "volume")
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(result):
        return None
    return result


def non_manifold_edge_count(mesh: Any) -> int | None:
    """Return the number of non-manifold edges (shared by more than 2 faces)."""
    edges_unique_inverse = _safe_getattr(mesh, "edges_unique_inverse")
    if edges_unique_inverse is None:
        return None
    try:
        edge_counts = np.bincount(edges_unique_inverse)
        return int(np.sum(edge_counts > 2))
    except Exception:
        return None


def degenerate_face_count(mesh: Any) -> int | None:
    """Return the number of degenerate faces."""
    nondegenerate_mask = _safe_getattr(mesh, "nondegenerate_faces")
    if nondegenerate_mask is None:
        return None
    try:
        if callable(nondegenerate_mask):
            mask = nondegenerate_mask()
        else:
            mask = nondegenerate_mask
        return int(len(getattr(mesh, "faces", ())) - np.count_nonzero(mask))
    except Exception:
        return None


def mesh_summary(mesh: Any) -> dict[str, object]:
    """Return a lightweight summary for a trimesh-like mesh."""
    return {
        "vertex_count": vertex_count(mesh),
        "face_count": face_count(mesh),
        "bounds": bounds(mesh),
        "is_empty": is_empty(mesh),
        "is_watertight": is_watertight(mesh),
        "euler_number": euler_number(mesh),
        "volume": volume(mesh),
        "non_manifold_edge_count": non_manifold_edge_count(mesh),
        "degenerate_face_count": degenerate_face_count(mesh),
    }


def _safe_getattr(mesh: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(mesh, name, default)
    except (AttributeError, TypeError, ValueError):
        return default

