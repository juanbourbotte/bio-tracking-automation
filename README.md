# 🔬 Automated Vesicle Tracking & Bio-Image Analytics Pipeline

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-red.svg)](https://streamlit.io/)

Una plataforma interactiva de análisis bioinformático diseñada para procesar, cuantificar y visualizar dinámicas de colocalización, fusión y fisión de vesículas a partir de datos de seguimiento (*tracking*) obtenidos por microscopía de fluorescencia.

---

## 🌟 Características Clave

* **Adaptabilidad de Marcadores:** Configura dinámicamente los nombres de las poblaciones o proteínas a comparar (ej. Cav1, EEA1, Rab5, Clatrina) desde la interfaz sin modificar el código.
* **Mapeo Inteligente e Interactivo de Columnas:** Detecta automáticamente las columnas estándar de herramientas de tracking (TrackMate, ImageJ, Imaris, Volocity) o permite un mapeo manual intuitivo mediante menús desplegables.
* **Calibración Espacio-Temporal en Tiempo Real:** Ajusta el paso de tiempo ($\Delta t$), el tamaño de píxel ($\mu\text{m/px}$) y el área celular de normalización desde la barra lateral.
* **Procesamiento de Datos Múltiples:** Soporta la carga simultánea de múltiples archivos Excel/CSV reconociendo condiciones experimentales (Control vs. Tratamiento).
* **Reportes y Gráficos Listos para Publicación:**
  * Generación automática de reportes en Excel multi-pestaña (`.xlsx`).
  * Exportación de figuras compuestas en alta resolución (**300 DPI**, formato PNG) con gráficos de caja, diagramas de dispersión y mapas espaciales 2D.
* **Carga de Datos de Prueba (1-Clic):** Incluye un conjunto de datos sintéticos realistas en `sample_data/` para probar la aplicación de inmediato.

---

## 🏗️ Arquitectura del Proyecto

```text
bio-tracking-automation/
├── app.py                   # Interfaz de usuario interactiva en Streamlit
├── Dockerfile               # Configuración para ejecución en contenedor
├── LICENSE                  # Licencia de código abierto MIT
├── README.md                # Documentación del repositorio
├── requirements.txt         # Lista de dependencias de Python
├── sample_data/             # Archivos Excel de prueba precargados
└── src/
    ├── config.py            # Parámetros espacio-temporales por defecto
    ├── ingestion.py         # Mapeo de columnas, validación y filtrado de datos
    ├── pipeline.py          # Algoritmos vectorizados de colocalización, fusión y fisión
    ├── reporting.py         # Generación de reportes Excel y figuras a 300 DPI
    └── stats_engine.py      # Motor de pruebas estadísticas (Mann-Whitney U, t-test)
