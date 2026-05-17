"""
정부 보조금 데이터 모듈 (정부_보조금.py)

왜 별도 모듈로 분리했는가:
- 보조금 정보는 주기적으로 업데이트 필요 (연 1회 이상)
- 지역별/건물유형별 필터링 로직이 별도로 필요
- 데이터만 수정하면 앱 코드를 건드리지 않아도 됨
"""

import datetime

# ── 보조금 프로그램 데이터 (2026년 최신 기준) ──
# region: "전국" 또는 특정 지역명(서울·경기, 강원, 충청, 전라, 경상, 제주)
# start_date, end_date: 'YYYY-MM-DD' 포맷. 오늘 날짜 기준으로 신청 여부 판독.
SUBSIDIES = [
    # ── [서울·경기] 지역 특화 보조금 ──
    {
        "name": "🏦 서울시 건물에너지효율화(BRP) 무이자 융자",
        "org": "서울특별시",
        "target": "서울시 내 단열, 창호, LED 등 고효율 개선 건물",
        "support": "에너지 개선 공사비의 100% 이내 무이자(0.0%) 융자 지원",
        "amount": "최대 1,500만원 ~ 20억원 (8년 균등분할상환)",
        "url": "https://building.seoul.go.kr",
        "building_types": ["아파트", "단독주택", "상가/오피스"],
        "min_age": "5~15년",
        "region": "서울·경기",
        "start_date": "2026-01-15",
        "end_date": "2026-11-30",
        "period_str": "2026.01.15 ~ 2026.11.30 (예산 소진 시 조기종료)",
        "direct_cash_manwon": 0, # 융자 지원이므로 현금 보조금 합산에선 0 처리
    },
    {
        "name": "☀️ 서울시/경기도 베란다형 미니태양광 설치 지원",
        "org": "서울시/경기도 및 각 지자체",
        "target": "관내 공동주택(아파트, 빌라) 거주자",
        "support": "아파트 베란다 소형 태양광 패널 설치비 약 70~80% 지원",
        "amount": "가구당 자부담 약 10~15만원선",
        "url": "거주지 지자체 기후환경과 문의",
        "building_types": ["아파트"],
        "min_age": None,
        "region": "서울·경기",
        "start_date": "2026-04-01",
        "end_date": "2026-11-15",
        "period_str": "2026.04.01 ~ 2026.11.15 (지자체 수량 소진 시 마감)",
        "direct_cash_manwon": 40, # 실 지원금 추정액 평균 40만원
    },
    # ── [강원] 지역 특화 보조금 ──
    {
        "name": "❄️ 강원도 한파 대비 녹색건축물 조성 지원",
        "org": "강원특별자치도",
        "target": "관내 15년 이상 된 노후 불량 주택",
        "support": "외벽 단열 보강 공사 및 고효율 창호 교체비의 50% 보조",
        "amount": "동당 최대 1,000만원 이내",
        "url": "https://www.provin.gangwon.kr",
        "building_types": ["단독주택"],
        "min_age": "15~30년",
        "region": "강원",
        "start_date": "2026-02-15",
        "end_date": "2026-06-30",
        "period_str": "2026.02.15 ~ 2026.06.30",
        "direct_cash_manwon": 1000,
    },
    # ── [제주] 지역 특화 보조금 ──
    {
        "name": "🌴 제주 CFI 2030 신재생에너지 주택 융복합 지원",
        "org": "제주특별자치도",
        "target": "제주도 내 단독주택 소유 거주자",
        "support": "태양광(3kW) 설치 시 정부지원금에 도비 매칭 추가 지급",
        "amount": "도비 추가 보조로 실질 자부담 약 10% 미만 실현",
        "url": "https://www.jeju.go.kr",
        "building_types": ["단독주택"],
        "min_age": None,
        "region": "제주",
        "start_date": "2026-03-10",
        "end_date": "2026-10-31",
        "period_str": "2026.03.10 ~ 2026.10.31",
        "direct_cash_manwon": 300,
    },
    # ── [충청] 지역 특화 보조금 ──
    {
        "name": "🌳 충청권 지자체 녹색건축물 개선비 지원사업",
        "org": "충청권 각 광역/기초 지자체",
        "target": "15년 이상 경과한 노후 민간 주택",
        "support": "옥상 단열, 창호, 고효율 보일러 설치비 매칭 무상 보조",
        "amount": "가구당 최대 500만원 이내",
        "url": "시·군·구청 홈페이지 고시 공고",
        "building_types": ["아파트", "단독주택"],
        "min_age": "15~30년",
        "region": "충청",
        "start_date": "2026-02-01",
        "end_date": "2026-07-31",
        "period_str": "2026.02.01 ~ 2026.07.31",
        "direct_cash_manwon": 500,
    },
    # ── [전라] 지역 특화 보조금 ──
    {
        "name": "🏡 전라권 햇살하우스 에너지 효율 개선 사업",
        "org": "전남/전북도청 및 기초지자체",
        "target": "단열 취약 및 에너지 저효율 노후 주택 거주자",
        "support": "벽체 외단열 및 천장 단열 공사 전액 또는 일부 무상 시공",
        "amount": "가구당 시공액 최대 400만원 수준 지원",
        "url": "전라 지역 각 시군구 사회복지/환경과",
        "building_types": ["단독주택"],
        "min_age": "15~30년",
        "region": "전라",
        "start_date": "2026-03-01",
        "end_date": "2026-08-31",
        "period_str": "2026.03.01 ~ 2026.08.31",
        "direct_cash_manwon": 400,
    },
    # ── [경상] 지역 특화 보조금 ──
    {
        "name": "🏛️ 경상권 노후 단독주택 주거환경 개선사업",
        "org": "경상권 각 시도 지자체",
        "target": "관내 건축년도 20년 이상 노후 불량 주택",
        "support": "지붕개량, 외부 도색, 단열 성능 개선 시 자부담 50% 보조",
        "amount": "가구당 최대 800만원 지원",
        "url": "관할 시·군청 주택과 공고 확인",
        "building_types": ["단독주택"],
        "min_age": "15~30년",
        "region": "경상",
        "start_date": "2026-02-01",
        "end_date": "2026-09-30",
        "period_str": "2026.02.01 ~ 2026.09.30",
        "direct_cash_manwon": 800,
    },
    # ── [전국] 공통 보조금 ──
    {
        "name": "🏗️ 민간건축물 그린리모델링 이자지원사업",
        "org": "국토교통부 / LH",
        "target": "노후 건축물의 에너지 효율 개선(창호, 단열)을 원하는 누구나",
        "support": "단열 성능 보강 공사 대출금에 대한 이자 일부 국가 보조(최대 3~4%)",
        "amount": "아파트 최대 2,000만원 / 단독주택 최대 5,000만원 한도 융자 이자 지원",
        "url": "https://www.greenremodeling.or.kr",
        "building_types": ["아파트", "단독주택"],
        "min_age": "15~30년",
        "region": "전국",
        "start_date": "2026-01-02",
        "end_date": "2026-12-15",
        "period_str": "2026.01.02 ~ 2026.12.15 (연중 수시 접수)",
        "direct_cash_manwon": 0, # 이자 지원이므로 현금 보조금 합산에선 0 처리
    },
    {
        "name": "🔥 가정용 친환경 콘덴싱 보일러 교체 지원금",
        "org": "환경부 및 전국 기초지자체",
        "target": "10년 이상 노후된 보일러를 친환경 1등급 콘덴싱으로 교체 시",
        "support": "교체 및 설치 비용의 일부를 현물 정액 지원",
        "amount": "일반 가구당 10만원 / 저소득·취약계층 가구당 60만원",
        "url": "https://www.green-boiler.go.kr",
        "building_types": ["아파트", "단독주택"],
        "min_age": "5~15년",
        "region": "전국",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "period_str": "2026.01.01 ~ 2026.12.31 (예산 한도 내 마감)",
        "direct_cash_manwon": 60, # 최대 수급 가능금액 기준
    },
    {
        "name": "⚡ 한전 고효율 가전제품 구매비용 환급",
        "org": "한국전력공사 (KEPCO)",
        "target": "복지 가구(다자녀, 대가족, 출산 가구, 장애인 등)",
        "support": "1등급 고효율 에너지 기자재(냉장고, 세탁기 등) 구매 비용 환급",
        "amount": "구매 금액의 10~20% 환급 (가구당 최대 30만원)",
        "url": "https://en-ter.co.kr",
        "building_types": ["아파트", "단독주택"],
        "min_age": None,
        "region": "전국",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "period_str": "2026.01.01 ~ 2026.12.31",
        "direct_cash_manwon": 30,
    },
    {
        "name": "☀️ 한국에너지공단 신재생에너지(태양광) 주택지원",
        "org": "한국에너지공단",
        "target": "단독주택 소유주 및 거주자",
        "support": "가정용 태양광 설비(3kW 기준) 설치 총공사비의 40~50% 국비 지원",
        "amount": "국비 약 250~300만원 내외 지원 (매년 공고 확인 필수)",
        "url": "https://www.knrec.or.kr",
        "building_types": ["단독주택"],
        "min_age": None,
        "region": "전국",
        "start_date": "2026-04-10",
        "end_date": "2026-05-31",
        "period_str": "2026.04.10 ~ 2026.05.31 (마감 임박!)",
        "direct_cash_manwon": 300,
    },
    {
        "name": "🏬 에너지공단 건물에너지 융자 및 보조금 지원사업",
        "org": "한국에너지공단",
        "target": "건물의 에너지 절약 시설 및 신재생에너지 설비 도입 건축주",
        "support": "설비 자금 무상 보조 또는 장기 저리 정책 자금 융자",
        "amount": "시설 소요 자금의 최대 70~80% 융자 (연 1.5%~2.5% 변동금리)",
        "url": "https://bpx.kemco.or.kr",
        "building_types": ["상가/오피스"],
        "min_age": None,
        "region": "전국",
        "start_date": "2026-01-15",
        "end_date": "2026-11-30",
        "period_str": "2026.01.15 ~ 2026.11.30",
        "direct_cash_manwon": 0,
    },
    # ── [기한 만료 테스트용 데이터 - 노출되지 않아야 함] ──
    {
        "name": "❄️ 동절기 긴급 노후 주택 난방비 특별 보조",
        "org": "기획재정부",
        "target": "전국 노후 주거시설 소유자",
        "support": "겨울철 급격한 가스비 상승 대비 긴급 난방 보강금 무상 지원",
        "amount": "가구당 30만원 (현금 지급)",
        "url": "https://www.moef.go.kr",
        "building_types": ["아파트", "단독주택"],
        "min_age": "15~30년",
        "region": "전국",
        "start_date": "2025-11-01",
        "end_date": "2026-03-15", # 이미 종료됨!
        "period_str": "2025.11.01 ~ 2026.03.15 (접수 종료)",
    }
]


