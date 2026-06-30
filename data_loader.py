from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable
from urllib.error import HTTPError, URLError

import pandas as pd


SPREADSHEET_ID = "1NeeQNSiG9D9u5U290vyW_LKIn9Siyd9EinwZaUXzIiM"
SPREADSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"

PAID_SHEETS = {
    "블로그": {"gid": "198507325", "sheet_name": "(DB)블로그(완료건 기준)"},
    "인스타그램": {"gid": "1485104371", "sheet_name": "(DB)인스타그램(완료건 기준)"},
    "유튜브": {"gid": "534722161", "sheet_name": "(DB)유튜브(완료건 기준)"},
    "X": {"gid": "1433936261", "sheet_name": "(DB)X(완료건 기준)"},
    "커뮤니티": {"gid": "1056422214", "sheet_name": "(DB)커뮤니티"},
    "브랜드커넥트": {"gid": "255349713", "sheet_name": "(DB)브랜드커넥트"},
}
PERFORMANCE_SHEET = {"gid": "1675730631", "sheet_name": "(DB)바이럴효율"}

PAID_COLUMNS = [
    "row_id",
    "date",
    "platform",
    "platform_group",
    "worker",
    "product_name",
    "manager",
    "transfer_status",
    "cost",
    "keyword",
    "url",
    "notes",
    "source_sheet",
    "match_nt_source",
    "match_nt_detail",
    "match_nt_keyword",
]

PERFORMANCE_METRICS = [
    "customer_count",
    "inflow_count",
    "page_count",
    "payment_count",
    "payment_amount",
    "payment_count_attributed",
    "payment_amount_attributed",
]

LATEST_SNAPSHOT_METRICS = ["customer_count", "inflow_count", "page_count"]
MAX_VALUE_METRICS = [
    "payment_count",
    "payment_amount",
    "payment_count_attributed",
    "payment_amount_attributed",
]


@dataclass(frozen=True)
class WorkbookSheets:
    paid: dict[str, str]
    performance: str


def load_data() -> dict[str, pd.DataFrame]:
    raw_data, load_errors = load_google_public_sheets_data()
    sheets = identify_sheets(raw_data.keys())

    paid_frames: list[pd.DataFrame] = []
    for platform_group, sheet_name in sheets.paid.items():
        standardized = standardize_paid_sheet(
            raw_data.get(sheet_name, pd.DataFrame()),
            platform_group,
            sheet_name,
        )
        if not standardized.empty:
            paid_frames.append(standardized)

    paid_df = (
        pd.concat(paid_frames, ignore_index=True)
        if paid_frames
        else pd.DataFrame(columns=PAID_COLUMNS)
    )
    paid_df = finalize_paid_df(paid_df)

    performance_raw = raw_data.get(sheets.performance, pd.DataFrame())
    performance_collection_dates = extract_collection_date(performance_raw)
    performance_df = finalize_performance_df(performance_raw)

    matched_df, unmatched_df = match_paid_with_performance(paid_df, performance_df)

    if performance_collection_dates.notna().any():
        latest_collection_date = performance_collection_dates.max().strftime("%Y-%m-%d")
        earliest_collection_date = performance_collection_dates.min().strftime("%Y-%m-%d")
    else:
        latest_collection_date = ""
        earliest_collection_date = ""

    source_meta = pd.DataFrame(
        [
            {
                "source_url": SPREADSHEET_URL,
                "collection_rule": "키별 최신 수집일 유지, 트래픽은 최신 기준, 결제는 최대값 기준",
                "latest_collection_date": latest_collection_date,
                "earliest_collection_date": earliest_collection_date,
                "load_errors": " | ".join(load_errors),
            }
        ]
    )

    return {
        "paid": paid_df,
        "performance": performance_df,
        "matched": matched_df,
        "unmatched": unmatched_df,
        "source_path": source_meta,
    }


