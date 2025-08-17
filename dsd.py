# app.py
# Streamlit 대시보드: 월별 매출 (5가지 시각화)
# 사용 라이브러리: streamlit, pandas, plotly

import io
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="월별 매출 대시보드", layout="wide")

# ------------------------
# 유틸 함수
# ------------------------
def fmt_won(n: float) -> str:
    try:
        return f"{int(n):,} 원"
    except Exception:
        return "-"

def won_axis_tick(v: float) -> str:
    # 억 단위 표기
    if abs(v) >= 1e8:
        return f"{v/1e8:.1f}억"
    return f"{int(v):,}"

@st.cache_data
def demo_dataframe() -> pd.DataFrame:
    data = [
        {"월":"2024-01", "매출액":12000000, "전년동월":10500000, "증감률":14.3},
        {"월":"2024-02", "매출액":13500000, "전년동월":11200000, "증감률":20.5},
        {"월":"2024-03", "매출액":11000000, "전년동월":12800000, "증감률":-14.1},
        {"월":"2024-04", "매출액":18000000, "전년동월":15200000, "증감률":18.4},
        {"월":"2024-05", "매출액":21000000, "전년동월":18500000, "증감률":13.5},
        {"월":"2024-06", "매출액":19000000, "전년동월":17000000, "증감률":11.8},
        {"월":"2024-07", "매출액":23000000, "전년동월":20000000, "증감률":15.0},
        {"월":"2024-08", "매출액":22000000, "전년동월":19500000, "증감률":12.8},
        {"월":"2024-09", "매출액":25000000, "전년동월":21000000, "증감률":19.0},
        {"월":"2024-10", "매출액":26000000, "전년동월":22500000, "증감률":15.6},
        {"월":"2024-11", "매출액":28000000, "전년동월":25000000, "증감률":12.0},
        {"월":"2024-12", "매출액":24000000, "전년동월":21000000, "증감률":14.3},
    ]
    df = pd.DataFrame(data)
    return df

# ------------------------
# 사이드바: 데이터 업로드/선택
# ------------------------
st.title("월별 매출 대시보드")
st.caption("열 이름: 월, 매출액, 전년동월, 증감률 | 형식 예시: 2024-01, 12000000, 10500000, 14.3")

with st.sidebar:
    st.header("데이터 입력")
    uploaded = st.file_uploader("CSV 파일 업로드", type=["csv"])
    use_demo = st.toggle("데모 데이터 사용", value=(uploaded is None))

if uploaded and not use_demo:
    df = pd.read_csv(uploaded)
else:
    df = demo_dataframe()

# ------------------------
# 전처리
# ------------------------
# 컬럼명 정규화(영문 대체 지원)
colmap = {
    "월": ["월", "month", "Month"],
    "매출액": ["매출액", "revenue", "Revenue"],
    "전년동월": ["전년동월", "last_year", "PY"],
    "증감률": ["증감률", "yoy", "YoY"],
}

rename_dict = {}
for std, alts in colmap.items():
    for c in df.columns:
        if c.strip() in alts:
            rename_dict[c] = std
            break

df = df.rename(columns=rename_dict)
required = ["월", "매출액", "전년동월", "증감률"]
missing = [c for c in required if c not in df.columns]
if missing:
    st.error(f"필수 열이 없습니다: {', '.join(missing)}")
    st.stop()

# 타입 처리 및 정렬
try:
    df["월"] = pd.to_datetime(df["월"], errors="coerce")
except Exception:
    pass

if df["월"].isna().any():
    st.warning("일부 '월' 값이 날짜로 변환되지 않았습니다. (YYYY-MM 권장)")

df = df.sort_values("월").reset_index(drop=True)

# 파생지표
df["증감액"] = df["매출액"] - df["전년동월"]
df["누적매출"] = df["매출액"].cumsum()

# 문자열 월 라벨(YYYY-MM)
df["월라벨"] = df["월"].dt.strftime("%Y-%m")

