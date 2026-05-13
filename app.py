"""
에너지 절감 코치 — 메인 앱 (5단계 마법사)

일반 소비자가 건물 정보를 단계별로 입력하면
AI가 에너지 진단 + 절감 방안 TOP 3 + 정부 보조금을 안내합니다.
"""
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go

# ── 유틸리티 모듈 임포트 ──
from utils.styles import get_main_css
from utils.energy_engine import (
    diagnose, won_to_manwon, ELEC_RATE, BUILDING_DEFAULTS,
    AGE_FACTOR, REGION_FACTOR, DISCOMFORT_EFFECTS,
)
from utils.recommendations import get_top_recommendations
from utils.subsidies import get_matching_subsidies
from utils.weather import (
    reverse_geocode, fetch_weather, calc_climate_factor,
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
# 프로그레스 바 렌더링
# ──────────────────────────────────────────────────────────────
def render_progress(current: int):
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
    <div style="background:#0D1526;border:1px solid #1A2740;border-radius:14px;padding:18px;margin:10px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div style="font-size:15px;font-weight:700;color:#E2E8F0;">📍 {geo.get('region', '')} {geo.get('city', '')}</div>
                <div style="font-size:12px;color:#6B8AB0;margin-top:4px;">{geo.get('full_address', '')[:60]}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:13px;color:#E2E8F0;">{w_text}</div>
                <div style="font-size:22px;font-weight:800;color:#38BDF8;">{weather['current_temp']}°C</div>
            </div>
        </div>
        <div style="display:flex;gap:20px;margin-top:12px;font-size:12px;color:#6B8AB0;flex-wrap:wrap;">
            <span>체감 {weather['feels_like']}°C</span>
            <span>습도 {weather['humidity']}%</span>
            <span>풍속 {weather['wind_speed']}m/s</span>
            <span>연평균 {weather['avg_temp']}°C</span>
            <span style="color:#50C878;font-weight:700;">기후 보정: {cf:.2f}</span>
        </div>
        <div style="font-size:11px;color:#4A6080;margin-top:8px;">
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
    # ── [초슬림] DOM Injection 기반 GPS 통신 채널 ──
    # CSS로 통신 전용 인풋 위젯을 완벽하게 은폐
    st.markdown("""
    <style>
    div[data-testid="stTextInput"]:has(input[placeholder="GPS_COORDINATES_EXCHANGE"]) {
        position: absolute;
        top: -9999px;
        left: -9999px;
        opacity: 0;
        pointer-events: none;
        height: 0px !important;
        margin: 0px !important;
        padding: 0px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # DOM 통신 전용 히든 위젯 렌더링
    st.text_input(
        "GPS_BUS",
        placeholder="GPS_COORDINATES_EXCHANGE",
        key="gps_sync_data",
        label_visibility="collapsed"
    )
    
    # 버스 데이터 파싱 및 위치 갱신 핸들러
    raw_sync = st.session_state.get("gps_sync_data", "").strip()
    if raw_sync and "," in raw_sync:
        try:
            lat_str, lng_str = raw_sync.split(',')
            q_lat = float(lat_str.strip())
            q_lng = float(lng_str.strip())
            
            # 중복 트리거 방지
            curr_lat = st.session_state.get("detected_lat", 0)
            if abs(curr_lat - q_lat) > 0.0001:
                _fetch_location_data(q_lat, q_lng)
                # 안전하게 리셋 및 재구동
                st.session_state.gps_sync_data = ""
                st.rerun()
        except Exception:
            pass

    # ── 하위 호환용 URL 쿼리 파라미터 감지 (폴백) ──
    q_params = st.query_params
    if "lat" in q_params and "lng" in q_params and not st.session_state.get("location_detected"):
        try:
            q_lat = float(q_params["lat"])
            q_lng = float(q_params["lng"])
            _fetch_location_data(q_lat, q_lng)
            st.query_params.clear()
            st.rerun()
        except Exception:
            pass

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
        st.markdown("""
        <div style="margin-bottom:10px;font-size:13px;color:#E2E8F0;">
            🛰️ <b>실시간 이동형 GPS 추적기 활성화</b><br/>
            <span style="color:#6B8AB0;font-size:11px;">디바이스 이동 시 지도 위의 마커가 실시간으로 움직이며 현재 위치를 중심점으로 추적합니다.</span>
        </div>
        """, unsafe_allow_html=True)

        # ── 실시간 이동 GPS 추적 & 다크 모드 인터랙티브 지도 ──
        tracker_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                body, html { margin:0; padding:0; height:100%; background:#0A0F1E; overflow:hidden; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
                #map { height:100%; width:100%; border-radius:12px; border:1px solid #1A2740; background:#0A0F1E; }
                
                /* 실시간 맥박 효과를 갖는 푸른색 GPS 점 CSS */
                .gps-pulse {
                    background: #38BDF8;
                    width: 14px;
                    height: 14px;
                    border-radius: 50%;
                    border: 2.5px solid #FFFFFF;
                    box-shadow: 0 0 0 rgba(56, 189, 248, 0.6);
                    animation: pulse-anim 1.6s infinite;
                }
                @keyframes pulse-anim {
                    0% { box-shadow: 0 0 0 0px rgba(56, 189, 248, 0.8); }
                    70% { box-shadow: 0 0 0 18px rgba(56, 189, 248, 0); }
                    100% { box-shadow: 0 0 0 0px rgba(56, 189, 248, 0); }
                }
                
                /* 화면 상/하단 플로팅 레이아웃 */
                .status-bar {
                    position: absolute; top:12px; left:12px; z-index:1000;
                    background: rgba(13, 21, 38, 0.9); color: #E2E8F0;
                    padding: 6px 12px; border-radius: 6px; font-size: 11px;
                    border: 1px solid rgba(255,255,255,0.08);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
                    backdrop-filter: blur(4px);
                    font-weight: 600;
                }
                .sync-btn {
                    position: absolute; bottom:18px; left:50%; transform: translateX(-50%);
                    z-index:1000; background: linear-gradient(135deg, #50C878, #38BDF8);
                    color: #0A0F1E; font-weight: 800; border: none;
                    padding: 10px 20px; border-radius: 30px; cursor: pointer;
                    font-size: 12px; box-shadow: 0 8px 20px rgba(56, 189, 248, 0.35);
                    display: none; transition: all 0.2s ease;
                    letter-spacing: -0.2px;
                }
                .sync-btn:hover { transform: translateX(-50%) scale(1.03); filter: brightness(1.1); }
                .sync-btn:active { transform: translateX(-50%) scale(0.97); }
            </style>
        </head>
        <body>
            <div class="status-bar" id="status">📡 위성 연결 및 위치 확인 권한 요청 중...</div>
            <button class="sync-btn" id="syncBtn">🎯 이 위치 기후 데이터 분석 반영</button>
            <div id="map"></div>
            
            <script>
                // 기본 중심 (서울)
                const map = L.map('map', {zoomControl: false}).setView([37.5665, 126.9780], 13);
                
                // 프리미엄 다크 타일
                L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                    attribution: '&copy; CARTO',
                    maxZoom: 19
                }).addTo(map);

                let marker = null;
                let circle = null;
                let currentLat = null;
                let currentLng = null;

                const pulseIcon = L.divIcon({
                    className: 'gps-pulse',
                    iconSize: [19, 19],
                    iconAnchor: [9, 9]
                });

                function updatePosition(lat, lng, accuracy) {
                    currentLat = lat;
                    currentLng = lng;
                    
                    document.getElementById('status').innerHTML = `🛰️ GPS 실시간 추적 중 (${lat.toFixed(5)}, ${lng.toFixed(5)})`;
                    const syncBtn = document.getElementById('syncBtn');
                    syncBtn.style.display = 'block';

                    if (!marker) {
                        // 최초 고정
                        marker = L.marker([lat, lng], {icon: pulseIcon}).addTo(map);
                        circle = L.circle([lat, lng], {
                            radius: Math.min(accuracy, 300), 
                            color: '#38BDF8', 
                            fillColor: '#38BDF8', 
                            fillOpacity: 0.1, 
                            weight: 1
                        }).addTo(map);
                        map.setView([lat, lng], 16);
                        
                        // 최초 위치 획득 후 부모 Streamlit의 쿼리 파라미터에 lat이 없을 때만 자동 1회 로딩
                        const parentUrl = new URL(window.parent.location.href);
                        if (!parentUrl.searchParams.get('lat')) {
                            setTimeout(() => {
                                triggerSync();
                            }, 1500);
                        }
                    } else {
                        // 디바이스가 움직이면 마커 및 원 위치 변경, 맵 중앙 정렬
                        marker.setLatLng([lat, lng]);
                        circle.setLatLng([lat, lng]);
                        circle.setRadius(Math.min(accuracy, 300));
                        map.panTo([lat, lng]);
                    }
                }

                function triggerSync() {
                    if (currentLat && currentLng) {
                        const dataStr = currentLat.toFixed(6) + "," + currentLng.toFixed(6);
                        
                        try {
                            const parentDoc = window.parent.document;
                            const inputs = parentDoc.querySelectorAll('input[placeholder="GPS_COORDINATES_EXCHANGE"]');
                            
                            if (inputs && inputs.length > 0) {
                                const targetInput = inputs[0];
                                
                                // React의 내부 변경 감지기(state tracker)를 작동시키는 네이티브 세터 호출
                                const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                                setter.call(targetInput, dataStr);
                                
                                // React/Streamlit의 상태 동기화를 유도하는 이벤트 연쇄 디스패치
                                targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                                targetInput.dispatchEvent(new Event('change', { bubbles: true }));
                                targetInput.dispatchEvent(new Event('blur', { bubbles: true }));
                                
                                document.getElementById('status').innerHTML = `✅ 동기화 신호 전송됨`;
                                return;
                            }
                        } catch (e) {
                            console.warn("DOM Injection failed, falling back to URL rewrite: ", e);
                        }

                        // ── 최후의 보루: DOM 연동 실패 시 기존의 URL 리로드 폴백 실행 ──
                        const parentUrl = new URL(window.parent.location.href);
                        const oldLat = parseFloat(parentUrl.searchParams.get('lat') || '0');
                        if (Math.abs(oldLat - currentLat) > 0.0001) {
                            parentUrl.searchParams.set('lat', currentLat.toFixed(6));
                            parentUrl.searchParams.set('lng', currentLng.toFixed(6));
                            window.parent.location.href = parentUrl.toString();
                        }
                    }
                }

                document.getElementById('syncBtn').onclick = function() {
                    this.innerText = "🔄 위치 기후 정보 연동 중...";
                    triggerSync();
                };

                if (navigator.geolocation) {
                    // watchPosition을 사용하여 연속적인 움직임 추적
                    const trackerId = navigator.geolocation.watchPosition(function(position) {
                        updatePosition(position.coords.latitude, position.coords.longitude, position.coords.accuracy);
                    }, function(error) {
                        const msgs = { 1: "권한 거부됨", 2: "GPS 연결실패", 3: "시간 초과" };
                        document.getElementById('status').innerHTML = `⚠️ GPS 수신 불안정 (${msgs[error.code] || '오류'})`;
                        document.getElementById('status').style.color = '#FFB347';
                    }, {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0 // 캐시 미사용으로 실시간성 극대화
                    });
                } else {
                    document.getElementById('status').innerHTML = `❌ 브라우저가 GPS를 지원하지 않습니다`;
                }
            </script>
        </body>
        </html>
        """
        components.html(tracker_html, height=360)

        # 수동 입력 폴백 구성 (에러 방지용)
        with st.expander("⚙️ GPS 데이터가 정확히 잡히지 않을 때 직접 입력"):
            col_lat, col_lng, col_btn = st.columns([2, 2, 1])
            with col_lat:
                manual_lat = st.number_input("위도", value=st.session_state.get("detected_lat", 37.5665), format="%.5f", key="man_lat")
            with col_lng:
                manual_lng = st.number_input("경도", value=st.session_state.get("detected_lng", 126.9780), format="%.5f", key="man_lng")
            with col_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔍 수동 강제 반영", key="manual_override_btn", use_container_width=True):
                    _fetch_location_data(manual_lat, manual_lng)
                    st.rerun()

        # 날씨 데이터 렌더링 시 show_map=False로 중복 표시 제거
        if st.session_state.get("location_detected"):
            _render_weather_widget(
                st.session_state.detected_weather,
                st.session_state.detected_geo,
                st.session_state.climate_factor,
                st.session_state.detected_lat,
                st.session_state.detected_lng,
                show_map=False
            )

        region = st.session_state.get("detected_geo", {}).get("region", "서울·경기")
    else:
        # 직접 선택 모드 (기존 방식)
        region = st.selectbox(
            "지역",
            ["서울·경기", "강원", "충청", "전라", "경상", "제주"],
            help="지역 기후에 따라 냉난방 에너지 소비가 달라집니다"
        )
        # 직접 선택 시 해당 지역 좌표로 날씨 가져오기
        if st.button("🌤️ 이 지역 날씨 불러오기", key="manual_weather"):
            coords = CITY_COORDS.get(region, (37.5665, 126.9780))
            _fetch_location_data(coords[0], coords[1])

        if st.session_state.get("location_detected"):
            _render_weather_widget(
                st.session_state.detected_weather,
                st.session_state.detected_geo,
                st.session_state.climate_factor,
                st.session_state.detected_lat,
                st.session_state.detected_lng
            )

    st.markdown("---")
    st.markdown("#### 🏢 건물 정보")

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

    monthly_bill = st.number_input(
        "현재 월 전기요금 (만원)", min_value=1, max_value=500,
        value=15, step=1,
        help="대략적인 금액을 입력해주세요. 정확하지 않아도 괜찮습니다."
    )

    # 세션에 저장
    st.session_state.building_type = building_type
    st.session_state.age = age
    st.session_state.region = region
    st.session_state.pyeong = pyeong
    st.session_state.monthly_bill = monthly_bill

    st.markdown("")
    col_l, col_r = st.columns([3, 1])
    with col_r:
        st.button("다음 단계 →", on_click=go_next, use_container_width=True)


# ──────────────────────────────────────────────────────────────
# STEP 2: 불편함 선택
# ──────────────────────────────────────────────────────────────
def render_step2():
    st.markdown("""
    <div class="hero">
        <div style="font-size:44px;margin-bottom:4px;">🔍</div>
        <div class="hero-title">어떤 불편함이 있으신가요?</div>
        <div class="hero-sub">해당하는 항목을 모두 선택해주세요. 선택하지 않아도 진단 가능합니다.</div>
    </div>
    """, unsafe_allow_html=True)

    discomfort_options = [
        ("☀️", "여름에 실내가 너무 더워요", "냉방을 틀어도 효과가 적은 경우"),
        ("❄️", "겨울에 실내가 금방 식어요", "난방을 꺼도 금방 추워지는 경우"),
        ("💨", "창문 틈으로 바람이 들어와요", "창호 기밀성이 떨어진 경우"),
        ("🌡️", "냉난방을 해도 효과가 없어요", "설비가 노후화된 경우"),
        ("💡", "전기요금이 비정상적으로 높아요", "사용량 대비 요금이 높은 경우"),
    ]

    selected = []
    for icon, label, hint in discomfort_options:
        if st.checkbox(f"{icon} {label}", help=hint):
            selected.append(label)

    # 리모델링 의향 별도 체크
    remodel = st.checkbox("🏗️ 리모델링을 검토 중이에요", help="개선 방안을 더 상세하게 안내드립니다")

    st.session_state.discomforts = selected
    st.session_state.remodel = remodel

    st.markdown("")
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.button("← 이전", on_click=go_prev, use_container_width=True)
    with col_r:
        st.button("AI 진단 시작 🔬", on_click=run_diagnosis, use_container_width=True)


def run_diagnosis():
    """진단 실행 후 STEP 3으로 이동. 실제 기후 데이터가 있으면 사용."""
    # 기상 데이터 기반 기후 보정 계수 (없으면 None → 정적 팩터 사용)
    cf = st.session_state.get("climate_factor", None)

    result = diagnose(
        pyeong=st.session_state.pyeong,
        building_type=st.session_state.building_type,
        age=st.session_state.age,
        region=st.session_state.region,
        discomforts=st.session_state.discomforts,
        monthly_bill=st.session_state.monthly_bill,
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

    # 월별 차트
    st.markdown("#### 📅 월별 에너지 소비 패턴")
    months = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"]
    m_now = dx["monthly"] / 1000
    m_opt = dx["monthly_opt"] / 1000

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=months, y=m_opt, name="최적 건물",
        marker_color="rgba(107,138,176,0.35)",
        hovertemplate="%{x} 최적: %{y:.2f} MWh<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=months, y=m_now, name="내 건물 (현재)",
        marker_color="#F87171" if not is_good else "#50C878",
        hovertemplate="%{x} 현재: %{y:.2f} MWh<extra></extra>"
    ))
    fig.update_layout(
        paper_bgcolor="#0A0F1E", plot_bgcolor="#0D1526",
        font=dict(family="Inter", color="#E2E8F0"),
        xaxis=dict(gridcolor="#1A2740"),
        yaxis=dict(gridcolor="#1A2740", title="에너지 (MWh)"),
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
# STEP 4: 절감 방안 TOP 3
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
        <div class="hero-title">절감 방안 TOP 3</div>
        <div class="hero-sub">AI가 투자 대비 효과가 가장 큰 개선 방법을 추천합니다</div>
    </div>
    """, unsafe_allow_html=True)

    recs = get_top_recommendations(dx, st.session_state.pyeong)
    rank_icons = ["🥇", "🥈", "🥉"]

    for i, rec in enumerate(recs):
        invest_str = f"{rec['invest_manwon']:,.0f}만원"
        saving_str = won_to_manwon(rec["annual_saving_won"])
        payback_str = f"{rec['payback_years']}년"

        st.markdown(f"""
        <div class="rec-card">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
                <span style="font-size:28px;">{rank_icons[i]}</span>
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
                    <div class="val" style="color:#FFB347;">{invest_str}</div>
                </div>
                <div class="rec-metric">
                    <div class="label">연간 절감</div>
                    <div class="val" style="color:#50C878;">{saving_str}</div>
                </div>
                <div class="rec-metric">
                    <div class="label">회수 기간</div>
                    <div class="val" style="color:#38BDF8;">{payback_str}</div>
                </div>
                <div class="rec-metric">
                    <div class="label">절감률</div>
                    <div class="val" style="color:#E2E8F0;">{rec['saving_pct']}%</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 총 절감 요약
    total_saving = sum(r["annual_saving_won"] for r in recs)
    total_invest = sum(r["invest_manwon"] for r in recs)
    st.markdown(f"""
    <div style="background:#0D1526;border:1px solid #1A5C35;border-radius:14px;padding:20px;margin-top:16px;text-align:center;">
        <div style="font-size:13px;color:#4A6080;font-weight:600;">3가지 모두 실행 시</div>
        <div style="font-size:14px;color:#E2E8F0;margin-top:8px;">
            총 투자: <b style="color:#FFB347;">{total_invest:,.0f}만원</b> &nbsp;→&nbsp;
            연간 절감: <b style="color:#50C878;">{won_to_manwon(total_saving)}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

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
    st.markdown("""
    <div class="hero">
        <div style="font-size:44px;margin-bottom:4px;">🏛️</div>
        <div class="hero-title">활용 가능한 정부 보조금</div>
        <div class="hero-sub">건물 조건에 맞는 지원 사업을 찾았습니다</div>
    </div>
    """, unsafe_allow_html=True)

    subsidies = get_matching_subsidies(
        st.session_state.building_type,
        st.session_state.age,
    )

    if not subsidies:
        st.info("현재 조건에 맞는 보조금 프로그램이 없습니다. 지자체별 추가 지원을 확인해보세요.")
    else:
        for s in subsidies:
            st.markdown(f"""
            <div class="subsidy-card">
                <div class="name">{s['name']}</div>
                <div class="detail">
                    <b>지원 기관:</b> {s['org']}<br>
                    <b>대상:</b> {s['target']}<br>
                    <b>지원 내용:</b> {s['support']}<br>
                    <b>지원 금액:</b> <span style="color:#50C878;font-weight:700;">{s['amount']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # 마무리 요약
    dx = st.session_state.diagnosis
    if dx:
        saving_str = won_to_manwon(dx["saving_potential"])
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0D1526,#0F2040);border:1px solid #1A2740;
                    border-radius:16px;padding:28px;margin-top:24px;text-align:center;">
            <div style="font-size:13px;color:#4A6080;margin-bottom:10px;">📋 진단 요약</div>
            <div style="font-size:18px;color:#E2E8F0;font-weight:700;">
                {st.session_state.building_type} · {st.session_state.pyeong}평 · 효율 등급
                <span style="color:#50C878;">{dx['grade']}</span>
            </div>
            <div style="font-size:14px;color:#6B8AB0;margin-top:8px;">
                연간 최대 <span style="color:#50C878;font-weight:800;font-size:20px;">{saving_str}</span>
                절감 가능
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