def build_csv_url(spreadsheet_id: str, gid: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"


def load_google_public_sheets_data() -> tuple[dict[str, pd.DataFrame], list[str]]:
    data: dict[str, pd.DataFrame] = {}
    errors: list[str] = []

    for sheet_meta in list(PAID_SHEETS.values()) + [PERFORMANCE_SHEET]:
        sheet_name = sheet_meta["sheet_name"]
        csv_url = build_csv_url(SPREADSHEET_ID, sheet_meta["gid"])
        try:
            data[sheet_name] = pd.read_csv(csv_url)
        except pd.errors.EmptyDataError:
            data[sheet_name] = pd.DataFrame()
        except (HTTPError, URLError, TimeoutError, ConnectionError, OSError) as exc:
            data[sheet_name] = pd.DataFrame()
            errors.append(f"{sheet_name}: {exc.__class__.__name__}")

    return data, errors


def identify_sheets(sheet_names: Iterable[str]) -> WorkbookSheets:
    available = set(sheet_names)
    paid = {
        platform_group: meta["sheet_name"]
        for platform_group, meta in PAID_SHEETS.items()
        if meta["sheet_name"] in available
    }
    performance = PERFORMANCE_SHEET["sheet_name"] if PERFORMANCE_SHEET["sheet_name"] in available else ""

    if not performance:
        raise ValueError(f"'{PERFORMANCE_SHEET['sheet_name']}' 시트를 찾지 못했습니다.")

    return WorkbookSheets(paid=paid, performance=performance)


def standardize_paid_sheet(df: pd.DataFrame, platform_group: str, sheet_name: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=PAID_COLUMNS)

    clean_df = df.copy()
    clean_df.columns = [sanitize_column_name(column) for column in clean_df.columns]
    clean_df = clean_df.loc[:, ~clean_df.columns.duplicated()]
    clean_df = clean_df.loc[:, ~clean_df.columns.str.startswith("unnamed")]
    clean_df = clean_df.dropna(how="all").copy()

    if platform_group == "커뮤니티":
        standardized = pd.DataFrame(
            {
                "date": to_datetime_series(get_series_by_alias(clean_df, ["날짜", "일자", "업로드일"])),
                "platform": get_series_by_alias(clean_df, ["플랫폼", "채널", "매체"]).map(clean_text),
                "platform_group": platform_group,
                "worker": first_non_empty_series(
                    get_series_by_alias(clean_df, ["작업자", "작업", "운영자"]),
                    get_series_by_alias(clean_df, ["플랫폼", "채널", "매체"]),
                ).map(clean_text),
                "product_name": first_non_empty_series(
                    get_series_by_alias(clean_df, ["키워드", "상품명", "상품"]),
                    get_series_by_alias(clean_df, ["제목", "콘텐츠명"]),
                ).map(clean_text),
                "manager": get_series_by_alias(clean_df, ["담당자", "담당"]).map(clean_text),
                "transfer_status": get_series_by_alias(clean_df, ["이체여부"]).map(clean_transfer_status),
                "cost": to_numeric_series(
                    first_non_empty_series(
                        get_series_by_alias(clean_df, ["비용", "집행금액", "예상비용"]),
                        get_series_by_alias(clean_df, ["광고비", "원고료"]),
                    )
                ),
                "keyword": first_non_empty_series(
                    get_series_by_alias(clean_df, ["키워드", "상품명", "상품"]),
                    get_series_by_alias(clean_df, ["제목", "콘텐츠명"]),
                ).map(clean_text),
                "url": get_link_series(clean_df).map(clean_text),
                "notes": get_series_by_alias(clean_df, ["비고", "메모"]).map(clean_text),
                "source_sheet": sheet_name,
            }
        )
    else:
        standardized = pd.DataFrame(
            {
                "date": to_datetime_series(
                    first_non_empty_series(
                        get_series_by_alias(clean_df, ["업로드날짜", "업로드일", "게시일"]),
                        get_series_by_alias(clean_df, ["날짜", "일자"]),
                    )
                ),
                "platform": platform_group,
                "platform_group": platform_group,
                "worker": get_series_by_alias(clean_df, ["작업자", "작업", "닉네임", "계정"]).map(clean_text),
                "product_name": first_non_empty_series(
                    get_series_by_alias(clean_df, ["제안상품", "제안제품", "상품명", "제품명", "상품"]),
                    get_series_by_alias(clean_df, ["키워드", "캠페인명"]),
                ).map(clean_text),
                "manager": get_series_by_alias(clean_df, ["담당자", "담당"]).map(clean_text),
                "transfer_status": get_series_by_alias(clean_df, ["이체여부"]).map(clean_transfer_status),
                "cost": to_numeric_series(
                    first_non_empty_series(
                        get_series_by_alias(clean_df, ["유상비용", "예상비용", "비용", "집행금액"]),
                        get_series_by_alias(clean_df, ["광고비", "원고료"]),
                    )
                ),
                "keyword": first_non_empty_series(
                    get_series_by_alias(clean_df, ["키워드"]),
                    get_series_by_alias(clean_df, ["제안상품", "제안제품", "상품명", "제품명", "상품"]),
                ).map(clean_text),
                "url": get_link_series(clean_df).map(clean_text),
                "notes": get_series_by_alias(clean_df, ["비고", "메모"]).map(clean_text),
                "source_sheet": sheet_name,
            }
        )

    standardized["row_id"] = [f"{platform_group}-{index + 1}" for index in range(len(standardized))]
    standardized = standardized.reindex(columns=PAID_COLUMNS[:-3])
    standardized = standardized.dropna(
        how="all",
        subset=["date", "worker", "product_name", "cost", "keyword"],
    )
    return standardized


def finalize_paid_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=PAID_COLUMNS)

    result = df.copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    result["platform"] = result["platform"].fillna(result["platform_group"]).map(clean_text)
    result["platform_group"] = result["platform_group"].map(clean_text)
    result["worker"] = result["worker"].map(clean_text)
    result["product_name"] = result["product_name"].map(clean_text)
    result["manager"] = result["manager"].map(clean_text)
    result["transfer_status"] = result["transfer_status"].map(clean_transfer_status)
    result["keyword"] = result["keyword"].map(clean_text)
    result["url"] = result["url"].map(clean_text)
    result["notes"] = result["notes"].map(clean_text)
    result["cost"] = to_numeric_series(result["cost"]).fillna(0)
    result["match_nt_detail"] = result["worker"].map(normalize_match_text)
    result["match_nt_keyword"] = result["keyword"].map(normalize_match_text)
    result["match_nt_source"] = result.apply(build_primary_nt_source, axis=1)
    return result.reindex(columns=PAID_COLUMNS)


