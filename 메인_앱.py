# -*- coding: utf-8 -*-
"""
에너지 절감 코치 — 메인 앱 (5단계 마법사)

일반 소비자가 건물 정보를 단계별로 입력하면
AI가 에너지 진단 + 절감 방안 TOP 3 + 정부 보조금을 안내합니다.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# ── 유틸리티 모듈 임포트 ──
from 유틸리티.디자인_스타일 import get_main_css
from 유틸리티.에너지_분석_엔진 import (
    diagnose, won_to_manwon, ELEC_RATE
)
from 유틸리티.절감_방안_추천 import get_all_recommendations
from 유틸리티.정부_보조금 import get_matching_subsidies
from 유틸리티.기상_정보_조회 import (
    reverse_geocode, geocode, fetch_weather, calc_climate_factor,
    weather_code_to_text, CITY_COORDS
)

# ── 페이지 설정 ──
st.set_page_config(
    page_title="에너지 절감 코치",
    page_icon="🏠",
    layout="centered",
)

# CSS 주입 (라이트 테마 강제)
st.markdown(get_main_css(), unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# 세션 스테이트 초기화
# ──────────────────────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step = 1
if "diagnosis" not in st.session_state:
    st.session_state.diagnosis = None
if "recorded_bills" not in st.session_state:
    # 초기 기본값 (만원 단위)
    st.session_state.recorded_bills = [12, 11, 9, 8, 9, 13, 18, 20, 14, 9, 8, 11]

def go_next(): st.session_state.step += 1
def go_prev(): st.session_state.step -= 1
def restart():
    for key in list(st.session_state.keys()): del st.session_state[key]

# ──────────────────────────────────────────────────────────────
# 프로그레스 바 렌더링
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
# STEP 1: 건물 정보 입력
# ──────────────────────────────────────────────────────────────
def render_step1():
    st.markdown('''
    <div class="hero-section">
        <h1 class="hero-title">에너지 절감 코치</h1>
        <p class="hero-subtitle">건물 정보를 입력하여 AI 기반의 맞춤형 에너지 절감 솔루션을 확인하세요</p>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown('<div class="section-title">📍 건물 위치 및 기본 정보</div>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            city = st.selectbox("지역 선택", ["서울", "인천", "대전", "대구", "광주", "부산", "울산", "제주"])
        with c2:
            pyeong = st.number_input("건물 면적 (평)", 1, 500, 30)
            
        building_type = st.selectbox("건물 유형", ["아파트", "단독주택", "상가/오피스"])
        age = st.selectbox("건축 연도", ["5년 이내", "5~15년", "15~30년", "30년 이상"], index=1)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">📊 월별 전기요금 (만원)</div>', unsafe_allow_html=True)
    
    cols = st.columns(6)
    for i in range(12):
        with cols[i % 6]:
            val = st.number_input(f"{i+1}월", 0, 1000, int(st.session_state.recorded_bills[i]), key=f"bill_{i}")
            st.session_state.recorded_bills[i] = val

    st.session_state.update({
        "building_type": building_type,
        "age": age,
        "pyeong": pyeong,
        "region": city
    })

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    st.button("다음 단계로 이동 →", type="primary", use_container_width=True, on_click=go_next)

# ──────────────────────────────────────────────────────────────
# STEP 2: 불편함 체크
# ──────────────────────────────────────────────────────────────
def render_step2():
    st.markdown('<div class="section-title">🌡️ 거주 성능 정량 평가</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    airtight = st.select_slider("외풍 수준 (1:완벽차단 ~ 5:심각)", options=[1,2,3,4,5], value=3)
    insulation = st.select_slider("단열 유지력 (1:3시간이상 ~ 5:즉시식음)", options=[1,2,3,4,5], value=3)
    st.markdown('</div>', unsafe_allow_html=True)

    st.session_state.discomfort_scores = {"airtight": airtight, "insulation": insulation, "hvac": 3, "solar": 3}
    
    c1, c2 = st.columns(2)
    with c1: st.button("← 이전", on_click=go_prev, use_container_width=True)
    with c2: st.button("AI 진단 시작 →", type="primary", on_click=run_diagnosis, use_container_width=True)

def run_diagnosis():
    result = diagnose(
        pyeong=st.session_state.pyeong,
        building_type=st.session_state.building_type,
        age=st.session_state.age,
        region=st.session_state.region,
        discomfort_scores=st.session_state.discomfort_scores,
        recorded_bills=st.session_state.recorded_bills,
        climate_factor=1.0
    )
    st.session_state.diagnosis = result
    st.session_state.step = 3

# ──────────────────────────────────────────────────────────────
# STEP 3: 진단 결과
# ──────────────────────────────────────────────────────────────
def render_step3():
    dx = st.session_state.diagnosis
    st.markdown(f'''
    <div class="hero-section">
        <h1 class="hero-title">AI 진단 결과</h1>
    </div>
    ''', unsafe_allow_html=True)
    
    st.markdown(f'''
    <div class="glass-card" style="text-align:center; background:linear-gradient(135deg, #0D631B, #071E27); color:white; padding:40px;">
        <div style="font-size:1.2rem; opacity:0.8; margin-bottom:10px;">우리 건물 에너지 등급</div>
        <div style="font-size:5rem; font-weight:900;">{dx['grade']}</div>
        <div style="margin-top:20px; font-size:1.1rem;">연간 예상 요금: <b>{won_to_manwon(dx['current_cost'])}</b></div>
    </div>
    ''', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1: st.button("← 이전", on_click=go_prev, use_container_width=True)
    with c2: st.button("절감 방안 보기 →", type="primary", on_click=go_next, use_container_width=True)

# ──────────────────────────────────────────────────────────────
# STEP 4: 절감 방안
# ──────────────────────────────────────────────────────────────
def render_step4():
    dx = st.session_state.diagnosis
    st.markdown('<div class="section-title">💡 맞춤형 절감 방안</div>', unsafe_allow_html=True)
    
    recs = get_all_recommendations(dx, st.session_state.pyeong)
    for r in recs[:3]:
        st.markdown(f'''
        <div class="glass-card" style="margin-bottom:12px;">
            <div style="font-size:1.2rem; font-weight:800; color:#0D631B;">{r['icon']} {r['name']}</div>
            <div style="font-size:0.9rem; color:#40493D; margin:8px 0;">{r['desc']}</div>
            <div style="font-size:0.85rem; font-weight:700;">예상 절감액: {won_to_manwon(r['annual_saving_won'])}/년</div>
        </div>
        ''', unsafe_allow_html=True)
        
    c1, c2 = st.columns(2)
    with c1: st.button("← 이전", on_click=go_prev, use_container_width=True)
    with c2: st.button("보조금 확인 →", type="primary", on_click=go_next, use_container_width=True)

# ──────────────────────────────────────────────────────────────
# STEP 5: 보조금
# ──────────────────────────────────────────────────────────────
def render_step5():
    st.markdown('<div class="section-title">🏛️ 정부 지원 보조금</div>', unsafe_allow_html=True)
    
    subsidies = get_matching_subsidies(st.session_state.building_type, st.session_state.age, st.session_state.region)
    for s in subsidies:
        st.markdown(f'''
        <div class="glass-card" style="margin-bottom:12px; border-left:4px solid #0D631B;">
            <div style="font-weight:800; color:#071E27;">{s['name']}</div>
            <div style="font-size:0.85rem; color:#40493D;">{s['support']}</div>
            <div style="font-size:0.85rem; font-weight:700; color:#0D631B; margin-top:4px;">지원: {s['amount']}</div>
        </div>
        ''', unsafe_allow_html=True)
        
    st.button("🔄 처음부터 다시", type="primary", use_container_width=True, on_click=restart)

# ── 메인 라우터 ──
current_step = st.session_state.step
render_progress(current_step)

if current_step == 1: render_step1()
elif current_step == 2: render_step2()
elif current_step == 3: render_step3()
elif current_step == 4: render_step4()
elif current_step == 5: render_step5()
