"""
정부 보조금 데이터 모듈 (subsidies.py)

왜 별도 모듈로 분리했는가:
- 보조금 정보는 주기적으로 업데이트 필요 (연 1회 이상)
- 지역별/건물유형별 필터링 로직이 별도로 필요
- 데이터만 수정하면 앱 코드를 건드리지 않아도 됨
"""

# ── 보조금 프로그램 데이터 (2025년 기준) ──
SUBSIDIES = [
    {
        "name": "🏗️ 그린리모델링 이자지원 사업",
        "org": "국토교통부 / LH",
        "target": "15년 이상 노후 건축물",
        "support": "리모델링 비용 대출 이자 지원 (최대 연 4.5%)",
        "amount": "최대 5,000만원 대출",
        "url": "https://www.greenremodeling.or.kr",
        "building_types": ["아파트", "단독주택", "상가/오피스"],
        "min_age": "15~30년",
        "direct_cash_manwon": 150,  # 이자 지원 효과 환산액
        "period_str": "연중 상시",
        "is_local": False,
    },
    {
        "name": "💡 건물에너지효율화 사업 (BRP)",
        "org": "한국에너지공단",
        "target": "에너지 다소비 건물",
        "support": "에너지 진단 + 설비 투자비 보조 (최대 50%)",
        "amount": "진단비 100% + 설비비 30~50%",
        "url": "https://bpr.kemco.or.kr",
        "building_types": ["상가/오피스"],
        "min_age": None,
        "direct_cash_manwon": 500,  # 평균 지원금 환산액
        "period_str": "상반기 공고",
        "is_local": False,
    },
    {
        "name": "🌿 에너지바우처 지원 사업",
        "org": "산업통상자원부",
        "target": "에너지 취약계층 (기초생활수급자 등)",
        "support": "냉난방비 직접 지원",
        "amount": "가구당 연 최대 18.9만원",
        "url": "https://www.energyv.or.kr",
        "building_types": ["아파트", "단독주택"],
        "min_age": None,
        "direct_cash_manwon": 19,
        "period_str": "10월 ~ 익년 5월",
        "is_local": False,
    },
    {
        "name": "🪟 노후 창호 교체 지원",
        "org": "각 지자체 (서울시, 경기도 등)",
        "target": "15년 이상 노후 주택 창호 교체",
        "support": "창호 교체 비용 일부 보조",
        "amount": "가구당 100~300만원 (지자체별 상이)",
        "url": "각 지자체 홈페이지 확인",
        "building_types": ["아파트", "단독주택"],
        "min_age": "15~30년",
        "direct_cash_manwon": 200,
        "period_str": "지자체 예산 소진 시까지",
        "is_local": True,
    },
    {
        "name": "🔥 노후 보일러 교체 지원",
        "org": "한국에너지공단",
        "target": "10년 이상 노후 보일러 가구",
        "support": "친환경 콘덴싱 보일러 교체 비용 지원",
        "amount": "대당 10~30만원",
        "url": "https://www.kemco.or.kr",
        "building_types": ["아파트", "단독주택"],
        "min_age": "5~15년",
        "direct_cash_manwon": 20,
        "period_str": "예산 소진 시까지",
        "is_local": False,
    },
    {
        "name": "☀️ 신재생에너지 보급 지원",
        "org": "한국에너지공단",
        "target": "태양광, 지열 등 신재생에너지 설치",
        "support": "설치비 일부 보조 (최대 50%)",
        "amount": "가구당 최대 335만원 (태양광 3kW 기준)",
        "url": "https://www.knrec.or.kr",
        "building_types": ["단독주택"],
        "min_age": None,
        "direct_cash_manwon": 330,
        "period_str": "3월 ~ 11월",
        "is_local": False,
    },
]


def get_matching_subsidies(building_type: str, age: str, region: str = None) -> list:
    """
    건물 유형과 연도, 지역에 맞는 보조금 필터링 및 우선순위 부여.

    Args:
        building_type: 아파트/단독주택/상가오피스
        age: 건축 연도 그룹
        region: 사용자 지역명

    Returns:
        해당 조건에 맞는 보조금 목록
    """
    # 연도 순서 (오래될수록 높은 인덱스)
    age_order = ["5년 이내", "5~15년", "15~30년", "30년 이상"]
    user_age_idx = age_order.index(age) if age in age_order else 0

    matched = []
    for s in SUBSIDIES:
        # 건물 유형 필터
        if building_type not in s["building_types"]:
            continue

        # 연도 필터 (min_age가 None이면 연도 무관)
        if s["min_age"] is not None:
            min_idx = age_order.index(s["min_age"]) if s["min_age"] in age_order else 0
            if user_age_idx < min_idx:
                continue

        item = s.copy()
        
        # 지역 맞춤형 사업이면 _p_score = 0 (is_local 체크), 전국 공통이면 1
        if item.get("is_local", False):
            item["_p_score"] = 0
        else:
            item["_p_score"] = 1

        matched.append(item)

    # _p_score 오름차순 정렬 (0인 지역 매칭이 위로 올라감)
    matched.sort(key=lambda x: x.get("_p_score", 1))
    return matched
