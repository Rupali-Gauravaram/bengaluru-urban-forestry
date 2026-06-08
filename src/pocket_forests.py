"""
Stage 3 — Pocket Forest siting.

Refactored from `Pocket Forests EDA.ipynb`. Identifies the highest heat-stress
ward in the Dasarahalli zone, then uses a point-in-polygon test to find bare
land parcels physically inside that ward as candidate pocket-forest sites.

(The original notebook's interactive matplotlib/seaborn plots are EDA only and
are intentionally left in the notebook, not ported into the batch pipeline.)
"""
import json

import pandas as pd
from sklearn.preprocessing import StandardScaler
from shapely.geometry import shape, Point

from . import config


def _load_ward_frame() -> pd.DataFrame:
    """Rebuild the merged ward frame (keeping `.geo` for geometry tests)."""
    df_temp = pd.read_csv(config.WARD_TEMP)[["Ward_Name", "Zone", "mean", ".geo"]].rename(
        columns={"mean": "surface_temp"}
    )
    df_urban = pd.read_csv(config.WARD_URBAN)[["Ward_Name", "mean"]].rename(
        columns={"mean": "urban_index"}
    )
    df_veg = pd.read_csv(config.WARD_VEG)[["Ward_Name", "mean"]].rename(
        columns={"mean": "veg_index"}
    )
    df_water = pd.read_csv(config.WARD_WATER)[["Ward_Name", "mean"]].rename(
        columns={"mean": "water_index"}
    )

    df = (
        df_temp.merge(df_urban, on="Ward_Name")
        .merge(df_veg, on="Ward_Name")
        .merge(df_water, on="Ward_Name")
    )
    df["Zone"] = df["Zone"].str.strip()
    return df


def find_target_ward(df: pd.DataFrame, zone: str = "Dasarahalli") -> pd.Series:
    """Pick the highest heat-priority ward within a zone.

    Heat priority targets hot, dense, vegetation-poor wards:
        +surface_temp  +urban_index  -veg_index

    All three drivers are standardised to z-scores FIRST so they are directly
    comparable. (The original notebook normalised only temperature and added raw
    urban/veg values, which let temperature dominate the ranking ~10x — a
    scale-mixing bug now fixed here.)
    """
    subset = df[df["Zone"] == zone].copy()
    if subset.empty:
        raise ValueError(f"No wards found in zone {zone!r}.")

    drivers = ["surface_temp", "urban_index", "veg_index"]
    z = pd.DataFrame(
        StandardScaler().fit_transform(subset[drivers]),
        columns=drivers,
        index=subset.index,
    )
    subset["heat_priority"] = z["surface_temp"] + z["urban_index"] - z["veg_index"]

    target = subset.sort_values("heat_priority", ascending=False).iloc[0]
    print(f"[pocket_forests] Target ward for pocket forest: {target['Ward_Name']}")
    return target


def find_planting_sites(target_ward: pd.Series) -> pd.DataFrame:
    """Find bare-land points inside the target ward's boundary polygon."""
    bare_land = pd.read_csv(config.BARE_LAND)
    ward_polygon = shape(json.loads(target_ward[".geo"]))

    def is_inside(row) -> bool:
        coords = json.loads(row[".geo"])["coordinates"]
        return ward_polygon.contains(Point(coords[0], coords[1]))

    sites = bare_land[bare_land.apply(is_inside, axis=1)]
    print(
        f"[pocket_forests] Found {len(sites)} potential pocket forest sites "
        f"in {target_ward['Ward_Name']}."
    )
    return sites


def run() -> pd.DataFrame:
    """Execute the full Stage 3 pipeline and return candidate planting sites."""
    config.ensure_output_dir()
    df = _load_ward_frame()
    target = find_target_ward(df)
    return find_planting_sites(target)


if __name__ == "__main__":
    run()
