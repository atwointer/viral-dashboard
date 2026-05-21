from __future__ import annotations

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
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(59,130,246,0.18), transparent 28%),
            radial-gradient(circle at top right, rgba(16,185,129,0.12), transparent 24%),
            linear-gradient(180deg, #0a0f1f 0%, #111827 52%, #0b1220 100%);
        color: #e5eefc;
    }
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }
    div[data-testid="stMetric"] {
        background: rgba(15, 23, 42, 0.82);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 18px;
        padding: 18px 18px 14px 18px;
        box-shadow: 0 12px 32px rgba(2, 6, 23, 0.28);
    }
    div[data-testid="stMetric"] label {
        color: #8fb4ff;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 18px;
        overflow: hidden;
    }
    .panel {
        background: rgba(15, 23, 42, 0.74);
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 22px;
        padding: 1.2rem 1.3rem;
        margin-bottom: 1rem;
        box-shadow: 0 16px 38px rgba(2, 6, 23, 0.22);
    }
    .hero-title {
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 0.2rem;
    }
    .hero-subtitle {
        color: #9db2ce;
        font-size: 0.98rem;
    }
    .badge {
        display: inline-block;
        margin-top: 0.7rem;
        margin-right: 0.45rem;
        padding: 0.35rem 0.7rem;
        border-radius: 999px;
        background: rgba(59, 130, 246, 0.14);
        border: 1px solid rgba(96, 165, 250, 0.28);
        color: #dbeafe;
        font-size: 0.82rem;
    }
    h2, h3 {
        letter-spacing: -0.02em;
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
    "cost": "#60a5fa",
    "payment_amount": "#f59e0b",
    "inflow_count": "#22c55e",
    "payment_count": "#f97316",
    "roas": "#38bdf8",
    "match_rate": "#a78bfa",
}

DISPLAY_NAMES = {
    "cost": "비용",
    "payment_amount": "결제금액",
    "inflow_count": "유입수",
    "payment_count": "결제수",
    "roas": "ROAS",
    "match_rate": "매칭률",
}


@st.cache_data(show_spinner=False, ttl=300)
def get_dashboard_data() -> dict[str, pd.DataFrame]:
    return load_data()