def get_matching_subsidies(building_type: str, age: str, region: str) -> list:
    """
    건물 유형, 연도, 거주 지역 및 오늘 날짜(접수 기간)에 맞는 보조금 데이터를 필터링 및 정렬합니다.

    우선순위:
    1. 사용자의 현재 지리적 지역(Local) 매칭 데이터 우선 정렬
    2. 범용 전국(National) 공통 지원금 후속 정렬
    3. 타 지역 전용 데이터는 원천 배제
    4. 신청 기간(start_date ~ end_date)에 오늘 날짜가 속한 건만 노출 (마감된 항목 자동 차단)
    """
    # 오늘 날짜 판독 (현재 시뮬레이션: 2026-05-15)
    # 서버 기준 실제 오늘 날짜 로드
    today = datetime.date.today()

    # 연도 순서 (오래될수록 높은 인덱스)
    age_order = ["5년 이내", "5~15년", "15~30년", "30년 이상"]
    user_age_idx = age_order.index(age) if age in age_order else 0

    matched = []
    for s in SUBSIDIES:
        # 1. 기간 필터링 (현재 신청 가능한 건만)
        try:
            start_dt = datetime.datetime.strptime(s["start_date"], "%Y-%m-%d").date()
            end_dt = datetime.datetime.strptime(s["end_date"], "%Y-%m-%d").date()
            if not (start_dt <= today <= end_dt):
                # 현재 모집 기간 외 항목은 제외
                continue
        except (KeyError, ValueError):
            # 날짜 규격이 깨졌거나 없는 항목 보수적으로 처리 (예외 로깅 생략하고 포함하거나 배제)
            pass

        # 2. 건물 유형 필터
        if building_type not in s["building_types"]:
            continue

        # 3. 연도 필터 (min_age가 None이면 연도 무관)
        if s["min_age"] is not None:
            min_idx = age_order.index(s["min_age"]) if s["min_age"] in age_order else 0
            if user_age_idx < min_idx:
                continue

        # 4. 지역 필터 및 점수화
        item_region = s.get("region", "전국")
        
        if item_region == "전국":
            priority = 1 # 전국 공통은 후순위
        elif item_region == region:
            priority = 0 # 지역 맞춤형이 최우선 (낮을수록 앞순서)
        else:
            # 타 지역 전용 데이터는 절대 보여주지 않음 (노이즈 차단)
            continue

        # 정렬용 속성 주입
        matched.append({
            **s,
            "_p_score": priority
        })

    # 우선순위 스코어 기준 오름차순 정렬 (_p_score가 0인 지역 우선, 그 뒤 전국 1)
    matched.sort(key=lambda x: x["_p_score"])
    return matched
