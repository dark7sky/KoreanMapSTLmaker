from app.data_prep import (
    build_fetch_buildings_command,
    build_import_dem_command,
    build_inspect_data_command,
    data_prep_defaults,
)
from app.field_inspection import inspect_building_fields
from app.runner import run_build
from app.result_summary import summarize_build_result
from app.ui_state import default_form_values, to_build_options


def main() -> None:
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:
        raise RuntimeError("Streamlit is not installed. Run: pip install streamlit") from exc

    st.set_page_config(page_title="KoreanMapSTLmaker", layout="centered")
    st.title("KoreanMapSTLmaker")
    tabs = st.tabs(["Build Model", "Data Prep"])

    with tabs[0]:
        defaults = default_form_values()
        with st.form("build-form"):
            area_path = st.text_input("Area path", defaults["area_path"])
            buildings_path = st.text_input("Buildings path (optional)", defaults["buildings_path"])
            field_result = inspect_building_fields(buildings_path) if buildings_path.strip() else None
            if field_result is not None and field_result.error:
                st.caption(f"Building fields unavailable: {field_result.error}")
            height_default = ", ".join(field_result.suggested_height_fields) if field_result else defaults["height_fields"]
            floor_default = ", ".join(field_result.suggested_floor_fields) if field_result else defaults["floor_fields"]
            height_fields = st.text_input("Height fields", height_default)
            floor_fields = st.text_input("Floor fields", floor_default)
            dem_path = st.text_input("DEM path", defaults["dem_path"])
            out_path = st.text_input("Output STL path", defaults["out_path"])
            area_crs = st.text_input("Area CRS fallback", defaults["area_crs"])
            building_crs = st.text_input("Building CRS fallback", defaults["building_crs"])
            dem_crs = st.text_input("DEM CRS fallback", defaults["dem_crs"])
            terrain_resolution = st.number_input(
                "Terrain resolution (m)",
                min_value=1.0,
                value=defaults["terrain_resolution"],
            )
            terrain_resampling = st.selectbox(
                "Terrain resampling",
                ["nearest", "bilinear"],
                index=["nearest", "bilinear"].index(defaults["terrain_resampling"]),
            )
            terrain_boundary_modes = ["grid", "polygon"]
            terrain_boundary_mode = st.selectbox(
                "Terrain boundary mode",
                terrain_boundary_modes,
                index=terrain_boundary_modes.index(defaults["terrain_boundary_mode"]),
            )
            base_modes = ["representative", "min", "mean", "min-corners"]
            building_base_mode = st.selectbox(
                "Building base mode",
                base_modes,
                index=base_modes.index(defaults["building_base_mode"]),
            )
            z_scale = st.number_input("Z scale", min_value=0.01, value=defaults["z_scale"])
            export_formats = st.multiselect("Export formats", ["stl", "obj", "glb", "gltf"], defaults["export_formats"])
            preview = st.checkbox("Generate preview HTML", value=defaults["preview"])
            submitted = st.form_submit_button("Build Model")

        if submitted:
            values = {
                **defaults,
                "area_path": area_path,
                "buildings_path": buildings_path,
                "dem_path": dem_path,
                "out_path": out_path,
                "area_crs": area_crs,
                "building_crs": building_crs,
                "dem_crs": dem_crs,
                "height_fields": height_fields,
                "floor_fields": floor_fields,
                "terrain_resolution": terrain_resolution,
                "terrain_resampling": terrain_resampling,
                "terrain_boundary_mode": terrain_boundary_mode,
                "building_base_mode": building_base_mode,
                "z_scale": z_scale,
                "export_formats": export_formats,
                "preview": preview,
            }
            options = to_build_options(values)
            result = run_build(options)
            if result.ok:
                st.success(f"Build completed in {result.elapsed_seconds:.2f}s")
                summary = result.summary or {}
                display = summarize_build_result(summary)

                st.subheader("Mesh Quality")
                if display.mesh_quality:
                    mesh_col_1, mesh_col_2, mesh_col_3 = st.columns(3)
                    mesh_col_1.metric("Watertight", "Yes" if display.mesh_quality.get("is_watertight") else "No")
                    mesh_col_2.metric("Non-manifold edges", int(display.mesh_quality.get("non_manifold_edge_count", 0)))
                    mesh_col_3.metric("Degenerate faces", int(display.mesh_quality.get("degenerate_face_count", 0)))
                    st.json(display.mesh_quality)
                else:
                    st.caption("No mesh quality data found in summary.")

                st.subheader("Outputs")
                if display.preview is not None:
                    st.markdown(f"[Open Preview HTML]({display.preview.uri})")

                if display.output_files:
                    for artifact in display.output_files:
                        status = "" if artifact.exists else " (missing)"
                        st.markdown(f"- `{artifact.label}`: [{artifact.path.name}]({artifact.uri}){status}")
                else:
                    st.caption("No output files listed.")

                if display.stl_download is not None:
                    with open(display.stl_download.path, "rb") as fh:
                        st.download_button(
                            "Download STL",
                            data=fh.read(),
                            file_name=display.stl_download.path.name,
                            mime="model/stl",
                        )
                else:
                    st.caption("STL download unavailable (file not found).")

                with st.expander("Raw summary JSON"):
                    st.json(summary)
            else:
                st.error(f"Build failed after {result.elapsed_seconds:.2f}s")
                st.code(result.error or "Unknown error")

    with tabs[1]:
        prep_defaults = data_prep_defaults()
        st.caption("Prepare buildings/DEM inputs, then inspect overlap and CRS before model build.")

        prep_area_path = st.text_input("Area path for prep", prep_defaults["area_path"])
        prep_area_crs = st.text_input("Area CRS fallback for prep (optional)", prep_defaults["area_crs"])
        prep_env_file = st.text_input("Env file for API key (optional)", prep_defaults["env_file"])

        st.subheader("Fetch Buildings")
        prep_buildings_out = st.text_input("Buildings output path", prep_defaults["buildings_out"])
        fetch_cmd = build_fetch_buildings_command(
            area_path=prep_area_path,
            buildings_out=prep_buildings_out,
            env_file=prep_env_file.strip() or None,
            area_crs=prep_area_crs.strip() or None,
        )
        st.code(fetch_cmd, language="powershell")

        st.subheader("Import DEM")
        prep_dem_source = st.text_input("DEM source path", prep_defaults["dem_source"])
        prep_dem_out = st.text_input("DEM output path", prep_defaults["dem_out"])
        prep_target_crs = st.text_input("DEM target CRS (optional)", prep_defaults["dem_target_crs"])
        prep_reproject = st.checkbox("Allow DEM reprojection", value=False)
        if prep_dem_source.strip():
            import_cmd = build_import_dem_command(
                source_path=prep_dem_source,
                dem_out=prep_dem_out,
                area_path=prep_area_path.strip() or None,
                area_crs=prep_area_crs.strip() or None,
                target_crs=prep_target_crs.strip() or None,
                reproject=prep_reproject,
            )
            st.code(import_cmd, language="powershell")
        else:
            st.caption("Enter DEM source path to generate import command.")

        st.subheader("Inspect and Validate Inputs")
        prep_inspect_buildings = st.text_input("Buildings path for inspection", prep_defaults["inspect_buildings"])
        prep_inspect_dem = st.text_input("DEM path for inspection", prep_defaults["inspect_dem"])
        inspect_cmd = build_inspect_data_command(
            area_path=prep_area_path,
            buildings_path=prep_inspect_buildings.strip() or None,
            dem_path=prep_inspect_dem.strip() or None,
            area_crs=prep_area_crs.strip() or None,
        )
        st.code(inspect_cmd, language="powershell")


if __name__ == "__main__":
    main()