def main() -> None:
    st.markdown(DARK_CSS, unsafe_allow_html=True)

    refresh_clicked = st.sidebar.button("원본 다시 불러오기", use_container_width=True)
    if refresh_clicked:
        get_dashboard_data.clear()
        st.session_state.pop("dashboard_data", None)

    if "dashboard_data" not in st.session_state:
        try:
            st.session_state["dashboard_data"] = get_dashboard_data()
        except Exception as exc:
            st.error(f"대시보드 로딩 실패: {exc}")
            return

    data = st.session_state["dashboard_data"]
    matched_df = ensure_table_columns(data["matched"].copy())
    performance_df = data["performance"].copy()
    source_meta = data["source_path"].iloc[0]

    render_header(source_meta, matched_df)
    filtered_df = render_filters(matched_df)
    filtered_performance_df = filter_performance_by_matched_rows(filtered_df, performance_df)

    render_kpis("매칭 기준 KPI", build_matched_kpis(filtered_df))
    render_charts(filtered_df)
    render_tables(filtered_df)

    st.markdown("---")
    render_kpis("원본 효율 DB 전체 합계", build_performance_kpis(filtered_performance_df))
    st.caption("현재 필터에 걸린 매칭 행과 연결된 효율 DB 기준 합계입니다.")


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
        <div class="panel">
            <div class="hero-title">바이럴 운영 관리자 대시보드</div>
            <div class="hero-subtitle">
                공개 Google Sheets 원본 DB와 NT 성과 원본을 Python에서 집계해 통합한 Streamlit 대시보드
            </div>
            <div class="badge">원본 시트: {source_url}</div>
            <div class="badge">매칭률: {coverage:.1f}% ({matched_count}/{total_count})</div>
            <div class="badge">집계 규칙: {collection_rule or "미설정"}</div>
            <div class="badge">최신 수집일: {latest_collection_date or "미기재"}</div>
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

    platforms = sorted(x for x in df["platform"].dropna().unique().tolist() if x)
    workers = sorted(x for x in df["worker"].dropna().unique().tolist() if x)
    products = sorted(x for x in df["product_name"].dropna().unique().tolist() if x)
    managers = sorted(x for x in df["manager"].dropna().unique().tolist() if x)
    transfer_options = sorted(x for x in df["transfer_status"].dropna().unique().tolist() if x)

    selected_platforms = st.sidebar.multiselect("플랫폼", platforms, default=platforms)
    selected_workers = st.sidebar.multiselect("작업자", workers)
    selected_products = st.sidebar.multiselect("상품명", products)
    selected_managers = st.sidebar.multiselect("담당자", managers)
    selected_transfers = st.sidebar.multiselect("이관 여부", transfer_options, default=transfer_options)

    filtered = df.copy()
    if len(date_range) == 2:
        start_date, end_date = map(pd.Timestamp, date_range)
        end_dt = end_date + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        filtered = filtered[
            filtered["date"].isna()
            | ((filtered["date"] >= start_date) & (filtered["date"] <= end_dt))
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

    st.sidebar.caption(f"필터 결과: {len(filtered):,}건")
    return filtered


def build_matched_kpis(df: pd.DataFrame) -> dict[str, float]:
    total_cost = float(df["cost"].sum())
    payment_amount = float(df["payment_amount"].sum())
    roas = payment_amount / total_cost * 100 if total_cost else 0.0

    return {
        "총 작업 수": float(len(df)),
        "총 비용": total_cost,
        "고객수": float(df["customer_count"].sum()),
        "유입수": float(df["inflow_count"].sum()),
        "클릭수": float(df["page_count"].sum()),
        "결제수": float(df["payment_count"].sum()),
        "결제금액": payment_amount,
        "ROAS": roas,
    }


def build_performance_kpis(df: pd.DataFrame) -> dict[str, float]:
    return {
        "효율DB 고객수": float(df["customer_count"].sum()),
        "효율DB 유입수": float(df["inflow_count"].sum()),
        "효율DB 페이지수": float(df["page_count"].sum()),
        "효율DB 결제수": float(df["payment_count"].sum()),
        "효율DB 결제금액": float(df["payment_amount"].sum()),
        "효율DB 기여결제수": float(df["payment_count_attributed"].sum()),
        "효율DB 기여결제금액": float(df["payment_amount_attributed"].sum()),
    }


def filter_performance_by_matched_rows(
    filtered_matched_df: pd.DataFrame,
    performance_df: pd.DataFrame,
) -> pd.DataFrame:
    if filtered_matched_df.empty or performance_df.empty:
        return performance_df.iloc[0:0].copy()

    matched_keys = (
        filtered_matched_df.loc[filtered_matched_df["is_matched"].fillna(False), "match_key"]
        .astype(str)
        .str.strip()
    )
    matched_keys = {key for key in matched_keys if key}
    if not matched_keys:
        return performance_df.iloc[0:0].copy()

    working_df = performance_df.copy()
    working_df["match_key"] = working_df.apply(
        lambda row: build_match_key(row["nt_source"], row["nt_detail"], row["nt_keyword"]),
        axis=1,
    )
    filtered = working_df[working_df["match_key"].isin(matched_keys)].copy()
    return filtered.drop(columns=["match_key"], errors="ignore")


def render_kpis(title: str, metrics: dict[str, float]) -> None:
    st.markdown(f"### {title}")
    columns = st.columns(4)
    count_tokens = ("작업 수", "고객수", "유입수", "페이지수", "결제수")

    for idx, (label, value) in enumerate(metrics.items()):
        with columns[idx % 4]:
            if any(token in label for token in count_tokens):
                st.metric(label, f"{value:,.0f}")
            elif "ROAS" in label:
                st.metric(label, f"{value:,.1f}%")
            else:
                st.metric(label, f"{value:,.0f}")


def render_charts(df: pd.DataFrame) -> None:
    summary_by_platform = summarize_chart_metrics(df, "platform")
    summary_by_worker = summarize_chart_metrics(df, "worker")
    daily_trend = build_time_series(df, "D")
    weekly_trend = build_time_series(df, "W-MON")
    monthly_trend = build_time_series(df, "M")
    revenue_share_df = summarize_revenue_share(summary_by_platform)

    top_left, top_right = st.columns((1.08, 0.92))

    with top_left:
        st.markdown("### 플랫폼별 비용 vs 결제금액")
        if summary_by_platform.empty:
            st.info("표시할 플랫폼 비교 데이터가 없습니다.")
        else:
            chart_df = (
                summary_by_platform.sort_values("cost", ascending=False)
                .melt(
                    id_vars="platform",
                    value_vars=["cost", "payment_amount"],
                    var_name="metric",
                    value_name="amount",
                )
            )
            chart_df["metric_label"] = chart_df["metric"].map(DISPLAY_NAMES)
            fig = px.bar(
                chart_df,
                x="platform",
                y="amount",
                color="metric_label",
                barmode="group",
                template="plotly_dark",
                color_discrete_map={
                    DISPLAY_NAMES["cost"]: CHART_COLORS["cost"],
                    DISPLAY_NAMES["payment_amount"]: CHART_COLORS["payment_amount"],
                },
                labels={"platform": "플랫폼", "amount": "금액", "metric_label": "지표"},
            )
            fig.update_xaxes(categoryorder="total descending")
            apply_chart_layout(fig, 360)
            st.plotly_chart(fig, use_container_width=True)

    with top_right:
        st.markdown("### 일별 유입수 vs 결제수")
        if daily_trend.empty:
            st.info("표시할 일별 추이 데이터가 없습니다.")
        else:
            daily_chart = daily_trend.rename(
                columns={
                    "inflow_count": DISPLAY_NAMES["inflow_count"],
                    "payment_count": DISPLAY_NAMES["payment_count"],
                }
            )
            fig = px.line(
                daily_chart,
                x="period",
                y=[DISPLAY_NAMES["inflow_count"], DISPLAY_NAMES["payment_count"]],
                template="plotly_dark",
                color_discrete_map={
                    DISPLAY_NAMES["inflow_count"]: CHART_COLORS["inflow_count"],
                    DISPLAY_NAMES["payment_count"]: CHART_COLORS["payment_count"],
                },
                labels={"period": "일자", "value": "수치", "variable": "지표"},
                markers=True,
            )
            apply_chart_layout(fig, 360)
            st.plotly_chart(fig, use_container_width=True)

    middle_left, middle_right = st.columns(2)

    with middle_left:
        st.markdown("### 주별 유입수 vs 결제수")
        if weekly_trend.empty:
            st.info("표시할 주별 추이 데이터가 없습니다.")
        else:
            weekly_chart = weekly_trend.rename(
                columns={
                    "inflow_count": DISPLAY_NAMES["inflow_count"],
                    "payment_count": DISPLAY_NAMES["payment_count"],
                }
            )
            fig = px.bar(
                weekly_chart,
                x="period_label",
                y=[DISPLAY_NAMES["inflow_count"], DISPLAY_NAMES["payment_count"]],
                barmode="group",
                template="plotly_dark",
                color_discrete_map={
                    DISPLAY_NAMES["inflow_count"]: CHART_COLORS["inflow_count"],
                    DISPLAY_NAMES["payment_count"]: CHART_COLORS["payment_count"],
                },
                labels={"period_label": "주차", "value": "수치", "variable": "지표"},
            )
            apply_chart_layout(fig, 340)
            st.plotly_chart(fig, use_container_width=True)

    with middle_right:
        st.markdown("### 월별 비용 vs 결제금액")
        if monthly_trend.empty:
            st.info("표시할 월별 추이 데이터가 없습니다.")
        else:
            monthly_chart = monthly_trend.rename(
                columns={
                    "cost": DISPLAY_NAMES["cost"],
                    "payment_amount": DISPLAY_NAMES["payment_amount"],
                }
            )
            fig = px.bar(
                monthly_chart,
                x="period_label",
                y=[DISPLAY_NAMES["cost"], DISPLAY_NAMES["payment_amount"]],
                barmode="group",
                template="plotly_dark",
                color_discrete_map={
                    DISPLAY_NAMES["cost"]: CHART_COLORS["cost"],
                    DISPLAY_NAMES["payment_amount"]: CHART_COLORS["payment_amount"],
                },
                labels={"period_label": "월", "value": "금액", "variable": "지표"},
            )
            apply_chart_layout(fig, 340)
            st.plotly_chart(fig, use_container_width=True)

    bottom_left, bottom_right = st.columns(2)

    with bottom_left:
        st.markdown("### 플랫폼별 유입수 vs ROAS")
        if summary_by_platform.empty:
            st.info("표시할 플랫폼 효율 데이터가 없습니다.")
        else:
            platform_efficiency = summary_by_platform.sort_values(
                ["payment_amount", "roas"],
                ascending=[False, False],
            )
            fig = px.scatter(
                platform_efficiency,
                x="inflow_count",
                y="roas",
                size="payment_amount",
                color="platform",
                template="plotly_dark",
                labels={"inflow_count": "유입수", "roas": "ROAS (%)", "platform": "플랫폼"},
                hover_data={"payment_amount": ":,.0f", "cost": ":,.0f", "payment_count": ":,.0f"},
            )
            fig.update_yaxes(ticksuffix="%")
            fig.update_traces(marker=dict(line=dict(width=1, color="rgba(255,255,255,0.35)")))
            apply_chart_layout(fig, 340)
            st.plotly_chart(fig, use_container_width=True)

    with bottom_right:
        st.markdown("### 작업자별 비용 vs 결제금액")
        if summary_by_worker.empty:
            st.info("표시할 작업자 데이터가 없습니다.")
        else:
            worker_chart = (
                summary_by_worker.sort_values("cost", ascending=False)
                .head(10)
                .melt(
                    id_vars="worker",
                    value_vars=["cost", "payment_amount"],
                    var_name="metric",
                    value_name="amount",
                )
            )
            worker_chart["metric_label"] = worker_chart["metric"].map(DISPLAY_NAMES)
            fig = px.bar(
                worker_chart,
                x="worker",
                y="amount",
                color="metric_label",
                barmode="group",
                template="plotly_dark",
                color_discrete_map={
                    DISPLAY_NAMES["cost"]: CHART_COLORS["cost"],
                    DISPLAY_NAMES["payment_amount"]: CHART_COLORS["payment_amount"],
                },
                labels={"worker": "작업자", "amount": "금액", "metric_label": "지표"},
            )
            apply_chart_layout(fig, 340)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 플랫폼별 결제금액 비중")
    if revenue_share_df.empty:
        st.info("표시할 결제금액 비중 데이터가 없습니다.")
    else:
        fig = px.pie(
            revenue_share_df,
            names="platform",
            values="payment_amount",
            template="plotly_dark",
            hole=0.52,
            color_discrete_sequence=["#38bdf8", "#34d399", "#f59e0b", "#f87171", "#f472b6"],
        )
        apply_chart_layout(fig, 360)
        st.plotly_chart(fig, use_container_width=True)


def apply_chart_layout(fig, height: int) -> None:
    fig.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=12, b=12),
        legend_title_text="",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.25)",
    )


