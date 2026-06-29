import json

import pytest

from scripts import fetch_buildings
from src.data_sources.config import load_env_file, parse_env_text


def test_parse_env_text_parses_key_value_and_ignores_comments():
    parsed = parse_env_text(
        """
        # comment
        VWORLD_API_KEY=abc123
        EMPTY=
        NOT_A_PAIR
        """
    )

    assert parsed == {"VWORLD_API_KEY": "abc123", "EMPTY": ""}


def test_load_env_file_does_not_override_existing_environment_variable(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("VWORLD_API_KEY=from-file\n", encoding="utf-8")
    environ = {"VWORLD_API_KEY": "from-env"}

    applied = load_env_file(env_file, environ=environ)

    assert applied == {}
    assert environ["VWORLD_API_KEY"] == "from-env"


def test_fetch_buildings_cli_uses_existing_env_over_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("VWORLD_API_KEY=from-file\n", encoding="utf-8")
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    out_path = tmp_path / "buildings.geojson"
    captured: dict[str, str | None] = {}

    class FakeProvider:
        name = "fake-provider"

        def __init__(self, api_key: str | None, base_url: str, data_name: str) -> None:
            captured["api_key"] = api_key

    def fake_fetch_buildings_geojson(**kwargs):
        return {"feature_count": 0, "source": "fixture", "metadata_path": str(tmp_path / "metadata.json")}

    monkeypatch.setenv("VWORLD_API_KEY", "from-env")
    monkeypatch.setattr(fetch_buildings, "VWorldGISBuildingProvider", FakeProvider)
    monkeypatch.setattr(fetch_buildings, "fetch_buildings_geojson", fake_fetch_buildings_geojson)
    monkeypatch.setattr(
        "sys.argv",
        [
            "fetch_buildings.py",
            "--bounds",
            "126",
            "37",
            "126.1",
            "37.1",
            "--out",
            str(out_path),
            "--fixture-response",
            str(fixture_path),
            "--env-file",
            str(env_file),
        ],
    )

    fetch_buildings.main()

    assert captured["api_key"] == "from-env"


def test_fetch_buildings_cli_uses_env_file_when_env_missing(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("VWORLD_API_KEY=from-file\n", encoding="utf-8")
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    out_path = tmp_path / "buildings.geojson"
    captured: dict[str, str | None] = {}

    class FakeProvider:
        name = "fake-provider"

        def __init__(self, api_key: str | None, base_url: str, data_name: str) -> None:
            captured["api_key"] = api_key

    def fake_fetch_buildings_geojson(**kwargs):
        return {"feature_count": 0, "source": "fixture", "metadata_path": str(tmp_path / "metadata.json")}

    monkeypatch.delenv("VWORLD_API_KEY", raising=False)
    monkeypatch.setattr(fetch_buildings, "VWorldGISBuildingProvider", FakeProvider)
    monkeypatch.setattr(fetch_buildings, "fetch_buildings_geojson", fake_fetch_buildings_geojson)
    monkeypatch.setattr(
        "sys.argv",
        [
            "fetch_buildings.py",
            "--bounds",
            "126",
            "37",
            "126.1",
            "37.1",
            "--out",
            str(out_path),
            "--fixture-response",
            str(fixture_path),
            "--env-file",
            str(env_file),
        ],
    )

    fetch_buildings.main()

    assert captured["api_key"] == "from-file"


def test_fetch_buildings_cli_errors_when_key_missing_after_env_load(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("OTHER_KEY=value\n", encoding="utf-8")
    out_path = tmp_path / "buildings.geojson"
    monkeypatch.delenv("VWORLD_API_KEY", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        [
            "fetch_buildings.py",
            "--bounds",
            "126",
            "37",
            "126.1",
            "37.1",
            "--out",
            str(out_path),
            "--env-file",
            str(env_file),
        ],
    )

    with pytest.raises(SystemExit) as error:
        fetch_buildings.main()

    assert "VWORLD_API_KEY is required for live fetches" in str(error.value)


def test_fetch_buildings_cli_errors_when_data_id_missing(tmp_path, monkeypatch):
    out_path = tmp_path / "buildings.geojson"
    monkeypatch.setenv("VWORLD_API_KEY", "issued-key")
    monkeypatch.delenv("VWORLD_BUILDING_DATA_NAME", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["fetch_buildings.py", "--bounds", "126", "37", "126.1", "37.1", "--out", str(out_path)],
    )

    with pytest.raises(SystemExit) as error:
        fetch_buildings.main()

    assert "building data ID is required" in str(error.value)