def finalize_performance_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=["nt_source", "nt_detail", "nt_keyword", "collected_at"]
            + PERFORMANCE_METRICS
            + ["perf_debug_rows", "perf_latest_collected_at"]
        )

    working = df.copy()
    working.columns = [sanitize_column_name(column) for column in working.columns]
    working = working.loc[:, ~working.columns.str.startswith("unnamed")]
    working = working.dropna(how="all").copy()

    working["nt_source"] = get_series_by_alias(
        working,
        ["nt_source", "ntsource", "소스", "매체", "플랫폼", "채널"],
    ).map(normalize_nt_source)
    working["nt_detail"] = first_non_empty_series(
        get_series_by_alias(working, ["nt_detail", "ntdetail", "상세", "작업자", "작업자명", "계정"]),
        get_series_by_alias(working, ["닉네임", "운영자"]),
    ).map(normalize_match_text)
    working["nt_keyword"] = first_non_empty_series(
        get_series_by_alias(working, ["nt_keyword", "ntkeyword", "키워드"]),
        get_series_by_alias(working, ["상품명", "상품", "캠페인명"]),
    ).map(normalize_match_text)
    working["collected_at"] = extract_collection_date(working)
    working["row_order"] = range(len(working))

    for metric in PERFORMANCE_METRICS:
        working[metric] = to_numeric_series(
            get_series_by_alias(
                working,
                performance_metric_aliases(metric),
            )
        ).fillna(0)

    working = working[
        working["nt_source"].ne("")
        | working["nt_detail"].ne("")
        | working["nt_keyword"].ne("")
    ].copy()

    return collapse_cumulative_performance_rows(
        working,
        key_columns=["nt_source", "nt_detail", "nt_keyword"],
    )


