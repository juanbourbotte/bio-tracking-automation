import os
import io
import streamlit as st
import pandas as pd
from src.config import (
    DISTANCE_THRESHOLD,
    MIN_COLOC_FRAMES,
    MAX_FRAME_GAP,
    TIME_INTERVAL_SEC,
    PIXEL_SIZE_UM,
    CELL_AREA_UM2,
)
from src.ingestion import (
    read_raw_dataframe,
    inspect_columns,
    load_vertical_excel,
    LABELS_MAP,
)
from src.pipeline import quantify_fusion_fission
from src.stats_engine import calculate_condition_statistics
from src.reporting import export_results_excel, generate_plots

st.set_page_config(page_title="Vesicle Tracking Pipeline", layout="wide")
st.title("🔬 Automated Vesicle Tracking & Bio-Image Analytics Pipeline")

# --- BARRA LATERAL: CONFIGURACIÓN Y CALIBRACIÓN ---
st.sidebar.header("🏷️ Configuración de Marcadores")
channel_a = st.sidebar.text_input("Canal / Proteína A", value="Cav1")
channel_b = st.sidebar.text_input("Canal / Proteína B", value="EEA1")

st.sidebar.header("⚙️ Parámetros Espacio-Temporales")
dist_thresh = st.sidebar.slider(
    "Umbral de distancia (µm)", 0.1, 1.0, float(DISTANCE_THRESHOLD)
)
min_frames = st.sidebar.slider(
    "Frames mín. de contacto", 1, 10, int(MIN_COLOC_FRAMES)
)
max_gap = st.sidebar.slider(
    "Tolerancia de parpadeo (frames)", 0, 5, int(MAX_FRAME_GAP)
)

st.sidebar.header("🔬 Calibración del Microscopio")
time_interval = st.sidebar.number_input(
    "Paso de tiempo (Δt en segundos)",
    min_value=0.01,
    max_value=60.0,
    value=float(TIME_INTERVAL_SEC),
    step=0.1,
)
pixel_size = st.sidebar.number_input(
    "Tamaño de Pixel / Factor de Escala (µm/px)",
    min_value=0.001,
    max_value=10.0,
    value=float(PIXEL_SIZE_UM),
    step=0.01,
    format="%.3f",
)
cell_area = st.sidebar.number_input(
    "Área Celular Promedio (µm²)",
    min_value=1.0,
    max_value=10000.0,
    value=float(CELL_AREA_UM2),
    step=10.0,
)

# --- INICIALIZAR ESTADO DE SESIÓN ---
if "files_payload" not in st.session_state:
    st.session_state["files_payload"] = []

# --- SECCIÓN DE CARGA DE DATOS ---
col_upload, col_sample = st.columns([3, 1])

with col_upload:
    uploaded_files = st.file_uploader(
        "Carga uno o más archivos Excel/CSV de tracking",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
    )

with col_sample:
    st.write("¿No tienes datos a mano?")
    btn_sample = st.button("🧪 Cargar datos de prueba (1-clic)", type="secondary")

# Lógica de actualización persistente en session_state
if uploaded_files:
    st.session_state["files_payload"] = []
    for f in uploaded_files:
        content = f.getvalue()
        buf = io.BytesIO(content)
        buf.name = f.name
        st.session_state["files_payload"].append(buf)

elif btn_sample:
    sample_dir = "sample_data"
    if os.path.exists(sample_dir):
        sample_paths = [
            os.path.join(sample_dir, f)
            for f in os.listdir(sample_dir)
            if f.endswith((".xlsx", ".csv"))
        ]
        st.session_state["files_payload"] = []
        for sp in sample_paths:
            with open(sp, "rb") as f:
                content = f.read()
                buf = io.BytesIO(content)
                buf.name = os.path.basename(sp)
                st.session_state["files_payload"].append(buf)
        st.toast("¡Datos de prueba cargados correctamente!", icon="🧪")
    else:
        st.error("No se encontró la carpeta sample_data/.")

files_to_process = st.session_state["files_payload"]

