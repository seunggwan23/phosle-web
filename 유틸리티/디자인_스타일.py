# -*- coding: utf-8 -*-
"""
CSS 스타일 관리 모듈
"""

def get_main_css() -> str:
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

html, body, [data-testid="stApp"] { font-family: 'Pretendard', 'Plus Jakarta Sans', sans-serif !important; }
[data-testid="stApp"] { background: #F8FAFC !important; color: #1E293B !important; }
.block-container { padding: 2rem !important; max-width: 850px !important; }

/* ── 1. 프로그레스 바 (진행 상태) ── */
.progress-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 30px;
    position: relative;
    padding: 0 10px;
}
.step-circle {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 14px;
    z-index: 2;
    transition: all 0.3s ease;
    background: #E2E8F0;
    color: #64748B;
    border: 3px solid #F8FAFC;
}
.step-circle.done { background: #059669; color: white; border-color: #D1FAE5; }
.step-circle.active { background: white; color: #059669; border-color: #059669; box-shadow: 0 0 10px rgba(5, 150, 105, 0.3); transform: scale(1.1); }
.step-circle.pending { background: #F1F5F9; color: #94A3B8; }

.step-connector {
    flex: 1;
    height: 4px;
    margin: 0 -8px;
    z-index: 1;
    background: #E2E8F0;
    border-radius: 2px;
}
.step-connector.done { background: #059669; }

/* ── 2. 히어로 섹션 ── */
.hero {
    background: linear-gradient(135deg, #059669, #10B981);
    border-radius: 24px;
    padding: 40px 30px;
    color: white !important;
    text-align: center;
    margin-bottom: 30px;
    box-shadow: 0 10px 25px rgba(5, 150, 105, 0.2);
}
.hero-title { font-family: 'Plus Jakarta Sans', sans-serif !important; font-size: 32px; font-weight: 800; margin-bottom: 10px; color: white !important; }
.hero-sub { font-size: 16px; opacity: 0.9; color: white !important; }

/* ── 3. KPI 및 게이지 ── */
.grade-badge {
    display: inline-flex; align-items: center; justify-content: center;
    width: 50px; height: 50px; border-radius: 12px; font-size: 24px; font-weight: 800;
    background: rgba(255,255,255,0.15); color: white;
}
.kpi-row { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
.kpi {
    flex: 1; min-width: 140px; background: white; border: 1px solid #E2E8F0;
    border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.02);
}
.kpi .label { font-size: 12px; color: #64748B; font-weight: 600; margin-bottom: 4px; }
.kpi .value { font-size: 22px; font-weight: 800; margin-bottom: 2px; }
.kpi .sub { font-size: 11px; color: #94A3B8; }

.gauge-container { margin-bottom: 16px; }
.gauge-label { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 12px; font-weight: 600; color: #334155; }
.gauge-label .value { color: #64748B; font-weight: 500; font-size: 11px; }
.gauge-bar { height: 8px; background: #E2E8F0; border-radius: 10px; overflow: hidden; }
.gauge-fill { height: 100%; border-radius: 10px; transition: width 0.8s ease; }
.gauge-fill.good { background: #059669; }
.gauge-fill.warn { background: #F59E0B; }
.gauge-fill.bad { background: #EF4444; }

/* ── 4. 추천 방안 카드 ── */
.rec-card {
    background: white; border: 1px solid #E2E8F0; border-radius: 16px; padding: 20px;
    margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.02);
}
.rec-card .title { font-size: 16px; font-weight: 700; color: #1E293B; margin-bottom: 4px; }
.rec-card .desc { font-size: 13px; color: #64748B; margin-bottom: 12px; line-height: 1.5; }
.rec-metrics { display: flex; gap: 8px; background: #F8FAFC; padding: 10px; border-radius: 8px; border: 1px solid #F1F5F9; flex-wrap: wrap;}
.rec-metric { flex: 1; min-width: 70px; text-align: center; }
.rec-metric .label { font-size: 11px; color: #94A3B8; margin-bottom: 2px; font-weight: 600;}
.rec-metric .val { font-size: 14px; font-weight: 800; }

/* ── 5. 보조금 카드 ── */
.subsidy-card {
    background: white; border-left: 4px solid #3B82F6; border-radius: 12px; padding: 16px;
    margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.02);
    border-top: 1px solid #F1F5F9; border-right: 1px solid #F1F5F9; border-bottom: 1px solid #F1F5F9;
}
.subsidy-card .name { font-size: 15px; font-weight: 700; color: #1E293B; margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px dashed #E2E8F0; }
.subsidy-card .detail { font-size: 13px; color: #475569; line-height: 1.6; }

/* ── 6. 공통 컴포넌트 ── */
.stButton > button {
    background: #059669 !important; color: white !important;
    border-radius: 10px !important; padding: 10px 20px !important;
    font-weight: 700 !important; border: none !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(5, 150, 105, 0.2) !important; }

/* 기존 다크 모드 스타일이 하드코딩된 부분의 텍스트 색상 오버라이드 (가시성 확보) */
[style*="background:#0D1526"], [style*="background:rgba(13, 21, 38"] {
    color: #F8FAFC !important;
}
</style>
"""
