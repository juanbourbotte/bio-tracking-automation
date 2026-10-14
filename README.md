# 🔬 Automated Vesicle Tracking & Bio-Image Analytics Pipeline

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-red.svg)](https://streamlit.io/)

An open-source, interactive bio-image analytics platform designed to process, quantify, and visualize vesicle colocalization, fusion, and fission dynamics from time-lapse fluorescence microscopy tracking data.

---

## 🌟 Key Features

* **Flexible Marker & Channel Selection:** Dynamically define protein or vesicle population labels (e.g., Cav1, EEA1, Rab5, Rab7, Clathrin) directly from the UI without modifying source code.
* **Smart & Interactive Column Mapping:** Automatically recognizes column naming conventions from major tracking software (TrackMate, ImageJ, Imaris, Volocity) or provides interactive fallback dropdowns for custom headers.
* **Real-Time Spatiotemporal Calibration:** Adjust time interval ($\Delta t$), spatial scaling ($\mu\text{m/px}$), and cell reference area ($\mu\text{m}^2$) via sidebar controls.
* **Multi-Condition Processing:** Seamlessly handles multiple file uploads, automatically inferring experimental conditions (e.g., Control vs. Treatment).
* **Publication-Ready Outputs:**
  * Multi-sheet Excel summary report (`.xlsx`).
  * High-resolution composite figures (**300 DPI**, PNG) including boxplots, duration distributions, and 2D spatial event maps.
* **1-Click Sample Data Demo:** Pre-loaded with synthetic, scientifically realistic tracking datasets in `sample_data/` for immediate testing.

---

## 🏗️ Repository Architecture

```text
bio-tracking-automation/
├── app.py                   # Streamlit web interface & session orchestration
├── Dockerfile               # Containerization build file for scientific deployments
├── HOW_TO_EXECUTE.md        # Step-by-step setup and execution guide
├── LICENSE                  # MIT Open Source License
├── README.md                # Main documentation
├── requirements.txt         # Python dependencies
├── sample_data/             # Pre-loaded sample datasets
└── src/
    ├── config.py            # Default spatiotemporal parameters
    ├── ingestion.py         # File ingestion, column mapping, and population filtering
    ├── pipeline.py          # Vectorized spatial colocalization, fusion, and fission logic
    ├── reporting.py         # Excel exporter and 300 DPI plot generator
    └── stats_engine.py      # Statistical analysis engine (Mann-Whitney U, t-test)