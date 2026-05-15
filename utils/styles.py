"""
CSS 스타일 관리 모듈
- 앱 전체 디자인 토큰과 스타일을 한 곳에서 관리
"""


def get_main_css() -> str:
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [data-testid="stApp"], p, h1, h2, h3, h4, h5, h6, input, button, select { font-family: 'Inter', sans-serif !important; }
[data-testid="stApp"] { background: #0A0F1E !important; color: #E2E8F0 !important; }
[data-testid="stSidebar"] { display: none !important; }
.block-container { padding: 1.5rem 2rem !important; max-width: 900px !important; }

.progress-bar { display:flex; align-items:center; justify-content:center; gap:0; margin:0 auto 28px; }
.step-circle { width:38px;height:38px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700; }
.step-circle.active { background:linear-gradient(135deg,#50C878,#38BDF8);color:#0A0F1E;box-shadow:0 0 16px rgba(80,200,120,0.3); }
.step-circle.done { background:rgba(80,200,120,0.2);color:#50C878;border:2px solid #50C878; }
.step-circle.pending { background:#1A2740;color:#4A6080;border:2px solid #2A3A55; }
.step-connector { width:36px;height:2px; }
.step-connector.done { background:#50C878; }
.step-connector.pending { background:#2A3A55; }

.hero { background:linear-gradient(135deg,#0D1526,#0F2040);border:1px solid #1A2740;border-radius:20px;padding:28px 36px;margin-bottom:24px;text-align:center; }
.hero-title { font-size:26px;font-weight:800;background:linear-gradient(90deg,#50C878,#38BDF8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text; }
.hero-sub { font-size:14px;color:#6B8AB0;margin-top:6px; }

.grade-badge { width:96px;height:96px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:36px;font-weight:800;flex-shrink:0; }
.grade-A { background:rgba(80,200,120,0.12);color:#50C878;border:3px solid rgba(80,200,120,0.4); }
.grade-B { background:rgba(56,189,248,0.12);color:#38BDF8;border:3px solid rgba(56,189,248,0.4); }
.grade-C { background:rgba(255,179,71,0.12);color:#FFB347;border:3px solid rgba(255,179,71,0.4); }
.grade-D { background:rgba(248,113,113,0.12);color:#F87171;border:3px solid rgba(248,113,113,0.4); }
.grade-E { background:rgba(200,80,80,0.15);color:#E05555;border:3px solid rgba(200,80,80,0.4); }

.gauge-container { margin:10px 0; }
.gauge-label { display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px; }
.gauge-label .name { color:#94A3B8;font-weight:600; }
.gauge-label .value { color:#E2E8F0;font-weight:700; }
.gauge-bar { height:8px;background:#1A2740;border-radius:4px;overflow:hidden; }
.gauge-fill { height:100%;border-radius:4px;transition:width 0.8s ease; }
.gauge-fill.good { background:linear-gradient(90deg,#50C878,#38BDF8); }
.gauge-fill.warn { background:linear-gradient(90deg,#FFB347,#FF8C00); }
.gauge-fill.bad { background:linear-gradient(90deg,#F87171,#DC2626); }

.rec-card { background:#0D1526;border:1px solid #1A2740;border-radius:16px;padding:22px;margin:12px 0; }
.rec-card:hover { border-color:#2A3A55; }
.rec-card .title { font-size:16px;font-weight:700;color:#E2E8F0; }
.rec-card .desc { font-size:13px;color:#6B8AB0;margin-top:4px;line-height:1.6; }
.rec-metrics { display:flex;gap:12px;margin-top:12px;flex-wrap:wrap; }
.rec-metric { background:#0A0F1E;border-radius:10px;padding:10px 14px;text-align:center;min-width:90px; }
.rec-metric .label { font-size:10px;color:#4A6080;font-weight:600; }
.rec-metric .val { font-size:16px;font-weight:800;margin-top:2px; }
.diff-easy { display:inline-block;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:700;background:rgba(80,200,120,0.12);color:#50C878; }
.diff-medium { display:inline-block;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:700;background:rgba(56,189,248,0.12);color:#38BDF8; }
.diff-hard { display:inline-block;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:700;background:rgba(255,179,71,0.12);color:#FFB347; }

.subsidy-card { background:#0D1526;border:1px solid #1A2740;border-left:4px solid #50C878;border-radius:12px;padding:16px 20px;margin:8px 0; }
.subsidy-card .name { font-size:15px;font-weight:700;color:#E2E8F0; }
.subsidy-card .detail { font-size:13px;color:#6B8AB0;margin-top:4px;line-height:1.6; }

.kpi-row { display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:14px 0; }
.kpi { background:#0D1526;border:1px solid #1A2740;border-radius:14px;padding:18px;text-align:center; }
.kpi .label { font-size:11px;color:#4A6080;font-weight:600; }
.kpi .value { font-size:26px;font-weight:800;margin:4px 0; }
.kpi .sub { font-size:12px;color:#6B8AB0; }

.stButton > button { background:linear-gradient(135deg,#50C878,#38BDF8)!important;color:#0A0F1E!important;font-weight:700!important;border:none!important;border-radius:12px!important;padding:10px 28px!important;font-size:14px!important; }
.stButton > button:hover { box-shadow:0 6px 20px rgba(80,200,120,0.3)!important; }
hr { border-color:#1A2740 !important; }
</style>
"""
