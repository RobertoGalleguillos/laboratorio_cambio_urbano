from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from config import PROCESSED_DIR, VECTOR_DIR


@dataclass
class DataPaths:
    stats_csv: Path = PROCESSED_DIR / "estadisticas_cambio.csv"
    indices_stats_csv: Path = PROCESSED_DIR / "estadisticas_indices.csv"
    indices_pattern: str = "indices_*.tif"
    zones_shp: Path = VECTOR_DIR / "manzanas_censales.shp"
    boundary_gpkg: Path = VECTOR_DIR / "limite_comuna.gpkg"


def list_index_years(processed_dir: Path, pattern: str = "indices_*.tif") -> list[int]:
    years: list[int] = []
    for tif in processed_dir.glob(pattern):
        stem = tif.stem
        parts = stem.split("_")
        if parts and parts[-1].isdigit():
            years.append(int(parts[-1]))
    return sorted(set(years))


def load_stats(paths: DataPaths) -> pd.DataFrame:
    df = pd.read_csv(paths.stats_csv)
    if "zona" in df.columns:
        df["zona"] = df["zona"].astype(str).str.strip()
    return df


def load_indices_stats(paths: DataPaths) -> pd.DataFrame:
    df = pd.read_csv(paths.indices_stats_csv)
    if df.columns[0] == "" or str(df.columns[0]).lower().startswith("unnamed"):
        df = df.rename(columns={df.columns[0]: "fecha"})
    if "fecha" not in df.columns:
        df = df.reset_index().rename(columns={"index": "fecha"})
    # Asegura que la columna de año sea la correcta (2018, 2020, etc.)
    def _is_year_series(series: pd.Series) -> bool:
        values = pd.to_numeric(series, errors="coerce").dropna()
        if values.empty:
            return False
        return bool(((values >= 1900) & (values <= 2100)).all())

    if "fecha" in df.columns and not _is_year_series(df["fecha"]):
        for col in df.columns:
            if col != "fecha" and _is_year_series(df[col]):
                df = df.rename(columns={col: "fecha"})
                break

    df["fecha"] = pd.to_numeric(df["fecha"], errors="ignore").astype(str)
    return df


def read_zones(paths: DataPaths):
    import geopandas as gpd

    zones = gpd.read_file(paths.zones_shp) if paths.zones_shp.exists() else None
    boundary = gpd.read_file(paths.boundary_gpkg) if paths.boundary_gpkg.exists() else None
    return zones, boundary


def detect_join_column(stats: pd.DataFrame, zones) -> str | None:
    if stats is None or zones is None or stats.empty or zones.empty:
        return None
    if "zona" not in stats.columns:
        return None
    stats_vals = stats["zona"].astype(str).str.strip()
    stats_set = set(stats_vals.head(200).tolist())
    best_col = None
    best_ratio = 0.0
    for col in zones.columns:
        if col == zones.geometry.name:
            continue
        col_vals = zones[col].astype(str).str.strip()
        zone_set = set(col_vals.head(1000).tolist())
        if not zone_set:
            continue
        matches = len(stats_set.intersection(zone_set))
        ratio = matches / max(len(stats_set), 1)
        if ratio > best_ratio:
            best_ratio = ratio
            best_col = col
    return best_col if best_ratio >= 0.2 else None


def join_stats(zones, stats: pd.DataFrame, join_col: str | None):
    if zones is None or stats is None or join_col is None:
        return zones
    stats = stats.copy()
    stats["zona"] = stats["zona"].astype(str).str.strip()
    zones = zones.copy()
    zones[join_col] = zones[join_col].astype(str).str.strip()
    return zones.merge(stats, left_on=join_col, right_on="zona", how="left")


def raster_to_rgb(path: Path):
    import rasterio
    from matplotlib import cm

    if not path.exists():
        return None
    with rasterio.open(path) as src:
        band = src.read(1).astype("float32")
        nodata = src.nodata
    if nodata is not None:
        band = np.where(band == nodata, np.nan, band)
    finite = band[np.isfinite(band)]
    if finite.size == 0:
        return None
    vmin, vmax = np.percentile(finite, [2, 98])
    if vmin == vmax:
        vmin, vmax = float(np.nanmin(band)), float(np.nanmax(band))
    if vmin == vmax:
        return None
    scaled = np.clip((band - vmin) / (vmax - vmin), 0, 1)
    rgba = cm.viridis(scaled)
    rgb = (rgba[:, :, :3] * 255).astype("uint8")
    return rgb