def match_paid_with_performance(
    paid_df: pd.DataFrame,
    performance_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if paid_df.empty:
        empty = paid_df.copy()
        for metric in PERFORMANCE_METRICS:
            empty[metric] = 0
        empty["match_status"] = "미매칭"
        empty["is_matched"] = False
        empty["match_key"] = ""
        empty["matched_nt_source"] = ""
        empty["match_method"] = ""
        empty["perf_debug_rows"] = ""
        empty["perf_latest_collected_at"] = ""
        empty["unmatched_reason"] = "유상 작업 데이터가 없습니다."
        return empty, empty.copy()

    perf_lookup = performance_df.copy()
    # 날짜 없는 성과행은 작업 시점을 특정할 수 없어 매칭에서 제외(미매칭 처리)
    perf_lookup = perf_lookup[perf_lookup["nt_keyword"].map(keyword_has_date)].copy()
    perf_lookup["match_key"] = perf_lookup.apply(
        lambda row: build_match_key(row["nt_source"], row["nt_detail"], row["nt_keyword"]),
        axis=1,
    )
    perf_lookup = collapse_duplicate_match_keys(perf_lookup)
    perf_map = perf_lookup.set_index("match_key").to_dict(orient="index")
    perf_candidates = perf_lookup.to_dict(orient="records")
    used_perf_keys: set[str] = set()

    records: list[dict] = []
    for _, row in paid_df.iterrows():
        matched: dict | None = None
        matched_source = ""
        match_method = ""

        for candidate_source in build_nt_source_candidates(row):
            key = build_match_key(candidate_source, row["match_nt_detail"], row["match_nt_keyword"])
            if key in perf_map and key not in used_perf_keys:
                matched = perf_map[key]
                matched_source = candidate_source
                match_method = "direct_key"
                used_perf_keys.add(key)
                break

        if matched is None:
            reverse_match = find_reverse_match(row, perf_candidates, used_perf_keys)
            if reverse_match is not None:
                matched = reverse_match
                matched_source = reverse_match.get("nt_source", "")
                match_method = "reverse_inference"
                used_perf_keys.add(reverse_match.get("match_key", ""))

        record = row.to_dict()
        record["match_key"] = build_match_key(
            matched_source or row["match_nt_source"],
            row["match_nt_detail"],
            row["match_nt_keyword"],
        )
        record["matched_nt_source"] = matched_source

        if matched is not None:
            for metric in PERFORMANCE_METRICS:
                record[metric] = matched.get(metric, 0)
            record["match_status"] = "매칭"
            record["is_matched"] = True
            record["match_method"] = match_method
            record["perf_debug_rows"] = matched.get("perf_debug_rows", "")
            record["perf_latest_collected_at"] = matched.get("perf_latest_collected_at", "")
            record["unmatched_reason"] = ""
        else:
            for metric in PERFORMANCE_METRICS:
                record[metric] = 0
            record["match_status"] = "미매칭"
            record["is_matched"] = False
            record["match_method"] = ""
            record["perf_debug_rows"] = ""
            record["perf_latest_collected_at"] = ""
            record["unmatched_reason"] = infer_unmatched_reason(row)

        records.append(record)

    matched_df = pd.DataFrame(records)
    unmatched_df = matched_df.loc[matched_df["match_status"] == "미매칭"].copy()
    return matched_df, unmatched_df


def build_primary_nt_source(row: pd.Series) -> str:
    candidates = build_nt_source_candidates(row)
    return candidates[0] if candidates else ""


def collapse_duplicate_match_keys(perf_lookup: pd.DataFrame) -> pd.DataFrame:
    if perf_lookup.empty or "match_key" not in perf_lookup.columns:
        return perf_lookup

    def first_non_empty(values: pd.Series) -> str:
        for value in values:
            cleaned = clean_text(value)
            if cleaned:
                return cleaned
        return ""

    def join_non_empty(values: pd.Series) -> str:
        cleaned_values = [clean_text(value) for value in values]
        return " | ".join(value for value in cleaned_values if value)

    aggregations = {
        "nt_source": first_non_empty,
        "nt_detail": first_non_empty,
        "nt_keyword": first_non_empty,
        "perf_debug_rows": join_non_empty,
        "perf_latest_collected_at": first_non_empty,
    }
    for metric in PERFORMANCE_METRICS:
        aggregations[metric] = "sum"

    return (
        perf_lookup.groupby("match_key", dropna=False, as_index=False)
        .agg(aggregations)
        .reset_index(drop=True)
    )


def build_nt_source_candidates(row: pd.Series) -> list[str]:
    platform_group = clean_text(row.get("platform_group", ""))
    platform_value = clean_text(row.get("platform", ""))

    if platform_group == "블로그":
        return ["naverblog", "naver"]
    if platform_group == "인스타그램":
        return ["instagram"]
    if platform_group == "유튜브":
        return ["youtube"]
    if platform_group == "X":
        return ["x", "twitter"]
    if platform_group == "브랜드커넥트":
        return ["nshoplive"]
    if platform_group == "커뮤니티":
        normalized_platform = normalize_nt_source(platform_value)
        return [normalized_platform] if normalized_platform else []

    normalized_platform_group = normalize_nt_source(platform_group)
    return [normalized_platform_group] if normalized_platform_group else []


def build_match_key(nt_source: str, nt_detail: str, nt_keyword: str) -> str:
    return "||".join(
        [
            normalize_nt_source(nt_source),
            normalize_match_text(nt_detail),
            normalize_keyword_token(nt_keyword),
        ]
    )


# 완료시트(한글)와 성과DB(영어)의 제품 표기 차이를 흡수하기 위한 치환표
KEYWORD_KO_EN = {
    "오픈이어": "openear",
    "키보드": "keyboard",
    "본": "bone",
    "네온": "neon",
    "플렉스": "flex",
    "프로": "pro",
}


def keyword_has_date(value: object) -> bool:
    """성과DB 키워드가 날짜(6~8자리)로 시작하는지."""
    return bool(re.match(r"^\d{6,8}", clean_text(value)))


def normalize_keyword_token(value: object) -> str:
    """매칭용 키워드 정규화: 소문자/공백제거 + 날짜접두어 제거 + 한글→영어 + 특수문자 제거."""
    text = normalize_match_text(value)
    text = re.sub(r"^\d{6,8}_?", "", text)
    for korean, english in KEYWORD_KO_EN.items():
        text = text.replace(korean, english)
    return re.sub(r"[^a-z0-9가-힣]", "", text)


def find_reverse_match(
    paid_row: pd.Series,
    perf_candidates: list[dict],
    used_perf_keys: set[str],
) -> dict | None:
    worker_token = normalize_match_text(paid_row.get("worker", ""))
    product_token = normalize_product_token(paid_row.get("product_name", ""))
    paid_date = pd.to_datetime(paid_row.get("date"), errors="coerce")

    if not worker_token or not product_token:
        return None

    for candidate in perf_candidates:
        candidate_key = candidate.get("match_key", "")
        if candidate_key in used_perf_keys:
            continue
        if normalize_match_text(candidate.get("nt_detail", "")) != worker_token:
            continue

        keyword_text = clean_text(candidate.get("nt_keyword", ""))
        if product_token not in normalize_product_token(keyword_text):
            continue

        keyword_date = extract_date_from_keyword(keyword_text)
        if paid_date is not pd.NaT and keyword_date is not None and pd.notna(paid_date):
            if paid_date.normalize() != keyword_date:
                continue

        return candidate

    return None


def infer_unmatched_reason(row: pd.Series) -> str:
    if not row.get("match_nt_keyword"):
        return "직접 매칭할 키워드가 없습니다."
    if not row.get("match_nt_detail"):
        return "작업자 정보가 없습니다."
    if not row.get("match_nt_source"):
        return "nt_source 추론 불가"
    return "성과 DB와 일치하는 키가 없습니다."


def extract_collection_date(df: pd.DataFrame) -> pd.Series:
    candidate_columns = {
        "수집일",
        "수집일자",
        "조회시작일",
        "조회종료일",
        "집계일",
        "기준일",
        "date",
        "collectedat",
    }
    for column in df.columns:
        if sanitize_column_name(column) in candidate_columns:
            return parse_flexible_date_series(df[column])
    return pd.Series([pd.NaT] * len(df), index=df.index, dtype="datetime64[ns]")


def collapse_cumulative_performance_rows(
    working: pd.DataFrame,
    key_columns: list[str],
) -> pd.DataFrame:
    if working.empty:
        return pd.DataFrame(
            columns=key_columns + PERFORMANCE_METRICS + ["perf_debug_rows", "perf_latest_collected_at"]
        )

    working = working.copy()
    working["effective_collected_at"] = working["collected_at"]

    if working["effective_collected_at"].notna().sum() == 0:
        grouped = (
            working.groupby(key_columns, dropna=False, as_index=False)[PERFORMANCE_METRICS]
            .sum()
            .sort_values(key_columns)
            .reset_index(drop=True)
        )
        grouped["perf_debug_rows"] = ""
        grouped["perf_latest_collected_at"] = ""
        return grouped

    collapsed_rows: list[dict] = []
    for _, group in working.groupby(key_columns, dropna=False, sort=False):
        if group.empty:
            continue

        if group["effective_collected_at"].notna().any():
            latest_timestamp = group["effective_collected_at"].max()
            latest_group = group.loc[group["effective_collected_at"].eq(latest_timestamp)].copy()
        else:
            latest_group = group.sort_values("row_order").tail(1).copy()

        row_data = {
            "nt_source": latest_group.iloc[0]["nt_source"],
            "nt_detail": latest_group.iloc[0]["nt_detail"],
            "nt_keyword": latest_group.iloc[0]["nt_keyword"],
            "perf_debug_rows": " | ".join(
                latest_group.apply(
                    lambda row: (
                        f"{row.get('nt_source', '')}/{row.get('nt_detail', '')}/{row.get('nt_keyword', '')}"
                    ),
                    axis=1,
                ).tolist()
            ),
            "perf_latest_collected_at": (
                latest_timestamp.strftime("%Y-%m-%d")
                if pd.notna(latest_group.iloc[0]["effective_collected_at"])
                else ""
            ),
        }

        for metric in LATEST_SNAPSHOT_METRICS:
            row_data[metric] = to_numeric_series(latest_group[metric]).fillna(0).sum()

        for metric in MAX_VALUE_METRICS:
            row_data[metric] = to_numeric_series(latest_group[metric]).fillna(0).sum()

        collapsed_rows.append(row_data)

    return pd.DataFrame(collapsed_rows)


def performance_metric_aliases(metric: str) -> list[str]:
    aliases = {
        "customer_count": ["고객수", "고객", "customer_count", "customercount"],
        "inflow_count": ["유입수", "유입", "inflow_count", "inflowcount"],
        "page_count": ["페이지수", "클릭수", "page_count", "pagecount", "페이지", "클릭"],
        "payment_count": ["결제수", "결제건수", "payment_count", "paymentcount"],
        "payment_amount": ["결제금액", "결제액", "payment_amount", "paymentamount", "매출"],
        "payment_count_attributed": ["기여결제수", "결제수기여", "payment_count_attributed"],
        "payment_amount_attributed": ["기여결제금액", "결제금액기여", "payment_amount_attributed"],
    }
    return aliases[metric]


def sanitize_column_name(value: object) -> str:
    text = unicodedata.normalize("NFKC", clean_text(value)).lower()
    text = re.sub(r"[\s\-_()/\[\]]+", "", text)
    return text


def clean_transfer_status(value: object) -> str:
    text = clean_text(value).lower()
    if text in {"o", "y", "yes", "완료"}:
        return "완료"
    if text in {"x", "n", "no", "미이체"}:
        return "미이체"
    return "미기재"


def clean_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "nat", "none"}:
        return ""
    return text


