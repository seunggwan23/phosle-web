"""
더미 데이터 생성기 + 물리 기반 에너지 시뮬레이터 (data_generator.py)

수정 사항:
- 사용자 파라미터(WWR, 단열재, HVAC)가 물리 법칙에 따라 에너지에 직접 반영
- 파라미터 변경 시 예측값이 즉시 반응하도록 설계
"""

import numpy as np
import pandas as pd
from math import pi


# ── 물리 상수 ────────────────────────────────────────────────────
U_VALUE_GLASS = 2.8        # 유리 열관류율 (W/m²K) - 일반 복층유리
SOLAR_HEAT_GAIN_COEFF = 0.6  # 태양열 취득 계수 (SHGC)
FLOOR_AREA_M2 = 1000       # 기준 바닥면적 (m²)
WALL_AREA_M2 = 2400        # 기준 외벽 면적 (m²)
COP_COOLING = 3.0          # 냉방 COP (성능계수)
COP_HEATING = 2.5          # 난방 COP


def get_insulation_u_value(thickness_mm: float) -> float:
    """
    단열재 두께(mm)로 열관류율(U-value, W/m²K)을 계산합니다.
    (열전도율 0.035 W/mK 기준 - EPS 단열재)
    """
    lambda_k = 0.035  # 열전도율 (W/mK)
    r_insulation = (thickness_mm / 1000) / lambda_k  # 단열 열저항
    r_base = 0.4  # 기타 구조체 열저항 (m²K/W)
    u_total = 1 / (r_base + r_insulation)
    return u_total


def compute_hourly_energy(
    outdoor_temp: np.ndarray,
    solar_radiation: np.ndarray,
    hour: np.ndarray,
    month: np.ndarray,
    dayofweek: np.ndarray,
    wwr: float,
    insulation_mm: float,
    hvac_setpoint: float,
) -> np.ndarray:
    """
    물리 기반 시간별 에너지 소비량을 계산합니다.

    Args:
        outdoor_temp: 시간별 외기 온도 배열 (°C)
        solar_radiation: 시간별 일사량 배열 (W/m²)
        hour: 시간 배열 (0~23)
        month: 월 배열 (1~12)
        dayofweek: 요일 배열 (0=월~6=일)
        wwr: 창면적비 (0.1~0.8)
        insulation_mm: 단열재 두께 (mm)
        hvac_setpoint: HVAC 설정 온도 (°C)

    Returns:
        np.ndarray: 시간별 에너지 소비량 (kWh)
    """
    n = len(outdoor_temp)

    # ── 건물 물리 계산 ──────────────────────────────────────────
    wall_area = WALL_AREA_M2 * (1 - wwr)    # 불투명 벽 면적
    window_area = WALL_AREA_M2 * wwr        # 창문 면적

    u_wall = get_insulation_u_value(insulation_mm)   # 벽 열관류율
    u_window = U_VALUE_GLASS                          # 창문 열관류율

    # ── 온도차 기반 열손실/열획득 (전도) ────────────────────────
    delta_t = outdoor_temp - hvac_setpoint

    # 전도 열부하 (W) = U × A × ΔT
    conduction_wall = u_wall * wall_area * np.abs(delta_t)
    conduction_window = u_window * window_area * np.abs(delta_t)
    conduction_total_w = conduction_wall + conduction_window  # W

    # ── 태양열 취득 (일사) ────────────────────────────────────
    # 창문을 통해 실내로 들어오는 태양 에너지
    solar_gain_w = solar_radiation * window_area * SOLAR_HEAT_GAIN_COEFF  # W

    # ── 냉방 / 난방 부하 분리 ────────────────────────────────
    need_cooling = delta_t > 0  # 외기가 설정 온도보다 높으면 냉방
    need_heating = delta_t < 0  # 외기가 설정 온도보다 낮으면 난방

    # 냉방 부하 = 전도 열취득 + 태양열 취득
    cooling_load_w = np.where(need_cooling, conduction_total_w + solar_gain_w, 0)
    # 난방 부하 = 전도 열손실 - 태양열 취득 (태양열이 난방에 도움)
    heating_load_w = np.where(need_heating, np.maximum(conduction_total_w - solar_gain_w * 0.5, 0), 0)

    # ── COP 적용으로 전력(kWh) 변환 ──────────────────────────
    cooling_kwh = cooling_load_w / (COP_COOLING * 1000)  # kW → kWh/h
    heating_kwh = heating_load_w / (COP_HEATING * 1000)
    hvac_kwh = cooling_kwh + heating_kwh

    # ── 조명 + 플러그 부하 (업무 시간대) ─────────────────────
    is_weekday = dayofweek < 5
    is_work_hour = (hour >= 9) & (hour <= 18)
    base_load = np.where(
        is_weekday & is_work_hour,
        15.0 + np.random.normal(0, 1.5, n),  # 업무시간 기저 부하 (kWh)
        3.0 + np.random.normal(0, 0.5, n),    # 비업무시간 기저 부하
    )
    base_load = np.maximum(base_load, 0.5)

    # ── 총 에너지 = HVAC + 기저부하 ─────────────────────────
    total_kwh = hvac_kwh + base_load
    return np.maximum(total_kwh, 0.1)


