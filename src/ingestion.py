import os
import io
import pandas as pd

# Mapeo canónico de nombres de columna comunes
CANONICAL_COL_MAP = {
    "X position": "POSITION_X", "X_position": "POSITION_X", "X": "POSITION_X", "x": "POSITION_X", "Position X": "POSITION_X",
    "Y position": "POSITION_Y", "Y_position": "POSITION_Y", "Y": "POSITION_Y", "y": "POSITION_Y", "Position Y": "POSITION_Y",
    "Track ID": "TRACK_ID",     "Track_ID": "TRACK_ID",     "Track": "TRACK_ID", "track_id": "TRACK_ID", "TRACK_ID": "TRACK_ID",
    "Frame": "FRAME",           "frame": "FRAME",           "FRAME": "FRAME",    "Time position(s)": "TIME", "Time_s": "TIME",
    "Cell_ID": "CELL_ID",       "Cell": "CELL_ID",          "Cell ID": "CELL_ID", "cell": "CELL_ID",
    "Population": "POPULATION", "Protein": "POPULATION",    "Channel": "POPULATION", "population": "POPULATION", "protein": "POPULATION",
    "Condition": "CONDITION",  "Treatment": "CONDITION",   "Trat": "CONDITION", "Group": "CONDITION", "condition": "CONDITION"
}

# Columnas obligatorias para ejecutar el análisis
REQUIRED_CANONICAL = ["POSITION_X", "POSITION_Y", "TRACK_ID", "FRAME", "POPULATION"]

LABELS_MAP = {
    "POSITION_X": "Coordenada X (Posición X)",
    "POSITION_Y": "Coordenada Y (Posición Y)",
    "TRACK_ID": "Identificador de Trayectoria (Track ID)",
    "FRAME": "Cuadro / Fotograma (Frame)",
    "POPULATION": "Población / Canal / Proteína"
}

def infer_condition_from_filename(filename):
    """Infiere la condición experimental basándose en palabras clave del nombre del archivo."""
    base_name = str(filename).lower()
    if any(k in base_name for k in ["tgf", "beta", "trat", "treatment", "tgfbeta"]):
        return "TGFbeta"
    elif any(k in base_name for k in ["ctrl", "control", "wt", "untreated"]):
        return "Control"
    else:
        clean_name = os.path.splitext(os.path.basename(base_name))[0]
        return clean_name if clean_name else "Control"

def read_raw_dataframe(file_or_path):
    """Lee el DataFrame crudo desde ruta, BytesIO u UploadedFile."""
    if isinstance(file_or_path, str):
        if file_or_path.endswith('.csv'):
            df_raw = pd.read_csv(file_or_path)
        else:
            excel_file = pd.ExcelFile(file_or_path)
            df_raw = pd.read_excel(excel_file, sheet_name=excel_file.sheet_names[0])
    else:
        file_name = getattr(file_or_path, 'name', 'dataset.xlsx')
        if hasattr(file_or_path, 'seek'):
            file_or_path.seek(0)
        if file_name.lower().endswith('.csv'):
            df_raw = pd.read_csv(file_or_path)
        else:
            df_raw = pd.read_excel(file_or_path, sheet_name=0)
            
    df_raw.columns = [str(c).strip() for c in df_raw.columns]
    return df_raw

def inspect_columns(df_raw, custom_col_map=None):
    """Aplica el mapeo estándar y/o personalizado e identifica columnas obligatorias faltantes."""
    col_map = CANONICAL_COL_MAP.copy()
    if custom_col_map:
        # Invertir custom_col_map: {col_original: col_canonica}
        inv_custom = {v: k for k, v in custom_col_map.items() if v}
        col_map.update(inv_custom)

    df_mapped = df_raw.rename(columns=col_map).copy()
    missing = [c for c in REQUIRED_CANONICAL if c not in df_mapped.columns]
    return df_mapped, missing

def load_vertical_excel(file_or_path, default_condition=None, channel_a="Cav1", channel_b="EEA1", custom_col_map=None):
    """Carga y procesa el DataFrame aplicando mapeos personalizados y filtros de población."""
    df_raw = read_raw_dataframe(file_or_path)
    df, missing = inspect_columns(df_raw, custom_col_map=custom_col_map)

    if missing:
        raise ValueError(f"No se pudieron encontrar las columnas requeridas: {missing}")

    file_name = file_or_path if isinstance(file_or_path, str) else getattr(file_or_path, 'name', 'dataset.xlsx')
    inferred = default_condition if default_condition else infer_condition_from_filename(file_name)

    if "CONDITION" not in df.columns or df["CONDITION"].isnull().all():
        df["CONDITION"] = inferred
    else:
        df["CONDITION"] = df["CONDITION"].astype(str).str.strip()
        df["CONDITION"] = df["CONDITION"].apply(
            lambda x: "TGFbeta" if any(k in str(x).lower() for k in ["tgf", "beta"])
            else ("Control" if any(k in str(x).lower() for k in ["ctrl", "control"]) else (inferred if x in ["", "nan", "None"] else x))
        )

    df_a = df[df["POPULATION"].astype(str).str.contains(channel_a, case=False, na=False)].copy()
    df_b = df[df["POPULATION"].astype(str).str.contains(channel_b, case=False, na=False)].copy()

    return df_a, df_b

def clean_trackmate_df(df):
    """Valida tipos de datos numéricos y remueve coordenadas incompletas."""
    if df.empty:
        return pd.DataFrame()

    required_cols = ["POSITION_X", "POSITION_Y", "TRACK_ID", "FRAME"]
    for c in required_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=[c for c in required_cols if c in df.columns])
    df["FRAME"] = df["FRAME"].astype(int)
    df["TRACK_ID"] = df["TRACK_ID"].astype(int)

    if "CELL_ID" not in df.columns:
        df["CELL_ID"] = 1
    else:
        df["CELL_ID"] = pd.to_numeric(df["CELL_ID"], errors="coerce").fillna(1).astype(int)

    if "CONDITION" not in df.columns:
        df["CONDITION"] = "Control"

    return df