"""
에너지 분석 엔진 (에너지_분석_엔진.py)

왜 분리했는가:
- 기존 app.py의 물리 계산 로직을 재활용
- 일반인 입력(건물유형/연도/지역)을 전문가 파라미터(WWR/단열/HVAC)로 매핑
"""
import numpy as np

# ── 기본 상수 ──
BASE_INTENSITIES = {
    "아파트": 65.0,         # kWh/m²/년 (한국 주거형 아파트 연간 실질 에너지 사용 강도)
    "단독주택": 95.0,      # kWh/m²/년 (단독주택 평균 사용 강도)
    "상가/오피스": 160.0,   # kWh/m²/년 (한국 업무시설/오피스용 건물 평균)
}
ELEC_RATE = 130          # 원/kWh (한전 평균 단가)
PYEONG_TO_M2 = 3.3058

# 월별 에너지 분포 (한국 기후 기준)
MONTHLY_W = np.array([.10,.09,.07,.06,.07,.10,.12,.12,.08,.07,.06,.06])
MONTHLY_W = MONTHLY_W / MONTHLY_W.sum()

# ── 건물 유형별 기본 파라미터 ──
BUILDING_DEFAULTS = {
    "아파트": {"wwr": 0.25, "insulation": 150, "hvac_eff": 1.0},
    "단독주택": {"wwr": 0.30, "insulation": 120, "hvac_eff": 0.9},
    "상가/오피스": {"wwr": 0.45, "insulation": 130, "hvac_eff": 0.95},
}

# ── 건축 연도별 단열 보정 계수 ──
# 오래될수록 단열 성능 저하
AGE_FACTOR = {
    "5년 이내": 1.0,
    "5~15년": 0.85,
    "15~30년": 0.65,
    "30년 이상": 0.45,
}

# ── 지역별 기후 보정 계수 ──
# 추운 지역일수록 난방 에너지 증가
REGION_FACTOR = {
    "서울·경기": 1.0,
    "강원": 1.15,
    "충청": 0.98,
    "전라": 0.93,
    "경상": 0.95,
    "제주": 0.88,
}

# ── 정량적 불편함 평가(1~5점) → 파라미터 스케일링 맵 ──
# 1점 = 베스트(손실 없음), 5점 = 워스트(심각한 비효율)
QUANTITATIVE_SCALES = {
    # 1. 태양열 유입(WWR 가산): 1점(0.0) ~ 5점(0.16)
    "solar": [0.0, 0.0, 0.03, 0.07, 0.12, 0.18], 
    # 2. 온도보존 단열성(곱연산): 1점(1.0) ~ 5점(0.55)
    "insulation": [1.0, 1.0, 0.92, 0.80, 0.68, 0.55],
    # 3. 설비도달력(HVAC 효율 곱연산): 1점(1.0) ~ 5점(0.60)
    "hvac": [1.0, 1.0, 0.95, 0.85, 0.72, 0.60],
    # 4. 기밀성 바람유입(손실 가산): 1점(0.0) ~ 5점(0.24)
    "airtight": [0.0, 0.0, 0.04, 0.09, 0.16, 0.24]
}