def generate_dummy_data(
    n_hours: int = 8760,
    wwr: float = 0.3,
    insulation_mm: float = 150.0,
    hvac_setpoint: float = 24.0,
    random_seed: int = 42,
) -> pd.DataFrame:
    """
    사용자 파라미터를 반영한 1년치 건물 에너지 데이터를 생성합니다.

    Args:
        n_hours: 생성할 시간 수 (기본: 8760 = 1년)
        wwr: 창면적비
        insulation_mm: 단열재 두께 (mm)
        hvac_setpoint: HVAC 설정 온도 (°C)
        random_seed: 재현성용 시드
    """
    np.random.seed(random_seed)

    # ── 시간 인덱스 (명세서 2.1) ─────────────────────────────
    timestamps = pd.date_range(start="2024-01-01", periods=n_hours, freq="h")
    df = pd.DataFrame(index=timestamps)
    df.index.name = "Timestamp"

    # ── 기상 데이터 생성 (한국 기후 기준) ───────────────────
    month_temp = {1: -3, 2: 0, 3: 7, 4: 14, 5: 19, 6: 23,
                  7: 27, 8: 28, 9: 22, 10: 15, 11: 7, 12: 0}
    base_temp = df.index.month.map(month_temp).astype(float)
    hour_variation = 5 * np.sin(2 * pi * df.index.hour / 24 - pi / 2)
    df["outdoor_temp"] = base_temp + hour_variation + np.random.normal(0, 1.5, n_hours)

    # .values로 numpy 배열 변환 → Index 객체에 .clip() 호출 불가 에러 방지
    hour_arr = df.index.hour.values
    doy_arr  = df.index.dayofyear.values
    solar_base = np.maximum(0, np.sin(2 * pi * (hour_arr - 6) / 24))
    season_factor = 0.7 + 0.3 * np.sin(2 * pi * (doy_arr - 80) / 365)
    df["solar_radiation"] = np.clip(solar_base * season_factor * 800 + np.random.normal(0, 30, n_hours), 0, None)

    df["wind_speed"] = np.random.weibull(2, n_hours) * 4.0
    humidity_raw = 50 + 20 * np.sin(2 * pi * doy_arr / 365) + np.random.normal(0, 10, n_hours)
    df["humidity"] = np.clip(humidity_raw, 20, 95)

    # ── 특징 공학 (명세서 2.2) ───────────────────────────────
    df["HDD"] = np.maximum(0, 18.5 - df["outdoor_temp"])
    df["CDD"] = np.maximum(0, df["outdoor_temp"] - 24.0)

    df["hr_sin"] = np.sin(2 * pi * df.index.hour.values / 24)
    df["hr_cos"] = np.cos(2 * pi * df.index.hour.values / 24)
    df["month_sin"] = np.sin(2 * pi * df.index.month.values / 12)
    df["month_cos"] = np.cos(2 * pi * df.index.month.values / 12)
    df["dayofweek"] = df.index.dayofweek.values
    df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)
    df["building_type_RC"] = 1
    df["building_type_steel"] = 0

    # ── 사용자 파라미터 컬럼 ─────────────────────────────────
    df["wwr"] = wwr
    df["insulation_mm"] = insulation_mm
    df["hvac_setpoint"] = hvac_setpoint

    # ── 물리 기반 에너지 계산 ────────────────────────────────
    df["energy_kwh"] = compute_hourly_energy(
        outdoor_temp=df["outdoor_temp"].values,
        solar_radiation=df["solar_radiation"].values,
        hour=df.index.hour.values.astype(int),
        month=df.index.month.values.astype(int),
        dayofweek=df.index.dayofweek.values.astype(int),
        wwr=wwr,
        insulation_mm=insulation_mm,
        hvac_setpoint=hvac_setpoint,
    )

    # ── 디버그 출력 ──────────────────────────────────────────
    print(f"[DEBUG] Shape={df.shape} | 결측치={df.isnull().sum().sum()} | "
          f"에너지 {df['energy_kwh'].min():.1f}~{df['energy_kwh'].max():.1f} kWh")

    return df


def get_feature_columns() -> list:
    """모델 학습에 사용될 특징 컬럼 목록"""
    return [
        "outdoor_temp", "solar_radiation", "wind_speed", "humidity",
        "HDD", "CDD",
        "hr_sin", "hr_cos", "month_sin", "month_cos",
        "dayofweek", "is_weekend",
        "building_type_RC", "building_type_steel",
        "wwr", "insulation_mm", "hvac_setpoint",
    ]
