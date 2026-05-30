from pathlib import Path

from app.ui_state import default_form_values, to_build_options


def test_to_build_options_maps_and_normalizes_values():
    values = default_form_values()
    values.update(
        {
            "area_path": "data/areas/a.geojson",
            "buildings_path": "",
            "dem_path": "data/dem/a.tif",
            "out_path": "output/a.stl",
            "area_crs": " EPSG:4326 ",
            "building_crs": " ",
            "dem_crs": " EPSG:5186 ",
            "height_fields": " HEIGHT, BUILD_H , ,",
            "floor_fields": ["GRND_FLR", " ", "FLOOR"],
            "export_formats": ["stl", "obj", "stl", "  ", "glb"],
            "terrain_boundary_mode": "polygon",
        }
    )

    options = to_build_options(values)

    assert options.area_path == Path("data/areas/a.geojson")
    assert options.buildings_path is None
    assert options.dem_path == Path("data/dem/a.tif")
    assert options.out_path == Path("output/a.stl")
    assert options.area_crs == "EPSG:4326"
    assert options.building_crs is None
    assert options.dem_crs == "EPSG:5186"
    assert options.height_fields == ("HEIGHT", "BUILD_H")
    assert options.floor_fields == ("GRND_FLR", "FLOOR")
    assert options.export_formats == ("stl", "obj", "glb")
    assert options.terrain_boundary_mode == "polygon"


def test_to_build_options_defaults_export_format_to_stl():
    values = default_form_values()
    values["export_formats"] = []

    options = to_build_options(values)

    assert options.export_formats == ("stl",)
