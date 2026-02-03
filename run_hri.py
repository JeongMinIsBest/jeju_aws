# ============================================================
# FINAL: OISST → Jeju SST(T_t) → HRI → Level Mapping → JSON Export
#
# HRI_t = α*max(0, T_t - T_base) + β*ln(D_con+1) + γ*V_var
# where:
#   T_base = 28.0℃
#   D_con  = consecutive days with T_t >= 28℃
#   V_var  = |T_t - T_{t-1}|
#
# Level mapping (policy-friendly):
#   NORMAL : T_t < 28
#   WATCH  : T_t >= 28 and D_con < 3          (예비/관심 단계)
#   WARNING: D_con >= 3 and T_t < 30          (경보 기준 충족)
#   SEVERE : D_con >= 3 and T_t >= 30         (치명 구간)
#
# Outputs:
#   outputs/oisst_jeju_hri.csv
#   outputs/trigger_events.json
#   outputs/final_alert_event.json
# ============================================================

import os
import json
from datetime import datetime, timedelta
from urllib.request import urlretrieve

import numpy as np
import pandas as pd
import xarray as xr


# -----------------------------
# 0) SETTINGS (edit only here)
# -----------------------------
DATA_DIR = r"D:\oisst_nc"     # OISST 파일 저장 폴더

START_DATE = "2024-07-20"
END_DATE   = "2024-10-05"

# Jeju ROI (OISST 0.25° grid -> 넉넉하게)
JEJU_LAT_MIN, JEJU_LAT_MAX = 32.0, 35.0
JEJU_LON_MIN, JEJU_LON_MAX = 124.0, 129.0

# HRI params
T_BASE = 28.0
ALPHA, BETA, GAMMA = 1.0, 0.8, 0.5

# Trigger threshold (policy-tunable)
HRI_THRESHOLD = 3.0

# Severe threshold (domain-tunable, "30도 위험" 스토리용)
SEVERE_TEMP = 30.0

# Domain/meta
REGION_ID = "JEJU_OFFSHORE"
DATASET_NAME = "NOAA OISST v2.1 AVHRR daily (0.25deg)"
MODEL_VERSION = "hri-v1.1-levels"

# NOAA OISST v2.1 daily file URL pattern
# File: oisst-avhrr-v02r01.YYYYMMDD.nc
OISST_URL_TEMPLATE = (
    "https://www.ncei.noaa.gov/data/sea-surface-temperature-optimum-interpolation/v2.1/access/avhrr/"
    "{year}{month}/oisst-avhrr-v02r01.{yyyymmdd}.nc"
)

# Output paths
OUT_DIR = "outputs"
OUT_HRI_CSV = os.path.join(OUT_DIR, "oisst_jeju_hri.csv")
OUT_TRIGGER_LIST_JSON = os.path.join(OUT_DIR, "trigger_events.json")
OUT_FINAL_EVENT_JSON = os.path.join(OUT_DIR, "final_alert_event.json")


# -----------------------------
# 1) Utilities
# -----------------------------
def daterange(start: datetime, end: datetime):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def ensure_oisst_file(day: datetime):
    """Download daily OISST file if missing; return local path or None."""
    yyyymmdd = day.strftime("%Y%m%d")
    year = day.strftime("%Y")
    month = day.strftime("%m")

    os.makedirs(DATA_DIR, exist_ok=True)
    local_path = os.path.join(DATA_DIR, f"oisst-avhrr-v02r01.{yyyymmdd}.nc")

    if os.path.exists(local_path):
        return local_path

    url = OISST_URL_TEMPLATE.format(year=year, month=month, yyyymmdd=yyyymmdd)
    print(f"[DL] {yyyymmdd} -> {url}")
    try:
        urlretrieve(url, local_path)
        return local_path
    except Exception as e:
        print(f"[WARN] download failed for {yyyymmdd}: {e}")
        return None


def compute_jeju_mean_sst(nc_path: str) -> float:
    """Read OISST NetCDF and compute ROI mean SST (degC)."""
    ds = xr.open_dataset(nc_path)

    if "sst" not in ds:
        ds.close()
        raise ValueError(f"'sst' variable not found. data_vars={list(ds.data_vars)}")

    sst = ds["sst"]
    lat = ds["lat"] if "lat" in ds.coords else ds["latitude"]
    lon = ds["lon"] if "lon" in ds.coords else ds["longitude"]

    sst_roi = sst.where(
        (lat >= JEJU_LAT_MIN) & (lat <= JEJU_LAT_MAX) &
        (lon >= JEJU_LON_MIN) & (lon <= JEJU_LON_MAX),
        drop=True
    )

    val = float(sst_roi.mean(skipna=True).values)
    ds.close()
    return val


def risk_level_from_T_D(T_t: float, D_con: int) -> str:
    """Policy-friendly level mapping using official-like thresholds."""
    if not np.isfinite(T_t):
        return "UNKNOWN"
    if T_t < T_BASE:
        return "NORMAL"
    # T_t >= 28
    if D_con < 3:
        return "WATCH"
    # D_con >= 3 => (72h satisfied)
    if T_t < SEVERE_TEMP:
        return "WARNING"
    return "SEVERE"


