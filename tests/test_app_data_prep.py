from app.data_prep import (
    build_fetch_buildings_command,
    build_import_dem_command,
    build_inspect_data_command,
    data_prep_defaults,
)


def test_data_prep_defaults_use_data_directories():
    defaults = data_prep_defaults()

    assert defaults["buildings_out"].startswith("data/buildings/")
    assert defaults["dem_out"].startswith("data/dem/")


def test_build_fetch_buildings_command_includes_validation_and_optional_values():
    command = build_fetch_buildings_command(
        area_path="data/areas/seoul area.geojson",
        buildings_out="data/buildings/seoul.geojson",
        env_file=".env.local",
        area_crs="EPSG:4326",
    )

    assert "'.venv/Scripts/python.exe'" in command
    assert "'scripts/fetch_buildings.py'" in command
    assert "'--validate-area' 'data/areas/seoul area.geojson'" in command
    assert "'--env-file' '.env.local'" in command
    assert "'--area-crs' 'EPSG:4326'" in command


def test_build_import_dem_command_handles_reproject_and_optional_flags():
    command = build_import_dem_command(
        source_path="C:/data/source dem.tif",
        dem_out="data/dem/site.tif",
        area_path="data/areas/site.geojson",
        area_crs="EPSG:5179",
        target_crs="EPSG:5179",
        reproject=True,
    )

    assert "'scripts/import_dem.py'" in command
    assert "'--source' 'C:/data/source dem.tif'" in command
    assert "'--out' 'data/dem/site.tif'" in command
    assert "'--reproject'" in command
    assert "'--validate-area' 'data/areas/site.geojson'" in command
    assert "'--validate-area-crs' 'EPSG:5179'" in command
    assert "'--target-crs' 'EPSG:5179'" in command


def test_build_inspect_data_command_escapes_quotes_for_powershell():
    command = build_inspect_data_command(
        area_path="data/areas/o'hare.geojson",
        buildings_path="data/buildings/site.geojson",
        dem_path=None,
        area_crs=None,
        building_crs=None,
    )

    assert "'data/areas/o''hare.geojson'" in command
    assert "'--buildings' 'data/buildings/site.geojson'" in command
    assert "--dem" not in command
