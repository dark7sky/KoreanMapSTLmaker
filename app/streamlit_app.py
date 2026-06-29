from pathlib import Path

from app.auto_build_ui import default_auto_build_values, run_auto_build_from_values
from app.data_prep import (
    build_fetch_buildings_command,
    build_import_dem_command,
    build_inspect_data_command,
    data_prep_defaults,
)
from app.field_inspection import inspect_building_fields
from app.runner import run_build
from app.result_summary import summarize_build_result
from app.quick_build import (
    build_quick_model,
    create_area_from_center,
    fetch_vworld_buildings,
    sanitize_output_name,
    save_uploaded_file,
)
from app.ui_state import default_form_values, to_build_options


def main() -> None:
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:
        raise RuntimeError("Streamlit is not installed. Run: pip install streamlit") from exc

    st.set_page_config(page_title="KoreanMapSTLmaker", page_icon=":material/map:", layout="wide")
    st.markdown(
        """
        <style>
        .stApp { background: #f7f8fa; color: #17202a; }
        [data-testid="stHeader"] { background: rgba(247, 248, 250, 0.92); }
        [data-testid="stMetric"] { background: #ffffff; border: 1px solid #dde3e8; padding: 14px; border-radius: 6px; }
        .stButton > button, .stDownloadButton > button { border-radius: 6px; font-weight: 700; }
        .block-container { max-width: 1180px; padding-top: 2rem; }
        h1, h2, h3 { letter-spacing: 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("KoreanMapSTLmaker")
    st.caption("선택한 지역의 지형과 건물을 결합해 3D 프린팅용 STL을 만듭니다.")
    tabs = st.tabs(["빠른 제작", "자동 제작", "수동 제작", "데이터 준비"])

    with tabs[0]:
        _render_quick_build_tab(st)

    with tabs[1]:
        defaults = default_auto_build_values()
        with st.form("auto-build-form"):
            area_path = st.text_input("Area file", str(defaults["area_path"]))
            registry_path = st.text_input("Dataset registry", str(defaults["registry_path"]))
            dataset_name = st.text_input("Dataset name (optional)", str(defaults["dataset_name"]))
            output_name = st.text_input("Output name", str(defaults["output_name"]))
            area_crs = st.text_input("Area CRS fallback", str(defaults["area_crs"]))
            target_crs = st.text_input("Target CRS", str(defaults["target_crs"]))
            output_dir = st.text_input("Output folder", str(defaults["output_dir"]))
            terrain_resolution = st.number_input(
                "Terrain resolution (m)",
                min_value=1.0,
                value=float(defaults["terrain_resolution"]),
                key="auto_terrain_resolution",
            )
            terrain_boundary_mode = st.selectbox(
                "Terrain boundary",
                ["polygon", "grid"],
                index=["polygon", "grid"].index(str(defaults["terrain_boundary_mode"])),
            )
            export_formats = st.multiselect(
                "Export formats",
                ["stl", "obj", "glb", "gltf"],
                list(defaults["export_formats"]),
                key="auto_export_formats",
            )
            preview = st.checkbox("Generate preview HTML", value=bool(defaults["preview"]))
            dry_run = st.checkbox("Validate only (dry run)", value=bool(defaults["dry_run"]))
            with st.expander("Advanced print/model options"):
                interpolate_nodata = st.checkbox("Interpolate small DEM nodata holes", value=bool(defaults["interpolate_nodata"]))
                z_scale = st.number_input("Terrain Z scale", min_value=0.01, value=float(defaults["z_scale"]))
                model_scale = st.number_input("Model scale", min_value=0.01, value=float(defaults["model_scale"]))
                base_plate_thickness = st.number_input(
                    "Base plate thickness",
                    min_value=0.0,
                    value=float(defaults["base_plate_thickness"]),
                )
                base_plate_margin = st.number_input(
                    "Base plate margin",
                    min_value=0.0,
                    value=float(defaults["base_plate_margin"]),
                )
                max_area_km2 = st.number_input("Max area (km²)", min_value=0.01, value=float(defaults["max_area_km2"]))
            submitted = st.form_submit_button("Validate / Build")

        if submitted:
            values = {
                **defaults,
                "area_path": area_path,
                "registry_path": registry_path,
                "dataset_name": dataset_name,
                "area_crs": area_crs,
                "target_crs": target_crs,
                "output_dir": output_dir,
                "output_name": output_name,
                "terrain_resolution": terrain_resolution,
                "terrain_boundary_mode": terrain_boundary_mode,
                "export_formats": export_formats,
                "preview": preview,
                "dry_run": dry_run,
                "interpolate_nodata": interpolate_nodata,
                "z_scale": z_scale,
                "model_scale": model_scale,
                "base_plate_thickness": base_plate_thickness,
                "base_plate_margin": base_plate_margin,
                "max_area_km2": max_area_km2,
            }
            result = run_auto_build_from_values(values)
            if result.ok:
                st.success(f"Auto build completed in {result.elapsed_seconds:.2f}s")
                st.code(result.text_report or "", language="text")
                report = result.report or {}
                build = report.get("build")
                if isinstance(build, dict):
                    display = summarize_build_result(build)
                    if display.preview is not None:
                        st.markdown(f"[Open Preview HTML]({display.preview.uri})")
                    if display.stl_download is not None:
                        with open(display.stl_download.path, "rb") as fh:
                            st.download_button(
                                "Download STL",
                                data=fh.read(),
                                file_name=display.stl_download.path.name,
                                mime="model/stl",
                            )
                with st.expander("Full auto-build report"):
                    st.json(report)
            else:
                st.error(f"Auto build failed after {result.elapsed_seconds:.2f}s")
                st.code(result.error or "Unknown error")

    with tabs[2]:
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

    with tabs[3]:
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


def _render_quick_build_tab(st) -> None:
    st.subheader("바로 시작")
    st.write("샘플로 기능을 확인하거나, 좌표와 실제 데이터를 넣어 모델을 제작하세요.")
    sample_col, sample_note = st.columns([1, 3])
    with sample_col:
        if st.button("샘플 모델 만들기", type="primary", use_container_width=True):
            sample_values = default_auto_build_values()
            sample_values["dry_run"] = False
            sample_values["export_formats"] = ["stl", "glb"]
            result = run_auto_build_from_values(sample_values)
            if result.ok:
                st.session_state["quick_report"] = result.report
            else:
                st.error(result.error or "샘플 모델 제작에 실패했습니다.")
    with sample_note:
        st.info("API 키나 외부 파일 없이 전체 제작 흐름과 STL 다운로드를 시험합니다.")

    st.divider()
    location_col, data_col = st.columns([1, 1])
    with location_col:
        st.subheader("1. 위치와 크기")
        coord_1, coord_2 = st.columns(2)
        latitude = coord_1.number_input("위도", value=37.5665, format="%.6f", key="quick_latitude")
        longitude = coord_2.number_input("경도", value=126.9780, format="%.6f", key="quick_longitude")
        size_1, size_2 = st.columns(2)
        width_m = size_1.number_input("가로 (m)", min_value=10, max_value=5000, value=300, step=10)
        height_m = size_2.number_input("세로 (m)", min_value=10, max_value=5000, value=300, step=10)
        st.map({"lat": [latitude], "lon": [longitude]}, zoom=15, height=330)

    with data_col:
        st.subheader("2. 지형과 건물")
        dem_upload = st.file_uploader("DEM GeoTIFF", type=["tif", "tiff"], key="quick_dem")
        building_mode = st.radio(
            "건물 데이터",
            ["파일 업로드", "VWorld API"],
            horizontal=True,
            key="quick_building_mode",
        )
        building_upload = None
        api_key = ""
        data_name = ""
        if building_mode == "파일 업로드":
            building_upload = st.file_uploader(
                "건물 GeoJSON 또는 GeoPackage",
                type=["geojson", "json", "gpkg"],
                key="quick_buildings",
            )
        else:
            api_key = st.text_input("VWorld API 키", type="password", key="quick_api_key")
            data_name = st.text_input(
                "GIS 건물 데이터 ID",
                help="VWorld 국가중점데이터 API 상세 화면에 표시되는 건물 데이터 식별자를 입력합니다.",
                key="quick_data_name",
            )
            st.caption("키 발급과 데이터 이용 조건은 VWorld 정책을 따릅니다.")

        output_name = st.text_input("결과 이름", value="seoul_model", key="quick_output_name")
        resolution = st.slider("지형 해상도 (m)", min_value=2, max_value=50, value=10, step=1)
        quick_build_clicked = st.button("3D 모델 만들기", type="primary", use_container_width=True)

    if quick_build_clicked:
        try:
            if dem_upload is None:
                raise ValueError("DEM GeoTIFF를 선택해 주세요.")
            safe_name = sanitize_output_name(output_name)
            work_dir = Path("data/local_sessions") / safe_name
            area_path = work_dir / "area.geojson"
            create_area_from_center(
                latitude=float(latitude),
                longitude=float(longitude),
                width_m=float(width_m),
                height_m=float(height_m),
                output_path=area_path,
            )
            dem_path = save_uploaded_file(
                name=dem_upload.name,
                data=bytes(dem_upload.getbuffer()),
                directory=work_dir,
                kind="dem",
            )
            if building_mode == "파일 업로드":
                if building_upload is None:
                    raise ValueError("건물 GeoJSON 또는 GeoPackage를 선택해 주세요.")
                buildings_path = save_uploaded_file(
                    name=building_upload.name,
                    data=bytes(building_upload.getbuffer()),
                    directory=work_dir,
                    kind="building",
                )
            else:
                buildings_path = work_dir / "vworld_buildings.geojson"
                with st.spinner("VWorld에서 건물 데이터를 가져오는 중입니다..."):
                    fetch_vworld_buildings(
                        area_path=area_path,
                        api_key=api_key,
                        data_name=data_name,
                        output_path=buildings_path,
                    )
            with st.spinner("지형과 건물을 결합해 3D 모델을 만드는 중입니다..."):
                st.session_state["quick_report"] = build_quick_model(
                    area_path=area_path,
                    dem_path=dem_path,
                    buildings_path=buildings_path,
                    output_name=safe_name,
                    work_dir=work_dir,
                    terrain_resolution=float(resolution),
                )
        except Exception as exc:
            st.session_state.pop("quick_report", None)
            st.error(str(exc))

    quick_report = st.session_state.get("quick_report")
    if isinstance(quick_report, dict):
        _render_auto_build_result(st, quick_report)


def _render_auto_build_result(st, report: dict) -> None:
    if report.get("status") != "built":
        st.warning(f"모델이 아직 생성되지 않았습니다. 상태: {report.get('status', 'unknown')}")
        with st.expander("상세 보고서"):
            st.json(report)
        return
    build = report.get("build")
    if not isinstance(build, dict):
        st.error("제작 결과 보고서에 모델 정보가 없습니다.")
        return
    display = summarize_build_result(build)
    st.success("3D 모델 제작이 완료되었습니다.")
    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("건물", f"{int(build.get('building_count', 0)):,}개")
    metric_2.metric("최저 지형", f"{float(build.get('min_elevation_m', 0.0)):.1f} m")
    quality = build.get("mesh_quality") or {}
    metric_3.metric("밀폐 메시", "정상" if quality.get("is_watertight") else "확인 필요")
    if display.stl_download is not None:
        with open(display.stl_download.path, "rb") as fh:
            st.download_button(
                "STL 다운로드",
                data=fh.read(),
                file_name=display.stl_download.path.name,
                mime="model/stl",
                type="primary",
                use_container_width=True,
            )
    if display.preview is not None:
        st.markdown(f"[3D 미리보기 열기]({display.preview.uri})")
    with st.expander("제작 상세 정보"):
        st.json(report)


if __name__ == "__main__":
    main()
