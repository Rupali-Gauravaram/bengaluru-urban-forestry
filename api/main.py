import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from src import config

df = pd.read_csv(config.OUT_WARD_MASTER)

class Ward(BaseModel):
    Ward_Name: str
    Zone: str
    surface_temp: float
    urban_index: float
    veg_index: float
    water_index: float
    health_score: float
    city_rank: int

class Zone(BaseModel):
    Zone: str
    ward_count: int
    avg_health_score: float

app = FastAPI()

@app.get("/health", response_model=dict[str, str])
def health():
    return {"status":"ok"}

@app.get("/wards", response_model=list[Ward])
def wards():
    return df.to_dict(orient="records")

@app.get("/wards/rankings/top", response_model=list[Ward])
def top_n_wards(n: int = Query(default=10, ge=1, le=50)):
    sorted_df = df.sort_values('city_rank')
    return sorted_df.head(n).to_dict(orient="records")

@app.get("/wards/{ward_name}", response_model=Ward)
def get_ward_name(ward_name: str):
    match = df[df['Ward_Name'].str.lower() == ward_name.lower()]
    if match.empty:
        raise HTTPException(status_code=404, detail="Ward not found")
    return match.to_dict(orient="records")[0]

@app.get("/zones", response_model=list[Zone])
def get_zones():
    zone_summary = df.groupby('Zone').agg(ward_count=('Ward_Name','count'),avg_health_score=('health_score','mean'))
    zone_summary['avg_health_score'] = zone_summary['avg_health_score'].round(2)
    zone_summary = zone_summary.reset_index()
    return zone_summary.to_dict(orient="records")