def map_inputs(building_type: str, age: str, region: str,
               discomfort_scores: dict, climate_factor: float = None) -> dict:
    """
    사용자의 정량 평가 점수(1~5단계)를 물리 기술 파라미터로 정밀 변환합니다.

    Args:
        discomfort_scores: {'airtight': 1~5, 'insulation': 1~5, 'hvac': 1~5, 'solar': 1~5}
        climate_factor: 실제 기상 데이터 기반 보정 계수 (None이면 정적 REGION_FACTOR 사용)

    Returns:
        dict: wwr, insulation_mm, hvac_eff, extra_loss, region_factor
    """
    base = BUILDING_DEFAULTS.get(building_type, BUILDING_DEFAULTS["아파트"])
    age_f = AGE_FACTOR.get(age, 1.0)
    reg_f = climate_factor if climate_factor is not None else REGION_FACTOR.get(region, 1.0)

    # 입력 데이터가 딕셔너리가 아닐 경우 기본값(보통 수준인 2점)으로 보호 처리
    if not isinstance(discomfort_scores, dict):
        scores = {"airtight": 2, "insulation": 2, "hvac": 2, "solar": 2}
    else:
        scores = discomfort_scores

    # 1-indexed 배열 조회를 위해 bound 체크 및 기본값 2 설정
    def get_valid_score(key):
        val = scores.get(key, 2)
        try:
            val = int(val)
            return max(1, min(5, val))
        except:
            return 2

    s_solar = get_valid_score("solar")
    s_ins = get_valid_score("insulation")
    s_hvac = get_valid_score("hvac")
    s_air = get_valid_score("airtight")

    # ── 정량 수치를 물리 공식 파라미터에 매핑 ──
    wwr_add = QUANTITATIVE_SCALES["solar"][s_solar]
    ins_mult = QUANTITATIVE_SCALES["insulation"][s_ins]
    hvac_mult = QUANTITATIVE_SCALES["hvac"][s_hvac]
    air_loss = QUANTITATIVE_SCALES["airtight"][s_air]

    # 최종 변수 조합
    wwr = base["wwr"] + wwr_add
    insulation = base["insulation"] * age_f * ins_mult
    hvac_eff = base["hvac_eff"] * hvac_mult
    extra_loss = air_loss

    return {
        "wwr": min(wwr, 0.8),
        "insulation_mm": max(insulation, 30),
        "hvac_eff": max(hvac_eff, 0.3), # 한계 효율 보장
        "extra_loss": extra_loss,
        "region_factor": reg_f,
    }


def calc_annual_kwh(pyeong: float, wwr: float, insulation_mm: float,
                    hvac_eff: float = 1.0, extra_loss: float = 0.0,
                    region_factor: float = 1.0, base_intensity: float = 65.0) -> float:
    """보정 계수 기반 연간 에너지 소비량(kWh) 계산"""
    m2 = pyeong * PYEONG_TO_M2

    wwr_delta = np.clip((wwr - 0.3) * 2.0, -0.35, 0.35)
    ins_delta = np.clip((150 - insulation_mm) / 150 * 0.30, -0.30, 0.30)
    hvac_delta = np.clip((1.0 - hvac_eff) * 0.5, 0, 0.30)

    intensity = base_intensity * (1 + wwr_delta + ins_delta + hvac_delta + extra_loss)
    intensity *= region_factor

    return intensity * m2


def calc_optimal_kwh(pyeong: float, region_factor: float = 1.0, base_intensity: float = 65.0) -> float:
    """최적 조건(최신 패시브하우스급 건물 기준) 에너지 소비량"""
    # 최적 창면적비 0.25, 고성능 단열 200mm, 초고효율 HVAC 1.0, 기밀 손실 0.0 적용
    return calc_annual_kwh(pyeong, 0.25, 200, 1.0, 0.0, region_factor, base_intensity)


def monthly_breakdown(annual_kwh: float) -> np.ndarray:
    return MONTHLY_W * annual_kwh


def get_grade(current_kwh: float, optimal_kwh: float) -> tuple:
    """에너지 효율 등급 판정 (A+ ~ E)"""
    ratio = current_kwh / optimal_kwh if optimal_kwh > 0 else 2.0
    if ratio <= 1.05:
        return "A+", "grade-A"
    elif ratio <= 1.20:
        return "A", "grade-A"
    elif ratio <= 1.40:
        return "B", "grade-B"
    elif ratio <= 1.70:
        return "C", "grade-C"
    elif ratio <= 2.10:
        return "D", "grade-D"
    else:
        return "E", "grade-E"


def won_to_manwon(won: float) -> str:
    mw = abs(won) / 10000
    if mw >= 1000:
        return f"{mw/100:.0f}억원"
    return f"{mw:,.0f}만원"


