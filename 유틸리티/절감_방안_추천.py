"""
개선안 추천 모듈 (절감_방안_추천.py)

왜 이렇게 설계했는가:
- 8가지 개선안 각각에 투자비/절감률/회수기간/난이도 데이터를 보유
- 사용자의 진단 결과에 따라 가장 효과적인 TOP 3를 동적으로 선별
- ROI(투자 회수 기간)가 짧은 순으로 우선순위 정렬
"""


# ── 개선안 풀 (8종) ──
# cost_per_pyeong: 평당 투자비(만원), saving_pct: 절감률(%), payback_years: 평균 회수기간
RECOMMENDATIONS_DB = [
    {
        "id": "window",
        "icon": "🪟",
        "name": "창호 교체 (이중/삼중유리)",
        "desc": "오래된 단층 유리를 고단열 이중·삼중 유리로 교체합니다. 냉난방 에너지 누출의 가장 큰 원인을 해결합니다.",
        "cost_per_pyeong": 8,
        "saving_pct": 18,
        "trigger": "cooling",  # 냉방 부하가 높을 때 추천
        "difficulty": "중간",
        "diff_css": "diff-medium",
    },
    {
        "id": "insulation",
        "icon": "🧱",
        "name": "외벽 단열 보강",
        "desc": "외단열 시스템(EIFS)을 적용하여 벽체를 통한 열 손실을 차단합니다. 겨울철 난방비 절감 효과가 큽니다.",
        "cost_per_pyeong": 6,
        "saving_pct": 15,
        "trigger": "heating",
        "difficulty": "어려움",
        "diff_css": "diff-hard",
    },
    {
        "id": "smart_thermo",
        "icon": "🌡️",
        "name": "스마트 온도조절기 설치",
        "desc": "AI 기반 온도조절기가 재실 여부와 외부 기온에 따라 자동으로 냉난방을 조절합니다.",
        "cost_per_pyeong": 0.8,
        "saving_pct": 10,
        "trigger": "hvac",
        "difficulty": "쉬움",
        "diff_css": "diff-easy",
    },
    {
        "id": "led",
        "icon": "💡",
        "name": "LED 조명 전면 교체",
        "desc": "기존 형광등/백열등을 고효율 LED로 교체합니다. 조명 전력을 최대 60% 절감합니다.",
        "cost_per_pyeong": 0.5,
        "saving_pct": 7,
        "trigger": "overall",
        "difficulty": "쉬움",
        "diff_css": "diff-easy",
    },
    {
        "id": "shading",
        "icon": "🏖️",
        "name": "외부 차양/블라인드 설치",
        "desc": "루버, 어닝, 외부 블라인드 등으로 직사광선을 차단합니다. 여름철 냉방비를 효과적으로 줄입니다.",
        "cost_per_pyeong": 2,
        "saving_pct": 12,
        "trigger": "cooling",
        "difficulty": "쉬움",
        "diff_css": "diff-easy",
    },
    {
        "id": "hvac_replace",
        "icon": "❄️",
        "name": "냉난방 시스템 교체",
        "desc": "노후 에어컨/보일러를 고효율 인버터 시스템으로 교체합니다. 에너지 소비를 크게 줄입니다.",
        "cost_per_pyeong": 10,
        "saving_pct": 22,
        "trigger": "hvac",
        "difficulty": "어려움",
        "diff_css": "diff-hard",
    },
    {
        "id": "roof_insulation",
        "icon": "🏠",
        "name": "지붕/옥상 단열 보강",
        "desc": "최상층의 열 손실/유입을 차단합니다. 특히 단독주택에서 효과가 큽니다.",
        "cost_per_pyeong": 4,
        "saving_pct": 10,
        "trigger": "heating",
        "difficulty": "중간",
        "diff_css": "diff-medium",
    },
    {
        "id": "boiler",
        "icon": "🔥",
        "name": "고효율 보일러 교체",
        "desc": "15년 이상 된 보일러를 콘덴싱 보일러로 교체합니다. 가스비를 최대 20% 절감합니다.",
        "cost_per_pyeong": 3,
        "saving_pct": 13,
        "trigger": "heating",
        "difficulty": "중간",
        "diff_css": "diff-medium",
    },
]


def get_all_recommendations(diagnosis: dict, pyeong: float) -> list:
    """
    모든 개선안에 대해 진단 결과를 반영하여 개별 스코어 및 재무 지표를 계산합니다.
    """
    gauges = diagnosis["gauges"]
    current_cost = diagnosis["current_cost"]

    # 트리거별 우선순위 점수 계산
    trigger_scores = {
        "cooling": gauges["냉방 부하"]["score"],
        "heating": gauges["난방 손실"]["score"],
        "hvac": gauges["설비 효율"]["score"],
        "airtight": gauges["기밀성"]["score"],
        "overall": sum(g["score"] for g in gauges.values()) / len(gauges),
    }

    scored = []
    for rec in RECOMMENDATIONS_DB:
        # 투자비 & 절감액 계산
        invest = rec["cost_per_pyeong"] * pyeong  # 만원
        annual_saving = current_cost * rec["saving_pct"] / 100  # 원
        annual_saving_manwon = annual_saving / 10000  # 만원

        # 회수 기간 (년)
        payback = invest / annual_saving_manwon if annual_saving_manwon > 0 else 99

        # 점수 = 트리거 관련도 × 절감률 / 회수기간 (높을수록 좋음)
        trigger_score = trigger_scores.get(rec["trigger"], 30)
        priority = trigger_score * rec["saving_pct"] / max(payback, 0.1)

        scored.append({
            **rec,
            "invest_manwon": invest,
            "annual_saving_won": annual_saving,
            "annual_saving_manwon": annual_saving_manwon,
            "payback_years": round(payback, 1),
            "priority": priority,
        })
    return scored


def get_top_recommendations(diagnosis: dict, pyeong: float, top_n: int = 3) -> list:
    """
    기본 호환용: 진단 결과를 기반으로 종합 추천 순(priority) TOP N을 선별합니다.
    """
    scored = get_all_recommendations(diagnosis, pyeong)
    scored.sort(key=lambda x: x["priority"], reverse=True)
    return scored[:top_n]
