"""
에너지 절감 코치 — 메인 앱 (5단계 마법사)

일반 소비자가 건물 정보를 단계별로 입력하면
AI가 에너지 진단 + 절감 방안 TOP 3 + 정부 보조금을 안내합니다.
"""
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import pandas as pd

# ── 유틸리티 모듈 임포트 ──
from 유틸리티.디자인_스타일 import get_main_css
from 유틸리티.에너지_분석_엔진 import (
    diagnose, won_to_manwon, ELEC_RATE, BUILDING_DEFAULTS,
    AGE_FACTOR, REGION_FACTOR,
)
from 유틸리티.절감_방안_추천 import get_top_recommendations, get_all_recommendations
from 유틸리티.정부_보조금 import get_matching_subsidies
from 유틸리티.기상_정보_조회 import (
    reverse_geocode, geocode, fetch_weather, calc_climate_factor,
    weather_code_to_text, CITY_COORDS,
)

# ── 페이지 설정 ──
st.set_page_config(
    page_title="에너지 절감 코치",
    page_icon="🏠",
    layout="centered",
)
st.markdown(get_main_css(), unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# 세션 스테이트 초기화
# ──────────────────────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step = 1
if "diagnosis" not in st.session_state:
    st.session_state.diagnosis = None
if "recorded_bills" not in st.session_state:
    # 초기 기본값 (만원 단위): 겨울/여름 부하 패턴이 고려된 현실적인 초기 데이터
    st.session_state.recorded_bills = [12, 11, 9, 8, 9, 13, 18, 20, 14, 9, 8, 11]


def go_next():
    st.session_state.step += 1

def go_prev():
    st.session_state.step -= 1

def go_to(n):
    st.session_state.step = n

def restart():
    for key in list(st.session_state.keys()):
        del st.session_state[key]


# ──────────────────────────────────────────────────────────────
# 프로그레스 바 렌더링 (design.md 스타일)
# ──────────────────────────────────────────────────────────────
def render_progress(current: int):
    labels = ["건물 정보", "불편함", "AI 진단", "절감 방안", "보조금"]
    pct = (current / 5) * 100
    
    html = f'''
    <div class="progress-container">
        <div class="progress-info">
            <div class="progress-label">Step {current}/5: {labels[current-1]}</div>
            <div class="progress-label">{int(pct)}% 완료</div>
        </div>
        <div class="progress-track">
            <div class="progress-fill" style="width: {pct}%"></div>
        </div>
    </div>
    '''
    st.markdown(html, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# 공통 컴포넌트: 날씨 위젯
# ──────────────────────────────────────────────────────────────
def _render_weather_widget(weather: dict, geo: dict, cf: float, lat: float, lng: float, show_map: bool = True):
    """날씨 정보 카드와 미니 지도를 일관성 있게 렌더링 (디자인 가이드 반영)"""
    w_text = weather_code_to_text(weather.get("weather_code", 0))
    
    st.markdown(f"""
    <div class="glass-card" style="margin: 16px 0; padding: 20px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <div style="font-family:'Plus Jakarta Sans'; font-size:16px; font-weight:800; color:#071E27; display:flex; align-items:center; gap:6px;">
                    <span class="material-icon" style="font-size:18px; color:#0D631B;">location_on</span>
                    {geo.get('region', '')} {geo.get('city', '') or '정보 없음'}
                </div>
                <div style="font-size:12px; color:#64748B; margin-top:4px; font-weight:500;">{geo.get('full_address', '')[:60]}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:13px; color:#64748B; font-weight:600;">{w_text}</div>
                <div style="font-family:'Plus Jakarta Sans'; font-size:24px; font-weight:800; color:#0D631B;">{weather['current_temp']}°C</div>
            </div>
        </div>
        <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap:12px; margin-top:16px; padding-top:16px; border-top:1px solid rgba(0,0,0,0.05);">
            <div style="display:flex; align-items:center; gap:8px;">
                <span class="material-icon" style="font-size:16px; color:#64748B;">thermostat</span>
                <span style="font-size:12px; color:#40493D;">체감 <b>{weather['feels_like']}°C</b></span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span class="material-icon" style="font-size:16px; color:#64748B;">humidity_percentage</span>
                <span style="font-size:12px; color:#40493D;">습도 <b>{weather['humidity']}%</b></span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span class="material-icon" style="font-size:16px; color:#64748B;">air</span>
                <span style="font-size:12px; color:#40493D;">풍속 <b>{weather['wind_speed']}m/s</b></span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span class="material-icon" style="font-size:16px; color:#0D631B;">verified</span>
                <span style="font-size:12px; color:#0D631B; font-weight:700;">기후 보정: <b>{cf:.2f}</b></span>
            </div>
        </div>
        <div style="font-size:11px; color:#94A3B8; margin-top:12px; text-align:center; background:rgba(0,0,0,0.02); padding:6px; border-radius:8px;">
            📊 HDD {weather['hdd']} · CDD {weather['cdd']} (기상 데이터 기반)
        </div>
    </div>
    """, unsafe_allow_html=True)

    if show_map:
        import pandas as pd
        map_data = pd.DataFrame({"lat": [lat], "lon": [lng]})
        st.map(map_data, zoom=11, use_container_width=True)


def render_step1():
    from streamlit_js_eval import get_geolocation

    # ── 불필요해진 구형 DOM 해킹 통신 코드 제거 및 간결화 ──
def render_step1():
    from streamlit_js_eval import get_geolocation

    # ── [프리미엄 Hero 섹션] ──
    st.markdown("""
    <div class="hero-section">
        <div class="hero-icon-wrapper">
            <span class="material-icon" style="font-size:32px; color:white;">eco</span>
        </div>
        <h1 class="hero-title">에너지 절감 코치</h1>
        <p class="hero-subtitle">건물 정보를 입력하여 AI 기반의 맞춤형 에너지 절감 솔루션을 확인하세요</p>
    </div>
    """, unsafe_allow_html=True)

    # ── 위치 감지 섹션 ──
    st.markdown('<div class="section-title">📍 건물 위치 설정</div>', unsafe_allow_html=True)

    loc_method = st.radio(
        "위치 설정 방법",
        ["📡 자동 감지 (GPS)", "✏️ 직접 선택"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if loc_method == "📡 자동 감지 (GPS)":
        if not st.session_state.get("location_detected"):
            st.markdown("""
            <div class="glass-card" style="text-align:center; padding:40px 20px; border: 1px dashed #0D631B;">
                <div class="material-icon" style="font-size:48px; color:#0D631B; margin-bottom:16px; animation: pulse 2s infinite;">location_searching</div>
                <div style="font-family:'Plus Jakarta Sans'; font-size:18px; font-weight:800; color:#071E27;">디바이스 GPS 수신 중...</div>
                <div style="font-size:14px; color:#64748B; margin-top:8px;">브라우저의 <b>'위치 허용'</b> 권한을 승인해 주세요.</div>
            </div>
            <style>
                @keyframes pulse {
                    0% { transform: scale(0.95); opacity: 0.7; }
                    50% { transform: scale(1.05); opacity: 1; }
                    100% { transform: scale(0.95); opacity: 0.7; }
                }
            </style>
            """, unsafe_allow_html=True)
            
            loc_res = get_geolocation()
            if loc_res and 'coords' in loc_res:
                _fetch_location_data(loc_res['coords']['latitude'], loc_res['coords']['longitude'])
                st.rerun()
            elif loc_res and 'error' in loc_res:
                st.warning("⚠️ GPS 신호를 잡을 수 없습니다. '직접 선택'을 이용해 주세요.")

        # 수동 좌표 입력 (디버그용)
        with st.expander("⚙️ 좌표 수동 보정"):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1: m_lat = st.number_input("위도", value=st.session_state.get("detected_lat", 37.5665), format="%.5f")
            with c2: m_lng = st.number_input("경도", value=st.session_state.get("detected_lng", 126.9780), format="%.5f")
            with c3:
                st.write("")
                if st.button("적용", use_container_width=True):
                    _fetch_location_data(m_lat, m_lng)
                    st.rerun()
    else:
        # 직접 선택 모드
        st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
        tab_addr, tab_city = st.tabs(["🏠 주소 검색", "📌 주요 도시"])
        
        with tab_addr:
            addr = st.text_input("도로명/지번 주소 입력", placeholder="예: 서울특별시 중구 세종대로 110", key="addr_in")
            if st.button("위치 찾기", key="btn_addr", type="primary", use_container_width=True):
                if addr:
                    with st.spinner("위치 조회 중..."):
                        res = geocode(addr)
                        if res.get("success"):
                            _fetch_location_data(res["lat"], res["lng"])
                            st.rerun()
                        else: st.error("주소를 찾을 수 없습니다.")
        
        with tab_city:
            city = st.selectbox("지역 선택", ["서울", "인천", "대전", "대구", "광주", "부산", "울산", "제주"], key="city_sel")
            if st.button("지역 날씨 적용", key="btn_city", use_container_width=True):
                coords = CITY_COORDS.get(city, (37.5665, 126.9780))
                _fetch_location_data(coords[0], coords[1])
                st.rerun()

    # ── [지도 및 날씨 표시] ──
    if st.session_state.get("location_detected"):
        lat, lng = st.session_state.detected_lat, st.session_state.detected_lng
        
        # 라이트 테마 지도
        map_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                body, html {{ margin:0; padding:0; height:100%; }}
                #map {{ height:100%; border-radius:16px; border:1px solid rgba(0,0,0,0.08); }}
                .pulse {{
                    width: 12px; height: 12px;
                    background:     # ── [건물 세부 정보] ──
    st.markdown('<div class="section-title">🏢 건물 세부 정보</div>', unsafe_allow_html=True)

    # 네이버 부동산 가이드 배너 (라이트 테마)
    geo_data = st.session_state.get("detected_geo", {})
    raw_addr = geo_data.get("full_address", "") if isinstance(geo_data, dict) else ""
    if raw_addr:
        parts = [p.strip() for p in raw_addr.split(',') if p.strip()]
        kw = " ".join([p for p in reversed(parts) if p not in ["대한민국", "Korea", "South Korea"]])
    else: kw = st.session_state.get("region", "서울특별시")
    
    import urllib.parse
    naver_url = f"https://new.land.naver.com/search?query={urllib.parse.quote(kw or '부동산')}"

    st.markdown(f"""
    <div style="background:rgba(13, 99, 27, 0.04); border:1px solid rgba(13, 99, 27, 0.15); border-radius:16px; padding:20px; margin-bottom:24px; display:flex; align-items:center; justify-content:space-between;">
        <div style="display:flex; align-items:center; gap:16px;">
            <div style="width:44px; height:44px; background:rgba(13, 99, 27, 0.1); border-radius:12px; display:flex; align-items:center; justify-content:center;">
                <span class="material-icon" style="color:#0D631B; font-size:24px;">info</span>
            </div>
            <div>
                <div style="font-family:'Plus Jakarta Sans'; font-size:15px; font-weight:800; color:#071E27; margin-bottom:2px;">정확한 면적과 연도를 모르시나요?</div>
                <div style="font-size:13px; color:#64748B;">네이버 부동산에서 <b>준공 연월 및 면적</b>을 쉽게 확인하실 수 있습니다.</div>
            </div>
        </div>
        <a href="{naver_url}" target="_blank" style="text-decoration:none;">
            <div style="background:#03C75A; color:white; font-size:13px; font-weight:700; padding:10px 20px; border-radius:10px; display:flex; align-items:center; gap:8px;">
                네이버 부동산 ↗
            </div>
        </a>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        building_type = st.selectbox("건물 유형", ["아파트", "단독주택", "상가/오피스"], key="bt_sel")
    with c2:
        age = st.selectbox("건축 연도", ["5년 이내", "5~15년", "15~30년", "30년 이상"], index=1, key="age_sel")
    with c3:
        pyeong = st.number_input("건물 면적 (평)", 1, 500, 30, 1, key="py_in")

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    
    # ── [전기요금 데이터] ──
    st.markdown('<div class="section-title">📊 월별 전기요금 기록</div>', unsafe_allow_html=True)
    
    ledger_col, chart_col = st.columns([1.2, 1.8])
    with ledger_col:
        st.markdown('<div style="font-size:13px; color:#64748B; margin-bottom:12px;">최근 1년간의 월별 요금을 입력해 주세요. (단위: 만원)</div>', unsafe_allow_html=True)
        sub1, sub2 = st.columns(2)
        for i in range(12):
            with (sub1 if i < 6 else sub2):
                val = st.number_input(f"{i+1}월", 0, 1000, int(st.session_state.recorded_bills[i]), 1, key=f"bill_{i}")
                st.session_state.recorded_bills[i] = int(val)

    with chart_col:
        months = [f"{i}월" for i in range(1, 13)]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=months, y=st.session_state.recorded_bills,
            mode='lines+markers+text',
            line=dict(color='#0D631B', width=3, shape='spline'),
            marker=dict(size=8, color='white', line=dict(width=2, color='#0D631B')),
            fill='tozeroy', fillcolor='rgba(13, 99, 27, 0.05)'
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=20, b=0), height=280,
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", title="요금 (만원)")
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # 세션 동기화
    st.session_state.building_type = building_type
    st.session_state.age = age
    st.session_state.region = region
    st.session_state.pyeong = pyeong

    st.markdown('<div style="height:40px;"></div>', unsafe_allow_html=True)
    if st.button("다음 단계로 이동 →", type="primary", use_container_width=True, on_click=go_next):
        pass
. 실시간으로 전력 소비 추이를 차트화하여 정밀 분석을 제공합니다."
        "</p>", 
        unsafe_allow_html=True
    )

    ledger_col, chart_col = st.columns([1.2, 2])

    with ledger_col:
        # 12개월 기본 리스트
        months_list = [f"{i}월" for i in range(1, 13)]
        
        st.markdown("<div style='padding-bottom: 8px; border-bottom: 1px solid #334155; margin-bottom: 12px;'><span style='font-size:13.5px; font-weight:700; color:#E2E8F0;'>💰 월별 요금 입력 (단위: 만원)</span></div>", unsafe_allow_html=True)
        
        # 두 개의 열로 6개월씩 깔끔하게 배치
        sub_l, sub_r = st.columns(2)
        
        for i in range(12):
            target_sub = sub_l if i < 6 else sub_r
            with target_sub:
                # Streamlit 고유 입력기로 원천적 버그 예방 및 매끄러운 UX 보장
                val = st.number_input(
                    f"{i+1}월 요금",
                    min_value=0,
                    max_value=1000,
                    value=int(st.session_state.recorded_bills[i]),
                    step=1,
                    key=f"bill_input_{i}"
                )
                # 입력 즉시 세션에 정수형 데이터 동기화
                st.session_state.recorded_bills[i] = int(val)

    with chart_col:
        # 실시간 기록 변화 차트 렌더링
        fig_log = go.Figure()
        fig_log.add_trace(go.Scatter(
            x=months_list, 
            y=st.session_state.recorded_bills,
            mode='lines+markers',
            name='기록된 요금',
            line=dict(color='#50C878', width=3, shape='spline'),
            marker=dict(size=8, color='#10B981', line=dict(width=2, color='#FFFFFF')),
            hovertemplate="%{x} 요금: <b>%{y}만원</b><extra></extra>"
        ))
        fig_log.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", 
            plot_bgcolor="rgba(15,23,42,0.4)",
            font=dict(family="Inter", color="#E2E8F0", size=11),
            xaxis=dict(gridcolor="#334155", zeroline=False),
            yaxis=dict(gridcolor="#334155", zeroline=False, title="전기요금 (만원)"),
            height=280,
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig_log, config={'displayModeBar': False}, use_container_width=True, key="realtime_trend")

    # 세션 변수 통합 (건물 정보 동기화)
    st.session_state.building_type = building_type
    st.session_state.age = age
    st.session_state.region = region
    st.session_state.pyeong = pyeong

    st.markdown("")
    col_l, col_r = st.columns([3, 1])
    with col_r:
        st.button("다음 단계 →", on_click=go_next, use_container_width=True)




# ──────────────────────────────────────────────────────────────
# STEP 2: 우리 건물 성능 정량 평가 (1~5단계)
# ──────────────────────────────────────────────────────────────
def render_step2():
    st.markdown("""
    <div class="hero">
        <div style="font-size:44px;margin-bottom:4px;">📊</div>
        <div class="hero-title">우리 건물 성능 정량 평가</div>
        <div class="hero-sub">실제 생활 체감을 기반으로 건물 에너지 성능을 1~5단계로 정밀 진단합니다.</div>
    </div>
    """, unsafe_allow_html=True)

    # 시각적 안내 블록
    st.markdown("""
    <div style="background:rgba(56,189,248,0.06);border:1px solid rgba(56,189,248,0.2);border-radius:12px;padding:15px 18px;margin-top:10px;margin-bottom:28px;">
        <div style="font-size:13px;color:#38BDF8;font-weight:800;margin-bottom:4px;">💡 정량 평가 가이드</div>
        <div style="font-size:12px;color:#E2E8F0;line-height:1.6;">
            • <b>1단계(우수)</b>에 가까울수록 신축 패시브하우스급의 뛰어난 에너지 세이빙 상태를 의미합니다.<br>
            • <b>5단계(취약)</b>에 가까울수록 자재 노후 및 열적 결손으로 인한 에너지 낭비가 극도로 심한 상태입니다.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 정량 설문 항목 4선 ──
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 💨 1. 외풍 차단 수준 (기밀성)")
        airtight_score = st.select_slider(
            "창문이나 틈새로 들어오는 바람의 정도",
            options=[1, 2, 3, 4, 5],
            value=2,
            format_func=lambda x: {
                1: "1단계: 완벽 차단 (밀봉급)",
                2: "2단계: 체감하기 힘듦 (양호)",
                3: "3단계: 바람 부는 날 가끔 유입",
                4: "4단계: 겨울철 명확한 외풍 느낌",
                5: "5단계: 황소바람 유입 (심각)"
            }[x],
            key="survey_airtight"
        )
        st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True)

        st.markdown("##### ❄️ 2. 실내 온도 보존력 (단열성)")
        insulation_score = st.select_slider(
            "냉난방 중단 후 실내 온기가 보존되는 시간",
            options=[1, 2, 3, 4, 5],
            value=2,
            format_func=lambda x: {
                1: "1단계: 3시간 이상 안정적 지속",
                2: "2단계: 1~2시간 내외 유지 (보통)",
                3: "3단계: 끄고 30분 내외로 금방 식음",
                4: "4단계: 정지 즉시 실내가 추워짐/더워짐",
                5: "5단계: 바깥 날씨와 즉각 동기화"
            }[x],
            key="survey_insulation"
        )

    with col2:
        st.markdown("##### 🌡️ 3. 냉난방 도달 속도 (설비 효율)")
        hvac_score = st.select_slider(
            "에어컨/보일러 가동 시 목표 온도 도달 시간",
            options=[1, 2, 3, 4, 5],
            value=2,
            format_func=lambda x: {
                1: "1단계: 15분 내 즉각 쾌적 온도 도달",
                2: "2단계: 30분 내외 원활한 조절 (보통)",
                3: "3단계: 1시간 연속 가동 시 겨우 도달",
                4: "4단계: 가동 대비 온도 하락/상승이 더딤",
                5: "5단계: 하루종일 틀어도 효과가 적음"
            }[x],
            key="survey_hvac"
        )
        st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True)

        st.markdown("##### ☀️ 4. 여름철 일사 부하 (채광열)")
        solar_score = st.select_slider(
            "커튼 없는 여름철 창을 통한 복사열 강도",
            options=[1, 2, 3, 4, 5],
            value=2,
            format_func=lambda x: {
                1: "1단계: 온화하고 은은한 채광",
                2: "2단계: 적절한 일시적 눈부심 (보통)",
                3: "3단계: 햇빛이 너무 강해 커튼이 필요",
                4: "4단계: 창가 주변이 후끈 달아오름",
                5: "5단계: 실내가 온실처럼 열기가 갇힘"
            }[x],
            key="survey_solar"
        )

    # 점수 데이터 바인딩
    st.session_state.discomfort_scores = {
        "airtight": airtight_score,
        "insulation": insulation_score,
        "hvac": hvac_score,
        "solar": solar_score
    }

    # 리모델링 의향
    st.markdown("<div style='height:35px;'></div>", unsafe_allow_html=True)
    remodel = st.checkbox("🏗️ 향후 단열/창호 개보수 또는 리모델링을 검토 중이신가요?", value=False,
                          help="선택 시 취약한 부분을 분석하여 우선 투자 회수 리포트를 추가 제공합니다.")
    st.session_state.remodel = remodel

    st.markdown("")
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.button("← 이전", on_click=go_prev, use_container_width=True)
    with col_r:
        st.button("AI 진단 시작 🔬", on_click=run_diagnosis, use_container_width=True)


def run_diagnosis():
    """정량 점수 딕셔너리를 사용하여 진단 엔진 구동"""
    cf = st.session_state.get("climate_factor", None)

    result = diagnose(
        pyeong=st.session_state.pyeong,
        building_type=st.session_state.building_type,
        age=st.session_state.age,
        region=st.session_state.region,
        discomfort_scores=st.session_state.discomfort_scores,
        recorded_bills=st.session_state.recorded_bills,
        climate_factor=cf,
    )
    st.session_state.diagnosis = result
    st.session_state.step = 3


# ──────────────────────────────────────────────────────────────
# STEP 3: AI 진단 결과
# ──────────────────────────────────────────────────────────────
def render_step3():
    dx = st.session_state.diagnosis
    if dx is None:
        st.error("진단 데이터가 없습니다. 처음부터 다시 시작해주세요.")
        st.button("처음으로", on_click=restart)
        return

    grade = dx["grade"]
    grade_css = dx["grade_css"]
    is_good = grade in ("A+", "A", "B")

    # 헤더
    emoji = "✅" if is_good else "⚠️"
    st.markdown(f"""
    <div class="hero">
        <div style="font-size:44px;margin-bottom:4px;">{emoji}</div>
        <div class="hero-title">AI 진단 결과</div>
        <div class="hero-sub">{st.session_state.building_type} · {st.session_state.pyeong}평 · {st.session_state.region} · {st.session_state.age}</div>
    </div>
    """, unsafe_allow_html=True)

    # 등급 + 비용 배너
    banner_bg = "linear-gradient(135deg,#071A0E,#0A2A18)" if is_good else "linear-gradient(135deg,#1A0C07,#2A1510)"
    border_c = "#1A5C35" if is_good else "#5C2A1A"
    cost_color = "#50C878" if is_good else "#F87171"

    annual_cost_str = won_to_manwon(dx["current_cost"])
    optimal_str = won_to_manwon(dx["optimal_cost"])
    saving_str = won_to_manwon(dx["saving_potential"])

    st.markdown(f"""
    <div style="background:{banner_bg};border:1px solid {border_c};border-radius:20px;
                padding:28px 36px;display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;">
        <div>
            <div style="font-size:12px;color:#4A6080;font-weight:600;letter-spacing:1px;margin-bottom:8px;">
                에너지 효율 진단 결과
            </div>
            <div style="font-size:15px;color:#E2E8F0;margin-bottom:6px;">
                연간 예상 전기요금: <b style="font-size:24px;color:{cost_color}">{annual_cost_str}</b>
            </div>
            <div style="font-size:13px;color:#6B8AB0;">
                같은 조건 최적 건물: {optimal_str} &nbsp;·&nbsp;
                <span style="color:{cost_color};font-weight:700;">최대 {saving_str} 절감 가능</span>
            </div>
        </div>
        <div style="text-align:center;flex-shrink:0;margin-left:24px;">
            <div class="grade-badge {grade_css}">{grade}</div>
            <div style="font-size:11px;color:#4A6080;margin-top:8px;font-weight:600;">에너지 효율 등급</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 기후 인텔리전스 적용 태그 ──
    rf = dx["params"]["region_factor"]
    is_realtime = st.session_state.get("location_detected", False)
    
    if is_realtime:
        geo = st.session_state.get("detected_geo", {})
        region_str = f"{geo.get('region', '')} {geo.get('city', '')}".strip() or st.session_state.region
        st.markdown(f"""
        <div style="background:rgba(56,189,248,0.08);border:1px solid rgba(56,189,248,0.25);border-radius:12px;
                    padding:12px 18px;margin-bottom:16px;display:flex;align-items:center;gap:10px;font-size:13px;">
            <span style="font-size:16px;">🛰️</span>
            <span style="color:#E2E8F0;">
                <b>실시간 기후 인텔리전스 적용:</b> {region_str}의 1년 기후 데이터 분석 완료 (기후 보정: <b>{rf:.2f}배</b>)
            </span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:rgba(107,138,176,0.08);border:1px solid rgba(107,138,176,0.2);border-radius:12px;
                    padding:12px 18px;margin-bottom:16px;display:flex;align-items:center;gap:10px;font-size:13px;">
            <span style="font-size:16px;">📊</span>
            <span style="color:#6B8AB0;">
                <b>표준 지역 통계 적용:</b> {st.session_state.region}의 기본 기후 계수 적용 (지역 보정: <b>{rf:.2f}배</b>)
            </span>
        </div>
        """, unsafe_allow_html=True)

    # KPI 3개
    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi">
            <div class="label">연간 에너지</div>
            <div class="value" style="color:#38BDF8">{dx['current_kwh']/1000:.1f} <span style="font-size:14px;color:#4A6080">MWh</span></div>
            <div class="sub">최적 {dx['optimal_kwh']/1000:.1f} MWh</div>
        </div>
        <div class="kpi">
            <div class="label">월 예상 비용</div>
            <div class="value" style="color:#FFB347">{won_to_manwon(dx['current_cost']/12)}</div>
            <div class="sub">최적 {won_to_manwon(dx['optimal_cost']/12)}</div>
        </div>
        <div class="kpi">
            <div class="label">절감 가능액</div>
            <div class="value" style="color:#50C878">{saving_str}</div>
            <div class="sub">연간 기준</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 에너지 낭비 게이지
    st.markdown("#### 📊 에너지 낭비 포인트")
    for name, data in dx["gauges"].items():
        score = data["score"]
        detail = data["detail"]
        if score >= 60:
            fill_cls = "bad"
        elif score >= 30:
            fill_cls = "warn"
        else:
            fill_cls = "good"

        st.markdown(f"""
        <div class="gauge-container">
            <div class="gauge-label">
                <span class="name">{name}</span>
                <span class="value">{detail}</span>
            </div>
            <div class="gauge-bar">
                <div class="gauge-fill {fill_cls}" style="width:{score}%"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 월별 요금 차트
    st.markdown("#### 📅 월별 전기요금 비교 패턴")
    st.markdown(f"""
    <div style='background: rgba(30, 41, 59, 0.5); border-left: 3px solid #3B82F6; padding: 10px 14px; border-radius: 6px; margin-top: -10px; margin-bottom: 15px;'>
        <p style='font-size:12.5px; color:#E2E8F0; margin:0; font-weight:600;'>💡 최적 건물 비교 기준 안내</p>
        <p style='font-size:11.5px; color:#94A3B8; margin:4px 0 0 0; line-height:1.5;'>
            동일 면적의 최신 <b>글로벌 패시브하우스(Passive House) 인증 수준</b>을 충족하는 고성능 건물(창면적비 25%, 외단열 200mm, 초고밀도 기밀 설계, 1등급 고효율 히트펌프 탑재)의 이론적 요금 한계선입니다.<br>
            선택하신 <b>{st.session_state.building_type}</b> 전용 에너지 강도 기저율을 적용하고 지역 기후 편차를 보정하여, 현실적으로 달성 가능한 최적의 절감 가이드를 제시합니다.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    months = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"]
    # 실제 기록 데이터 가져오기 (만원)
    m_now = st.session_state.recorded_bills 
    # 최적 건물 에너지(kWh)를 요금(만원)으로 환산: (kWh * 130원) / 10000원
    m_opt = [(kwh * ELEC_RATE) / 10000.0 for kwh in dx["monthly_opt"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=months, y=m_opt, name="최적 건물 (요금)",
        marker_color="rgba(107,138,176,0.35)",
        hovertemplate="%{x} 최적: <b>%{y:.1f}만원</b><extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=months, y=m_now, name="기록된 내 건물 요금",
        marker_color="#F87171" if not is_good else "#50C878",
        hovertemplate="%{x} 내요금: <b>%{y}만원</b><extra></extra>"
    ))
    fig.update_layout(
        paper_bgcolor="#0A0F1E", plot_bgcolor="#0D1526",
        font=dict(family="Inter", color="#E2E8F0"),
        xaxis=dict(gridcolor="#1A2740"),
        yaxis=dict(gridcolor="#1A2740", title="전기요금 (만원)"),
        barmode="group", bargap=0.25, height=300,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#94A3B8"),
                    orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=16, r=16, t=40, b=16),
    )
    st.plotly_chart(fig, key="step3_chart", use_container_width=True)

    st.markdown("")
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.button("← 이전", on_click=go_prev, use_container_width=True, key="s3_prev")
    with col_r:
        st.button("절감 방안 보기 →", on_click=go_next, use_container_width=True, key="s3_next")


# ──────────────────────────────────────────────────────────────
# STEP 4: 맞춤형 절감 방안 가이드
# ──────────────────────────────────────────────────────────────
def render_step4():
    dx = st.session_state.diagnosis
    if dx is None:
        st.error("진단 데이터가 없습니다.")
        st.button("처음으로", on_click=restart)
        return

    st.markdown("""
    <div class="hero">
        <div style="font-size:44px;margin-bottom:4px;">💡</div>
        <div class="hero-title">맞춤형 절감 방안 추천</div>
        <div class="hero-sub">필터링 기준에 따라 AI가 선별한 건물의 최적 개선 솔루션을 확인해보세요</div>
    </div>
    """, unsafe_allow_html=True)

    all_recs = get_all_recommendations(dx, st.session_state.pyeong)
    rank_icons = ["🥇", "🥈", "🥉", "🎖️", "🎖️", "🎖️", "🎖️", "🎖️"]

    # 기준별 탭 생성
    tab_overall, tab_invest, tab_saving, tab_pct = st.tabs([
        "🏆 종합 추천 기준", 
        "💰 투자비 절약 기준", 
        "🔥 절감 금액 기준", 
        "⚡ 절감률 효율 기준"
    ])

    def render_rec_list(sorted_list, group_label, highlight_col=""):
        """지정된 정렬 리스트를 렌더링하고 동적 요약 패널을 노출합니다."""
        for idx, rec in enumerate(sorted_list[:4]): # 각 탭당 상위 4개씩 노출
            invest_str = f"{rec['invest_manwon']:,.0f}만원"
            saving_str = won_to_manwon(rec["annual_saving_won"])
            payback_str = f"{rec['payback_years']}년"

            # 정렬 기준 컬럼 시각적 강조 처리
            inv_hl = "border-bottom: 2px solid #FFB347; font-weight: bold; padding-bottom: 1px;" if highlight_col == "invest" else ""
            sav_hl = "border-bottom: 2px solid #50C878; font-weight: bold; padding-bottom: 1px;" if highlight_col == "saving" else ""
            pct_hl = "border-bottom: 2px solid #38BDF8; font-weight: bold; padding-bottom: 1px;" if highlight_col == "pct" else ""

            st.markdown(f"""
            <div class="rec-card">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
                    <span style="font-size:28px;">{rank_icons[idx]}</span>
                    <span style="font-size:22px;">{rec['icon']}</span>
                    <div>
                        <div class="title">{rec['name']}</div>
                        <span class="{rec['diff_css']}">{rec['difficulty']}</span>
                    </div>
                </div>
                <div class="desc">{rec['desc']}</div>
                <div class="rec-metrics">
                    <div class="rec-metric">
                        <div class="label">투자비</div>
                        <div class="val" style="color:#FFB347;{inv_hl}">{invest_str}</div>
                    </div>
                    <div class="rec-metric">
                        <div class="label">연간 절감</div>
                        <div class="val" style="color:#50C878;{sav_hl}">{saving_str}</div>
                    </div>
                    <div class="rec-metric">
                        <div class="label">회수 기간</div>
                        <div class="val" style="color:#38BDF8;">{payback_str}</div>
                    </div>
                    <div class="rec-metric">
                        <div class="label">절감률</div>
                        <div class="val" style="color:#E2E8F0;{pct_hl}">{rec['saving_pct']}%</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 상위 3개 선택 시 총 절감 요약
        top3 = sorted_list[:3]
        total_saving = sum(r["annual_saving_won"] for r in top3)
        total_invest = sum(r["invest_manwon"] for r in top3)
        st.markdown(f"""
        <div style="background:rgba(13, 21, 38, 0.6);border:1px solid #1A5C35;border-radius:14px;padding:18px;margin-top:16px;text-align:center;">
            <div style="font-size:13px;color:#94A3B8;font-weight:600;">💡 {group_label} 상위 3개 방안 결합 적용 시</div>
            <div style="font-size:15px;color:#E2E8F0;margin-top:8px;font-weight:500;">
                총 예상 투자비: <b style="color:#FFB347;">{total_invest:,.0f}만원</b> &nbsp;→&nbsp;
                연간 요금 절감액: <b style="color:#50C878;">{won_to_manwon(total_saving)}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 1. 종합 추천 기준 (우선순위 Score 내림차순)
    with tab_overall:
        st.markdown("<p style='color:#94A3B8; font-size:13px; margin-bottom:16px;'>💡 회수 기간과 현재 건물의 부하 상태(냉난방/단열)를 종합적으로 균형 있게 고려한 AI 베스트 추천순입니다.</p>", unsafe_allow_html=True)
        recs_sorted = sorted(all_recs, key=lambda x: x["priority"], reverse=True)
        render_rec_list(recs_sorted, "종합 추천")

    # 2. 투자비 절약 기준 (투자비 오름차순 - 낮은 것 우선)
    with tab_invest:
        st.markdown("<p style='color:#94A3B8; font-size:13px; margin-bottom:16px;'>💡 초기 투입되는 시공 비용이 가장 적은 항목 순으로 나열합니다. 가벼운 셀프 개선이나 저가형 시공이 우선 배치됩니다.</p>", unsafe_allow_html=True)
        recs_sorted = sorted(all_recs, key=lambda x: x["invest_manwon"])
        render_rec_list(recs_sorted, "최저 투자비", highlight_col="invest")

    # 3. 절감 금액 기준 (연간 절감액 내림차순 - 높은 것 우선)
    with tab_saving:
        st.markdown("<p style='color:#94A3B8; font-size:13px; margin-bottom:16px;'>💡 매달 통장에서 나가는 실제 전기요금을 가장 '많이' 줄여주는 현금 환산 가치가 높은 항목 순서입니다.</p>", unsafe_allow_html=True)
        recs_sorted = sorted(all_recs, key=lambda x: x["annual_saving_won"], reverse=True)
        render_rec_list(recs_sorted, "최대 현금 절감", highlight_col="saving")

    # 4. 절감률 효율 기준 (에너지 절감 비율 내림차순 - 높은 것 우선)
    with tab_pct:
        st.markdown("<p style='color:#94A3B8; font-size:13px; margin-bottom:16px;'>💡 투자 규모와 상관없이 물리적인 에너지 소비량 단위를 순수하게 가장 크게 낮춰주는 효율 기술 성능 순서입니다.</p>", unsafe_allow_html=True)
        recs_sorted = sorted(all_recs, key=lambda x: x["saving_pct"], reverse=True)
        render_rec_list(recs_sorted, "최고 절감 효율", highlight_col="pct")

    st.markdown("")
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.button("← 진단 결과", on_click=go_prev, use_container_width=True, key="s4_prev")
    with col_r:
        st.button("보조금 확인 →", on_click=go_next, use_container_width=True, key="s4_next")


# ──────────────────────────────────────────────────────────────
# STEP 5: 정부 보조금 안내
# ──────────────────────────────────────────────────────────────
def render_step5():
    region_nm = st.session_state.region
    
    # 보조금 리스트 먼저 조회 (배너 요약 계산용)
    subsidies = get_matching_subsidies(
        st.session_state.building_type,
        st.session_state.age,
        st.session_state.region,
    )
    
    st.markdown(f"""
    <div class="hero">
        <div style="font-size:44px;margin-bottom:4px;">🏛️</div>
        <div class="hero-title">활용 가능한 정부 보조금</div>
        <div class="hero-sub">📍{region_nm} 지역 혜택 및 전국 공동 지원 사업을 조회했습니다</div>
    </div>
    """, unsafe_allow_html=True)

    # 상단에 정부 보조금 혜택 총합을 안내하는 프리미엄 요약 배너 배치
    dx = st.session_state.diagnosis
    if dx:
        saving_str = won_to_manwon(dx["saving_potential"])
        total_direct_cash = sum(s.get("direct_cash_manwon", 0) for s in subsidies)
        
        # 주의: Markdown 마크업 파싱 에러 방지를 위해 HTML 컨텐츠는 첫 칸(No Indent)부터 작성해야 합니다.
        st.markdown(f"""
<div style="background:linear-gradient(135deg,#0D2240,#0F3A5F);border:1px solid #1A4B73;border-radius:16px;padding:24px 20px;margin-top:10px;margin-bottom:28px;box-shadow:0 4px 15px rgba(0,0,0,0.35);">
<div style="font-size:13px;color:#60A5FA;margin-bottom:8px;text-align:center;font-weight:700;letter-spacing:1px;">📋 종합 진단 혜택 요약</div>
<div style="font-size:18px;color:#F1F5F9;font-weight:800;text-align:center;margin-bottom:20px;letter-spacing:-0.5px;">{st.session_state.building_type} · {st.session_state.pyeong}평 · 에너지 등급 <span style="color:#50C878;">{dx['grade']}</span></div>
<div style="display:flex;flex-wrap:wrap;justify-content:space-around;border-top:1px solid #1E4A6F;padding-top:20px;gap:12px;">
<div style="text-align:center;min-width:140px;flex:1;">
<div style="font-size:12px;color:#94A3B8;margin-bottom:6px;font-weight:600;">⚡ 연간 예상 에너지 요금 절감</div>
<div style="font-size:22px;color:#10B981;font-weight:900;">{saving_str}</div>
</div>
<div style="width:1px;background:#1E4A6F;align-self:stretch;display:block;"></div>
<div style="text-align:center;min-width:140px;flex:1;">
<div style="font-size:12px;color:#94A3B8;margin-bottom:6px;font-weight:600;">🎁 정부 보조금 혜택 (최대)</div>
<div style="font-size:22px;color:#3B82F6;font-weight:900;">{total_direct_cash}만원</div>
</div>
</div>
<div style="text-align:center;font-size:11px;color:#4A6B8F;margin-top:16px;">* 지원 조건 및 금융 지원(무이자 융자 등) 혜택에 따라 최종 수급액은 변동될 수 있습니다.</div>
</div>
""", unsafe_allow_html=True)

    # 개별 보조금 카드 렌더링
    if not subsidies:
        st.info("현재 조건에 맞는 보조금 프로그램이 없습니다. 지자체별 추가 지원을 확인해보세요.")
    else:
        for s in subsidies:
            # 지역/전국 여부에 따라 뱃지 다변화
            is_local = s.get("_p_score", 1) == 0
            badge_html = ""
            if is_local:
                badge_html = f"""<span style="background:#10B98120;color:#10B981;border:1px solid #10B98140;
                              font-size:11px;padding:3px 8px;border-radius:12px;font-weight:600;
                              margin-left:8px;vertical-align:middle;">📍 {region_nm} 전용</span>"""
            else:
                badge_html = """<span style="background:#3B82F620;color:#60A5FA;border:1px solid #3B82F640;
                              font-size:11px;padding:3px 8px;border-radius:12px;font-weight:600;
                              margin-left:8px;vertical-align:middle;">🇰🇷 전국 공통</span>"""

            st.markdown(f"""
<div class="subsidy-card">
    <div class="name" style="display:flex;justify-content:space-between;align-items:center;">
        <span>{s['name']}</span>
        {badge_html}
    </div>
    <div class="detail">
        <b>지원 기관:</b> {s['org']}<br>
        <b>대상:</b> {s['target']}<br>
        <b>지원 내용:</b> {s['support']}<br>
        <b>신청 기간:</b> <span style="color:#EAB308;font-weight:600;">{s.get('period_str', '연중 상시')}</span><br>
        <b>지원 금액:</b> <span style="color:#50C878;font-weight:700;">{s['amount']}</span><br>
        <b>바로가기:</b> <a href="{s['url']}" target="_blank" style="color:#3B82F6;text-decoration:underline;font-size:13px;">{s['url']}</a>
    </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("")
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.button("← 절감 방안", on_click=go_prev, use_container_width=True, key="s5_prev")
    with col_r:
        st.button("🔄 처음부터 다시", on_click=restart, use_container_width=True, key="s5_restart")



# ──────────────────────────────────────────────────────────────
# 메인 라우터
# ──────────────────────────────────────────────────────────────
current_step = st.session_state.step
render_progress(current_step)

if current_step == 1:
    render_step1()
elif current_step == 2:
    render_step2()
elif current_step == 3:
    render_step3()
elif current_step == 4:
    render_step4()
elif current_step == 5:
    render_step5()
else:
    render_step1()
