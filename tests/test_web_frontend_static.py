from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_FRONTEND = ROOT / "web_frontend" / "index.html"


def test_web_frontend_is_static_and_declares_expected_controls():
    html = WEB_FRONTEND.read_text(encoding="utf-8")

    expected_ids = [
        "apiBaseInput",
        "buildEndpointInput",
        "healthButton",
        "healthStatus",
        "areaPathInput",
        "buildingsPathInput",
        "demPathInput",
        "outPathInput",
        "terrainResolutionInput",
        "buildingBaseModeInput",
        "heightFieldsInput",
        "floorFieldsInput",
        "refreshPayloadButton",
        "copyPayloadButton",
        "submitBuildButton",
        "buildStatus",
        "payloadOutput",
    ]

    for element_id in expected_ids:
        assert f'id="{element_id}"' in html

    assert "<script src=" not in html
    assert "type=\"module\"" not in html
    assert "npm install" not in html
    assert 'value="http://localhost:8000"' in html
    assert 'value="/build"' in html
    assert 'value="data/sample/area.geojson"' in html
    assert 'value="data/sample/buildings.geojson"' in html
    assert 'value="data/sample/dem.tif"' in html
    assert 'value="output/model.stl"' in html


def test_web_frontend_payload_and_fetch_contract_matches_api_scaffold():
    html = WEB_FRONTEND.read_text(encoding="utf-8")

    expected_fragments = [
        'fetch(`${apiBaseInput.value.replace(/\\/$/, "")}/health`)',
        'fetch(`${apiBaseInput.value.replace(/\\/$/, "")}${buildEndpointInput.value}`',
        'method: "POST"',
        '"Content-Type": "application/json"',
        "body: payloadOutput.value",
        "function buildPayload()",
        "area_path: areaPathInput.value.trim()",
        "buildings_path: buildingsPathInput.value.trim()",
        "dem_path: demPathInput.value.trim()",
        "out_path: outPathInput.value.trim()",
        'target_crs: "EPSG:5179"',
        "terrain_resolution: Number(terrainResolutionInput.value)",
        "height_fields: heightFieldsInput.value.trim()",
        "floor_fields: floorFieldsInput.value.trim()",
        "building_base_mode: buildingBaseModeInput.value",
        'export_formats: ["stl"]',
        "function updatePayload()",
        "JSON.stringify(buildPayload(), null, 2)",
    ]

    for fragment in expected_fragments:
        assert fragment in html
