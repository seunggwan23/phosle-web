"""
?먮꼫吏 ?덇컧 肄붿튂 ??硫붿씤 ??(5?④퀎 留덈쾿??

?쇰컲 ?뚮퉬?먭? 嫄대Ъ ?뺣낫瑜??④퀎蹂꾨줈 ?낅젰?섎㈃
AI媛 ?먮꼫吏 吏꾨떒 + ?덇컧 諛⑹븞 TOP 3 + ?뺣? 蹂댁“湲덉쓣 ?덈궡?⑸땲??
"""
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import pandas as pd

# ?? ?좏떥由ы떚 紐⑤뱢 ?꾪룷????
from ?좏떥由ы떚.?붿옄???ㅽ???import get_main_css
from ?좏떥由ы떚.?먮꼫吏_遺꾩꽍_?붿쭊 import (
    diagnose, won_to_manwon, ELEC_RATE, BUILDING_DEFAULTS,
    AGE_FACTOR, REGION_FACTOR,
)
from ?좏떥由ы떚.?덇컧_諛⑹븞_異붿쿇 import get_top_recommendations, get_all_recommendations
from ?좏떥由ы떚.?뺣?_蹂댁“湲?import get_matching_subsidies
from ?좏떥由ы떚.湲곗긽_?뺣낫_議고쉶 import (
    reverse_geocode, geocode, fetch_weather, calc_climate_factor,
    weather_code_to_text, CITY_COORDS,
)

# ?? ?섏씠吏 ?ㅼ젙 ??
st.set_page_config(
    page_title="?먮꼫吏 ?덇컧 肄붿튂",
    page_icon="?룧",
    layout="centered",
)
st.markdown(get_main_css(), unsafe_allow_html=True)


# ??????????????????????????????????????????????????????????????
# ?몄뀡 ?ㅽ뀒?댄듃 珥덇린??
# ??????????????????????????????????????????????????????????????
if "step" not in st.session_state:
    st.session_state.step = 1
if "diagnosis" not in st.session_state:
    st.session_state.diagnosis = None
if "recorded_bills" not in st.session_state:
    # 珥덇린 湲곕낯媛?(留뚯썝 ?⑥쐞): 寃⑥슱/?щ쫫 遺???⑦꽩??怨좊젮???꾩떎?곸씤 珥덇린 ?곗씠??
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


# ??????????????????????????????????????????????????????????????
# ?꾨줈洹몃젅??諛??뚮뜑留?(design.md ?ㅽ???
# ??????????????????????????????????????????????????????????????
def render_progress(current: int):
    labels = ["嫄대Ъ ?뺣낫", "遺덊렪??, "AI 吏꾨떒", "?덇컧 諛⑹븞", "蹂댁“湲?]
    pct = (current / 5) * 100
    
    html = f'''
    <div class="progress-container">
        <div class="progress-info">
            <div class="progress-label">Step {current}/5: {labels[current-1]}</div>
            <div class="progress-label">{int(pct)}% ?꾨즺</div>
        </div>
        <div class="progress-track">
            <div class="progress-fill" style="width: {pct}%"></div>
        </div>
    </div>
    '''
    st.markdown(html, unsafe_allow_html=True)


# ??????????????????????????????????????????????????????????????
# 怨듯넻 而댄룷?뚰듃: ?좎뵪 ?꾩젽
# ??????????????????????????????????????????????????????????????
def _render_weather_widget(weather: dict, geo: dict, cf: float, lat: float, lng: float, show_map: bool = True):
    """?좎뵪 ?뺣낫 移대뱶? 誘몃땲 吏?꾨? ?쇨????덇쾶 ?뚮뜑留?(?붿옄??媛?대뱶 諛섏쁺)"""
    w_text = weather_code_to_text(weather.get("weather_code", 0))
    
    st.markdown(f"""
    <div class="glass-card" style="margin: 16px 0; padding: 20px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <div style="font-family:'Plus Jakarta Sans'; font-size:16px; font-weight:800; color:#071E27; display:flex; align-items:center; gap:6px;">
                    <span class="material-icon" style="font-size:18px; color:#0D631B;">location_on</span>
                    {geo.get('region', '')} {geo.get('city', '') or '?뺣낫 ?놁쓬'}
                </div>
                <div style="font-size:12px; color:#64748B; margin-top:4px; font-weight:500;">{geo.get('full_address', '')[:60]}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:13px; color:#64748B; font-weight:600;">{w_text}</div>
                <div style="font-family:'Plus Jakarta Sans'; font-size:24px; font-weight:800; color:#0D631B;">{weather['current_temp']}째C</div>
            </div>
        </div>
        <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap:12px; margin-top:16px; padding-top:16px; border-top:1px solid rgba(0,0,0,0.05);">
            <div style="display:flex; align-items:center; gap:8px;">
                <span class="material-icon" style="font-size:16px; color:#64748B;">thermostat</span>
                <span style="font-size:12px; color:#40493D;">泥닿컧 <b>{weather['feels_like']}째C</b></span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span class="material-icon" style="font-size:16px; color:#64748B;">humidity_percentage</span>
                <span style="font-size:12px; color:#40493D;">?듬룄 <b>{weather['humidity']}%</b></span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span class="material-icon" style="font-size:16px; color:#64748B;">air</span>
                <span style="font-size:12px; color:#40493D;">?띿냽 <b>{weather['wind_speed']}m/s</b></span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span class="material-icon" style="font-size:16px; color:#0D631B;">verified</span>
                <span style="font-size:12px; color:#0D631B; font-weight:700;">湲고썑 蹂댁젙: <b>{cf:.2f}</b></span>
            </div>
        </div>
        <div style="font-size:11px; color:#94A3B8; margin-top:12px; text-align:center; background:rgba(0,0,0,0.02); padding:6px; border-radius:8px;">
            ?뱤 HDD {weather['hdd']} 쨌 CDD {weather['cdd']} (湲곗긽 ?곗씠??湲곕컲)
        </div>
    </div>
    """, unsafe_allow_html=True)

    if show_map:
        import pandas as pd
        map_data = pd.DataFrame({"lat": [lat], "lon": [lng]})
        st.map(map_data, zoom=11, use_container_width=True)