def normalize_match_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", clean_text(value)).lower()
    return re.sub(r"\s+", "", text)


def normalize_nt_source(value: object) -> str:
    text = normalize_match_text(value)
    aliases = {
        "blog": "naverblog",
        "블로그": "naverblog",
        "naverblog": "naverblog",
        "naver": "naver",
        "인스타": "instagram",
        "인스타그램": "instagram",
        "instagram": "instagram",
        "insta": "instagram",
        "유튜브": "youtube",
        "youtube": "youtube",
        "x": "x",
        "twitter": "x",
        "커뮤니티": "community",
        "community": "community",
        "브랜드커넥트": "nshoplive",
        "nshoplive": "nshoplive",
        "toss": "toss",
        "cafe": "cafe",
        "카페": "cafe",
    }
    return aliases.get(text, text)


def normalize_product_token(value: object) -> str:
    text = normalize_match_text(value)
    return re.sub(r"[^a-z0-9가-힣]", "", text)


def extract_date_from_keyword(value: object) -> pd.Timestamp | None:
    text = clean_text(value)
    match = re.match(r"^(\d{8}|\d{6})", text)
    if not match:
        return None

    token = match.group(1)
    if len(token) == 8:
        parsed = pd.to_datetime(token, format="%Y%m%d", errors="coerce")
    else:
        parsed = pd.to_datetime(token, format="%y%m%d", errors="coerce")

    if pd.isna(parsed):
        return None
    return parsed.normalize()


