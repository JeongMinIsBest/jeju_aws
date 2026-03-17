# 🌊 제주 연안 고수온 리스크 지수 (HRI) 산출 파이프라인
위성 기반 해수면 수온(SST) 데이터를 활용하여 제주 연안의 고수온 위험을 정량화하고,  
보험 · 정책 · 조기경보 트리거로 활용 가능한 Heat Risk Index(HRI)를 산출하는 파이프라인입니다.
<br/>
<br/>

## 🎯 프로젝트 목표
- 위성 SST 기반 일 단위 고수온 리스크 지수(HRI) 산출
- 해양수산부 · 기상청 고수온 특보 기준과 정합되는 지표 구조 설계
- 보험·정책 시스템에 바로 연동 가능한 트리거 이벤트 출력
- 센서 미설치 해역에서도 적용 가능한 위성 기반 표준 파이프라인 구축
<br/>
<br/>

## 🛰 사용 데이터

### 1️⃣ 위성 해수면 수온 (SST)
- 데이터명 : OISST (Optimum Interpolation Sea Surface Temperature)
- 제공 기관 : NOAA / NCEI
- 데이터 특징
  - 전 지구 일 단위 SST 제공
  - 위성(AVHRR), 부이, 관측 자료를 보정·결합한 표준 SST
  - 정책 · 보험 적용에 적합한 공공 데이터
- 공간 범위
  - 제주 연안 인근 격자 평균
  - ROI : lat 32–35, lon 124–129
- 시간 범위 : 2024-07-20 ~ 2024-10-05
<br/>

### 2️⃣ 기준 정책 데이터
- 해양수산부 / 기상청 고수온 특보 기준 : `28°C 이상, 72시간 지속`
- 본 기준을 HRI 계산 및 경보 단계 매핑에 구조적으로 반영
<br/>
<br/>

## 🧮 HRI (Heat Risk Index) 산출 파이프라인
HRI는 단순 온도 초과 여부가 아니라 기준 임계 온도 초과 정도, 누적 지속성,  
단기 변동성을 종합적으로 반영한 **연속형 리스크 지수**입니다.
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

**1. OISST NetCDF 로드**
  - xarray 기반 데이터 로딩
  - 일 단위 SST 시계열 확보
  
**2. 제주 연안 공간 평균**
  - 설정된 ROI 내 격자 평균
  - 단일 지역 대표 SST T_t 생성
  
**3. 파생 지표 계산**
  - 기준 초과 수온
  - 고수온 연속 지속 일수
  - 전일 대비 수온 변동성
  
**4. HRI 산출**
  - 연속형 리스크 지수 계산
  - 정책 기준과 연결 가능한 수치화
  
**5. 경보 단계 및 트리거 생성**
  - 경보 단계(NORMAL–SEVERE) 매핑
  - 시스템 연계용 JSON 출력
<br/>
<br/>

## 🚨 고수온 경보 단계 매핑
| 단계 | 조건 |
|---|---|
| **NORMAL** | `T_t < 28°C` |
| **WATCH (관심)** | `T_t ≥ 28°C` & `D_con < 3` |
| **WARNING (경보)** | `D_con ≥ 3` & `T_t < 30°C` |
| **SEVERE (심각)** | `D_con ≥ 3` & `T_t ≥ 30°C` |
<br/>
<br/>

## 🧱 프로젝트 구조
```
jeju_aws/
├── data/           # 입력 데이터
├── run_hri.py      # HRI 산출 메인 실행 파일
├── utils/          # SST 처리 및 계산 유틸
├── outputs/        # 결과 파일 (CSV / JSON)
└── README.md
```
<br/>
<br/>

## 🚀 실행 방법

### 1️⃣ 환경 설정
```
pip install -r requirements.txt
```
<br/>

### 2️⃣ HRI 산출 실행
```
python run_hri.py
```
<br/>
<br/>
