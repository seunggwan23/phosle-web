"""
Plotly 차트 생성 모듈 (charts.py)

디자인 명세 반영:
- 전체 다크 테마 (#0D1117 배경)
- Emerald Green (#50C878) + Soft Orange (#FFB347) 강조색
- 인터랙티브 Area Chart, Correlation Heatmap, Feature Importance Bar Chart
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np


# ── 디자인 토큰 정의 ──────────────────────────────────────────────
DARK_BG = "#0D1117"           # 메인 배경
CARD_BG = "#161B22"           # 카드 배경
BORDER = "#30363D"            # 테두리
EMERALD = "#50C878"           # 강조색 (에너지 효율)
ORANGE = "#FFB347"            # 경고색 (에너지 낭비)
TEXT_PRIMARY = "#E6EDF3"      # 주요 텍스트
TEXT_MUTED = "#8B949E"        # 보조 텍스트
GRID_COLOR = "#21262D"        # 차트 격자

# 공통 레이아웃 설정 (모든 차트에 재사용)
LAYOUT_BASE = dict(
    paper_bgcolor=DARK_BG,
    plot_bgcolor=CARD_BG,
    font=dict(family="Inter, Pretendard, sans-serif", color=TEXT_PRIMARY),
    margin=dict(l=16, r=16, t=40, b=16),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor=BORDER,
        font=dict(color=TEXT_MUTED)
    )
)


def create_energy_trend_chart(df: pd.DataFrame, predictions: np.ndarray) -> go.Figure:
    """
    시간별 에너지 소비 추이 차트 (Area Chart)
    
    디자인 명세 3항:
    - Area Chart로 시각적 볼륨감 표현
    - 실제값(Actual) vs 예측값(Predicted) 비교
    - 마우스 오버 툴팁으로 정확한 수치 표시
    
    Args:
        df: 에너지 데이터프레임 (energy_kwh 컬럼 포함)
        predictions: AI 예측값 배열
    
    Returns:
        Plotly Figure 객체
    """
    # 시각화를 위해 최근 7일(168시간) 데이터만 사용
    display_df = df.tail(168)
    pred_display = predictions[-168:]
    
    fig = go.Figure()
    
    # 실제 에너지 소비 Area
    fig.add_trace(go.Scatter(
        x=display_df.index,
        y=display_df["energy_kwh"],
        name="실제 소비량",
        fill="tozeroy",
        fillcolor=f"rgba(80, 200, 120, 0.15)",  # Emerald 반투명
        line=dict(color=EMERALD, width=2),
        hovertemplate="<b>%{x|%Y-%m-%d %H:%M}</b><br>실제: %{y:.1f} kWh<extra></extra>"
    ))
    
    # AI 예측값 Line
    fig.add_trace(go.Scatter(
        x=display_df.index,
        y=pred_display,
        name="AI 예측값",
        fill="tonexty",
        fillcolor=f"rgba(255, 179, 71, 0.08)",  # Orange 반투명
        line=dict(color=ORANGE, width=2, dash="dot"),
        hovertemplate="<b>%{x|%Y-%m-%d %H:%M}</b><br>예측: %{y:.1f} kWh<extra></extra>"
    ))
    
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="⚡ 시간별 에너지 소비 추이 (최근 7일)", font=dict(size=16, color=TEXT_PRIMARY)),
        xaxis=dict(
            gridcolor=GRID_COLOR,
            linecolor=BORDER,
            title="날짜/시간",
            tickformat="%m/%d %H:%M"
        ),
        yaxis=dict(
            gridcolor=GRID_COLOR,
            linecolor=BORDER,
            title="에너지 소비량 (kWh)"
        ),
        hovermode="x unified"
    )
    
    return fig


def create_correlation_heatmap(df: pd.DataFrame) -> go.Figure:
    """
    기상 변수 간 상관관계 히트맵
    
    디자인 명세 3항: 색상 스케일 'Viridis' 사용
    
    Args:
        df: 상관관계를 계산할 데이터프레임
    
    Returns:
        Plotly Figure 객체
    """
    # 상관관계 분석 대상 컬럼
    corr_cols = {
        "outdoor_temp": "외기 온도",
        "solar_radiation": "일사량",
        "humidity": "습도",
        "wind_speed": "풍속",
        "HDD": "난방도일",
        "CDD": "냉방도일",
        "energy_kwh": "에너지 소비"
    }
    
    available_cols = [col for col in corr_cols.keys() if col in df.columns]
    corr_matrix = df[available_cols].corr()
    
    # 한국어 레이블 매핑
    labels = [corr_cols[col] for col in available_cols]
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=labels,
        y=labels,
        colorscale="Viridis",  # 명세서 지정 색상 스케일
        zmin=-1,
        zmax=1,
        text=np.round(corr_matrix.values, 2),
        texttemplate="%{text}",
        textfont=dict(size=11),
        hovertemplate="%{y} ↔ %{x}<br>상관계수: %{z:.3f}<extra></extra>"
    ))
    
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="🔗 기상 변수 간 상관관계", font=dict(size=16, color=TEXT_PRIMARY)),
        xaxis=dict(side="bottom", tickangle=-30),
        height=420
    )
    
    return fig


def create_feature_importance_chart(feature_importance: dict) -> go.Figure:
    """
    모델 특징 중요도 가로 바 차트
    
    디자인 명세 3항: "모델이 어떤 변수를 가장 중요하게 판단했는지" 시각화
    
    Args:
        feature_importance: {특징명: 중요도} 딕셔너리
    
    Returns:
        Plotly Figure 객체
    """
    # 한국어 레이블 변환
    label_map = {
        "outdoor_temp": "외기 온도",
        "solar_radiation": "일사량",
        "wind_speed": "풍속",
        "humidity": "습도",
        "HDD": "난방도일 (HDD)",
        "CDD": "냉방도일 (CDD)",
        "hr_sin": "시간 주기성 (sin)",
        "hr_cos": "시간 주기성 (cos)",
        "month_sin": "월 주기성 (sin)",
        "month_cos": "월 주기성 (cos)",
        "dayofweek": "요일",
        "is_weekend": "주말 여부",
        "wwr": "창면적비 (WWR)",
        "insulation_mm": "단열재 두께",
        "hvac_setpoint": "HVAC 설정 온도",
        "building_type_RC": "건물 구조 (RC)",
        "building_type_steel": "건물 구조 (철골)"
    }
    
    # 상위 12개만 표시 (가독성)
    top_n = dict(list(feature_importance.items())[:12])
    
    features = [label_map.get(k, k) for k in top_n.keys()]
    importances = list(top_n.values())
    
    # 중요도에 따라 색상 그라데이션 적용
    colors = [EMERALD if v > 0.1 else ORANGE if v > 0.05 else TEXT_MUTED for v in importances]
    
    fig = go.Figure(go.Bar(
        x=importances,
        y=features,
        orientation="h",
        marker=dict(
            color=colors,
            line=dict(color=BORDER, width=1)
        ),
        text=[f"{v:.3f}" for v in importances],
        textposition="outside",
        textfont=dict(color=TEXT_MUTED, size=11),
        hovertemplate="%{y}<br>중요도: %{x:.4f}<extra></extra>"
    ))
    
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="🧠 AI 특징 중요도 (Feature Importance)", font=dict(size=16, color=TEXT_PRIMARY)),
        xaxis=dict(
            gridcolor=GRID_COLOR,
            title="중요도 (Gain)",
            showline=True,
            linecolor=BORDER
        ),
        yaxis=dict(
            linecolor=BORDER,
            autorange="reversed"  # 상위 항목이 위에 오도록
        ),
        height=430
    )
    
    return fig


def create_monthly_summary_chart(df: pd.DataFrame, predictions: np.ndarray) -> go.Figure:
    """
    월별 에너지 소비 요약 차트 (실제 vs 예측 Bar Chart)
    
    Args:
        df: 에너지 데이터프레임
        predictions: AI 예측값 배열
    
    Returns:
        Plotly Figure 객체
    """
    df_copy = df.copy()
    df_copy["predicted"] = predictions
    df_copy["month"] = df_copy.index.month
    
    monthly_actual = df_copy.groupby("month")["energy_kwh"].sum()
    monthly_pred = df_copy.groupby("month")["predicted"].sum()
    
    month_names = ["1월", "2월", "3월", "4월", "5월", "6월",
                   "7월", "8월", "9월", "10월", "11월", "12월"]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=[month_names[m-1] for m in monthly_actual.index],
        y=monthly_actual.values,
        name="실제 소비량",
        marker=dict(color=EMERALD, opacity=0.85),
        hovertemplate="%{x}<br>실제: %{y:,.0f} kWh<extra></extra>"
    ))
    
    fig.add_trace(go.Bar(
        x=[month_names[m-1] for m in monthly_pred.index],
        y=monthly_pred.values,
        name="AI 예측값",
        marker=dict(color=ORANGE, opacity=0.7),
        hovertemplate="%{x}<br>예측: %{y:,.0f} kWh<extra></extra>"
    ))
    
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="📅 월별 에너지 소비 요약", font=dict(size=16, color=TEXT_PRIMARY)),
        xaxis=dict(gridcolor=GRID_COLOR, title="월"),
        yaxis=dict(gridcolor=GRID_COLOR, title="총 에너지 소비량 (kWh)"),
        barmode="group",
        bargap=0.2
    )
    
    return fig
