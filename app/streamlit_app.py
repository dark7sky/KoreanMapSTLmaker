from app.runner import run_build
from app.ui_state import default_form_values, to_build_options


def main() -> None:
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:
        raise RuntimeError("Streamlit is not installed. Run: pip install streamlit") from exc

    st.set_page_config(page_title="KoreanMapSTLmaker", layout="centered")
    st.title("KoreanMapSTLmaker")

    defaults = default_form_values()
    with st.form("build-form"):
        area_path = st.text_input("Area path", defaults["area_path"])
        buildings_path = st.text_input("Buildings path (optional)", defaults["buildings_path"])
        dem_path = st.text_input("DEM path", defaults["dem_path"])
        out_path = st.text_input("Output STL path", defaults["out_path"])
        area_crs = st.text_input("Area CRS fallback", defaults["area_crs"])
        building_crs = st.text_input("Building CRS fallback", defaults["building_crs"])
        dem_crs = st.text_input("DEM CRS fallback", defaults["dem_crs"])
        terrain_resolution = st.number_input("Terrain resolution (m)", min_value=1.0, value=defaults["terrain_resolution"])
        z_scale = st.number_input("Z scale", min_value=0.01, value=defaults["z_scale"])
        export_formats = st.multiselect("Export formats", ["stl", "obj", "glb", "gltf"], defaults["export_formats"])
        preview = st.checkbox("Generate preview HTML", value=defaults["preview"])
        submitted = st.form_submit_button("Build Model")

    if not submitted:
        return

    values = {
        **defaults,
        "area_path": area_path,
        "buildings_path": buildings_path,
        "dem_path": dem_path,
        "out_path": out_path,
        "area_crs": area_crs,
        "building_crs": building_crs,
        "dem_crs": dem_crs,
        "terrain_resolution": terrain_resolution,
        "z_scale": z_scale,
        "export_formats": export_formats,
        "preview": preview,
    }
    options = to_build_options(values)
    result = run_build(options)
    if result.ok:
        st.success(f"Build completed in {result.elapsed_seconds:.2f}s")
        st.json(result.summary)
    else:
        st.error(f"Build failed after {result.elapsed_seconds:.2f}s")
        st.code(result.error or "Unknown error")


if __name__ == "__main__":
    main()