def summarize_chart_metrics(df: pd.DataFrame, group_column: str) -> pd.DataFrame:
    if df.empty or group_column not in df.columns:
        return pd.DataFrame()

    working_df = df.copy()
    working_df[group_column] = working_df[group_column].fillna("").astype(str).str.strip()
    working_df = working_df[working_df[group_column].ne("")].copy()
    if working_df.empty:
        return pd.DataFrame()

    summary = (
        working_df.groupby(group_column, dropna=False, as_index=False)
        .agg(
            rows=("row_id", "count"),
            cost=("cost", "sum"),
            inflow_count=("inflow_count", "sum"),
            payment_count=("payment_count", "sum"),
            payment_amount=("payment_amount", "sum"),
            matched_rows=("is_matched", "sum"),
        )
    )
    summary["roas"] = summary.apply(
        lambda row: row["payment_amount"] / row["cost"] * 100 if row["cost"] else 0,
        axis=1,
    )
    summary["match_rate"] = summary.apply(
        lambda row: row["matched_rows"] / row["rows"] * 100 if row["rows"] else 0,
        axis=1,
    )
    return summary


def summarize_revenue_share(summary_by_platform: pd.DataFrame) -> pd.DataFrame:
    if summary_by_platform.empty:
        return pd.DataFrame(columns=["platform", "payment_amount"])

    revenue_share_df = summary_by_platform[["platform", "payment_amount"]].copy()
    revenue_share_df = revenue_share_df[revenue_share_df["payment_amount"] > 0].copy()
    return revenue_share_df.sort_values("payment_amount", ascending=False).reset_index(drop=True)


