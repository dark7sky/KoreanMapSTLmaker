import geopandas as gpd
from shapely.geometry import Polygon

from app import field_inspection


def test_inspect_building_fields_reads_non_geometry_columns(tmp_path, monkeypatch):
    path = tmp_path / "buildings.geojson"
    path.write_text("{}", encoding="utf-8")
    gdf = gpd.GeoDataFrame(
        [
            {"HEIGHT": 12.0, "GRND_FLR": 4, "name": "a", "geometry": Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])}
        ],
        geometry="geometry",
        crs="EPSG:5179",
    )

    monkeypatch.setattr(field_inspection.gpd, "read_file", lambda *_: gdf)
    result = field_inspection.inspect_building_fields(path)

    assert result.error is None
    assert result.fields == ("HEIGHT", "GRND_FLR", "name")
    assert result.suggested_height_fields[0] == "HEIGHT"
    assert result.suggested_floor_fields[0] == "GRND_FLR"


def test_inspect_building_fields_returns_error_for_read_failure(tmp_path, monkeypatch):
    path = tmp_path / "missing.geojson"

    monkeypatch.setattr(
        field_inspection.gpd,
        "read_file",
        lambda *_: (_ for _ in ()).throw(RuntimeError("read failed")),
    )
    result = field_inspection.inspect_building_fields(path)

    assert result.fields == ()
    assert result.suggested_height_fields == ()
    assert result.suggested_floor_fields == ()
    assert result.error == "read failed"


def test_suggest_fields_scores_korean_and_english_names():
    fields = ("\uac74\ubb3c\ub192\uc774", "\uce35\uc218", "height_m", "total_floor", "name")

    suggested_height = field_inspection.suggest_fields(fields, kind="height")
    suggested_floor = field_inspection.suggest_fields(fields, kind="floor")

    assert "\uac74\ubb3c\ub192\uc774" in suggested_height
    assert "height_m" in suggested_height
    assert "\uce35\uc218" in suggested_floor
    assert "total_floor" in suggested_floor
