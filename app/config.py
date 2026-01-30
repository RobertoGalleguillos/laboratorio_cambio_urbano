from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
VECTOR_DIR = DATA_DIR / "vector"
OUTPUTS_DIR = ROOT_DIR / "outputs"

APP_TITLE = "Análisis de Cambio Urbano"
APP_ICON = None
