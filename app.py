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
from src.ingestion import load_vertical_excel
from src.pipeline import quantify_fusion_fission
from src.stats_engine import calculate_condition_statistics
from src.reporting import export_results_excel, generate_plots

st.set_page_config(page_title="Vesicle Tracking Pipeline", layout="wide")
st.title("🔬 Automated Vesicle Tracking & Bio-Image Analytics Pipeline")

uploaded_files = st.file_uploader(
    "Carga uno o más archivos Excel/CSV de tracking (soporta múltiples condiciones)",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=True,
)

if uploaded_files:
    st.sidebar.header("Parámetros de Análisis Espacio-Temporal")
    dist_thresh = st.sidebar.slider(
        "Umbral de distancia (µm)", 0.1, 1.0, DISTANCE_THRESHOLD
    )
    min_frames = st.sidebar.slider(
        "Frames mín. de contacto", 1, 10, MIN_COLOC_FRAMES
    )
    max_gap = st.sidebar.slider(
        "Tolerancia de parpadeo (frames)", 0, 5, MAX_FRAME_GAP
    )

    st.subheader("Archivos Cargados y Detección de Condiciones")

    valid_data_list = []

    for file in uploaded_files:
        try:
            file_bytes = file.getvalue()
            bytes_io = io.BytesIO(file_bytes)
            bytes_io.name = file.name

            c1, c2 = load_vertical_excel(bytes_io)
            detected_cond = (
                c1["CONDITION"].iloc[0] if not c1.empty else "Desconocido"
            )

            st.success(
                f"📁 **{file.name}** -> Condición asignada: `{detected_cond}` ({len(c1):,} filas Cav1, {len(c2):,} filas EEA1)"
            )
            valid_data_list.append((c1, c2))

            os.makedirs("data/raw", exist_ok=True)
            with open(os.path.join("data/raw", file.name), "wb") as f_out:
                f_out.write(file_bytes)

        except Exception as e:
            st.error(f"❌ Error al leer el archivo **{file.name}**: {str(e)}")

    if valid_data_list:
        st.markdown("---")

        # Botón para detonar el cálculo y guardar en session_state
        if st.button("🚀 Ejecutar Análisis Comparativo", type="primary"):
            with st.spinner(
                "Ejecutando pipeline vectorial y pruebas estadísticas..."
            ):
                all_cav1 = [item[0] for item in valid_data_list]
                all_eea1 = [item[1] for item in valid_data_list]

                combined_cav1 = pd.concat(all_cav1, ignore_index=True)
                combined_eea1 = pd.concat(all_eea1, ignore_index=True)

                summary_df, events_df, coloc_df = quantify_fusion_fission(
                    combined_cav1,
                    combined_eea1,
                    dist_thresh,
                    min_frames,
                    max_gap,
                    PIXEL_SIZE_UM,
                    TIME_INTERVAL_SEC,
                    CELL_AREA_UM2,
                )
                stats_df = calculate_condition_statistics(
                    summary_df, events_df
                )

                out_dir = "data/processed"
                out_excel = os.path.join(
                    out_dir, "Resultados_Cuantificacion.xlsx"
                )
                export_results_excel(
                    summary_df, events_df, coloc_df, stats_df, out_excel
                )
                generate_plots(summary_df, events_df, stats_df, out_dir)

                # Persistir los resultados en la sesión de Streamlit
                st.session_state["analyzed"] = True
                st.session_state["summary_df"] = summary_df
                st.session_state["events_df"] = events_df
                st.session_state["coloc_df"] = coloc_df
                st.session_state["stats_df"] = stats_df
                st.session_state["out_excel"] = out_excel

            st.balloons()

        # Renderizar vista si el análisis ya fue calculado
        if st.session_state.get("analyzed", False):
            st.success("¡Análisis comparativo disponible!")

            summary_df = st.session_state["summary_df"]
            events_df = st.session_state["events_df"]
            coloc_df = st.session_state["coloc_df"]
            stats_df = st.session_state["stats_df"]
            out_excel = st.session_state["out_excel"]
            out_dir = "data/processed"

            tab1, tab2, tab3 = st.tabs(
                [
                    "📊 Resumen & Estadística",
                    "📈 Gráficos de Dinámica",
                    "📋 Tablas Detalladas",
                ]
            )

            with tab1:
                st.subheader("Resumen Cuantitativo por Celda")
                st.dataframe(summary_df, use_container_width=True)

                if not stats_df.empty:
                    st.subheader(
                        "Comparaciones Estadísticas (Control vs. Tratamiento)"
                    )
                    st.dataframe(stats_df, use_container_width=True)

                fig1_p = os.path.join(
                    out_dir, "Figure1_Condition_Statistical_Comparisons.png"
                )
                if os.path.exists(fig1_p):
                    st.image(
                        fig1_p,
                        caption="Figura 1: Frecuencia de Fusión/Fisión, Conteo por Celda y Resumen Estadístico",
                    )
                    with open(fig1_p, "rb") as f:
                        st.download_button(
                            "📥 Descargar Figura 1 (PNG 300 DPI)",
                            f,
                            file_name="Figure1_Condition_Statistical_Comparisons.png",
                            mime="image/png",
                        )

            with tab2:
                fig2_p = os.path.join(
                    out_dir, "Figure2_Dynamics_and_Spatial_Map.png"
                )
                if os.path.exists(fig2_p):
                    st.image(
                        fig2_p,
                        caption="Figura 2: Distribución de Tiempos de Contacto, Distribución Temporal y Coordenadas Espaciales 2D",
                    )
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