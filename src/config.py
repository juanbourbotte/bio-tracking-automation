# Parámetros por defecto para la cuantificación espacio-temporal
DISTANCE_THRESHOLD = 0.3   # Distancia máxima entre centroides (µm)
MIN_COLOC_FRAMES   = 3     # Frames mínimos consecutivos de contacto
MAX_FRAME_GAP      = 1     # Parpadeo/flicker permitido durante contacto
TIME_INTERVAL_SEC  = 1.0   # Intervalo entre frames en segundos
PIXEL_SIZE_UM      = 1.0   # Factor de escala (1.0 si ya está en µm)
CELL_AREA_UM2      = 500.0 # Área celular para normalización (µm²)