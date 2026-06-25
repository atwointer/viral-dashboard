from __future__ import annotations

import hmac
import re
import unicodedata

import pandas as pd
import plotly.express as px
import streamlit as st

from data_loader import build_match_key, load_data


st.set_page_config(
    page_title="바이럴 운영 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


DARK_CSS = """
<style>
    :root {
        --bg-main: #0b1020;
        --bg-grad-top: #121828;
        --bg-grad-bottom: #0f172a;
        --panel: rgba(18, 24, 39, 0.92);
        --panel-soft: rgba(20, 28, 46, 0.90);
        --line: rgba(148, 163, 184, 0.14);
        --line-strong: rgba(148, 163, 184, 0.22);
        --text-main: #f8fafc;
        --text-soft: #aeb8cc;
        --text-dim: #7f8aa3;
    }
    .stApp {
        background:
            radial-gradient(circle at 12% 0%, rgba(124, 92, 255, 0.16), transparent 24%),
            radial-gradient(circle at 100% 20%, rgba(34, 197, 94, 0.08), transparent 18%),
            linear-gradient(180deg, #121828 0%, #0f172a 46%, #0b1020 100%);
        color: var(--text-main);
    }
    .block-container {
        max-width: 1450px;
        padding-top: 1.35rem;
        padding-bottom: 2.1rem;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(10, 14, 26, 0.98) 0%, rgba(15, 21, 36, 0.98) 100%);
        border-right: 1px solid rgba(148, 163, 184, 0.10);
    }
    [data-testid="stSidebar"] * {
        color: #dde5f1;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] .stDateInput > div > div {
        background: rgba(17, 24, 39, 0.92);
        border-color: var(--line-strong);
        border-radius: 14px;
    }
    [data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {
        background: rgba(124, 92, 255, 0.18);
        border: 1px solid rgba(124, 92, 255, 0.30);
        color: #f4f0ff;
    }
    .hero-shell {
        background: linear-gradient(180deg, rgba(14, 19, 33, 0.96) 0%, rgba(16, 24, 40, 0.96) 100%);
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 1.05rem 1.15rem 1rem 1.15rem;
        margin-bottom: 1rem;
        box-shadow: 0 20px 52px rgba(2, 6, 23, 0.22);
    }
    .hero-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
    }
    .hero-title {
        font-size: 1.75rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        margin-bottom: 0.15rem;
    }
    .hero-subtitle {
        color: var(--text-soft);
        font-size: 0.9rem;
        line-height: 1.5;
        max-width: 760px;
    }
    .hero-status {
        min-width: 190px;
        background: rgba(124, 92, 255, 0.16);
        border: 1px solid rgba(124, 92, 255, 0.20);
        border-radius: 16px;
        padding: 0.75rem 0.85rem;
    }
    .hero-status-label {
        color: #c5bcff;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.2rem;
    }
    .hero-status-value {
        color: white;
        font-weight: 800;
        font-size: 1.2rem;
        letter-spacing: -0.03em;
    }
    .hero-status-sub {
        color: #c9d3e5;
        font-size: 0.74rem;
        margin-top: 0.1rem;
    }
    .hero-badges {
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        margin-top: 0.75rem;
    }
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.45rem 0.72rem;
        border-radius: 999px;
        background: rgba(23, 32, 53, 0.95);
        border: 1px solid rgba(148, 163, 184, 0.15);
        color: #dee6f3;
        font-size: 0.78rem;
    }
    .section-title {
        font-size: 1.4rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        margin: 1.1rem 0 0.7rem 0;
        color: var(--text-main);
    }
    .section-caption {
        color: var(--text-dim);
        margin-top: -0.1rem;
        margin-bottom: 0.8rem;
    }
    .metric-note {
        color: var(--text-dim);
        margin: 0.45rem 0 0.8rem 0;
        font-size: 0.82rem;
    }
    .kpi-card {
        position: relative;
        overflow: hidden;
        border-radius: 20px;
        padding: 1rem 1rem 0.95rem 1rem;
        border: 1px solid rgba(255, 255, 255, 0.10);
        box-shadow: 0 14px 32px rgba(2, 6, 23, 0.16);
        min-height: 132px;
        margin-bottom: 0.8rem;
    }
    .kpi-card::after {
        content: "";
        position: absolute;
        width: 120px;
        height: 120px;
        right: -36px;
        top: -42px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.10);
    }
    .kpi-card.primary-a { background: linear-gradient(135deg, #5b63ff 0%, #6f7cff 56%, #8194ff 100%); }
    .kpi-card.primary-b { background: linear-gradient(135deg, #1f6fff 0%, #3d84ff 58%, #65a0ff 100%); }
    .kpi-card.primary-c { background: linear-gradient(135deg, #0f9f7a 0%, #16b38a 58%, #31c99d 100%); }
    .kpi-card.primary-d {
        background: linear-gradient(135deg, #f59e0b 0%, #f7b731 56%, #f8ca62 100%);
        color: #172033;
    }
    .kpi-card.primary-d .kpi-label,
    .kpi-card.primary-d .kpi-value { color: #172033; }
    .kpi-card.secondary {
        background: linear-gradient(180deg, rgba(15, 21, 36, 0.98) 0%, rgba(18, 27, 45, 0.98) 100%);
        border: 1px solid var(--line);
        min-height: 112px;
    }
    .kpi-card.secondary::after {
        background: rgba(124, 92, 255, 0.10);
    }
    .kpi-label {
        position: relative;
        z-index: 1;
        font-size: 0.8rem;
        font-weight: 700;
        opacity: 0.90;
        letter-spacing: 0.01em;
        margin-bottom: 0.55rem;
    }
    .kpi-value {
        position: relative;
        z-index: 1;
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        line-height: 1.05;
    }
    .chart-card {
        background: linear-gradient(180deg, rgba(14, 19, 33, 0.98) 0%, rgba(18, 26, 42, 0.98) 100%);
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 0.8rem 0.9rem 0.3rem 0.9rem;
        box-shadow: 0 18px 42px rgba(2, 6, 23, 0.18);
        margin-bottom: 0.9rem;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 22px;
        overflow: hidden;
        box-shadow: 0 14px 32px rgba(2, 6, 23, 0.14);
    }
    .stButton button {
        background: linear-gradient(180deg, #7c5cff 0%, #5d3df5 100%);
        color: white;
        border: none;
        border-radius: 14px;
        font-weight: 700;
    }
</style>
"""


TABLE_FALLBACK_COLUMNS = {
    "perf_latest_collected_at": "",
    "perf_debug_rows": "",
    "match_nt_source": "",
    "match_nt_detail": "",
    "match_nt_keyword": "",
    "unmatched_reason": "",
    "match_method": "",
    "match_status": "",
    "match_key": "",
}

CHART_COLORS = {
    "cost": "#8aa4ff",
    "payment_amount": "#ffb347",
    "inflow_count": "#46d39a",
    "payment_count": "#ff7a59",
    "roas": "#8f7dff",
}

DISPLAY_NAMES = {
    "cost": "비용",
    "payment_amount": "결제금액",
    "inflow_count": "유입수",
    "payment_count": "결제수",
    "roas": "ROAS",
}


@st.cache_data(show_spinner=False, ttl=300)
def get_dashboard_data() -> dict[str, pd.DataFrame]:
    return load_data()


def check_password() -> bool:
    """비밀번호 게이트. secrets에 설정된 값과 일치할 때만 대시보드를 연다."""
    if st.session_state.get("password_ok"):
        return True

    try:
        expected = st.secrets.get("app_password", "")
    except Exception:
        expected = ""
    if not expected:
        st.error(
            "로그인 비밀번호가 설정되지 않았습니다. "
            ".streamlit/secrets.toml 파일에 app_password 값을 지정하세요."
        )
        return False

    def _verify() -> None:
        entered = st.session_state.get("password_input", "")
        if hmac.compare_digest(str(entered), str(expected)):
            st.session_state["password_ok"] = True
            st.session_state.pop("password_input", None)
        else:
            st.session_state["password_ok"] = False

    st.markdown(DARK_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-shell"><div class="hero-title">바이럴 운영 대시보드</div>'
        '<div class="hero-subtitle">접속하려면 비밀번호를 입력하세요.</div></div>',
        unsafe_allow_html=True,
    )
    st.text_input("비밀번호", type="password", key="password_input", on_change=_verify)
    if st.session_state.get("password_ok") is False:
        st.error("비밀번호가 올바르지 않습니다.")
    return False


def main() -> None:
    if not check_password():
        return

    st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)
    st.markdown(DARK_CSS, unsafe_allow_html=True)

    if st.sidebar.button("원본 다시 불러오기", use_container_width=True):
        get_dashboard_data.clear()

    try:
        data = get_dashboard_data()
    except Exception as exc:
        st.error(f"대시보드 로딩 실패: {exc}")
        return
    matched_df = ensure_table_columns(data["matched"].copy())
    performance_df = data["performance"].copy()
    source_meta = data["source_path"].iloc[0]

    render_header(source_meta, matched_df)
    filtered_df = render_filters(matched_df)
    filtered_performance_df = filter_performance_by_matched_rows(filtered_df, performance_df)

    render_kpi_section(filtered_df)
    render_chart_section(filtered_df)
    render_tables(filtered_df)
    render_performance_totals(filtered_performance_df)