def diagnose(pyeong, building_type, age, region, discomfort_scores,
             recorded_bills=None, climate_factor=None):
    """
    전체 진단을 수행하고 결과 딕셔너리 반환.
    recorded_bills가 주어지면, 이론 계산 대신 실제 수동 기록된 매달 요금을 기반으로 분석을 진행합니다.

    Args:
        recorded_bills (list): 1월부터 12월까지의 실제 전기요금 기록 (단위: 만원)
        climate_factor: 실제 기상 데이터 기반 보정 계수 (weather.py에서 계산)

    Returns:
        dict: 진단 결과 전체 (에너지, 등급, 비용, 게이지 등)
    """
    params = map_inputs(building_type, age, region, discomfort_scores, climate_factor)

    # 0. 건물 유형에 맞는 현실적 에너지 강도 기저값(BASE_INTENSITY) 매핑
    base_intensity = BASE_INTENSITIES.get(building_type, BASE_INTENSITIES["아파트"])

    # 1. 최적 건물 시뮬레이션 (최신 패시브하우스급 기준선)
    optimal_kwh = calc_optimal_kwh(pyeong, params["region_factor"], base_intensity)
    optimal_cost = optimal_kwh * ELEC_RATE
    monthly_opt = monthly_breakdown(optimal_kwh)

    # 2. 현재 내 건물 계산 (기록 데이터 vs 물리 시뮬레이션)
    if recorded_bills is not None and len(recorded_bills) == 12:
        # 사용자가 직접 기록한 데이터를 기반으로 정밀 역연산 수행
        current_monthly_won = np.array([float(b) * 10000 for b in recorded_bills])
        current_cost = float(np.sum(current_monthly_won))
        
        # 요금을 이용 요금 단가로 환산하여 실제 소비 kWh 도출
        monthly = current_monthly_won / ELEC_RATE
        current_kwh = float(np.sum(monthly))
    else:
        # 기록 데이터가 누락된 경우 물리 엔진 기반 이론값 활용
        current_kwh = calc_annual_kwh(
            pyeong, params["wwr"], params["insulation_mm"],
            params["hvac_eff"], params["extra_loss"], params["region_factor"],
            base_intensity
        )
        current_cost = current_kwh * ELEC_RATE
        monthly = monthly_breakdown(current_kwh)

    saving_potential = current_cost - optimal_cost
    # 요금이 더 낮다면(최적보다 우수) 잠재력은 0으로 바인딩
    if saving_potential < 0:
        saving_potential = 0

    grade, grade_css = get_grade(current_kwh, optimal_kwh)

    # 에너지 낭비 포인트 게이지 (0~100)
    ratio = current_kwh / optimal_kwh if optimal_kwh > 0 else 2.0
    cooling_score = min(100, int(params["wwr"] / 0.8 * 100))
    heating_score = min(100, int((200 - params["insulation_mm"]) / 200 * 100))
    airtight_score = min(100, int(params["extra_loss"] / 0.3 * 100))
    hvac_score = min(100, int((1.0 - params["hvac_eff"]) / 0.5 * 100))

    return {
        "params": params,
        "current_kwh": current_kwh,
        "optimal_kwh": optimal_kwh,
        "current_cost": current_cost,
        "optimal_cost": optimal_cost,
        "saving_potential": saving_potential,
        "grade": grade,
        "grade_css": grade_css,
        "gauges": {
            "냉방 부하": {"score": cooling_score, "detail": f"창면적비 {params['wwr']:.0%}"},
            "난방 손실": {"score": heating_score, "detail": f"단열 {params['insulation_mm']:.0f}mm"},
            "기밀성": {"score": airtight_score, "detail": f"손실 {params['extra_loss']:.0%}"},
            "설비 효율": {"score": hvac_score, "detail": f"효율 {params['hvac_eff']:.0%}"},
        },
        "monthly": monthly,
        "monthly_opt": monthly_opt,
    }
