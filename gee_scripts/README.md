# Google Earth Engine scripts

These JavaScript scripts run in the [Google Earth Engine Code Editor](https://code.earthengine.google.com/)
and produced the remote-sensing inputs used by the pipeline. They document the
**provenance** of the ward-level datasets.

| Script | Produces |
|--------|----------|
| `01_lst_heatmap.js` | Land Surface Temperature (Landsat 8 ST_B10, 2024–2025) per ward — source of `surface_temp` |
| `02_lulc_bareland_points.js` | LULC classification + bare-land coordinate points — source of the LULC and bare-land CSVs |

They are not run by the Python pipeline; they are the upstream data-generation
step, included here for reproducibility and transparency.