def ensure_table_columns(df: pd.DataFrame) -> pd.DataFrame:
    working_df = df.copy()
    for column, default_value in TABLE_FALLBACK_COLUMNS.items():
        if column not in working_df.columns:
            working_df[column] = default_value
    return working_df


def render_header(source_meta: pd.Series, matched_df: pd.DataFrame) -> None:
    matched_count = int(matched_df["is_matched"].fillna(False).astype(bool).sum())
    total_count = len(matched_df)
    coverage = matched_count / total_count * 100 if total_count else 0

    source_url = str(source_meta.get("source_url", ""))
    collection_rule = str(source_meta.get("collection_rule", ""))
    latest_collection_date = str(source_meta.get("latest_collection_date", ""))
    load_errors = str(source_meta.get("load_errors", ""))

    st.markdown(
        f"""
        <div class="hero-shell">
            <div class="hero-top">
                <div>
                    <div class="hero-title">바이럴 운영 관리사 대시보드</div>
                    <div class="hero-subtitle">공개 Google Sheets 원본 DB와 NT 성과 원본을 Python에서 집계해 통합한 운영형 Streamlit 대시보드</div>
                </div>
                <div class="hero-status">
                    <div class="hero-status-label">매칭률</div>
                    <div class="hero-status-value">{coverage:.1f}%</div>
                    <div class="hero-status-sub">{matched_count}/{total_count}건</div>
                </div>
            </div>
            <div class="hero-badges">
                <div class="badge">원본 시트: {source_url}</div>
                <div class="badge">집계 규칙: {collection_rule or "미기재"}</div>
                <div class="badge">최신 수집일: {latest_collection_date or "미기재"}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if load_errors:
        st.warning(f"일부 시트 로딩 실패: {load_errors}")


def render_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("필터")

    valid_dates = df["date"].dropna()
    today = pd.Timestamp.today().date()
    min_date = valid_dates.min().date() if not valid_dates.empty else today
    max_date = valid_dates.max().date() if not valid_dates.empty else today

    date_range = st.sidebar.date_input(
        "기간",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    platforms = normalized_option_values(df["platform"])
    workers = normalized_option_values(df["worker"])
    products = normalized_option_values(df["product_name"])
    managers = normalized_option_values(df["manager"])
    transfer_options = normalized_option_values(df["transfer_status"])

    selected_platforms = st.sidebar.multiselect("플랫폼", platforms, default=platforms)
    selected_workers = st.sidebar.multiselect("작업자", workers)
    selected_products = st.sidebar.multiselect("상품명", products)
    selected_managers = st.sidebar.multiselect("담당자", managers)
    selected_transfers = st.sidebar.multiselect("이체 여부", transfer_options, default=transfer_options)

    filtered = df.copy()
    if len(date_range) == 2:
        start_date, end_date = map(pd.Timestamp, date_range)
        end_dt = end_date + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        filtered = filtered[
            (filtered["date"] >= start_date) & (filtered["date"] <= end_dt)
        ]

    if selected_platforms:
        filtered = filtered[filtered["platform"].isin(selected_platforms)]
    if selected_workers:
        filtered = filtered[filtered["worker"].isin(selected_workers)]
    if selected_products:
        filtered = filtered[filtered["product_name"].isin(selected_products)]
    if selected_managers:
        filtered = filtered[filtered["manager"].isin(selected_managers)]
    if selected_transfers:
        filtered = filtered[filtered["transfer_status"].isin(selected_transfers)]

    return filtered.sort_values(["date", "platform", "worker"], ascending=[False, True, True])


def render_kpi_section(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">핵심 KPI</div>', unsafe_allow_html=True)
    primary_metrics, secondary_metrics = build_kpis(df)

    primary_classes = ["primary-a", "primary-b", "primary-c", "primary-d"]
    primary_columns = st.columns(4)
    for column, metric, card_class in zip(primary_columns, primary_metrics, primary_classes, strict=False):
        with column:
            st.markdown(render_kpi_card(metric, card_class), unsafe_allow_html=True)

    st.markdown('<div class="metric-note">핵심 지표를 먼저 배치했습니다.</div>', unsafe_allow_html=True)

    secondary_columns = st.columns(4)
    for column, metric in zip(secondary_columns, secondary_metrics, strict=False):
        with column:
            st.markdown(render_kpi_card(metric, "secondary"), unsafe_allow_html=True)


def build_kpis(df: pd.DataFrame) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    total_cost = float(df["cost"].fillna(0).sum())
    total_payment_amount = float(df["payment_amount"].fillna(0).sum())
    total_payment_count = float(df["payment_count"].fillna(0).sum())

    # ROAS는 매칭된 작업만으로 계산 (미매칭은 매출 0이라 효율을 왜곡하므로 제외)
    if "is_matched" in df.columns:
        matched_only = df[df["is_matched"].fillna(False).astype(bool)]
    else:
        matched_only = df.iloc[0:0]
    matched_cost = float(matched_only["cost"].fillna(0).sum())
    matched_payment_amount = float(matched_only["payment_amount"].fillna(0).sum())
    roas_matched = (matched_payment_amount / matched_cost * 100) if matched_cost else 0

    primary = [
        {"label": "고객수", "value": format_number(df["customer_count"].fillna(0).sum())},
        {"label": "유입수", "value": format_number(df["inflow_count"].fillna(0).sum())},
        {"label": "클릭수", "value": format_number(df["page_count"].fillna(0).sum())},
        {"label": "ROAS (매칭분)", "value": format_percent(roas_matched)},
    ]
    secondary = [
        {"label": "총 비용", "value": format_currency(total_cost)},
        {"label": "결제금액", "value": format_currency(total_payment_amount)},
        {"label": "결제수", "value": format_number(total_payment_count)},
        {"label": "총 작업 수", "value": format_number(len(df))},
    ]
    return primary, secondary


def render_kpi_card(metric: dict[str, str], card_class: str) -> str:
    return f"""
    <div class="kpi-card {card_class}">
        <div class="kpi-label">{metric["label"]}</div>
        <div class="kpi-value">{metric["value"]}</div>
    </div>
    """


def render_chart_section(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">성과 흐름과 효율</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-caption">핵심 비교는 크게, 보조 비교는 압축해서 배치했습니다.</div>', unsafe_allow_html=True)

    platform_perf = summarize_by_platform(df)
    daily_trend = build_time_series(df, "D")
    monthly_trend = build_time_series(df, "M")
    worker_perf = summarize_by_worker(df, limit=7)

    top_left, top_right = st.columns(2)
    with top_left:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(build_platform_performance_chart(platform_perf), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with top_right:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(build_daily_trend_chart(daily_trend), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    middle_left, middle_right = st.columns(2)
    with middle_left:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(build_monthly_trend_chart(monthly_trend), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with middle_right:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(build_platform_roas_scatter(platform_perf), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(build_worker_performance_chart(worker_perf), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with bottom_right:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(build_payment_share_donut(platform_perf), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


def summarize_by_platform(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["platform", "cost", "payment_amount", "inflow_count", "payment_count", "roas"])

    grouped = (
        df.groupby("platform", dropna=False, as_index=False)[["cost", "payment_amount", "inflow_count", "payment_count"]]
        .sum()
        .fillna(0)
    )
    grouped["platform"] = grouped["platform"].replace("", "미기재")
    grouped["roas"] = grouped.apply(
        lambda row: (row["payment_amount"] / row["cost"] * 100) if row["cost"] else 0,
        axis=1,
    )
    return grouped.sort_values("payment_amount", ascending=False)


def summarize_by_worker(df: pd.DataFrame, limit: int = 7) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["worker", "cost", "payment_amount"])

    grouped = (
        df.groupby("worker", dropna=False, as_index=False)[["cost", "payment_amount"]]
        .sum()
        .fillna(0)
    )
    grouped["worker"] = grouped["worker"].replace("", "미기재")
    grouped = grouped.sort_values("payment_amount", ascending=False).head(limit)
    return grouped.sort_values("payment_amount", ascending=True)


def build_time_series(df: pd.DataFrame, frequency: str) -> pd.DataFrame:
    dated = df.loc[df["date"].notna()].copy()
    if dated.empty:
        return pd.DataFrame(columns=["period", "inflow_count", "payment_count", "cost", "payment_amount"])

    dated["period"] = dated["date"].dt.normalize() if frequency == "D" else dated["date"].dt.to_period(frequency).dt.to_timestamp()
    return (
        dated.groupby("period", as_index=False)[["inflow_count", "payment_count", "cost", "payment_amount"]]
        .sum()
        .sort_values("period")
    )


def build_platform_performance_chart(df: pd.DataFrame):
    if df.empty:
        return empty_figure("플랫폼별 투자 대비 매출")

    melted = df.melt(
        id_vars="platform",
        value_vars=["cost", "payment_amount"],
        var_name="metric",
        value_name="value",
    )
    melted["metric_label"] = melted["metric"].map(DISPLAY_NAMES)

    fig = px.bar(
        melted,
        x="platform",
        y="value",
        color="metric_label",
        barmode="group",
        color_discrete_map={
            DISPLAY_NAMES["cost"]: CHART_COLORS["cost"],
            DISPLAY_NAMES["payment_amount"]: CHART_COLORS["payment_amount"],
        },
        title="플랫폼별 투자 대비 매출",
    )
    fig.update_traces(hovertemplate="플랫폼=%{x}<br>지표=%{fullData.name}<br>금액=%{y:,.0f}원<extra></extra>")
    apply_currency_yaxis(fig)
    apply_common_layout(fig)
    return fig


def build_daily_trend_chart(df: pd.DataFrame):
    if df.empty:
        return empty_figure("일별 유입과 결제 흐름")

    melted = df.melt(
        id_vars="period",
        value_vars=["inflow_count", "payment_count"],
        var_name="metric",
        value_name="value",
    )
    melted["metric_label"] = melted["metric"].map(DISPLAY_NAMES)

    fig = px.line(
        melted,
        x="period",
        y="value",
        color="metric_label",
        markers=True,
        color_discrete_map={
            DISPLAY_NAMES["inflow_count"]: CHART_COLORS["inflow_count"],
            DISPLAY_NAMES["payment_count"]: CHART_COLORS["payment_count"],
        },
        title="일별 유입과 결제 흐름",
    )
    fig.update_traces(hovertemplate="일자=%{x|%Y-%m-%d}<br>지표=%{fullData.name}<br>수치=%{y:,.0f}<extra></extra>")
    apply_count_yaxis(fig)
    apply_common_layout(fig)
    return fig


def build_monthly_trend_chart(df: pd.DataFrame):
    if df.empty:
        return empty_figure("월별 집행 대비 회수")

    melted = df.melt(
        id_vars="period",
        value_vars=["cost", "payment_amount"],
        var_name="metric",
        value_name="value",
    )
    melted["metric_label"] = melted["metric"].map(DISPLAY_NAMES)

    fig = px.line(
        melted,
        x="period",
        y="value",
        color="metric_label",
        markers=True,
        color_discrete_map={
            DISPLAY_NAMES["cost"]: CHART_COLORS["cost"],
            DISPLAY_NAMES["payment_amount"]: CHART_COLORS["payment_amount"],
        },
        title="월별 집행 대비 회수",
    )
    fig.update_traces(hovertemplate="월=%{x|%Y-%m}<br>지표=%{fullData.name}<br>금액=%{y:,.0f}원<extra></extra>")
    apply_currency_yaxis(fig)
    apply_common_layout(fig)
    return fig


def build_platform_roas_scatter(df: pd.DataFrame):
    if df.empty:
        return empty_figure("유입 대비 효율 높은 플랫폼")

    fig = px.scatter(
        df,
        x="inflow_count",
        y="roas",
        size="payment_amount",
        color="platform",
        text="platform",
        custom_data=["payment_amount"],
        title="유입 대비 효율 높은 플랫폼",
    )
    fig.update_traces(
        textposition="top center",
        hovertemplate="플랫폼=%{text}<br>유입수=%{x:,.0f}<br>ROAS=%{y:.1f}%<br>결제금액=%{customdata[0]:,.0f}원<extra></extra>",
    )
    fig.update_xaxes(title="유입수", tickformat=",.0f")
    fig.update_yaxes(title="ROAS (%)", ticksuffix="%", tickformat=",.1f")
    apply_common_layout(fig)
    return fig


def build_worker_performance_chart(df: pd.DataFrame):
    if df.empty:
        return empty_figure("상위 작업자 집행 대비 매출")

    melted = df.melt(
        id_vars="worker",
        value_vars=["cost", "payment_amount"],
        var_name="metric",
        value_name="value",
    )
    melted["metric_label"] = melted["metric"].map(DISPLAY_NAMES)

    fig = px.bar(
        melted,
        x="value",
        y="worker",
        orientation="h",
        color="metric_label",
        barmode="group",
        color_discrete_map={
            DISPLAY_NAMES["cost"]: CHART_COLORS["cost"],
            DISPLAY_NAMES["payment_amount"]: CHART_COLORS["payment_amount"],
        },
        title="상위 작업자 집행 대비 매출",
    )
    fig.update_traces(hovertemplate="작업자=%{y}<br>지표=%{fullData.name}<br>금액=%{x:,.0f}원<extra></extra>")
    fig.update_xaxes(title="금액")
    apply_currency_xaxis(fig)
    apply_common_layout(fig)
    return fig


def build_payment_share_donut(df: pd.DataFrame):
    if df.empty:
        return empty_figure("플랫폼별 결제금액 비중")

    chart_df = df.loc[df["payment_amount"] > 0, ["platform", "payment_amount"]].copy()
    if chart_df.empty:
        chart_df = pd.DataFrame({"platform": ["결제 없음"], "payment_amount": [1]})

    fig = px.pie(
        chart_df,
        names="platform",
        values="payment_amount",
        hole=0.60,
        title="플랫폼별 결제금액 비중",
        color_discrete_sequence=["#8f7dff", "#ffb347", "#46d39a", "#ff7a59", "#8aa4ff", "#f472b6"],
    )
    fig.update_traces(textinfo="percent+label", hovertemplate="플랫폼=%{label}<br>결제금액=%{value:,.0f}원<extra></extra>")
    apply_common_layout(fig)
    return fig


def render_tables(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">작업 리스트</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-caption">실행 결과와 미매칭 사유를 한 번에 확인할 수 있게 정리했습니다.</div>', unsafe_allow_html=True)

    detail_columns = [
        "date", "platform", "worker", "product_name", "manager", "transfer_status",
        "cost", "keyword", "customer_count", "inflow_count", "page_count",
        "payment_count", "payment_amount", "match_status",
    ]
    detail_df = df.reindex(columns=detail_columns).copy()
    detail_df = detail_df.rename(columns={
        "date": "일자",
        "platform": "플랫폼",
        "worker": "작업자",
        "product_name": "상품명",
        "manager": "담당자",
        "transfer_status": "이체여부",
        "cost": "비용",
        "keyword": "키워드",
        "customer_count": "고객수",
        "inflow_count": "유입수",
        "page_count": "클릭수",
        "payment_count": "결제수",
        "payment_amount": "결제금액",
        "match_status": "매칭상태",
    })
    detail_df["일자"] = pd.to_datetime(detail_df["일자"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    for currency_column in ["비용", "결제금액"]:
        detail_df[currency_column] = detail_df[currency_column].fillna(0).map(format_currency)
    st.dataframe(detail_df, use_container_width=True, hide_index=True)

    unmatched_df = df.loc[
        df["match_status"] == "미매칭",
        ["date", "platform", "worker", "product_name", "keyword", "unmatched_reason"],
    ].copy()
    unmatched_df = unmatched_df.rename(columns={
        "date": "일자",
        "platform": "플랫폼",
        "worker": "작업자",
        "product_name": "상품명",
        "keyword": "키워드",
        "unmatched_reason": "미매칭 사유",
    })
    unmatched_df["일자"] = pd.to_datetime(unmatched_df["일자"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    st.markdown('<div class="section-title" style="font-size:1.2rem; margin-top:1.1rem;">매칭 실패 리스트</div>', unsafe_allow_html=True)
    st.dataframe(unmatched_df, use_container_width=True, hide_index=True)


def render_performance_totals(performance_df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">원본 효율 DB 전체 합계</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-caption">현재 필터에 걸린 매칭 행과 연결된 효율 DB 기준 합계입니다.</div>', unsafe_allow_html=True)
    kpis = build_performance_kpis(performance_df)
    columns = st.columns(len(kpis))
    for column, metric in zip(columns, kpis, strict=False):
        with column:
            st.metric(metric["label"], metric["value"])


def build_performance_kpis(df: pd.DataFrame) -> list[dict[str, str]]:
    if df.empty:
        return [
            {"label": "고객수", "value": "0"},
            {"label": "유입수", "value": "0"},
            {"label": "클릭수", "value": "0"},
            {"label": "결제수", "value": "0"},
            {"label": "결제금액", "value": format_currency(0)},
        ]

    return [
        {"label": "고객수", "value": format_number(df["customer_count"].fillna(0).sum())},
        {"label": "유입수", "value": format_number(df["inflow_count"].fillna(0).sum())},
        {"label": "클릭수", "value": format_number(df["page_count"].fillna(0).sum())},
        {"label": "결제수", "value": format_number(df["payment_count"].fillna(0).sum())},
        {"label": "결제금액", "value": format_currency(df["payment_amount"].fillna(0).sum())},
    ]


def filter_performance_by_matched_rows(matched_df: pd.DataFrame, performance_df: pd.DataFrame) -> pd.DataFrame:
    if matched_df.empty or performance_df.empty:
        return performance_df.iloc[0:0].copy()

    keys = set(
        matched_df.loc[matched_df["is_matched"].fillna(False)]
        .apply(
            lambda row: build_match_key(
                row["matched_nt_source"] or row["match_nt_source"],
                row["match_nt_detail"],
                row["match_nt_keyword"],
            ),
            axis=1,
        )
        .tolist()
    )
    if not keys:
        return performance_df.iloc[0:0].copy()

    working = performance_df.copy()
    working["match_key"] = working.apply(
        lambda row: build_match_key(row["nt_source"], row["nt_detail"], row["nt_keyword"]),
        axis=1,
    )
    return working.loc[working["match_key"].isin(keys)].copy()


def format_currency(value: float) -> str:
    return f"₩{float(value):,.0f}"


def format_percent(value: float) -> str:
    return f"{float(value):,.1f}%"


def format_number(value: float | int) -> str:
    return f"{float(value):,.0f}"


def apply_currency_yaxis(fig) -> None:
    fig.update_yaxes(tickprefix="₩", tickformat=",.0f")


def apply_currency_xaxis(fig) -> None:
    fig.update_xaxes(tickprefix="₩", tickformat=",.0f")


def apply_count_yaxis(fig) -> None:
    fig.update_yaxes(tickformat=",.0f")


def apply_common_layout(fig) -> None:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        font=dict(color="#dde5f1"),
        legend_title_text="",
        margin=dict(l=18, r=18, t=60, b=18),
        hoverlabel=dict(bgcolor="#111827", font_color="#f8fafc"),
        title_font=dict(size=18, color="#f8fafc"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(148, 163, 184, 0.18)", zeroline=False)


def empty_figure(title: str):
    fig = px.scatter(title=title)
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[dict(text="표시할 데이터가 없습니다.", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper", font=dict(color="#94a3b8", size=14))],
    )
    apply_common_layout(fig)
    return fig


def normalize_option_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", text).strip()


def normalized_option_values(series: pd.Series) -> list[str]:
    unique_values: dict[str, str] = {}
    for raw_value in series.dropna().astype(str).tolist():
        normalized = normalize_option_text(raw_value)
        if not normalized:
            continue
        unique_values.setdefault(normalized.casefold(), normalized)
    return sorted(unique_values.values())


if __name__ == "__main__":
    main()