if files_to_process:
    st.subheader("Archivos Cargados y Verificación de Estructura")
    valid_data_list = []

    for file_buf in files_to_process:
        try:
            file_buf.seek(0)
            file_bytes = file_buf.read()
            bytes_io = io.BytesIO(file_bytes)
            bytes_io.name = getattr(file_buf, "name", "dataset.xlsx")

            df_raw = read_raw_dataframe(bytes_io)
            df_mapped, missing = inspect_columns(df_raw)

            custom_mapping = {}

            if missing:
                st.warning(
                    f"⚠️ **{bytes_io.name}**: No se detectaron automáticamente algunas columnas requeridas. Asígnalas manualmente:"
                )
                cols_in_file = ["-- Seleccionar --"] + list(df_raw.columns)
                col_cols = st.columns(len(missing))

                for idx, miss_col in enumerate(missing):
                    with col_cols[idx]:
                        label = LABELS_MAP.get(miss_col, miss_col)
                        selected = st.selectbox(
                            f"Mapear '{label}':",
                            cols_in_file,
                            key=f"{bytes_io.name}_{miss_col}",
                        )
                        if selected != "-- Seleccionar --":
                            custom_mapping[miss_col] = selected

                _, still_missing = inspect_columns(
                    df_raw, custom_col_map=custom_mapping
                )
                if still_missing:
                    st.info(f"☝️ Selecciona las columnas faltantes para continuar con **{bytes_io.name}**.")
                    continue

            bytes_io.seek(0)
            c1, c2 = load_vertical_excel(
                bytes_io,
                channel_a=channel_a,
                channel_b=channel_b,
                custom_col_map=custom_mapping if custom_mapping else None,
            )
            detected_cond = (
                c1["CONDITION"].iloc[0] if not c1.empty else "Desconocido"
            )

            st.success(
                f"✅ **{bytes_io.name}** -> Condición: `{detected_cond}` | Filas: **{len(c1):,}** ({channel_a}), **{len(c2):,}** ({channel_b})"
            )
            valid_data_list.append((c1, c2))

            os.makedirs("data/raw", exist_ok=True)
            with open(os.path.join("data/raw", bytes_io.name), "wb") as f_out:
                f_out.write(file_bytes)

        except Exception as e:
            st.error(f"❌ Error al procesar **{getattr(file_buf, 'name', 'archivo')}**: {str(e)}")

    if valid_data_list:
        st.markdown("---")
        if st.button("🚀 Ejecutar Análisis Comparativo", type="primary"):
            with st.spinner("Ejecutando pipeline vectorial y pruebas estadísticas..."):
                all_pop_a = [item[0] for item in valid_data_list if not item[0].empty]
                all_pop_b = [item[1] for item in valid_data_list if not item[1].empty]

                if not all_pop_a or not all_pop_b:
                    st.error(f"❌ No se encontraron datos válidos para los canales '{channel_a}' y/o '{channel_b}'. Revisa los nombres asignados en la barra lateral.")
                else:
                    combined_pop_a = pd.concat(all_pop_a, ignore_index=True)
                    combined_pop_b = pd.concat(all_pop_b, ignore_index=True)

                    summary_df, events_df, coloc_df = quantify_fusion_fission(
                        combined_pop_a,
                        combined_pop_b,
                        dist_thresh,
                        min_frames,
                        max_gap,
                        pixel_size,
                        time_interval,
                        cell_area,
                    )
                    stats_df = calculate_condition_statistics(summary_df, events_df)

                    out_dir = "data/processed"
                    out_excel = os.path.join(out_dir, "Resultados_Cuantificacion.xlsx")
                    export_results_excel(summary_df, events_df, coloc_df, stats_df, out_excel)
                    generate_plots(summary_df, events_df, stats_df, out_dir)

                    st.session_state["analyzed"] = True
                    st.session_state["summary_df"] = summary_df
                    st.session_state["events_df"] = events_df
                    st.session_state["coloc_df"] = coloc_df
                    st.session_state["stats_df"] = stats_df
                    st.session_state["out_excel"] = out_excel

                    st.balloons()

        if st.session_state.get("analyzed", False):
            st.success("¡Análisis comparativo disponible!")

            summary_df = st.session_state["summary_df"]
            events_df = st.session_state["events_df"]
            coloc_df = st.session_state["coloc_df"]
            stats_df = st.session_state["stats_df"]
            out_excel = st.session_state["out_excel"]
            out_dir = "data/processed"

            tab1, tab2, tab3 = st.tabs(
                ["📊 Resumen & Estadística", "📈 Gráficos de Dinámica", "📋 Tablas Detalladas"]
            )

            with tab1:
                st.subheader("Resumen Cuantitativo por Celda")
                st.dataframe(summary_df, use_container_width=True)

                if not stats_df.empty:
                    st.subheader("Comparaciones Estadísticas (Control vs. Tratamiento)")
                    st.dataframe(stats_df, use_container_width=True)

                fig1_p = os.path.join(out_dir, "Figure1_Condition_Statistical_Comparisons.png")
                if os.path.exists(fig1_p):
                    st.image(fig1_p, caption="Figura 1: Resumen Estadístico y Conteo de Eventos")
                    with open(fig1_p, "rb") as f:
                        st.download_button(
                            "📥 Descargar Figura 1 (PNG 300 DPI)",
                            f,
                            file_name="Figure1_Condition_Statistical_Comparisons.png",
                            mime="image/png",
                        )

            with tab2:
                fig2_p = os.path.join(out_dir, "Figure2_Dynamics_and_Spatial_Map.png")
                if os.path.exists(fig2_p):
                    st.image(fig2_p, caption="Figura 2: Dinámica Temporal y Mapa de Coordenadas 2D")
                    with open(fig2_p, "rb") as f:
                        st.download_button(
                            "📥 Descargar Figura 2 (PNG 300 DPI)",
                            f,
                            file_name="Figure2_Dynamics_and_Spatial_Map.png",
                            mime="image/png",
                        )

            with tab3:
                st.subheader("Eventos Detallados de Fusión y Fisión")
                st.dataframe(events_df, use_container_width=True)

                st.subheader("Todas las Colocalizaciones Detectadas")
                st.dataframe(coloc_df, use_container_width=True)

            if os.path.exists(out_excel):
                with open(out_excel, "rb") as f:
                    st.download_button(
                        "📊 Descargar Reporte Excel Completo (.xlsx)",
                        f,
                        file_name="Resultados_Cuantificacion.xlsx",
                    )