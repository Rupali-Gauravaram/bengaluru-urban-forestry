"""
Central configuration for the Bengaluru Urban Forestry pipeline.

Paths are resolved relative to the project root and can be overridden with
environment variables so the same code runs unchanged on a laptop or inside a
container (where data is mounted at /app/data and output at /app/output).
"""
from pathlib import Path
import os

# Project root = parent of this file's directory (src/)
ROOT = Path(__file__).resolve().parent.parent

# Input data directory. Resolution order:
#   1. DATA_DIR env var (set explicitly, e.g. mounted in Docker)
#   2. ./data       — the author's full private dataset (gitignored)
#   3. ./sample_data — a small committed sample so the repo runs out-of-the-box
if os.environ.get("DATA_DIR"):
    DATA_DIR = Path(os.environ["DATA_DIR"])
elif (ROOT / "data").exists():
    DATA_DIR = ROOT / "data"
else:
    DATA_DIR = ROOT / "sample_data"

OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", ROOT / "output"))

# --- Input files (Stage 2 / 3) ---
LULC_POINTS = DATA_DIR / "Bengaluru_All_LULC_Points_2024_2025.csv"
WARD_TEMP = DATA_DIR / "Bengaluru_Ward_Temp_Stats.csv"
WARD_URBAN = DATA_DIR / "Bengaluru_Ward_Urban_Stats.csv"
WARD_VEG = DATA_DIR / "Bengaluru_Ward_Veg_Stats.csv"
WARD_WATER = DATA_DIR / "Bengaluru_Ward_Water_Stats.csv"
BARE_LAND = DATA_DIR / "Bare_Land_Coordinates_for_ML.csv"

# --- Input files (Stage 1, PDFs) ---
PDF_ANNEXURE5 = DATA_DIR / "annexure5.pdf"
PDF_CES_FULL = DATA_DIR / "CES_TVR_ETR75_TREES_24may2014.pdf"
PDF_CES_EXTRACT = DATA_DIR / "CES_TVR_ETR75_TREES_24may2014 Extract[38-48].pdf"

# --- Output files ---
OUT_PROCESSED_LULC = OUTPUT_DIR / "Processed_LULC_Points.csv"
OUT_WARD_MASTER = OUTPUT_DIR / "Bengaluru_Ward_Master_Stats.csv"
OUT_TREE_PALETTE = OUTPUT_DIR / "Bengaluru_Tree_Palette.csv"
OUT_WARD_TREES = OUTPUT_DIR / "Ward_wise_tree_details.csv"
OUT_PROMINENT_TREES = OUTPUT_DIR / "Annexure3_Prominent_Trees.csv"


def ensure_output_dir() -> None:
    """Create the output directory if it does not exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Environmental Health Score configuration
# ---------------------------------------------------------------------------
# Explicit, declared weights for each standardised driver. Positive weights are
# "good" (raise the score); negative weights are "bad" (lower it). Equal
# magnitudes encode an explicit 1:1:1:1 value judgement that can be tuned here
# rather than being implicit in the formula. Edit these to reweight the index.
HEALTH_WEIGHTS = {
    "veg_index": +1.0,      # vegetation cover — protective
    "water_index": +1.0,    # surface water / moisture — protective
    "surface_temp": -1.0,   # land surface temperature — heat stress
    "urban_index": -1.0,    # built-up density — heat / impervious cover
}

# Final score is rescaled to this range so it is interpretable to planners
# (higher = healthier). Set to None to keep the raw standardised composite.
HEALTH_SCORE_RANGE = (0, 100)
