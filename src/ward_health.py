"""
Stage 2 — Ward Environmental Health Score & Ranking.

Refactored from `Prescriptive Urban Forestry.ipynb`. Reads the four ward-level
stat CSVs, merges them, computes a normalised Environmental Health Score, and
ranks every ward (rank 1 = healthiest). Also extracts lat/long from the GEE
`.geo` column of the LULC points file.
"""
import json

import pandas as pd
from sklearn.preprocessing import StandardScaler

from . import config


def preprocess_lulc() -> pd.DataFrame:
    """Extract longitude/latitude from the GEE `.geo` JSON strings."""
    df = pd.read_csv(config.LULC_POINTS)

    def extract_coords(geo_str):
        try:
            geo_dict = json.loads(geo_str)
            return pd.Series(geo_dict["coordinates"])
        except (json.JSONDecodeError, TypeError, KeyError):
            return pd.Series([None, None])

    df[["longitude", "latitude"]] = df[".geo"].apply(extract_coords)
    df.to_csv(config.OUT_PROCESSED_LULC, index=False)
    print(f"[ward_health] LULC coordinates extracted -> {config.OUT_PROCESSED_LULC.name}")
    return df


def _merge_ward_stats() -> pd.DataFrame:
    """Merge the four ward-stat CSVs, validating that no ward is silently lost.

    An inner merge would quietly drop wards missing from any single file. We
    instead track the ward set per source and warn on any mismatch so data-
    quality problems surface rather than vanish.
    """
    sources = {
        "surface_temp": (config.WARD_TEMP, ["Ward_Name", "Zone", "mean"]),
        "urban_index": (config.WARD_URBAN, ["Ward_Name", "mean"]),
        "veg_index": (config.WARD_VEG, ["Ward_Name", "mean"]),
        "water_index": (config.WARD_WATER, ["Ward_Name", "mean"]),
    }

    frames = {}
    ward_sets = {}
    for new_col, (path, cols) in sources.items():
        df = pd.read_csv(path)[cols].rename(columns={"mean": new_col})
        frames[new_col] = df
        ward_sets[new_col] = set(df["Ward_Name"])

    all_wards = set.union(*ward_sets.values())
    common_wards = set.intersection(*ward_sets.values())
    if len(common_wards) < len(all_wards):
        dropped = sorted(all_wards - common_wards)
        print(
            f"[ward_health] WARNING: {len(dropped)} ward(s) missing from one or "
            f"more inputs and will be dropped: {dropped}"
        )

    master_df = frames["surface_temp"]
    for col in ("urban_index", "veg_index", "water_index"):
        master_df = master_df.merge(frames[col], on="Ward_Name", how="inner")
    return master_df


def consolidate_ward_data() -> pd.DataFrame:
    """Merge ward stats and compute the Environmental Health Score + ranking.

    Method:
      1. Standardise each driver to a z-score (mean 0, sd 1). Unlike min-max,
         z-scores are robust to single outliers and stable when new data is
         added, so a ward's score does not silently shift when the dataset is
         updated next year.
      2. Combine drivers with explicit, declared weights (config.HEALTH_WEIGHTS)
         rather than an implicit 1:1:1:1 sign convention buried in a formula.
      3. Rescale the composite to 0-100 (config.HEALTH_SCORE_RANGE) so the score
         is interpretable to non-technical planners (higher = healthier).
    """
    master_df = _merge_ward_stats()

    cols = list(config.HEALTH_WEIGHTS)
    scaler = StandardScaler()
    z = pd.DataFrame(scaler.fit_transform(master_df[cols]), columns=cols, index=master_df.index)

    # Weighted sum of standardised drivers (signs live in HEALTH_WEIGHTS).
    composite = sum(z[col] * weight for col, weight in config.HEALTH_WEIGHTS.items())

    rng = config.HEALTH_SCORE_RANGE
    if rng is not None:
        lo, hi = composite.min(), composite.max()
        scaled = (composite - lo) / (hi - lo) if hi > lo else composite * 0
        master_df["health_score"] = (scaled * (rng[1] - rng[0]) + rng[0]).round(2)
    else:
        master_df["health_score"] = composite

    master_df["city_rank"] = master_df["health_score"].rank(ascending=False).astype(int)
    master_df = master_df.sort_values("city_rank")

    master_df.to_csv(config.OUT_WARD_MASTER, index=False)
    print(
        f"[ward_health] Ward health rankings calculated ({len(master_df)} wards) "
        f"-> {config.OUT_WARD_MASTER.name}"
    )
    return master_df


def get_neighbourhood_report(ward_name: str, master_df: pd.DataFrame):
    """Look up a single ward's current status."""
    ward_data = master_df[master_df["Ward_Name"].str.lower() == ward_name.lower()]
    if ward_data.empty:
        return "Ward not found."
    return ward_data.to_dict(orient="records")[0]


def get_plot_prescription(plot_size_sqft: float, num_storeys: int) -> dict:
    """Architectural greening interventions based on Bengaluru standards."""
    min_green_cover = plot_size_sqft * 0.15

    if num_storeys >= 4:
        roof_rec = "High Density: 60% of terrace must be intensive green roof."
    else:
        roof_rec = "Low/Mid Density: 30% of terrace area for kitchen garden/green roof."

    # Rainwater harvesting: 20 L per square metre of roof (1 sqft = 0.0929 sqm).
    rwh_tank_capacity = (plot_size_sqft * 0.0929) * 20

    return {
        "Min Ground Green Cover (sqft)": round(min_green_cover, 2),
        "Roof Target": roof_rec,
        "Est. RWH Tank Size (Liters)": round(rwh_tank_capacity, 2),
        "Vertical Greening": "Required on South/West walls"
        if num_storeys > 2
        else "Recommended",
    }


def run() -> pd.DataFrame:
    """Execute the full Stage 2 pipeline and return the ranked master frame."""
    config.ensure_output_dir()
    preprocess_lulc()
    master_stats = consolidate_ward_data()

    # Example usage mirroring the original notebook's __main__ demo.
    report = get_neighbourhood_report("Halsoor", master_stats)
    if isinstance(report, dict):
        print("\n--- NEIGHBOURHOOD REPORT ---")
        print(f"Ward: {report['Ward_Name']} | City Rank: {report['city_rank']} / 198")
        print(f"Health Score: {round(report['health_score'], 2)}")

    print("\n--- PLOT PRESCRIPTION (1200 sqft, 3 storeys) ---")
    for key, value in get_plot_prescription(1200, 3).items():
        print(f"{key}: {value}")

    return master_stats


if __name__ == "__main__":
    run()
