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
# pyrefly: ignore [missing-import]
from utils.styles import get_main_css
from utils.energy_engine import (
    diagnose, won_to_manwon, ELEC_RATE, BUILDING_DEFAULTS,
    AGE_FACTOR, REGION_FACTOR,
)
from utils.recommendations import get_top_recommendations, get_all_recommendations
from utils.subsidies import get_matching_subsidies
from utils.weather import (
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
# 데이터 저장/불러오기 로직 (간단한 JSON 기반)
# ──────────────────────────────────────────────────────────────
def load_user_data(username):
    import os, json
    DB_FILE = "user_data.json"
    if not os.path.exists(DB_FILE): return None
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(username)
    except:
        return None

def save_user_data(username, bills):
    if not username: return
    import os, json
    DB_FILE = "user_data.json"
    data = {}
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            pass
    
    if username not in data:
        data[username] = {}
    
    data[username]["recorded_bills"] = bills
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ──────────────────────────────────────────────────────────────
# 세션 스테이트 초기화
# ──────────────────────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step = 0
if "diagnosis" not in st.session_state:
    st.session_state.diagnosis = None
if "recorded_bills" not in st.session_state:
    # 초기 기본값 (만원 단위): 겨울/여름 부하 패턴이 고려된 현실적인 초기 데이터
    st.session_state.recorded_bills = [12, 11, 9, 8, 9, 13, 18, 20, 14, 9, 8, 11]
if "username" not in st.session_state:
    st.session_state.username = None
if "building_type" not in st.session_state:
    st.session_state.building_type = "아파트"
if "age" not in st.session_state:
    st.session_state.age = "5~15년"
if "region" not in st.session_state:
    st.session_state.region = "서울·경기"
if "pyeong" not in st.session_state:
    st.session_state.pyeong = 30
if "discomfort_scores" not in st.session_state:
    st.session_state.discomfort_scores = {"airtight": 2, "insulation": 2, "hvac": 2, "solar": 2}


def go_next():
    st.session_state.step += 1

def go_prev():
    st.session_state.step -= 1

def go_to(n):
    st.session_state.step = n

def restart():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ──────────────────────────────────────────────────────────────
# 프로그레스 바 렌더링
# ──────────────────────────────────────────────────────────────
def render_progress(current: int):
    if current == 0:
        return
    labels = ["건물 정보", "불편함", "AI 진단", "절감 방안", "보조금"]
    html = '<div class="progress-bar">'
    for i, label in enumerate(labels, 1):
        if i < current:
            cls = "done"
        elif i == current:
            cls = "active"
        else:
            cls = "pending"
        html += f'<div class="step-circle {cls}">{i}</div>'
        if i < 5:
            conn_cls = "done" if i < current else "pending"
            html += f'<div class="step-connector {conn_cls}"></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# STEP 0: 사용자 로그인 / 계정 연동
# ──────────────────────────────────────────────────────────────
def _mock_social_login(provider):
    import time
    # 프로토타입/MVP 테스트용 목업 ID 생성
    mock_id = f"{provider}_user_001" 
    st.session_state.username = mock_id
    
    saved_data = load_user_data(st.session_state.username)
    if saved_data and "recorded_bills" in saved_data:
        st.session_state.recorded_bills = saved_data["recorded_bills"]
        st.success(f"✅ [{provider.upper()}] 간편 로그인 성공! 기존 데이터를 불러왔습니다.")
    else:
        st.info(f"✅ [{provider.upper()}] 간편 로그인 성공! 새로운 세션이 생성되었습니다.")
    
    time.sleep(1.2)
    st.session_state.step = 1
    st.rerun()

def render_step0():
    st.markdown("""
    <div class="hero">
        <div style="font-size:44px;margin-bottom:4px;">👋</div>
        <div class="hero-title">에너지 절감 코치 시작하기</div>
        <div class="hero-sub">안전하고 간편하게 3초 만에 소셜 계정으로 시작하세요</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🟡 카카오로 시작", use_container_width=True):
            _mock_social_login("kakao")
            
    with col2:
        if st.button("🟢 네이버로 시작", use_container_width=True):
            _mock_social_login("naver")
            
    with col3:
        if st.button("⚪ 구글로 시작", use_container_width=True):
            _mock_social_login("google")

    st.markdown("""
    <div style='background:#F8FAFC; border:1px solid #E2E8F0; padding:15px; border-radius:12px; margin-top:30px; font-size:12px; color:#475569;'>
        <b style="color:#0EA5E9;">💡 상용화 가이드 (개발자용)</b><br>
        현재는 <b>OAuth 시뮬레이션(Mock) 모드</b>로 동작합니다. 테스트를 위해 카카오/네이버/구글 클릭 시 각각 고정된 <code>_user_001</code> ID로 세션이 발급되어, 데이터가 어떻게 분리 저장되고 불러와지는지 체험할 수 있습니다.<br>
        실제 서비스 배포 시에는 <a href="https://console.firebase.google.com/" target="_blank">Firebase Auth</a> 또는 각 플랫폼 개발자 센터의 Client API Key를 입력하여 코드를 치환하면 완벽한 보안 환경이 구성됩니다.
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# STEP 1: 건물 기본 정보 입력 + 위치 자동감지
# ──────────────────────────────────────────────────────────────
def _detect_location():
    """브라우저 GPS 좌표를 다시 받아오기 위해 JS 코드를 실행"""
    st.session_state.location_requested = True

def _fetch_location_data(lat: float, lng: float):
    """좌표로부터 주소 + 기상 데이터를 가져와 세션에 저장"""
    geo = reverse_geocode(lat, lng)
    weather = fetch_weather(lat, lng)
    climate_f = calc_climate_factor(weather)

    st.session_state.detected_lat = lat
    st.session_state.detected_lng = lng
    st.session_state.detected_geo = geo
    st.session_state.detected_weather = weather
    st.session_state.climate_factor = climate_f
    st.session_state.location_detected = True


def _render_weather_widget(weather: dict, geo: dict, cf: float, lat: float, lng: float, show_map: bool = True):
    """날씨 정보 카드와 미니 지도를 일관성 있게 렌더링"""
    w_text = weather_code_to_text(weather.get("weather_code", 0))
    
    st.markdown(f"""
    <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:14px;padding:18px;margin:10px 0;box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div style="font-size:15px;font-weight:700;color:#1E293B;">📍 {geo.get('region', '')} {geo.get('city', '')}</div>
                <div style="font-size:12px;color:#64748B;margin-top:4px;">{geo.get('full_address', '')[:60]}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:13px;color:#1E293B;">{w_text}</div>
                <div style="font-size:22px;font-weight:800;color:#0ea5e9;">{weather['current_temp']}°C</div>
            </div>
        </div>
        <div style="display:flex;gap:20px;margin-top:12px;font-size:12px;color:#64748B;flex-wrap:wrap;">
            <span>체감 {weather['feels_like']}°C</span>
            <span>습도 {weather['humidity']}%</span>
            <span>풍속 {weather['wind_speed']}m/s</span>
            <span>연평균 {weather['avg_temp']}°C</span>
            <span style="color:#059669;font-weight:700;">기후 보정: {cf:.2f}</span>
        </div>
        <div style="font-size:11px;color:#94A3B8;margin-top:8px;">
            📊 365일 기상 데이터 기반 | 난방도일(HDD) {weather['hdd']} · 냉방도일(CDD) {weather['cdd']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if show_map:
        # ── 미니 지도 렌더링 (프리미엄 시각 효과) ──
        import pandas as pd
        map_data = pd.DataFrame({"lat": [lat], "lon": [lng]})
        st.map(map_data, zoom=10, use_container_width=True)


def render_step1():
    from streamlit_js_eval import get_geolocation

    # ── 불필요해진 구형 DOM 해킹 통신 코드 제거 및 간결화 ──
    st.markdown("""
    <div class="hero">
        <div style="font-size:44px;margin-bottom:4px;">🏠</div>
        <div class="hero-title">에너지 절감 코치</div>
        <div class="hero-sub">건물 정보를 알려주시면, AI가 에너지 절감 방법을 찾아드립니다</div>
    </div>
    """, unsafe_allow_html=True)

    # ── 위치 감지 섹션 ──
    st.markdown("#### 📍 건물 위치")

    loc_method = st.radio(
        "위치 설정 방법",
        ["📡 자동 감지 (GPS)", "✏️ 직접 선택"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if loc_method == "📡 자동 감지 (GPS)":
        # 아직 위치 측정 성공 정보가 없을 시 실시간 디바이스 수신 채널 가동
        if not st.session_state.get("location_detected"):
            st.markdown("""
            <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:25px;text-align:center;margin-bottom:15px;box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                <div style="font-size:32px;margin-bottom:10px;animation: pulse-glow 2s infinite;">📡</div>
                <div style="font-weight:700;font-size:14px;color:#1E293B;">디바이스 정밀 GPS 위성 신호 수신 중...</div>
                <div style="font-size:11px;color:#64748B;margin-top:8px;">브라우저 상단 혹은 주소창 옆의 <b>'위치 허용(Allow)'</b>을 승인해 주세요.</div>
                <style>
                    @keyframes pulse-glow {
                        0% { opacity: 0.6; transform: scale(0.96); }
                        50% { opacity: 1; transform: scale(1.04); }
                        100% { opacity: 0.6; transform: scale(0.96); }
                    }
                </style>
            </div>
            """, unsafe_allow_html=True)
            
            # Native Streamlit JS API를 호출하여 Geolocation 값 취득
            loc_res = get_geolocation()
            
            if loc_res and 'coords' in loc_res:
                det_lat = loc_res['coords']['latitude']
                det_lng = loc_res['coords']['longitude']
                _fetch_location_data(det_lat, det_lng)
                st.rerun()
            elif loc_res and 'error' in loc_res:
                st.warning("⚠️ 디바이스 GPS 센서에 연결할 수 없습니다. '직접 선택' 탭의 주소 검색이나 도시 선택을 이용해 주세요.")

        # GPS 데이터 위경도 수동 강제 보정 기능 제공
        with st.expander("⚙️ GPS 위도/경도 좌표 직접 입력 (에러 방지용)"):
            col_lat, col_lng, col_btn = st.columns([2, 2, 1])
            with col_lat:
                manual_lat = st.number_input("위도", value=st.session_state.get("detected_lat", 35.1764), format="%.5f", key="man_lat")
            with col_lng:
                manual_lng = st.number_input("경도", value=st.session_state.get("detected_lng", 126.8996), format="%.5f", key="man_lng")
            with col_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔍 수동 강제 반영", key="manual_override_btn", use_container_width=True):
                    _fetch_location_data(manual_lat, manual_lng)
                    st.rerun()
    else:
        # ── ✏️ 직접 선택 모드 (주소 검색 vs 주요 도시 선택) ──
        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        
        # 탭 기반의 유려하고 직관적인 UI 설계
        direct_tab1, direct_tab2 = st.tabs(["🏠 주소 직접 검색", "📌 주요 도시 선택"])
        
        with direct_tab1:
            addr_input = st.text_input(
                "도로명 주소 또는 지번 주소를 입력하세요", 
                placeholder="예: 서울특별시 강남구 테헤란로 152 / 부산 해운대구 우동",
                key="direct_addr_input",
                help="지번 주소, 건물명, 도로명 주소 모두 검색이 가능합니다."
            )
            
            if st.button("🔍 주소 검색 및 위치 반영", key="btn_addr_search", type="primary", use_container_width=True):
                if addr_input.strip():
                    with st.spinner("입력하신 주소의 위성 좌표를 조회하고 있습니다..."):
                        res = geocode(addr_input.strip())
                        if res.get("success"):
                            st.success(f"✅ 검색 완료: {res['display_name'][:60]}...")
                            _fetch_location_data(res["lat"], res["lng"])
                            st.rerun()
                        else:
                            st.error("❌ 주소를 찾지 못했습니다. 도로명이나 주요 키워드를 포함해 보다 정확하게 입력해주세요.")
                else:
                    st.warning("먼저 검색할 주소를 입력해 주세요.")
                    
        with direct_tab2:
            region_select = st.selectbox(
                "주요 지역 거점 선택",
                ["서울·경기", "강원", "충청", "전라", "경상", "제주"],
                key="direct_region_select",
                help="지역 기후에 따라 난방/냉방 에너지 가중치가 달라집니다."
            )
            if st.button("🌤️ 이 지역 날씨 및 기후 불러오기", key="manual_weather", use_container_width=True):
                coords = CITY_COORDS.get(region_select, (35.1764, 126.8996))
                _fetch_location_data(coords[0], coords[1])
                st.rerun()

    # ── 📍 공통 영역: 위치가 감지/설정되었을 때 지도와 날씨 위젯 시각화 ──
    if st.session_state.get("location_detected"):
        lat = st.session_state.detected_lat
        lng = st.session_state.detected_lng
        
        # 실시간 위치 기반의 다크 테마 Leaflet 지도 렌더링
        visual_map_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
body, html {{ margin:0; padding:0; height:100%; background:#F8FAFC; overflow:hidden; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
#map {{ height:100%; width:100%; border-radius:12px; border:1px solid #E2E8F0; background:#F8FAFC; }}
.gps-pulse {{
background: #0ea5e9;
width: 14px; height: 14px;
border-radius: 50%;
border: 2.5px solid #FFFFFF;
box-shadow: 0 0 0 rgba(14, 165, 233, 0.6);
animation: pulse-anim 1.6s infinite;
}}
@keyframes pulse-anim {{
0% {{ box-shadow: 0 0 0 0px rgba(14, 165, 233, 0.8); }}
70% {{ box-shadow: 0 0 0 18px rgba(14, 165, 233, 0); }}
100% {{ box-shadow: 0 0 0 0px rgba(14, 165, 233, 0); }}
}}
.status-bar {{
position: absolute; top:12px; left:12px; z-index:1000;
background: rgba(255, 255, 255, 0.95); color: #1E293B;
padding: 6px 12px; border-radius: 6px; font-size: 11px;
border: 1px solid rgba(14, 165, 233, 0.35);
box-shadow: 0 4px 12px rgba(0,0,0,0.1);
font-weight: 600;
}}
.leaflet-control-attribution {{ display: none !important; }}
</style>
</head>
<body>
<div class="status-bar" id="status">🎯 위치 확인 성공 ({lat:.5f}, {lng:.5f})</div>
<div id="map"></div>
<script>
const map = L.map('map', {{zoomControl: false}}).setView([{lat}, {lng}], 15);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
attribution: '&copy; CARTO',
maxZoom: 19
}}).addTo(map);
const pulseIcon = L.divIcon({{
className: 'gps-pulse',
iconSize: [19, 19],
iconAnchor: [9, 9]
}});
L.marker([{lat}, {lng}], {{icon: pulseIcon}}).addTo(map);
L.circle([{lat}, {lng}], {{
radius: 150,
color: '#0ea5e9',
fillColor: '#0ea5e9',
fillOpacity: 0.08,
weight: 1
}}).addTo(map);
</script>
</body>
</html>
"""
        components.html(visual_map_html, height=300)
        
        # 날씨 데이터 위젯 로드
        _render_weather_widget(
            st.session_state.detected_weather,
            st.session_state.detected_geo,
            st.session_state.climate_factor,
            st.session_state.detected_lat,
            st.session_state.detected_lng,
            show_map=False
        )
        
        # 위치 초기화 및 재설정 액션 버튼
        c1, c2 = st.columns([3.2, 1])
        with c2:
            if st.button("🔄 위치 변경 및 초기화", key="reset_location_btn", use_container_width=True):
                st.session_state.location_detected = False
                st.rerun()

    # ── 💾 단계 전환 및 백엔드 로직용 최종 region 변수 확정 ──
    if st.session_state.get("location_detected"):
        region = st.session_state.get("detected_geo", {}).get("region", "광주광역시")
    else:
        if loc_method == "✏️ 직접 선택":
            region = st.session_state.get("direct_region_select", "서울·경기")
        else:
            region = "광주광역시"

    st.markdown("---")
    st.markdown("#### 🏢 건물 정보")

    # ── [프리미엄 정보 도우미] 네이버 부동산 다이렉트 검색 링크 탑재 ──
    geo_data = st.session_state.get("detected_geo", {})
    raw_full_address = geo_data.get("full_address", "") if isinstance(geo_data, dict) else ""
    
    # Nominatim 전체 주소에서 불필요 부 제거 및 한국 순서(시도-시군구-동)로 역정렬해 자연스러운 검색어 생성
    if raw_full_address:
        parts = [p.strip() for p in raw_full_address.split(',') if p.strip()]
        clean_parts = [p for p in reversed(parts) if p not in ["대한민국", "Korea", "South Korea"]]
        search_keyword = " ".join(clean_parts)
    else:
        search_keyword = st.session_state.get("region", "광주광역시")
        
    if not search_keyword:
        search_keyword = "부동산"

    import urllib.parse
    encoded_keyword = urllib.parse.quote(search_keyword)
    naver_land_url = f"https://new.land.naver.com/search?query={encoded_keyword}"

    # 프리미엄 UI 디자인에 맞춘 직관적인 가이드 및 새 창 링크 버튼
    st.markdown(f"""
    <div style="background:linear-gradient(90deg, rgba(3,199,90,0.09) 0%, rgba(56,189,248,0.05) 100%);border:1px solid rgba(3,199,90,0.25);border-radius:12px;padding:15px 18px;margin-bottom:20px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 4px 15px rgba(0,0,0,0.2);">
        <div style="display:flex;align-items:center;gap:12px;">
            <div style="font-size:22px;background:rgba(3,199,90,0.15);border-radius:10px;width:40px;height:40px;display:flex;align-items:center;justify-content:center;border:1px solid rgba(3,199,90,0.3);">🏢</div>
            <div>
                <div style="font-size:13px;font-weight:700;color:#FFFFFF;margin-bottom:2px;">내 건물의 연도나 평수를 모르시나요?</div>
                <div style="font-size:11px;color:#94A3B8;">네이버 부동산에서 건물을 검색하면 <b>준공 연월 및 전용/공급면적</b>을 간편히 알 수 있습니다.</div>
            </div>
        </div>
        <a href="{naver_land_url}" target="_blank" style="text-decoration:none;">
            <div style="background:#03C75A;color:#FFFFFF;font-size:11.5px;font-weight:800;padding:10px 18px;border-radius:8px;display:flex;align-items:center;gap:6px;transition:all 0.25s ease;box-shadow:0 4px 12px rgba(3,199,90,0.35);letter-spacing:-0.2px;white-space:nowrap;" onmouseover="this.style.transform='translateY(-1.5px)';this.style.filter='brightness(1.08)';" onmouseout="this.style.transform='none';this.style.filter='none';">
                🔍 네이버 부동산 바로가기 ↗
            </div>
        </a>
    </div>
    """, unsafe_allow_html=True)

    building_type = st.selectbox(
        "건물 유형",
        ["아파트", "단독주택", "상가/오피스"],
        help="건물 유형에 따라 에너지 사용 패턴이 달라집니다"
    )

    age = st.selectbox(
        "건축 연도",
        ["5년 이내", "5~15년", "15~30년", "30년 이상"],
        index=1,
        help="오래된 건물일수록 단열 성능이 낮아 에너지 낭비가 큽니다"
    )

    pyeong = st.slider(
        "건물 면적 (평)", 10, 200, 30, 5,
        help="1평 ≈ 3.3m². 아파트 24평, 단독주택 40평 기준"
    )

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("#### 📊 월별 전기요금 기록 장부")
    st.markdown(
        "<p style='font-size:12.5px;color:#64748B;margin-top:-10px;margin-bottom:15px;'>"
        "실제 납부하신 월별 전기요금을 아래 표에 기록해 주세요. 실시간으로 전력 소비 추이를 차트화하여 정밀 분석을 제공합니다."
        "</p>", 
        unsafe_allow_html=True
    )

    ledger_col, chart_col = st.columns([1.2, 2])

    with ledger_col:
        # 12개월 기본 리스트
        months_list = [f"{i}월" for i in range(1, 13)]
        
        st.markdown("<div style='padding-bottom: 8px; border-bottom: 1px solid #E2E8F0; margin-bottom: 12px;'><span style='font-size:13.5px; font-weight:700; color:#1E293B;'>💰 월별 요금 입력 (단위: 만원)</span></div>", unsafe_allow_html=True)
        
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
            plot_bgcolor="rgba(0,0,0,0)", # 완전히 투명하게 설정하여 다크 테마 배경에 스며들도록 함
            font=dict(family="Inter", color="#6B8AB0", size=11), # 가독성을 위해 밝은 회청색 글꼴 색상 적용
            xaxis=dict(gridcolor="#1A2740", zeroline=False), # 테마와 어울리는 짙은 남색 그리드 라인
            yaxis=dict(
                gridcolor="#1A2740", 
                zeroline=False, 
                title=dict(text="전기요금 (만원)", font=dict(color="#6B8AB0"))
            ),
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
    <div style="background:#F0F9FF;border:1px solid #BAE6FD;border-radius:12px;padding:15px 18px;margin-top:10px;margin-bottom:28px;">
        <div style="font-size:13px;color:#0284C7;font-weight:800;margin-bottom:4px;">💡 정량 평가 가이드</div>
        <div style="font-size:12px;color:#334155;line-height:1.6;">
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
    banner_bg = "linear-gradient(135deg,#D1FAE5,#A7F3D0)" if is_good else "linear-gradient(135deg,#FEE2E2,#FECACA)"
    border_c = "#059669" if is_good else "#DC2626"
    cost_color = "#059669" if is_good else "#DC2626"

    annual_cost_str = won_to_manwon(dx["current_cost"])
    optimal_str = won_to_manwon(dx["optimal_cost"])
    saving_str = won_to_manwon(dx["saving_potential"])

    st.markdown(f"""
    <div style="background:{banner_bg};border:1px solid {border_c};border-radius:20px;
                padding:28px 36px;display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
        <div>
            <div style="font-size:12px;color:#475569;font-weight:600;letter-spacing:1px;margin-bottom:8px;">
                에너지 효율 진단 결과
            </div>
            <div style="font-size:15px;color:#1E293B;margin-bottom:6px;">
                연간 예상 전기요금: <b style="font-size:24px;color:{cost_color}">{annual_cost_str}</b>
            </div>
            <div style="font-size:13px;color:#475569;">
                같은 조건 최적 건물: {optimal_str} &nbsp;·&nbsp;
                <span style="color:{cost_color};font-weight:700;">최대 {saving_str} 절감 가능</span>
            </div>
        </div>
        <div style="text-align:center;flex-shrink:0;margin-left:24px;">
            <div class="grade-badge {grade_css}" style="background: white; color: {cost_color}; border: 2px solid {cost_color};">{grade}</div>
            <div style="font-size:11px;color:#475569;margin-top:8px;font-weight:600;">에너지 효율 등급</div>
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
        <div style="background:#F0F9FF;border:1px solid #BAE6FD;border-radius:12px;
                    padding:12px 18px;margin-bottom:16px;display:flex;align-items:center;gap:10px;font-size:13px;">
            <span style="font-size:16px;">🛰️</span>
            <span style="color:#0f172a;">
                <b>실시간 기후 인텔리전스 적용:</b> {region_str}의 1년 기후 데이터 분석 완료 (기후 보정: <b>{rf:.2f}배</b>)
            </span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;
                    padding:12px 18px;margin-bottom:16px;display:flex;align-items:center;gap:10px;font-size:13px;">
            <span style="font-size:16px;">📊</span>
            <span style="color:#475569;">
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
    <div style='background: #F1F5F9; border-left: 3px solid #3B82F6; padding: 10px 14px; border-radius: 6px; margin-top: -10px; margin-bottom: 15px;'>
        <p style='font-size:12.5px; color:#1E293B; margin:0; font-weight:600;'>💡 최적 건물 비교 기준 안내</p>
        <p style='font-size:11.5px; color:#475569; margin:4px 0 0 0; line-height:1.5;'>
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
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)", # 투명 배경 설정
        font=dict(family="Inter", color="#6B8AB0"), # 축 레이블 색상 변경
        xaxis=dict(gridcolor="#1A2740"),
        yaxis=dict(
            gridcolor="#1A2740", 
            title=dict(text="전기요금 (만원)", font=dict(color="#6B8AB0"))
        ),
        barmode="group", bargap=0.25, height=300,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#E2E8F0"), # 범례 글꼴 흰색 계열 적용
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
                        <div class="val" style="color:#0f172a;{pct_hl}">{rec['saving_pct']}%</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 상위 3개 선택 시 총 절감 요약
        top3 = sorted_list[:3]
        total_saving = sum(r["annual_saving_won"] for r in top3)
        total_invest = sum(r["invest_manwon"] for r in top3)
        st.markdown(f"""
        <div style="background:#F0FDF4;border:1px solid #86EFAC;border-radius:14px;padding:18px;margin-top:16px;text-align:center;">
            <div style="font-size:13px;color:#166534;font-weight:600;">💡 {group_label} 상위 3개 방안 결합 적용 시</div>
            <div style="font-size:15px;color:#1E293B;margin-top:8px;font-weight:500;">
                총 예상 투자비: <b style="color:#F97316;">{total_invest:,.0f}만원</b> &nbsp;→&nbsp;
                연간 요금 절감액: <b style="color:#059669;">{won_to_manwon(total_saving)}</b>
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
<div style="background:linear-gradient(135deg,#EFF6FF,#DBEAFE);border:1px solid #93C5FD;border-radius:16px;padding:24px 20px;margin-top:10px;margin-bottom:28px;box-shadow:0 4px 15px rgba(0,0,0,0.05);">
<div style="font-size:13px;color:#1D4ED8;margin-bottom:8px;text-align:center;font-weight:700;letter-spacing:1px;">📋 종합 진단 혜택 요약</div>
<div style="font-size:18px;color:#0F172A;font-weight:800;text-align:center;margin-bottom:20px;letter-spacing:-0.5px;">{st.session_state.building_type} · {st.session_state.pyeong}평 · 에너지 등급 <span style="color:#059669;">{dx['grade']}</span></div>
<div style="display:flex;flex-wrap:wrap;justify-content:space-around;border-top:1px solid #BFDBFE;padding-top:20px;gap:12px;">
<div style="text-align:center;min-width:140px;flex:1;">
<div style="font-size:12px;color:#475569;margin-bottom:6px;font-weight:600;">⚡ 연간 예상 에너지 요금 절감</div>
<div style="font-size:22px;color:#059669;font-weight:900;">{saving_str}</div>
</div>
<div style="width:1px;background:#BFDBFE;align-self:stretch;display:block;"></div>
<div style="text-align:center;min-width:140px;flex:1;">
<div style="font-size:12px;color:#475569;margin-bottom:6px;font-weight:600;">🎁 정부 보조금 혜택 (최대)</div>
<div style="font-size:22px;color:#2563EB;font-weight:900;">{total_direct_cash}만원</div>
</div>
</div>
<div style="text-align:center;font-size:11px;color:#64748B;margin-top:16px;">* 지원 조건 및 금융 지원(무이자 융자 등) 혜택에 따라 최종 수급액은 변동될 수 있습니다.</div>
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

if current_step == 0:
    render_step0()
elif current_step == 1:
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
    render_step0()

# 실시간 자동 저장 로직 (모든 step에서 값이 바뀌면 자동 기록)
if st.session_state.get("username"):
    save_user_data(st.session_state.username, st.session_state.recorded_bills)

# ── 웹앱 Wakeup / Keep-alive 유지 (브라우저 유휴 상태 수면 방지) ──
# 사용자가 브라우저 창을 띄워놓고 오랫동안 조작하지 않아도,
# 1분마다 서버의 헬스체크 API를 호출하여 WebSocket 연결 해제 및 Streamlit Cloud의 절전 모드 진입을 방지합니다.
keep_alive_js = """
<script>
    setInterval(function() {
        fetch('/_stcore/health')
            .then(response => {
                if(response.ok) {
                    console.log('Keep-alive ping sent to Streamlit server');
                }
            })
            .catch(error => console.warn('Keep-alive ping failed', error));
    }, 60000); // 60초(1분)마다 반복 호출
</script>
"""
components.html(keep_alive_js, height=0, width=0)