def build_hri(df_daily: pd.DataFrame) -> pd.DataFrame:
    """Compute D_con, V_var, HRI, trigger, level for daily dataframe."""
    df = df_daily.copy().sort_values("date").reset_index(drop=True)

    # D_con: consecutive days with T_t >= T_BASE
    streak = 0
    dcon = []
    for t in df["T_t"].values:
        if np.isfinite(t) and t >= T_BASE:
            streak += 1
        else:
            streak = 0
        dcon.append(streak)
    df["D_con"] = dcon

    # V_var: |T_t - T_{t-1}|
    df["V_var"] = df["T_t"].diff().abs().fillna(0.0)

    # HRI formula (exact)
    df["HRI"] = (
        ALPHA * np.maximum(0.0, df["T_t"] - T_BASE)
        + BETA * np.log(df["D_con"] + 1.0)
        + GAMMA * df["V_var"]
    )

    # Trigger (binary)
    df["trigger"] = df["HRI"] >= HRI_THRESHOLD

    # Level mapping (NORMAL/WATCH/WARNING/SEVERE)
    df["level"] = [
        risk_level_from_T_D(t, int(d))
        for t, d in zip(df["T_t"].values, df["D_con"].values)
    ]

    return df


def to_float(x):
    try:
        return float(x)
    except Exception:
        return None


def build_final_event(row: pd.Series) -> dict:
    """Build a SINGLE JSON payload for teammate's alert system."""
    date_str = pd.to_datetime(row["date"]).strftime("%Y-%m-%d")

    payload = {
        "event_type": "HRI_TRIGGER",
        "region": REGION_ID,
        "date": date_str,

        "metrics": {
            "T_t": to_float(row["T_t"]),
            "D_con": int(row["D_con"]),
            "V_var": to_float(row["V_var"]),
            "HRI": to_float(row["HRI"]),
        },

        "threshold": {
            "HRI": float(HRI_THRESHOLD),
            "T_base": float(T_BASE),
            "severe_temp": float(SEVERE_TEMP),
            "warning_duration_days": 3
        },

        "weights": {
            "alpha": float(ALPHA),
            "beta": float(BETA),
            "gamma": float(GAMMA),
        },

        "source": {
            "dataset": DATASET_NAME,
            "roi": {
                "lat_min": float(JEJU_LAT_MIN),
                "lat_max": float(JEJU_LAT_MAX),
                "lon_min": float(JEJU_LON_MIN),
                "lon_max": float(JEJU_LON_MAX),
            },
            "model_version": MODEL_VERSION,
        },

        "decision": {
            "triggered": True,
            "level": str(row["level"]),  # WATCH/WARNING/SEVERE
        },

        "message": f"[{REGION_ID}] {row['level']} - HRI trigger on {date_str} (HRI≥{HRI_THRESHOLD})."
    }

    return payload


# -----------------------------
# 2) Main
# -----------------------------
def main():
    start = datetime.strptime(START_DATE, "%Y-%m-%d")
    end = datetime.strptime(END_DATE, "%Y-%m-%d")

    rows = []
    for day in daterange(start, end):
        nc_path = ensure_oisst_file(day)
        if not nc_path:
            continue

        try:
            T_t = compute_jeju_mean_sst(nc_path)
            rows.append({
                "date": day.date(),
                "file": os.path.basename(nc_path),
                "T_t": T_t
            })
            print(f"[OK] {day.date()} T_t={T_t:.2f}°C")
        except Exception as e:
            print(f"[WARN] parse failed {day.date()}: {e}")

    if not rows:
        raise RuntimeError("No processed days. Check network/URL/permissions.")

    df_daily = pd.DataFrame(rows)
    df_daily["date"] = pd.to_datetime(df_daily["date"])

    df_hri = build_hri(df_daily)

    # outputs
    os.makedirs(OUT_DIR, exist_ok=True)
    df_hri.to_csv(OUT_HRI_CSV, index=False, encoding="utf-8-sig")

    # triggered list (all triggered days)
    triggered = df_hri[df_hri["trigger"]].copy()
    triggered["date"] = triggered["date"].dt.strftime("%Y-%m-%d")
    trigger_list = triggered.to_dict(orient="records")

    with open(OUT_TRIGGER_LIST_JSON, "w", encoding="utf-8") as f:
        json.dump(trigger_list, f, ensure_ascii=False, indent=2)

    # final single event for teammate (first trigger day)
    if len(trigger_list) > 0:
        first_trigger_row = df_hri[df_hri["trigger"]].iloc[0]
        final_event = build_final_event(first_trigger_row)

        with open(OUT_FINAL_EVENT_JSON, "w", encoding="utf-8") as f:
            json.dump(final_event, f, ensure_ascii=False, indent=2)

        print("\n✅ 완료!")
        print(f"- {OUT_HRI_CSV}")
        print(f"- {OUT_TRIGGER_LIST_JSON}")
        print(f"- {OUT_FINAL_EVENT_JSON}")
        print(f"\n🚨 Trigger first day: {final_event['date']} (level={final_event['decision']['level']})")
    else:
        # write an "empty" final payload for predictable integration
        final_event = {
            "event_type": "HRI_TRIGGER",
            "region": REGION_ID,
            "date": None,
            "decision": {"triggered": False, "level": "NORMAL"},
            "message": f"[{REGION_ID}] No trigger in {START_DATE} ~ {END_DATE}. Adjust threshold if needed."
        }
        with open(OUT_FINAL_EVENT_JSON, "w", encoding="utf-8") as f:
            json.dump(final_event, f, ensure_ascii=False, indent=2)

        print("\n✅ 완료!")
        print(f"- {OUT_HRI_CSV}")
        print(f"- {OUT_TRIGGER_LIST_JSON}")
        print(f"- {OUT_FINAL_EVENT_JSON}")
        print("\n🟢 No trigger events (you can tune HRI_THRESHOLD).")


if __name__ == "__main__":
    main()
