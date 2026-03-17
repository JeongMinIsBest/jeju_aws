# 🌊 Jeju Coastal Heat Risk Index (HRI) Calculation Pipeline
This pipeline quantifies heat risk in the coastal waters of Jeju using satellite-based Sea Surface Temperature (SST) data and  
computes a Heat Risk Index (HRI) that can be used for insurance · policy · early warning triggers.
<br/>
<br/>

## 🎯 Project Objectives
- Calculate a daily Heat Risk Index (HRI) based on satellite SST
- Design an index structure aligned with the marine heatwave alert standards of the Ministry of Oceans and Fisheries and the Korea Meteorological Administration
- Output trigger events that can be directly integrated into insurance and policy systems
- Build a standardized satellite-based pipeline applicable even in areas without in-situ sensors
<br/>
<br/>

## 🛰 Data Used

### 1️⃣ Satellite Sea Surface Temperature (SST)
- Dataset : OISST (Optimum Interpolation Sea Surface Temperature)
- Provider : NOAA / NCEI
- Data Characteristics
  - Provides global daily SST
  - Standard SST product corrected and combined from satellite (AVHRR), buoy, and observational data
  - Public data suitable for policy · insurance applications
- Spatial Coverage
  - Average grid values around the Jeju coastal area
  - ROI : lat 32–35, lon 124–129
- Time Range : 2024-07-20 ~ 2024-10-05
<br/>

### 2️⃣ Reference Policy Data
- Marine heatwave alert criteria from the Ministry of Oceans and Fisheries / Korea Meteorological Administration : `28°C or higher, sustained for 72 hours`
- This criterion is structurally reflected in HRI calculation and alert-level mapping
<br/>
<br/>

## 🧮 HRI (Heat Risk Index) Calculation Pipeline
HRI is not simply based on whether a temperature threshold is exceeded.  
It is a **continuous risk index** that integrates the magnitude of threshold exceedance, cumulative persistence,  
and short-term variability.
<br/>

```
OISST NetCDF (daily)
        ↓
Spatial subsetting (Jeju ROI)
        ↓
Daily mean SST (T_t)
        ↓
Derived indicators
  - Temperature exceedance
  - Consecutive hot days (D_con)
  - Day-to-day variability (V_var)
        ↓
Heat Risk Index (HRI_t)
        ↓
Policy-aligned alert level mapping
        ↓
Trigger event export (CSV / JSON)
```
<br/>

**1. Load OISST NetCDF**
  - Load data using xarray
  - Obtain daily SST time series
  
**2. Spatial Averaging for Jeju Coastal Area**
  - Compute grid average within the defined ROI
  - Generate a representative regional SST \(T_t\)
  
**3. Derived Indicator Calculation**
  - Threshold-exceeding temperature
  - Consecutive hot-day duration
  - Day-to-day SST variability
  
**4. HRI Calculation**
  - Compute a continuous heat risk index
  - Convert values into policy-compatible numerical indicators
  
**5. Alert Level and Trigger Generation**
  - Map alert levels (NORMAL–SEVERE)
  - Export JSON for system integration
<br/>
<br/>

## 🚨 Marine Heatwave Alert Level Mapping
| Level | Condition |
|---|---|
| **NORMAL** | `T_t < 28°C` |
| **WATCH** | `T_t ≥ 28°C` & `D_con < 3` |
| **WARNING** | `D_con ≥ 3` & `T_t < 30°C` |
| **SEVERE** | `D_con ≥ 3` & `T_t ≥ 30°C` |
<br/>
<br/>

## 🧱 Project Structure
```
jeju_aws/
├── data/           # Input data
├── run_hri.py      # Main execution file for HRI calculation
├── utils/          # SST processing and calculation utilities
├── outputs/        # Result files (CSV / JSON)
└── README.md
```
<br/>
<br/>

## 🚀 How to Run

### 1️⃣ Environment Setup
```
pip install -r requirements.txt
```
<br/>

### 2️⃣ Run HRI Calculation
```
python run_hri.py
```
<br/>
<br/>