def to_datetime_series(series: pd.Series | pd.DataFrame | None) -> pd.Series:
    if series is None:
        return pd.Series(dtype="datetime64[ns]")
    return parse_flexible_date_series(ensure_series(series))


def to_numeric_series(series: pd.Series | pd.DataFrame | None) -> pd.Series:
    if series is None:
        return pd.Series(dtype="float64")

    series = ensure_series(series)
    text = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("₩", "", regex=False)
        .str.replace("￦", "", regex=False)
        .str.replace("원", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
        .str.replace(r"[^\d\.\-]", "", regex=True)
    )
    return pd.to_numeric(text, errors="coerce")


def get_series_by_alias(df: pd.DataFrame, aliases: list[str]) -> pd.Series:
    if df.empty:
        return pd.Series(dtype="object")

    normalized_aliases = {sanitize_column_name(alias) for alias in aliases}
    for column in df.columns:
        if sanitize_column_name(column) in normalized_aliases:
            return ensure_series(df[column])
    return pd.Series([""] * len(df), index=df.index, dtype="object")


def get_link_series(df: pd.DataFrame) -> pd.Series:
    candidates = ["링크", "url", "주소", "게시링크", "콘텐츠링크"]
    series = get_series_by_alias(df, candidates)
    if series.map(clean_text).ne("").any():
        return series

    for column in df.columns:
        if clean_text(column).endswith("링크"):
            return ensure_series(df[column])
    return pd.Series([""] * len(df), index=df.index, dtype="object")


