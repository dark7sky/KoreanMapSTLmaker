from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AREA_SELECTOR = ROOT / "tools" / "area_selector.html"


def test_area_selector_declares_expected_controls_and_defaults():
    html = AREA_SELECTOR.read_text(encoding="utf-8")

    expected_ids = [
        "downloadButton",
        "copyButton",
        "fitButton",
        "clearButton",
        "copyCommandButton",
        "resetCommandButton",
        "commandTypeInput",
        "areaPathInput",
        "buildingsPathInput",
        "demPathInput",
        "outPathInput",
        "resolutionInput",
        "commandOutput",
        "geojsonOutput",
    ]

    for element_id in expected_ids:
        assert f'id="{element_id}"' in html

    assert 'value="data\\areas\\area.geojson"' in html
    assert 'value="data\\buildings\\my_region_buildings.shp"' in html
    assert 'value="data\\dem\\my_region_dem.tif"' in html
    assert 'value="output\\my_area.stl"' in html
    assert 'value="10"' in html


def test_area_selector_command_template_matches_workflow_contract():
    html = AREA_SELECTOR.read_text(encoding="utf-8")

    expected_fragments = [
        r".\\.venv\\Scripts\\python.exe scripts\\inspect_data.py `",
        r".\\.venv\\Scripts\\python.exe make_model.py `",
        "--area-crs EPSG:4326",
        "--buildings ${buildingsPathInput.value}",
        "--dem ${demPathInput.value}",
        "--terrain-resolution ${resolutionInput.value}",
        "--height-field HEIGHT",
        "--floor-field GRND_FLR",
        "--separate",
        "--preview",
    ]

    for fragment in expected_fragments:
        assert fragment in html

    assert '<option value="inspect">Inspect data</option>' in html
    assert '<option value="model">Make model</option>' in html
    assert "function updateCommand()" in html
    assert 'commandTypeInput.value === "inspect"' in html
    assert "copyCommandButton.addEventListener" in html
    assert "resetCommandButton.addEventListener" in html