def build_time_series(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    dated_df = df.dropna(subset=["date"]).copy()
    if dated_df.empty:
        return pd.DataFrame()

    if freq == "D":
        dated_df["period"] = dated_df["date"].dt.normalize()
    elif freq == "M":
        dated_df["period"] = dated_df["date"].dt.to_period("M").dt.to_timestamp()
    else:
        dated_df["period"] = dated_df["date"].dt.to_period(freq).dt.to_timestamp()

    summary = (
        dated_df.groupby("period", as_index=False)
        .agg(
            cost=("cost", "sum"),
            inflow_count=("inflow_count", "sum"),
            payment_count=("payment_count", "sum"),
            payment_amount=("payment_amount", "sum"),
        )
        .sort_values("period")
        .reset_index(drop=True)
    )

    if freq == "D":
        summary["period_label"] = summary["period"].dt.strftime("%Y-%m-%d")
    elif freq == "M":
        summary["period_label"] = summary["period"].dt.strftime("%Y-%m")
    else:
        period_end = summary["period"] + pd.Timedelta(days=6)
        summary["period_label"] = (
            summary["period"].dt.strftime("%m/%d") + " - " + period_end.dt.strftime("%m/%d")
        )

    return summary


def summarize_transfer_status(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "transfer_status" not in df.columns:
        return pd.DataFrame(columns=["transfer_status", "rows"])

    transfer_df = df.copy()
    transfer_df["transfer_status"] = transfer_df["transfer_status"].fillna("").astype(str).str.strip()
    transfer_df["transfer_status"] = transfer_df["transfer_status"].replace("", "미기재")
    return (
        transfer_df.groupby("transfer_status", as_index=False)
        .agg(rows=("row_id", "count"))
        .sort_values("rows", ascending=False)
        .reset_index(drop=True)
    )


def render_tables(df: pd.DataFrame) -> None:
    working_df = ensure_table_columns(df)

    st.markdown("### 플랫폼별 성과 요약")
    st.dataframe(format_summary_table(summarize_by_platform(working_df)), use_container_width=True, hide_index=True)

    st.markdown("### 작업자별 성과 요약")
    st.dataframe(format_summary_table(summarize_by_worker(working_df)), use_container_width=True, hide_index=True)

    st.markdown("### 작업 상세 리스트")
    detail_columns = [
        "date",
        "platform",
        "worker",
        "product_name",
        "manager",
        "transfer_status",
        "cost",
        "keyword",
        "customer_count",
        "inflow_count",
        "page_count",
        "payment_count",
        "payment_amount",
        "match_status",
        "match_method",
        "perf_latest_collected_at",
        "perf_debug_rows",
    ]
    detail_df = working_df[detail_columns].sort_values(["date", "platform", "worker"], ascending=[False, True, True]).copy()
    detail_df["date"] = detail_df["date"].dt.strftime("%Y-%m-%d").fillna("")
    st.dataframe(detail_df, use_container_width=True, hide_index=True)

    st.markdown("### 매칭 실패 리스트")
    unmatched = working_df[working_df["match_status"] != "매칭"][
        [
            "date",
            "platform",
            "worker",
            "product_name",
            "manager",
            "transfer_status",
            "cost",
            "keyword",
            "match_nt_source",
            "match_nt_detail",
            "match_nt_keyword",
            "match_method",
            "perf_latest_collected_at",
            "perf_debug_rows",
            "unmatched_reason",
        ]
    ].copy()
    unmatched["date"] = unmatched["date"].dt.strftime("%Y-%m-%d").fillna("")
    st.dataframe(unmatched, use_container_width=True, hide_index=True)


def summarize_by_platform(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=["platform", "작업수", "총비용", "고객수", "유입수", "페이지수", "결제수", "결제금액", "매칭건수", "ROAS", "매칭률"]
        )

    summary = (
        df.groupby("platform", dropna=False)
        .agg(
            작업수=("row_id", "count"),
            총비용=("cost", "sum"),
            고객수=("customer_count", "sum"),
            유입수=("inflow_count", "sum"),
            페이지수=("page_count", "sum"),
            결제수=("payment_count", "sum"),
            결제금액=("payment_amount", "sum"),
            매칭건수=("is_matched", "sum"),
        )
        .reset_index()
    )
    summary["ROAS"] = summary.apply(
        lambda row: row["결제금액"] / row["총비용"] * 100 if row["총비용"] else 0,
        axis=1,
    )
    summary["매칭률"] = summary.apply(
        lambda row: row["매칭건수"] / row["작업수"] * 100 if row["작업수"] else 0,
        axis=1,
    )
    return summary.sort_values("총비용", ascending=False).reset_index(drop=True)


def summarize_by_worker(df: pd.DataFrame) -> pd.DataFrame:
    working_df = df.copy()
    working_df["worker"] = working_df["worker"].fillna("").astype(str).str.strip()
    working_df = working_df[working_df["worker"].ne("")].copy()

    if working_df.empty:
        return pd.DataFrame(
            columns=["작업자", "작업수", "총비용", "고객수", "유입수", "페이지수", "결제수", "결제금액", "매칭건수", "ROAS", "매칭률"]
        )

    summary = (
        working_df.groupby("worker", dropna=False)
        .agg(
            작업수=("row_id", "count"),
            총비용=("cost", "sum"),
            고객수=("customer_count", "sum"),
            유입수=("inflow_count", "sum"),
            페이지수=("page_count", "sum"),
            결제수=("payment_count", "sum"),
            결제금액=("payment_amount", "sum"),
            매칭건수=("is_matched", "sum"),
        )
        .reset_index()
        .rename(columns={"worker": "작업자"})
    )
    summary["ROAS"] = summary.apply(
        lambda row: row["결제금액"] / row["총비용"] * 100 if row["총비용"] else 0,
        axis=1,
    )
    summary["매칭률"] = summary.apply(
        lambda row: row["매칭건수"] / row["작업수"] * 100 if row["작업수"] else 0,
        axis=1,
    )
    return summary.sort_values("총비용", ascending=False).reset_index(drop=True)


def format_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    formatted = df.copy()
    for column in formatted.columns:
        if column in {"platform", "작업자"}:
            continue
        if column in {"ROAS", "매칭률"}:
            formatted[column] = formatted[column].map(lambda value: f"{value:,.1f}%")
        else:
            formatted[column] = formatted[column].map(lambda value: f"{value:,.0f}")
    return formatted


if __name__ == "__main__":
    main()
