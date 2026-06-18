import pytest
from shapely.geometry import MultiPolygon, Polygon, box

from src.chunking import chunk_selected_area


def test_chunk_selected_area_splits_square_into_row_major_grid():
    area = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])

    result = chunk_selected_area(area, 4.0)

    assert result.source_bounds == (0.0, 0.0, 10.0, 10.0)
    assert result.grid_cols == 3
    assert result.grid_rows == 3
    assert result.chunk_count == 9
    assert [chunk.tile_index for chunk in result.chunks] == list(range(9))
    assert result.metadata["chunk_count"] == 9
    assert result.metadata["grid_cols"] == 3
    assert result.metadata["grid_rows"] == 3

    first = result.chunks[0]
    assert first.row == 0
    assert first.col == 0
    assert first.tile_bounds == (0.0, 0.0, 4.0, 4.0)
    assert first.geometry.equals(box(0.0, 0.0, 4.0, 4.0))

    last = result.chunks[-1]
    assert last.row == 2
    assert last.col == 2
    assert last.tile_bounds == (8.0, 8.0, 10.0, 10.0)
    assert last.geometry.equals(box(8.0, 8.0, 10.0, 10.0))

    assert all(chunk.geometry.within(area) or chunk.geometry.equals(area) for chunk in result.chunks)
    assert all((chunk.tile_bounds[2] - chunk.tile_bounds[0]) <= 4.0 for chunk in result.chunks)
    assert all((chunk.tile_bounds[3] - chunk.tile_bounds[1]) <= 4.0 for chunk in result.chunks)


def test_chunk_selected_area_skips_empty_tiles_and_keeps_metadata_stable():
    area = MultiPolygon(
        [
            box(0.5, 0.5, 2.5, 2.2),
            box(6.6, 0.4, 7.9, 2.3),
        ]
    )

    result = chunk_selected_area(area, 3.0)

    assert result.grid_cols == 3
    assert result.grid_rows == 1
    assert result.chunk_count == 2
    assert [chunk.tile_index for chunk in result.chunks] == [0, 2]
    assert [chunk.col for chunk in result.chunks] == [0, 2]

    left, right = result.chunks
    assert left.geometry.area == pytest.approx(3.4)
    assert right.geometry.area == pytest.approx(2.47, rel=1e-6)
    assert left.metadata["coverage_ratio"] < 1.0
    assert right.metadata["coverage_ratio"] < 1.0
    assert left.geometry.within(area)
    assert right.geometry.within(area)
    assert left.geometry_bounds == (0.5, 0.5, 2.5, 2.2)
    assert right.geometry_bounds == (6.6, 0.4, 7.9, 2.3)


def test_chunk_selected_area_rejects_non_positive_chunk_size():
    area = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])

    with pytest.raises(ValueError, match="greater than 0"):
        chunk_selected_area(area, 0.0)