# ------------------------
# KPI 카드
# ------------------------
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("올해 누적 매출", fmt_won(df["매출액"].sum()))
with col2:
    st.metric("평균 증감률", f"{df['증감률'].mean():.1f}%")
with col3:
    max_idx = df["매출액"].idxmax()
    st.metric("최고 매출 월", f"{df.loc[max_idx,'월라벨']} · {fmt_won(df.loc[max_idx,'매출액'])}")
with col4:
    min_idx = df["매출액"].idxmin()
    st.metric("최저 매출 월", f"{df.loc[min_idx,'월라벨']} · {fmt_won(df.loc[min_idx,'매출액'])}")

st.divider()

# ------------------------
# ① 월별 매출액 비교 (라인)
# ------------------------
fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=df["월라벨"], y=df["매출액"], mode="lines+markers", name="당해 매출액"))
fig1.add_trace(go.Scatter(x=df["월라벨"], y=df["전년동월"], mode="lines+markers", name="전년동월 매출액"))
fig1.update_layout(title="① 월별 매출액 비교 (당해 vs 전년동월)", legend=dict(orientation="h"))
fig1.update_yaxes(title_text="매출액", tickformat=",", tickprefix="", tickfont=dict(size=11))
st.plotly_chart(fig1, use_container_width=True)

# ------------------------
# ② 증감률 막대 + 매출액 라인 (이중축)
# ------------------------
fig2 = go.Figure()
fig2.add_trace(go.Bar(x=df["월라벨"], y=df["증감률"], name="증감률(%)", opacity=0.75))
fig2.add_trace(go.Scatter(x=df["월라벨"], y=df["매출액"], name="매출액", mode="lines+markers", yaxis="y2"))
fig2.update_layout(
    title="② 증감률(%) 막대 + 매출액 라인",
    xaxis=dict(title="월"),
    yaxis=dict(title="증감률(%)"),
    yaxis2=dict(title="매출액", overlaying="y", side="right"),
    legend=dict(orientation="h"),
)
st.plotly_chart(fig2, use_container_width=True)

# ------------------------
# ③ 월별 증감률 히트맵
# ------------------------
# 단일 열(증감률) × 여러 행(월) 형태의 heatmap
heat_z = np.array(df[["증감률"]]).T  # shape (1, n)
fig3 = go.Figure(data=go.Heatmap(
    z=heat_z,
    x=["증감률"],
    y=df["월라벨"],
    colorscale="RdYlGn",
    zmin=df["증감률"].min(),
    zmax=df["증감률"].max(),
    showscale=True,
    hovertemplate="%{y}: %{z:.1f}%<extra></extra>",
))
fig3.update_layout(title="③ 월별 증감률 히트맵")
st.plotly_chart(fig3, use_container_width=True)

# ------------------------
# ④ 누적 매출액 추이 (라인, area)
# ------------------------
fig4 = px.area(df, x="월라벨", y="누적매출", title="④ 누적 매출액 추이")
fig4.update_yaxes(tickformat=",")
st.plotly_chart(fig4, use_container_width=True)

# ------------------------
# ⑤ 전년 대비 증감액 (양/음 색상)
# ------------------------
colors = ["#2563eb" if v >= 0 else "#ef4444" for v in df["증감액"].tolist()]
fig5 = go.Figure(go.Bar(x=df["월라벨"], y=df["증감액"], marker_color=colors, name="증감액"))
fig5.update_layout(title="⑤ 전년 대비 증감액", xaxis_title="월", yaxis_title="증감액")
st.plotly_chart(fig5, use_container_width=True)

# 원본 데이터 미리보기
with st.expander("데이터 미리보기"):
    st.dataframe(df[["월라벨","매출액","전년동월","증감률","증감액","누적매출"]], use_container_width=True)

st.caption("© 2025 매출 대시보드 · Streamlit + Plotly")
