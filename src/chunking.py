from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from shapely.geometry import box
from shapely.geometry.base import BaseGeometry

from src.geometry import repair_polygonal_geometry


@dataclass(frozen=True)
class AreaChunk:
    tile_index: int
    row: int
    col: int
    tile_bounds: tuple[float, float, float, float]
    geometry: BaseGeometry

    @property
    def geometry_bounds(self) -> tuple[float, float, float, float]:
        return tuple(float(value) for value in self.geometry.bounds)

    @property
    def tile_area(self) -> float:
        minx, miny, maxx, maxy = self.tile_bounds
        return float((maxx - minx) * (maxy - miny))

    @property
    def geometry_area(self) -> float:
        return float(self.geometry.area)

    @property
    def coverage_ratio(self) -> float:
        tile_area = self.tile_area
        if tile_area <= 0:
            return 0.0
        return float(self.geometry_area / tile_area)

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "tile_index": self.tile_index,
            "row": self.row,
            "col": self.col,
            "tile_bounds": [float(value) for value in self.tile_bounds],
            "geometry_bounds": [float(value) for value in self.geometry_bounds],
            "tile_area": self.tile_area,
            "geometry_area": self.geometry_area,
            "coverage_ratio": self.coverage_ratio,
        }


@dataclass(frozen=True)
class ChunkedArea:
    source_bounds: tuple[float, float, float, float]
    max_chunk_size: float
    grid_rows: int
    grid_cols: int
    chunks: tuple[AreaChunk, ...]

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "source_bounds": [float(value) for value in self.source_bounds],
            "max_chunk_size": float(self.max_chunk_size),
            "grid_rows": self.grid_rows,
            "grid_cols": self.grid_cols,
            "chunk_count": self.chunk_count,
            "chunks": [chunk.metadata for chunk in self.chunks],
        }


def chunk_selected_area(area: BaseGeometry, max_chunk_size: float) -> ChunkedArea:
    if max_chunk_size <= 0:
        raise ValueError("max_chunk_size must be greater than 0.")
    if area is None or area.is_empty:
        raise ValueError("Selected area is empty.")

    repaired_area = repair_polygonal_geometry(area)
    if repaired_area is None or repaired_area.is_empty:
        raise ValueError("Selected area does not contain polygonal geometry.")

    minx, miny, maxx, maxy = (float(value) for value in repaired_area.bounds)
    width = maxx - minx
    height = maxy - miny
    if width <= 0 or height <= 0:
        raise ValueError("Selected area bounds must have positive width and height.")

    grid_cols = max(1, ceil(width / max_chunk_size))
    grid_rows = max(1, ceil(height / max_chunk_size))
    x_edges = _build_edges(minx, maxx, grid_cols, max_chunk_size)
    y_edges = _build_edges(miny, maxy, grid_rows, max_chunk_size)

    chunks: list[AreaChunk] = []
    for row in range(grid_rows):
        tile_miny = y_edges[row]
        tile_maxy = y_edges[row + 1]
        for col in range(grid_cols):
            tile_minx = x_edges[col]
            tile_maxx = x_edges[col + 1]
            tile = box(tile_minx, tile_miny, tile_maxx, tile_maxy)
            clipped = repair_polygonal_geometry(repaired_area.intersection(tile))
            if clipped is None or clipped.is_empty or clipped.area <= 0:
                continue
            chunks.append(
                AreaChunk(
                    tile_index=row * grid_cols + col,
                    row=row,
                    col=col,
                    tile_bounds=(float(tile_minx), float(tile_miny), float(tile_maxx), float(tile_maxy)),
                    geometry=clipped,
                )
            )

    return ChunkedArea(
        source_bounds=(minx, miny, maxx, maxy),
        max_chunk_size=float(max_chunk_size),
        grid_rows=grid_rows,
        grid_cols=grid_cols,
        chunks=tuple(chunks),
    )


def _build_edges(start: float, end: float, segments: int, max_chunk_size: float) -> list[float]:
    edges = [float(start)]
    for index in range(1, segments):
        edge = min(float(start) + (index * max_chunk_size), float(end))
        edges.append(edge)
    edges.append(float(end))
    return edges