def render_step1():
    from streamlit_js_eval import get_geolocation

    # ?? 遺덊븘?뷀빐吏?援ы삎 DOM ?댄궧 ?듭떊 肄붾뱶 ?쒓굅 諛?媛꾧껐????
def render_step1():
    from streamlit_js_eval import get_geolocation

    # ?? [?꾨━誘몄뾼 Hero ?뱀뀡] ??
    st.markdown("""
    <div class="hero-section">
        <div class="hero-icon-wrapper">
            <span class="material-icon" style="font-size:32px; color:white;">eco</span>
        </div>
        <h1 class="hero-title">?먮꼫吏 ?덇컧 肄붿튂</h1>
        <p class="hero-subtitle">嫄대Ъ ?뺣낫瑜??낅젰?섏뿬 AI 湲곕컲??留욎땄???먮꼫吏 ?덇컧 ?붾（?섏쓣 ?뺤씤?섏꽭??/p>
    </div>
    """, unsafe_allow_html=True)

    # ?? ?꾩튂 媛먯? ?뱀뀡 ??
    st.markdown('<div class="section-title">?뱧 嫄대Ъ ?꾩튂 ?ㅼ젙</div>', unsafe_allow_html=True)

    loc_method = st.radio(
        "?꾩튂 ?ㅼ젙 諛⑸쾿",
        ["?뱻 ?먮룞 媛먯? (GPS)", "?륅툘 吏곸젒 ?좏깮"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if loc_method == "?뱻 ?먮룞 媛먯? (GPS)":
        if not st.session_state.get("location_detected"):
            st.markdown("""
            <div class="glass-card" style="text-align:center; padding:40px 20px; border: 1px dashed #0D631B;">
                <div class="material-icon" style="font-size:48px; color:#0D631B; margin-bottom:16px; animation: pulse 2s infinite;">location_searching</div>
                <div style="font-family:'Plus Jakarta Sans'; font-size:18px; font-weight:800; color:#071E27;">?붾컮?댁뒪 GPS ?섏떊 以?..</div>
                <div style="font-size:14px; color:#64748B; margin-top:8px;">釉뚮씪?곗???<b>'?꾩튂 ?덉슜'</b> 沅뚰븳???뱀씤??二쇱꽭??</div>
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
                st.warning("?좑툘 GPS ?좏샇瑜??≪쓣 ???놁뒿?덈떎. '吏곸젒 ?좏깮'???댁슜??二쇱꽭??")

        # ?섎룞 醫뚰몴 ?낅젰 (?붾쾭洹몄슜)
        with st.expander("?숋툘 醫뚰몴 ?섎룞 蹂댁젙"):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1: m_lat = st.number_input("?꾨룄", value=st.session_state.get("detected_lat", 37.5665), format="%.5f")
            with c2: m_lng = st.number_input("寃쎈룄", value=st.session_state.get("detected_lng", 126.9780), format="%.5f")
            with c3:
                st.write("")
                if st.button("?곸슜", use_container_width=True):
                    _fetch_location_data(m_lat, m_lng)
                    st.rerun()
    else:
        # 吏곸젒 ?좏깮 紐⑤뱶
        st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
        tab_addr, tab_city = st.tabs(["?룧 二쇱냼 寃??, "?뱦 二쇱슂 ?꾩떆"])
        
        with tab_addr:
            addr = st.text_input("?꾨줈紐?吏踰?二쇱냼 ?낅젰", placeholder="?? ?쒖슱?밸퀎??以묎뎄 ?몄쥌?濡?110", key="addr_in")
            if st.button("?꾩튂 李얘린", key="btn_addr", type="primary", use_container_width=True):
                if addr:
                    with st.spinner("?꾩튂 議고쉶 以?.."):
                        res = geocode(addr)
                        if res.get("success"):
                            _fetch_location_data(res["lat"], res["lng"])
                            st.rerun()
                        else: st.error("二쇱냼瑜?李얠쓣 ???놁뒿?덈떎.")
        
        with tab_city:
            city = st.selectbox("吏???좏깮", ["?쒖슱", "?몄쿇", "???, "?援?, "愿묒＜", "遺??, "?몄궛", "?쒖＜"], key="city_sel")
            if st.button("吏???좎뵪 ?곸슜", key="btn_city", use_container_width=True):
                coords = CITY_COORDS.get(city, (37.5665, 126.9780))
                _fetch_location_data(coords[0], coords[1])
                st.rerun()

    # ?? [吏??諛??좎뵪 ?쒖떆] ??
    if st.session_state.get("location_detected"):
        lat, lng = st.session_state.detected_lat, st.session_state.detected_lng
        
        # ?쇱씠???뚮쭏 吏??
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
                    background:     # ?? [嫄대Ъ ?몃? ?뺣낫] ??
    st.markdown('<div class="section-title">?룫 嫄대Ъ ?몃? ?뺣낫</div>', unsafe_allow_html=True)

    # ?ㅼ씠踰?遺?숈궛 媛?대뱶 諛곕꼫 (?쇱씠???뚮쭏)
    geo_data = st.session_state.get("detected_geo", {})
    raw_addr = geo_data.get("full_address", "") if isinstance(geo_data, dict) else ""
    if raw_addr:
        parts = [p.strip() for p in raw_addr.split(',') if p.strip()]
        kw = " ".join([p for p in reversed(parts) if p not in ["??쒕?援?, "Korea", "South Korea"]])
    else: kw = st.session_state.get("region", "?쒖슱?밸퀎??)
    
    import urllib.parse
    naver_url = f"https://new.land.naver.com/search?query={urllib.parse.quote(kw or '遺?숈궛')}"

    st.markdown(f"""
    <div style="background:rgba(13, 99, 27, 0.04); border:1px solid rgba(13, 99, 27, 0.15); border-radius:16px; padding:20px; margin-bottom:24px; display:flex; align-items:center; justify-content:space-between;">
        <div style="display:flex; align-items:center; gap:16px;">
            <div style="width:44px; height:44px; background:rgba(13, 99, 27, 0.1); border-radius:12px; display:flex; align-items:center; justify-content:center;">
                <span class="material-icon" style="color:#0D631B; font-size:24px;">info</span>
            </div>
            <div>
                <div style="font-family:'Plus Jakarta Sans'; font-size:15px; font-weight:800; color:#071E27; margin-bottom:2px;">?뺥솗??硫댁쟻怨??곕룄瑜?紐⑤Ⅴ?쒕굹??</div>
                <div style="font-size:13px; color:#64748B;">?ㅼ씠踰?遺?숈궛?먯꽌 <b>以怨??곗썡 諛?硫댁쟻</b>???쎄쾶 ?뺤씤?섏떎 ???덉뒿?덈떎.</div>
            </div>
        </div>
        <a href="{naver_url}" target="_blank" style="text-decoration:none;">
            <div style="background:#03C75A; color:white; font-size:13px; font-weight:700; padding:10px 20px; border-radius:10px; display:flex; align-items:center; gap:8px;">
                ?ㅼ씠踰?遺?숈궛 ??
            </div>
        </a>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        building_type = st.selectbox("嫄대Ъ ?좏삎", ["?꾪뙆??, "?⑤룆二쇳깮", "?곴?/?ㅽ뵾??], key="bt_sel")
    with c2:
        age = st.selectbox("嫄댁텞 ?곕룄", ["5???대궡", "5~15??, "15~30??, "30???댁긽"], index=1, key="age_sel")
    with c3:
        pyeong = st.number_input("嫄대Ъ 硫댁쟻 (??", 1, 500, 30, 1, key="py_in")

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    
    # ?? [?꾧린?붽툑 ?곗씠?? ??
    st.markdown('<div class="section-title">?뱤 ?붾퀎 ?꾧린?붽툑 湲곕줉</div>', unsafe_allow_html=True)
    
    ledger_col, chart_col = st.columns([1.2, 1.8])
    with ledger_col:
        st.markdown('<div style="font-size:13px; color:#64748B; margin-bottom:12px;">理쒓렐 1?꾧컙???붾퀎 ?붽툑???낅젰??二쇱꽭?? (?⑥쐞: 留뚯썝)</div>', unsafe_allow_html=True)
        sub1, sub2 = st.columns(2)
        for i in range(12):
            with (sub1 if i < 6 else sub2):
                val = st.number_input(f"{i+1}??, 0, 1000, int(st.session_state.recorded_bills[i]), 1, key=f"bill_{i}")
                st.session_state.recorded_bills[i] = int(val)

    with chart_col:
        months = [f"{i}?? for i in range(1, 13)]
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
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", title="?붽툑 (留뚯썝)")
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # ?몄뀡 ?숆린??
    st.session_state.building_type = building_type
    st.session_state.age = age
    st.session_state.region = region
    st.session_state.pyeong = pyeong

    st.markdown('<div style="height:40px;"></div>', unsafe_allow_html=True)
    if st.button("?ㅼ쓬 ?④퀎濡??대룞 ??, type="primary", use_container_width=True, on_click=go_next):
        pass
슂. ?ㅼ떆媛꾩쑝濡??꾨젰 ?뚮퉬 異붿씠瑜?李⑦듃?뷀븯???뺣? 遺꾩꽍???쒓났?⑸땲??"
        "</p>", 
        unsafe_allow_html=True
    )

    ledger_col, chart_col = st.columns([1.2, 2])

    with ledger_col:
        # 12媛쒖썡 湲곕낯 由ъ뒪??
        months_list = [f"{i}?? for i in range(1, 13)]
        
        st.markdown("<div style='padding-bottom: 8px; border-bottom: 1px solid #334155; margin-bottom: 12px;'><span style='font-size:13.5px; font-weight:700; color:#E2E8F0;'>?뮥 ?붾퀎 ?붽툑 ?낅젰 (?⑥쐞: 留뚯썝)</span></div>", unsafe_allow_html=True)
        
        # ??媛쒖쓽 ?대줈 6媛쒖썡??源붾걫?섍쾶 諛곗튂
        sub_l, sub_r = st.columns(2)
        
        for i in range(12):
            target_sub = sub_l if i < 6 else sub_r
            with target_sub:
                # Streamlit 怨좎쑀 ?낅젰湲곕줈 ?먯쿇??踰꾧렇 ?덈갑 諛?留ㅻ걚?ъ슫 UX 蹂댁옣
                val = st.number_input(
                    f"{i+1}???붽툑",
                    min_value=0,
                    max_value=1000,
                    value=int(st.session_state.recorded_bills[i]),
                    step=1,
                    key=f"bill_input_{i}"
                )
                # ?낅젰 利됱떆 ?몄뀡???뺤닔???곗씠???숆린??
                st.session_state.recorded_bills[i] = int(val)

    with chart_col:
        # ?ㅼ떆媛?湲곕줉 蹂??李⑦듃 ?뚮뜑留?
        fig_log = go.Figure()
        fig_log.add_trace(go.Scatter(
            x=months_list, 
            y=st.session_state.recorded_bills,
            mode='lines+markers',
            name='湲곕줉???붽툑',
            line=dict(color='#50C878', width=3, shape='spline'),
            marker=dict(size=8, color='#10B981', line=dict(width=2, color='#FFFFFF')),
            hovertemplate="%{x} ?붽툑: <b>%{y}留뚯썝</b><extra></extra>"
        ))
        fig_log.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", 
            plot_bgcolor="rgba(15,23,42,0.4)",
            font=dict(family="Inter", color="#E2E8F0", size=11),
            xaxis=dict(gridcolor="#334155", zeroline=False),
            yaxis=dict(gridcolor="#334155", zeroline=False, title="?꾧린?붽툑 (留뚯썝)"),
            height=280,
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig_log, config={'displayModeBar': False}, use_container_width=True, key="realtime_trend")

    # ?몄뀡 蹂???듯빀 (嫄대Ъ ?뺣낫 ?숆린??
    st.session_state.building_type = building_type
    st.session_state.age = age
    st.session_state.region = region
    st.session_state.pyeong = pyeong

    st.markdown("")
    col_l, col_r = st.columns([3, 1])
    with col_r:
        st.button("?ㅼ쓬 ?④퀎 ??, on_click=go_next, use_container_width=True)




# ??????????????????????????????????????????????????????????????
# STEP 2: ?곕━ 嫄대Ъ ?깅뒫 ?뺣웾 ?됯? (1~5?④퀎)
# ??????????????????????????????????????????????????????????????
def render_step2():
    st.markdown("""
    <div class="hero">
        <div style="font-size:44px;margin-bottom:4px;">?뱤</div>
        <div class="hero-title">?곕━ 嫄대Ъ ?깅뒫 ?뺣웾 ?됯?</div>
        <div class="hero-sub">?ㅼ젣 ?앺솢 泥닿컧??湲곕컲?쇰줈 嫄대Ъ ?먮꼫吏 ?깅뒫??1~5?④퀎濡??뺣? 吏꾨떒?⑸땲??</div>
    </div>
    """, unsafe_allow_html=True)

    # ?쒓컖???덈궡 釉붾줉
    st.markdown("""
    <div style="background:rgba(56,189,248,0.06);border:1px solid rgba(56,189,248,0.2);border-radius:12px;padding:15px 18px;margin-top:10px;margin-bottom:28px;">
        <div style="font-size:13px;color:#38BDF8;font-weight:800;margin-bottom:4px;">?뮕 ?뺣웾 ?됯? 媛?대뱶</div>
        <div style="font-size:12px;color:#E2E8F0;line-height:1.6;">
            ??<b>1?④퀎(?곗닔)</b>??媛源뚯슱?섎줉 ?좎텞 ?⑥떆釉뚰븯?곗뒪湲됱쓽 ?곗뼱???먮꼫吏 ?몄씠鍮??곹깭瑜??섎??⑸땲??<br>
            ??<b>5?④퀎(痍⑥빟)</b>??媛源뚯슱?섎줉 ?먯옱 ?명썑 諛??댁쟻 寃곗넀?쇰줈 ?명븳 ?먮꼫吏 ??퉬媛 洹밸룄濡??ы븳 ?곹깭?낅땲??
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ?? ?뺣웾 ?ㅻЦ ??ぉ 4????
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### ?뮜 1. ?명뭾 李⑤떒 ?섏? (湲곕???")
        airtight_score = st.select_slider(
            "李쎈Ц?대굹 ?덉깉濡??ㅼ뼱?ㅻ뒗 諛붾엺???뺣룄",
            options=[1, 2, 3, 4, 5],
            value=2,
            format_func=lambda x: {
                1: "1?④퀎: ?꾨꼍 李⑤떒 (諛遊됯툒)",
                2: "2?④퀎: 泥닿컧?섍린 ?섎벀 (?묓샇)",
                3: "3?④퀎: 諛붾엺 遺????媛???좎엯",
                4: "4?④퀎: 寃⑥슱泥?紐낇솗???명뭾 ?먮굦",
                5: "5?④퀎: ?⑹냼諛붾엺 ?좎엯 (?ш컖)"
            }[x],
            key="survey_airtight"
        )
        st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True)

        st.markdown("##### ?꾬툘 2. ?ㅻ궡 ?⑤룄 蹂댁〈??(?⑥뿴??")
        insulation_score = st.select_slider(
            "?됰궃諛?以묐떒 ???ㅻ궡 ?④린媛 蹂댁〈?섎뒗 ?쒓컙",
            options=[1, 2, 3, 4, 5],
            value=2,
            format_func=lambda x: {
                1: "1?④퀎: 3?쒓컙 ?댁긽 ?덉젙??吏??,
                2: "2?④퀎: 1~2?쒓컙 ?댁쇅 ?좎? (蹂댄넻)",
                3: "3?④퀎: ?꾧퀬 30遺??댁쇅濡?湲덈갑 ?앹쓬",
                4: "4?④퀎: ?뺤? 利됱떆 ?ㅻ궡媛 異붿썙吏??붿썙吏?,
                5: "5?④퀎: 諛붽묑 ?좎뵪? 利됯컖 ?숆린??
            }[x],
            key="survey_insulation"
        )

    with col2:
        st.markdown("##### ?뙜截?3. ?됰궃諛??꾨떖 ?띾룄 (?ㅻ퉬 ?⑥쑉)")
        hvac_score = st.select_slider(
            "?먯뼱而?蹂댁씪??媛????紐⑺몴 ?⑤룄 ?꾨떖 ?쒓컙",
            options=[1, 2, 3, 4, 5],
            value=2,
            format_func=lambda x: {
                1: "1?④퀎: 15遺???利됯컖 苡뚯쟻 ?⑤룄 ?꾨떖",
                2: "2?④퀎: 30遺??댁쇅 ?먰솢??議곗젅 (蹂댄넻)",
                3: "3?④퀎: 1?쒓컙 ?곗냽 媛????寃⑥슦 ?꾨떖",
                4: "4?④퀎: 媛???鍮??⑤룄 ?섎씫/?곸듅???붾뵥",
                5: "5?④퀎: ?섎（醫낆씪 ??대룄 ?④낵媛 ?곸쓬"
            }[x],
            key="survey_hvac"
        )
        st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True)

        st.markdown("##### ?截?4. ?щ쫫泥??쇱궗 遺??(梨꾧킅??")
        solar_score = st.select_slider(
            "而ㅽ듉 ?녿뒗 ?щ쫫泥?李쎌쓣 ?듯븳 蹂듭궗??媛뺣룄",
            options=[1, 2, 3, 4, 5],
            value=2,
            format_func=lambda x: {
                1: "1?④퀎: ?⑦솕?섍퀬 ????梨꾧킅",
                2: "2?④퀎: ?곸젅???쇱떆???덈???(蹂댄넻)",
                3: "3?④퀎: ?뉖튆???덈Т 媛뺥빐 而ㅽ듉???꾩슂",
                4: "4?④퀎: 李쎄? 二쇰????꾨걟 ?ъ븘?ㅻ쫫",
                5: "5?④퀎: ?ㅻ궡媛 ?⑥떎泥섎읆 ?닿린媛 媛뉙옒"
            }[x],
            key="survey_solar"
        )

    # ?먯닔 ?곗씠??諛붿씤??
    st.session_state.discomfort_scores = {
        "airtight": airtight_score,
        "insulation": insulation_score,
        "hvac": hvac_score,
        "solar": solar_score
    }

    # 由щえ?몃쭅 ?섑뼢
    st.markdown("<div style='height:35px;'></div>", unsafe_allow_html=True)
    remodel = st.checkbox("?룛截??ν썑 ?⑥뿴/李쏀샇 媛쒕낫???먮뒗 由щえ?몃쭅??寃??以묒씠?좉???", value=False,
                          help="?좏깮 ??痍⑥빟??遺遺꾩쓣 遺꾩꽍?섏뿬 ?곗꽑 ?ъ옄 ?뚯닔 由ы룷?몃? 異붽? ?쒓났?⑸땲??")
    st.session_state.remodel = remodel

    st.markdown("")
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.button("???댁쟾", on_click=go_prev, use_container_width=True)
    with col_r:
        st.button("AI 吏꾨떒 ?쒖옉 ?뵮", on_click=run_diagnosis, use_container_width=True)


def run_diagnosis():
    """?뺣웾 ?먯닔 ?뺤뀛?덈━瑜??ъ슜?섏뿬 吏꾨떒 ?붿쭊 援щ룞"""
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


# ??????????????????????????????????????????????????????????????
# STEP 3: AI 吏꾨떒 寃곌낵
# ??????????????????????????????????????????????????????????????
def render_step3():
    dx = st.session_state.diagnosis
    if dx is None:
        st.error("吏꾨떒 ?곗씠?곌? ?놁뒿?덈떎. 泥섏쓬遺???ㅼ떆 ?쒖옉?댁＜?몄슂.")
        st.button("泥섏쓬?쇰줈", on_click=restart)
        return

    grade = dx["grade"]
    grade_css = dx["grade_css"]
    is_good = grade in ("A+", "A", "B")

    # ?ㅻ뜑
    emoji = "?? if is_good else "?좑툘"
    st.markdown(f"""
    <div class="hero">
        <div style="font-size:44px;margin-bottom:4px;">{emoji}</div>
        <div class="hero-title">AI 吏꾨떒 寃곌낵</div>
        <div class="hero-sub">{st.session_state.building_type} 쨌 {st.session_state.pyeong}??쨌 {st.session_state.region} 쨌 {st.session_state.age}</div>
    </div>
    """, unsafe_allow_html=True)

    # ?깃툒 + 鍮꾩슜 諛곕꼫
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
                ?먮꼫吏 ?⑥쑉 吏꾨떒 寃곌낵
            </div>
            <div style="font-size:15px;color:#E2E8F0;margin-bottom:6px;">
                ?곌컙 ?덉긽 ?꾧린?붽툑: <b style="font-size:24px;color:{cost_color}">{annual_cost_str}</b>
            </div>
            <div style="font-size:13px;color:#6B8AB0;">
                媛숈? 議곌굔 理쒖쟻 嫄대Ъ: {optimal_str} &nbsp;쨌&nbsp;
                <span style="color:{cost_color};font-weight:700;">理쒕? {saving_str} ?덇컧 媛??/span>
            </div>
        </div>
        <div style="text-align:center;flex-shrink:0;margin-left:24px;">
            <div class="grade-badge {grade_css}">{grade}</div>
            <div style="font-size:11px;color:#4A6080;margin-top:8px;font-weight:600;">?먮꼫吏 ?⑥쑉 ?깃툒</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ?? 湲고썑 ?명뀛由ъ쟾???곸슜 ?쒓렇 ??
    rf = dx["params"]["region_factor"]
    is_realtime = st.session_state.get("location_detected", False)
    
    if is_realtime:
        geo = st.session_state.get("detected_geo", {})
        region_str = f"{geo.get('region', '')} {geo.get('city', '')}".strip() or st.session_state.region
        st.markdown(f"""
        <div style="background:rgba(56,189,248,0.08);border:1px solid rgba(56,189,248,0.25);border-radius:12px;
                    padding:12px 18px;margin-bottom:16px;display:flex;align-items:center;gap:10px;font-size:13px;">
            <span style="font-size:16px;">?쎇截?/span>
            <span style="color:#E2E8F0;">
                <b>?ㅼ떆媛?湲고썑 ?명뀛由ъ쟾???곸슜:</b> {region_str}??1??湲고썑 ?곗씠??遺꾩꽍 ?꾨즺 (湲고썑 蹂댁젙: <b>{rf:.2f}諛?/b>)
            </span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:rgba(107,138,176,0.08);border:1px solid rgba(107,138,176,0.2);border-radius:12px;
                    padding:12px 18px;margin-bottom:16px;display:flex;align-items:center;gap:10px;font-size:13px;">
            <span style="font-size:16px;">?뱤</span>
            <span style="color:#6B8AB0;">
                <b>?쒖? 吏???듦퀎 ?곸슜:</b> {st.session_state.region}??湲곕낯 湲고썑 怨꾩닔 ?곸슜 (吏??蹂댁젙: <b>{rf:.2f}諛?/b>)
            </span>
        </div>
        """, unsafe_allow_html=True)

    # KPI 3媛?
    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi">
            <div class="label">?곌컙 ?먮꼫吏</div>
            <div class="value" style="color:#38BDF8">{dx['current_kwh']/1000:.1f} <span style="font-size:14px;color:#4A6080">MWh</span></div>
            <div class="sub">理쒖쟻 {dx['optimal_kwh']/1000:.1f} MWh</div>
        </div>
        <div class="kpi">
            <div class="label">???덉긽 鍮꾩슜</div>
            <div class="value" style="color:#FFB347">{won_to_manwon(dx['current_cost']/12)}</div>
            <div class="sub">理쒖쟻 {won_to_manwon(dx['optimal_cost']/12)}</div>
        </div>
        <div class="kpi">
            <div class="label">?덇컧 媛?μ븸</div>
            <div class="value" style="color:#50C878">{saving_str}</div>
            <div class="sub">?곌컙 湲곗?</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ?먮꼫吏 ??퉬 寃뚯씠吏
    st.markdown("#### ?뱤 ?먮꼫吏 ??퉬 ?ъ씤??)
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

    # ?붾퀎 ?붽툑 李⑦듃
    st.markdown("#### ?뱟 ?붾퀎 ?꾧린?붽툑 鍮꾧탳 ?⑦꽩")
    st.markdown(f"""
    <div style='background: rgba(30, 41, 59, 0.5); border-left: 3px solid #3B82F6; padding: 10px 14px; border-radius: 6px; margin-top: -10px; margin-bottom: 15px;'>
        <p style='font-size:12.5px; color:#E2E8F0; margin:0; font-weight:600;'>?뮕 理쒖쟻 嫄대Ъ 鍮꾧탳 湲곗? ?덈궡</p>
        <p style='font-size:11.5px; color:#94A3B8; margin:4px 0 0 0; line-height:1.5;'>
            ?숈씪 硫댁쟻??理쒖떊 <b>湲濡쒕쾶 ?⑥떆釉뚰븯?곗뒪(Passive House) ?몄쬆 ?섏?</b>??異⑹”?섎뒗 怨좎꽦??嫄대Ъ(李쎈㈃?곷퉬 25%, ?몃떒??200mm, 珥덇퀬諛??湲곕? ?ㅺ퀎, 1?깃툒 怨좏슚???덊듃?뚰봽 ?묒옱)???대줎???붽툑 ?쒓퀎?좎엯?덈떎.<br>
            ?좏깮?섏떊 <b>{st.session_state.building_type}</b> ?꾩슜 ?먮꼫吏 媛뺣룄 湲곗??⑥쓣 ?곸슜?섍퀬 吏??湲고썑 ?몄감瑜?蹂댁젙?섏뿬, ?꾩떎?곸쑝濡??ъ꽦 媛?ν븳 理쒖쟻???덇컧 媛?대뱶瑜??쒖떆?⑸땲??
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    months = ["1??,"2??,"3??,"4??,"5??,"6??,"7??,"8??,"9??,"10??,"11??,"12??]
    # ?ㅼ젣 湲곕줉 ?곗씠??媛?몄삤湲?(留뚯썝)
    m_now = st.session_state.recorded_bills 
    # 理쒖쟻 嫄대Ъ ?먮꼫吏(kWh)瑜??붽툑(留뚯썝)?쇰줈 ?섏궛: (kWh * 130?? / 10000??
    m_opt = [(kwh * ELEC_RATE) / 10000.0 for kwh in dx["monthly_opt"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=months, y=m_opt, name="理쒖쟻 嫄대Ъ (?붽툑)",
        marker_color="rgba(107,138,176,0.35)",
        hovertemplate="%{x} 理쒖쟻: <b>%{y:.1f}留뚯썝</b><extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=months, y=m_now, name="湲곕줉????嫄대Ъ ?붽툑",
        marker_color="#F87171" if not is_good else "#50C878",
        hovertemplate="%{x} ?댁슂湲? <b>%{y}留뚯썝</b><extra></extra>"
    ))
    fig.update_layout(
        paper_bgcolor="#0A0F1E", plot_bgcolor="#0D1526",
        font=dict(family="Inter", color="#E2E8F0"),
        xaxis=dict(gridcolor="#1A2740"),
        yaxis=dict(gridcolor="#1A2740", title="?꾧린?붽툑 (留뚯썝)"),
        barmode="group", bargap=0.25, height=300,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#94A3B8"),
                    orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=16, r=16, t=40, b=16),
    )
    st.plotly_chart(fig, key="step3_chart", use_container_width=True)

    st.markdown("")
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.button("???댁쟾", on_click=go_prev, use_container_width=True, key="s3_prev")
    with col_r:
        st.button("?덇컧 諛⑹븞 蹂닿린 ??, on_click=go_next, use_container_width=True, key="s3_next")


# ??????????????????????????????????????????????????????????????
# STEP 4: 留욎땄???덇컧 諛⑹븞 媛?대뱶
# ??????????????????????????????????????????????????????????????
def render_step4():
    dx = st.session_state.diagnosis
    if dx is None:
        st.error("吏꾨떒 ?곗씠?곌? ?놁뒿?덈떎.")
        st.button("泥섏쓬?쇰줈", on_click=restart)
        return

    st.markdown("""
    <div class="hero">
        <div style="font-size:44px;margin-bottom:4px;">?뮕</div>
        <div class="hero-title">留욎땄???덇컧 諛⑹븞 異붿쿇</div>
        <div class="hero-sub">?꾪꽣留?湲곗????곕씪 AI媛 ?좊퀎??嫄대Ъ??理쒖쟻 媛쒖꽑 ?붾（?섏쓣 ?뺤씤?대낫?몄슂</div>
    </div>
    """, unsafe_allow_html=True)

    all_recs = get_all_recommendations(dx, st.session_state.pyeong)
    rank_icons = ["?쪍", "?쪎", "?쪏", "?럷截?, "?럷截?, "?럷截?, "?럷截?, "?럷截?]

    # 湲곗?蹂????앹꽦
    tab_overall, tab_invest, tab_saving, tab_pct = st.tabs([
        "?룇 醫낇빀 異붿쿇 湲곗?", 
        "?뮥 ?ъ옄鍮??덉빟 湲곗?", 
        "?뵦 ?덇컧 湲덉븸 湲곗?", 
        "???덇컧瑜??⑥쑉 湲곗?"
    ])

    def render_rec_list(sorted_list, group_label, highlight_col=""):
        """吏?뺣맂 ?뺣젹 由ъ뒪?몃? ?뚮뜑留곹븯怨??숈쟻 ?붿빟 ?⑤꼸???몄텧?⑸땲??"""
        for idx, rec in enumerate(sorted_list[:4]): # 媛???떦 ?곸쐞 4媛쒖뵫 ?몄텧
            invest_str = f"{rec['invest_manwon']:,.0f}留뚯썝"
            saving_str = won_to_manwon(rec["annual_saving_won"])
            payback_str = f"{rec['payback_years']}??

            # ?뺣젹 湲곗? 而щ읆 ?쒓컖??媛뺤“ 泥섎━
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
                        <div class="label">?ъ옄鍮?/div>
                        <div class="val" style="color:#FFB347;{inv_hl}">{invest_str}</div>
                    </div>
                    <div class="rec-metric">
                        <div class="label">?곌컙 ?덇컧</div>
                        <div class="val" style="color:#50C878;{sav_hl}">{saving_str}</div>
                    </div>
                    <div class="rec-metric">
                        <div class="label">?뚯닔 湲곌컙</div>
                        <div class="val" style="color:#38BDF8;">{payback_str}</div>
                    </div>
                    <div class="rec-metric">
                        <div class="label">?덇컧瑜?/div>
                        <div class="val" style="color:#E2E8F0;{pct_hl}">{rec['saving_pct']}%</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ?곸쐞 3媛??좏깮 ??珥??덇컧 ?붿빟
        top3 = sorted_list[:3]
        total_saving = sum(r["annual_saving_won"] for r in top3)
        total_invest = sum(r["invest_manwon"] for r in top3)
        st.markdown(f"""
        <div style="background:rgba(13, 21, 38, 0.6);border:1px solid #1A5C35;border-radius:14px;padding:18px;margin-top:16px;text-align:center;">
            <div style="font-size:13px;color:#94A3B8;font-weight:600;">?뮕 {group_label} ?곸쐞 3媛?諛⑹븞 寃고빀 ?곸슜 ??/div>
            <div style="font-size:15px;color:#E2E8F0;margin-top:8px;font-weight:500;">
                珥??덉긽 ?ъ옄鍮? <b style="color:#FFB347;">{total_invest:,.0f}留뚯썝</b> &nbsp;??nbsp;
                ?곌컙 ?붽툑 ?덇컧?? <b style="color:#50C878;">{won_to_manwon(total_saving)}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 1. 醫낇빀 異붿쿇 湲곗? (?곗꽑?쒖쐞 Score ?대┝李⑥닚)
    with tab_overall:
        st.markdown("<p style='color:#94A3B8; font-size:13px; margin-bottom:16px;'>?뮕 ?뚯닔 湲곌컙怨??꾩옱 嫄대Ъ??遺???곹깭(?됰궃諛??⑥뿴)瑜?醫낇빀?곸쑝濡?洹좏삎 ?덇쾶 怨좊젮??AI 踰좎뒪??異붿쿇?쒖엯?덈떎.</p>", unsafe_allow_html=True)
        recs_sorted = sorted(all_recs, key=lambda x: x["priority"], reverse=True)
        render_rec_list(recs_sorted, "醫낇빀 異붿쿇")

    # 2. ?ъ옄鍮??덉빟 湲곗? (?ъ옄鍮??ㅻ쫫李⑥닚 - ??? 寃??곗꽑)
    with tab_invest:
        st.markdown("<p style='color:#94A3B8; font-size:13px; margin-bottom:16px;'>?뮕 珥덇린 ?ъ엯?섎뒗 ?쒓났 鍮꾩슜??媛???곸? ??ぉ ?쒖쑝濡??섏뿴?⑸땲?? 媛踰쇱슫 ???媛쒖꽑?대굹 ?媛???쒓났???곗꽑 諛곗튂?⑸땲??</p>", unsafe_allow_html=True)
        recs_sorted = sorted(all_recs, key=lambda x: x["invest_manwon"])
        render_rec_list(recs_sorted, "理쒖? ?ъ옄鍮?, highlight_col="invest")

    # 3. ?덇컧 湲덉븸 湲곗? (?곌컙 ?덇컧???대┝李⑥닚 - ?믪? 寃??곗꽑)
    with tab_saving:
        st.markdown("<p style='color:#94A3B8; font-size:13px; margin-bottom:16px;'>?뮕 留ㅻ떖 ?듭옣?먯꽌 ?섍????ㅼ젣 ?꾧린?붽툑??媛??'留롮씠' 以꾩뿬二쇰뒗 ?꾧툑 ?섏궛 媛移섍? ?믪? ??ぉ ?쒖꽌?낅땲??</p>", unsafe_allow_html=True)
        recs_sorted = sorted(all_recs, key=lambda x: x["annual_saving_won"], reverse=True)
        render_rec_list(recs_sorted, "理쒕? ?꾧툑 ?덇컧", highlight_col="saving")

    # 4. ?덇컧瑜??⑥쑉 湲곗? (?먮꼫吏 ?덇컧 鍮꾩쑉 ?대┝李⑥닚 - ?믪? 寃??곗꽑)
    with tab_pct:
        st.markdown("<p style='color:#94A3B8; font-size:13px; margin-bottom:16px;'>?뮕 ?ъ옄 洹쒕え? ?곴??놁씠 臾쇰━?곸씤 ?먮꼫吏 ?뚮퉬???⑥쐞瑜??쒖닔?섍쾶 媛???ш쾶 ??떠二쇰뒗 ?⑥쑉 湲곗닠 ?깅뒫 ?쒖꽌?낅땲??</p>", unsafe_allow_html=True)
        recs_sorted = sorted(all_recs, key=lambda x: x["saving_pct"], reverse=True)
        render_rec_list(recs_sorted, "理쒓퀬 ?덇컧 ?⑥쑉", highlight_col="pct")

    st.markdown("")
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.button("??吏꾨떒 寃곌낵", on_click=go_prev, use_container_width=True, key="s4_prev")
    with col_r:
        st.button("蹂댁“湲??뺤씤 ??, on_click=go_next, use_container_width=True, key="s4_next")


# ??????????????????????????????????????????????????????????????
# STEP 5: ?뺣? 蹂댁“湲??덈궡
# ??????????????????????????????????????????????????????????????
def render_step5():
    region_nm = st.session_state.region
    
    # 蹂댁“湲?由ъ뒪??癒쇱? 議고쉶 (諛곕꼫 ?붿빟 怨꾩궛??
    subsidies = get_matching_subsidies(
        st.session_state.building_type,
        st.session_state.age,
        st.session_state.region,
    )
    
    st.markdown(f"""
    <div class="hero">
        <div style="font-size:44px;margin-bottom:4px;">?룢截?/div>
        <div class="hero-title">?쒖슜 媛?ν븳 ?뺣? 蹂댁“湲?/div>
        <div class="hero-sub">?뱧{region_nm} 吏???쒗깮 諛??꾧뎅 怨듬룞 吏???ъ뾽??議고쉶?덉뒿?덈떎</div>
    </div>
    """, unsafe_allow_html=True)

    # ?곷떒???뺣? 蹂댁“湲??쒗깮 珥앺빀???덈궡?섎뒗 ?꾨━誘몄뾼 ?붿빟 諛곕꼫 諛곗튂
    dx = st.session_state.diagnosis
    if dx:
        saving_str = won_to_manwon(dx["saving_potential"])
        total_direct_cash = sum(s.get("direct_cash_manwon", 0) for s in subsidies)
        
        # 二쇱쓽: Markdown 留덊겕???뚯떛 ?먮윭 諛⑹?瑜??꾪빐 HTML 而⑦뀗痢좊뒗 泥?移?No Indent)遺???묒꽦?댁빞 ?⑸땲??
        st.markdown(f"""
<div style="background:linear-gradient(135deg,#0D2240,#0F3A5F);border:1px solid #1A4B73;border-radius:16px;padding:24px 20px;margin-top:10px;margin-bottom:28px;box-shadow:0 4px 15px rgba(0,0,0,0.35);">
<div style="font-size:13px;color:#60A5FA;margin-bottom:8px;text-align:center;font-weight:700;letter-spacing:1px;">?뱥 醫낇빀 吏꾨떒 ?쒗깮 ?붿빟</div>
<div style="font-size:18px;color:#F1F5F9;font-weight:800;text-align:center;margin-bottom:20px;letter-spacing:-0.5px;">{st.session_state.building_type} 쨌 {st.session_state.pyeong}??쨌 ?먮꼫吏 ?깃툒 <span style="color:#50C878;">{dx['grade']}</span></div>
<div style="display:flex;flex-wrap:wrap;justify-content:space-around;border-top:1px solid #1E4A6F;padding-top:20px;gap:12px;">
<div style="text-align:center;min-width:140px;flex:1;">
<div style="font-size:12px;color:#94A3B8;margin-bottom:6px;font-weight:600;">???곌컙 ?덉긽 ?먮꼫吏 ?붽툑 ?덇컧</div>
<div style="font-size:22px;color:#10B981;font-weight:900;">{saving_str}</div>
</div>
<div style="width:1px;background:#1E4A6F;align-self:stretch;display:block;"></div>
<div style="text-align:center;min-width:140px;flex:1;">
<div style="font-size:12px;color:#94A3B8;margin-bottom:6px;font-weight:600;">?럞 ?뺣? 蹂댁“湲??쒗깮 (理쒕?)</div>
<div style="font-size:22px;color:#3B82F6;font-weight:900;">{total_direct_cash}留뚯썝</div>
</div>
</div>
<div style="text-align:center;font-size:11px;color:#4A6B8F;margin-top:16px;">* 吏??議곌굔 諛?湲덉쑖 吏??臾댁씠???듭옄 ?? ?쒗깮???곕씪 理쒖쥌 ?섍툒?≪? 蹂?숇맆 ???덉뒿?덈떎.</div>
</div>
""", unsafe_allow_html=True)

    # 媛쒕퀎 蹂댁“湲?移대뱶 ?뚮뜑留?
    if not subsidies:
        st.info("?꾩옱 議곌굔??留욌뒗 蹂댁“湲??꾨줈洹몃옩???놁뒿?덈떎. 吏?먯껜蹂?異붽? 吏?먯쓣 ?뺤씤?대낫?몄슂.")
    else:
        for s in subsidies:
            # 吏???꾧뎅 ?щ????곕씪 諭껋? ?ㅻ???
            is_local = s.get("_p_score", 1) == 0
            badge_html = ""
            if is_local:
                badge_html = f"""<span style="background:#10B98120;color:#10B981;border:1px solid #10B98140;
                              font-size:11px;padding:3px 8px;border-radius:12px;font-weight:600;
                              margin-left:8px;vertical-align:middle;">?뱧 {region_nm} ?꾩슜</span>"""
            else:
                badge_html = """<span style="background:#3B82F620;color:#60A5FA;border:1px solid #3B82F640;
                              font-size:11px;padding:3px 8px;border-radius:12px;font-weight:600;
                              margin-left:8px;vertical-align:middle;">?눖?눟 ?꾧뎅 怨듯넻</span>"""

            st.markdown(f"""
<div class="subsidy-card">
    <div class="name" style="display:flex;justify-content:space-between;align-items:center;">
        <span>{s['name']}</span>
        {badge_html}
    </div>
    <div class="detail">
        <b>吏??湲곌?:</b> {s['org']}<br>
        <b>???</b> {s['target']}<br>
        <b>吏???댁슜:</b> {s['support']}<br>
        <b>?좎껌 湲곌컙:</b> <span style="color:#EAB308;font-weight:600;">{s.get('period_str', '?곗쨷 ?곸떆')}</span><br>
        <b>吏??湲덉븸:</b> <span style="color:#50C878;font-weight:700;">{s['amount']}</span><br>
        <b>諛붾줈媛湲?</b> <a href="{s['url']}" target="_blank" style="color:#3B82F6;text-decoration:underline;font-size:13px;">{s['url']}</a>
    </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("")
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.button("???덇컧 諛⑹븞", on_click=go_prev, use_container_width=True, key="s5_prev")
    with col_r:
        st.button("?봽 泥섏쓬遺???ㅼ떆", on_click=restart, use_container_width=True, key="s5_restart")



# ??????????????????????????????????????????????????????????????
# 硫붿씤 ?쇱슦??
# ??????????????????????????????????????????????????????????????
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
