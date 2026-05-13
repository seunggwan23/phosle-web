"""
에너지 계산 엔진 (energy_engine.py)

왜 분리했는가:
- 기존 app.py의 물리 계산 로직을 재활용
- 일반인 입력(건물유형/연도/지역)을 전문가 파라미터(WWR/단열/HVAC)로 매핑
"""
import numpy as np

# ── 기본 상수 ──
BASE_INTENSITY = 150.0   # kWh/m²/년 (한국 업무용 건물 평균)
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

# ── 불편함 → 파라미터 보정 ──
DISCOMFORT_EFFECTS = {
    "여름에 실내가 너무 더워요": {"wwr_add": 0.10, "desc": "창문 면적 과다 / 차양 부족"},
    "겨울에 실내가 금방 식어요": {"insulation_mult": 0.7, "desc": "단열 성능 저하"},
    "창문 틈으로 바람이 들어와요": {"airtight_loss": 0.12, "desc": "창호 기밀성 부족"},
    "냉난방을 해도 효과가 없어요": {"hvac_mult": 0.7, "desc": "설비 노후 / 효율 저하"},
    "전기요금이 비정상적으로 높아요": {"overall_add": 0.15, "desc": "전반적 비효율"},
}


def map_inputs(building_type: str, age: str, region: str,
               discomforts: list, climate_factor: float = None) -> dict:
    """
    일반인 입력을 기술 파라미터로 변환.

    Args:
        climate_factor: 실제 기상 데이터 기반 보정 계수 (None이면 정적 REGION_FACTOR 사용)

    Returns:
        dict: wwr, insulation_mm, hvac_eff, extra_loss, region_factor
    """
    base = BUILDING_DEFAULTS.get(building_type, BUILDING_DEFAULTS["아파트"])
    age_f = AGE_FACTOR.get(age, 1.0)

    # climate_factor가 있으면 실제 기상 데이터 사용, 없으면 정적 팩터
    reg_f = climate_factor if climate_factor is not None else REGION_FACTOR.get(region, 1.0)

    wwr = base["wwr"]
    insulation = base["insulation"] * age_f
    hvac_eff = base["hvac_eff"]
    extra_loss = 0.0

    for d in discomforts:
        eff = DISCOMFORT_EFFECTS.get(d, {})
        wwr += eff.get("wwr_add", 0)
        if "insulation_mult" in eff:
            insulation *= eff["insulation_mult"]
        if "hvac_mult" in eff:
            hvac_eff *= eff["hvac_mult"]
        extra_loss += eff.get("airtight_loss", 0)
        extra_loss += eff.get("overall_add", 0)

    return {
        "wwr": min(wwr, 0.8),
        "insulation_mm": max(insulation, 30),
        "hvac_eff": hvac_eff,
        "extra_loss": extra_loss,
        "region_factor": reg_f,
    }


def calc_annual_kwh(pyeong: float, wwr: float, insulation_mm: float,
                    hvac_eff: float = 1.0, extra_loss: float = 0.0,
                    region_factor: float = 1.0) -> float:
    """보정 계수 기반 연간 에너지 소비량(kWh) 계산"""
    m2 = pyeong * PYEONG_TO_M2

    wwr_delta = np.clip((wwr - 0.3) * 2.0, -0.35, 0.35)
    ins_delta = np.clip((150 - insulation_mm) / 150 * 0.30, -0.30, 0.30)
    hvac_delta = np.clip((1.0 - hvac_eff) * 0.5, 0, 0.30)

    intensity = BASE_INTENSITY * (1 + wwr_delta + ins_delta + hvac_delta + extra_loss)
    intensity *= region_factor

    return intensity * m2


def calc_optimal_kwh(pyeong: float, region_factor: float = 1.0) -> float:
    """최적 조건(최신 건물 기준) 에너지 소비량"""
    return calc_annual_kwh(pyeong, 0.25, 200, 1.0, 0.0, region_factor)


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


def diagnose(pyeong, building_type, age, region, discomforts,
             monthly_bill=None, climate_factor=None):
    """
    전체 진단을 수행하고 결과 딕셔너리 반환.

    Args:
        climate_factor: 실제 기상 데이터 기반 보정 계수 (weather.py에서 계산)

    Returns:
        dict: 진단 결과 전체 (에너지, 등급, 비용, 게이지 등)
    """
    params = map_inputs(building_type, age, region, discomforts, climate_factor)

    current_kwh = calc_annual_kwh(
        pyeong, params["wwr"], params["insulation_mm"],
        params["hvac_eff"], params["extra_loss"], params["region_factor"]
    )
    optimal_kwh = calc_optimal_kwh(pyeong, params["region_factor"])

    current_cost = current_kwh * ELEC_RATE
    optimal_cost = optimal_kwh * ELEC_RATE
    saving_potential = current_cost - optimal_cost

    grade, grade_css = get_grade(current_kwh, optimal_kwh)

    # 에너지 낭비 포인트 게이지 (0~100)
    ratio = current_kwh / optimal_kwh if optimal_kwh > 0 else 2.0
    cooling_score = min(100, int(params["wwr"] / 0.8 * 100))
    heating_score = min(100, int((200 - params["insulation_mm"]) / 200 * 100))
    airtight_score = min(100, int(params["extra_loss"] / 0.3 * 100))
    hvac_score = min(100, int((1.0 - params["hvac_eff"]) / 0.5 * 100))

    monthly = monthly_breakdown(current_kwh)
    monthly_opt = monthly_breakdown(optimal_kwh)

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
