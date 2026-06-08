# Bengaluru Urban Forestry

A reproducible, containerised data pipeline that scores and ranks Bengaluru's
198 wards by environmental health and identifies candidate sites for "pocket
forests" — small, dense urban tree plantations targeted at the city's worst
heat-stress neighbourhoods.

The analysis began as exploratory Jupyter notebooks (kept in
[`notebooks/`](notebooks/) as documentation) and was refactored into a modular,
production-style Python pipeline that runs identically on any machine via Docker.

---

## Pipeline architecture

The project is a three-stage ETL/analytics pipeline:

```
                 ┌─────────────────────────┐
  IISc PDFs ───▶ │ 1. extract_trees        │ ─▶ tree palette / ward tree CSVs
                 └─────────────────────────┘
                 ┌─────────────────────────┐
 ward stat CSVs ▶│ 2. ward_health          │ ─▶ Environmental Health Score
   + LULC points │    (merge + z-score      │    + city-wide ward ranking
                 │     + weighted index)   │
                 └─────────────────────────┘
                 ┌─────────────────────────┐
   bare-land     │ 3. pocket_forests       │ ─▶ candidate planting sites
   coordinates ─▶│    (heat-priority +     │    inside the target ward
                 │     point-in-polygon)   │
                 └─────────────────────────┘
```

| Stage | Module | Input | Output |
|-------|--------|-------|--------|
| 1 | `src/extract_trees.py` | IISc tree PDFs | `Bengaluru_Tree_Palette.csv`, `Ward_wise_tree_details.csv`, `Annexure3_Prominent_Trees.csv` |
| 2 | `src/ward_health.py` | ward Temp/Urban/Veg/Water stats, LULC points | `Bengaluru_Ward_Master_Stats.csv`, `Processed_LULC_Points.csv` |
| 3 | `src/pocket_forests.py` | bare-land coordinates + ward geometry | candidate pocket-forest sites |

---

## Methodology — Environmental Health Score

Each ward is described by four remote-sensing drivers (Google Earth Engine,
2024–2025):

| Driver | Proxy | Effect on health |
|--------|-------|------------------|
| `surface_temp` | Land Surface Temperature (LST) | negative (heat stress) |
| `urban_index` | Built-up index (NDBI) | negative (impervious cover) |
| `veg_index` | Vegetation index (NDVI) | positive (canopy, cooling) |
| `water_index` | Water/moisture index (NDWI) | positive |

**Scoring method:**

1. **Standardise** each driver to a z-score (mean 0, sd 1). z-scores are used
   instead of min-max scaling because they are robust to single outliers and
   stable when the dataset is refreshed — a ward's score does not silently shift
   just because one extreme ward enters the data next year.
2. **Combine** the standardised drivers using *explicit, declared weights*
   (`config.HEALTH_WEIGHTS`) rather than an implicit sign convention buried in a
   formula. Weights are equal in magnitude by default and can be tuned in one
   place.
3. **Rescale** the composite to **0–100** so the score is interpretable to
   non-technical planners (higher = healthier).

Wards are then ranked (rank 1 = healthiest). Stage 3 uses the same z-score
discipline to compute a *heat-priority* index (`+temp +urban −veg`) and selects
the highest-priority ward in a target zone for pocket-forest siting, then runs a
point-in-polygon test to find bare-land parcels inside that ward.

**Validation.** Across the dataset, the healthiest 20 wards average ~3.5 °C
cooler and roughly twice the vegetation of the worst 20 — confirming the index
separates wards in the physically expected direction.

### Limitations

- The four drivers are weighted equally by default; this is a deliberate, stated
  value judgement, not a calibrated physical model. Reweight via
  `config.HEALTH_WEIGHTS` for sensitivity analysis.
- `urban_index` (NDBI) has a narrow raw spread in this dataset and therefore
  carries a relatively low signal-to-noise ratio.
- `surface_temp` is partly *driven by* vegetation and built-up cover, so the
  index intentionally reinforces the heat signal rather than treating the four
  drivers as fully independent.
- The score is a **relative** composite index for prioritisation, not an
  absolute, externally calibrated measure of environmental health.

---

## Project layout

```
.
├── src/
│   ├── config.py          # central paths + scoring weights (env-overridable)
│   ├── extract_trees.py   # Stage 1
│   ├── ward_health.py     # Stage 2
│   └── pocket_forests.py  # Stage 3
├── main.py                # orchestrator (run all stages, or one by name)
├── notebooks/             # original EDA notebooks (documentation)
├── data/                  # input CSVs / PDFs (mounted at run time)
├── output/                # pipeline writes results here
├── Dockerfile             # multi-stage build
├── requirements.txt       # pinned runtime deps
└── .github/workflows/     # CI: build + publish image to GHCR
```

---

## Running locally (without Docker)

```bash
pip install -r requirements.txt
python main.py                 # run the whole pipeline
python main.py ward_health     # run a single stage
```

Inputs are read from `data/` and results written to `output/` by default; both
are overridable via the `DATA_DIR` / `OUTPUT_DIR` environment variables.

### A note on data

The full ward-level datasets are the author's own work (derived from Google
Earth Engine and IISc sources) and are **not redistributed** in this repository.
A small **28-ward sample** lives in [`sample_data/`](sample_data/) so the
pipeline and Docker image run out-of-the-box on `git clone`. The code resolves
its input directory automatically: `DATA_DIR` env var → `data/` (if present) →
`sample_data/`. The full dataset is available from the author on request.

---

## Running with Docker

### Build

```bash
docker build -t bengaluru-forestry .
```

The [`Dockerfile`](Dockerfile) uses a **multi-stage build**: a *builder* stage
compiles dependencies (including the geospatial `shapely`/`libgeos` and
`pdfplumber` toolchains) into an isolated virtualenv, and a slim *runtime* stage
copies only that virtualenv plus the application code. Build tooling never
reaches the final image, which keeps it small (~187 MB content) and reduces its
attack surface. The container runs as a non-root `appuser`.

### Run

Mount your data in and your output back out so results persist after the
container exits:

```bash
docker run --rm \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/output:/app/output" \
  bengaluru-forestry            # add a stage name (e.g. ward_health) to run just one
```

On Windows PowerShell:

```powershell
docker run --rm `
  -v "${PWD}\data:/app/data" `
  -v "${PWD}\output:/app/output" `
  bengaluru-forestry ward_health
```

---

## Design notes

- **Notebook → script refactor.** The runnable artifact is a clean `src/`
  package, not a raw notebook. The notebooks remain as EDA documentation.
- **Reproducible builds.** Dependencies are pinned to the exact versions used in
  development, and dependency install is layered *before* the code copy so the
  expensive `pip install` layer caches across code edits.
- **Cross-platform correctness.** All file paths are resolved centrally in
  `config.py`, avoiding the case-insensitive-Windows vs. case-sensitive-Linux
  filename mismatch that would otherwise crash the pipeline inside a container.
- **CI/CD.** Every push builds the image; pushes to `main` and version tags
  publish it to the GitHub Container Registry.

---

## Data sources

Ward-level statistics are derived from Google Earth Engine (LST, NDVI, NDWI,
NDBI) for Bengaluru (2024–2025). Tree palette and species data are extracted
from IISc's *CES_TVR_ETR75* technical reports.