def first_non_empty_series(*series_list: pd.Series | pd.DataFrame | None) -> pd.Series:
    prepared: list[pd.Series] = []
    for series in series_list:
        if series is not None:
            prepared.append(ensure_series(series))

    if not prepared:
        return pd.Series(dtype="object")

    result = prepared[0].copy()
    for candidate in prepared[1:]:
        mask = result.map(clean_text).eq("")
        result.loc[mask] = candidate.loc[mask]
    return result


def parse_flexible_date_series(series: pd.Series | pd.DataFrame) -> pd.Series:
    series = ensure_series(series)
    text = (
        series.astype(str)
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA, "NaT": pd.NA, "None": pd.NA})
    )
    normalized = (
        text.str.replace(r"\s+", "", regex=True)
        .str.replace(".", "-", regex=False)
        .str.replace("/", "-", regex=False)
    )

    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    for date_format in ["%Y-%m-%d", "%y-%m-%d", "%Y%m%d", "%y%m%d"]:
        mask = parsed.isna() & normalized.notna()
        if not mask.any():
            break
        parsed.loc[mask] = pd.to_datetime(normalized.loc[mask], format=date_format, errors="coerce")

    remaining = parsed.isna() & normalized.notna()
    if remaining.any():
        parsed.loc[remaining] = pd.to_datetime(normalized.loc[remaining], errors="coerce")

    return parsed


def ensure_series(value: pd.Series | pd.DataFrame) -> pd.Series:
    if isinstance(value, pd.DataFrame):
        if value.shape[1] == 0:
            return pd.Series([""] * len(value), index=value.index, dtype="object")
        return value.iloc[:, 0]
    return value
