# django_ma/commission/views.py

import os
import io
import datetime
import pandas as pd

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html.parser import HTMLParser

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.db import transaction
from django.db.models import Q, Sum
from django.core.files.storage import FileSystemStorage
from django.utils import timezone

from accounts.decorators import grade_required
from accounts.models import CustomUser

from .models import DepositSummary, DepositUploadLog, DepositSurety, DepositOther


# =========================================================
# Constants
# =========================================================
UPLOAD_CATEGORIES = [
    "최종지급액", "환수지급예상", "보증증액", "보증보험", "기타채권", "통산생보", "통산손보", "응당생보", "응당손보"]

SUPPORTED_UPLOAD_TYPES = {"최종지급액", "보증증액", "응당생보", "응당손보", "보증보험", "기타채권", "통산손보", '통산생보'}

# 통산손보(소수) 저장 시 기본 소수자리 (프론트 toFixed(2) 기준)
DEC2 = Decimal("0.00")


# =========================================================
# JSON helpers
# =========================================================
def _fmt_date(d):
    return d.strftime("%Y-%m-%d") if d else "-"


def _json_error(message, status=400, **extra):
    payload = {"ok": False, "message": message}
    payload.update(extra)
    return JsonResponse(payload, status=status)


def _json_ok(message=None, **extra):
    payload = {"ok": True}
    if message is not None:
        payload["message"] = message
    payload.update(extra)
    return JsonResponse(payload)


# =========================================================
# Value converters
# =========================================================
def _to_int(v, default=0):
    try:
        if v is None:
            return default
        s = str(v).strip().replace(",", "")
        if s.lower() in ("", "nan", "none", "-"):
            return default
        return int(float(s))
    except Exception:
        return default


def _to_decimal(v, default=Decimal("0.00")):
    try:
        if v is None:
            return default
        s = str(v).strip().replace(",", "")
        if s.lower() in ("", "nan", "none", "-"):
            return default
        return Decimal(s)
    except (InvalidOperation, Exception):
        return default


def _to_decimal_q2(v, default=DEC2):
    """
    Decimal 변환 + 소수 2자리 반올림(ROUND_HALF_UP)
    """
    try:
        d = _to_decimal(v, default=default)
        if d is None:
            return default
        return d.quantize(DEC2, rounding=ROUND_HALF_UP)
    except Exception:
        return default


def _to_date(v):
    """엑셀 날짜(날짜/문자/NaN) -> date or None"""
    try:
        if v is None:
            return None
        if isinstance(v, pd.Timestamp):
            return v.date()
        if hasattr(v, "date") and callable(v.date):
            return v.date()
        s = str(v).strip()
        if not s or s.lower() in ("nan", "none", "-"):
            return None
        s = s.replace(".", "-").replace("/", "-")
        return pd.to_datetime(s, errors="coerce").date()
    except Exception:
        return None


def _to_div(v, default=""):
    s = ("" if v is None else str(v)).strip()
    if not s or s.lower() in ("nan", "none"):
        return default
    if "분급" in s:
        return "분급"
    if "정상" in s:
        return "정상"
    return default


def _norm_emp_id(v):
    if v is None:
        return ""
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none"):
        return ""
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _safe_decimal_q2(v, default=DEC2):
    """
    raw matrix(통산손보)에서 셀 값을 Decimal(2자리)로 안전 변환
    - 숫자/문자/NaN/공백/콤마 모두 처리
    """
    try:
        if v is None:
            return default
        if hasattr(pd, "isna") and pd.isna(v):
            return default
        s = str(v).strip().replace(",", "")
        if s.lower() in ("", "nan", "none", "-"):
            return default
        return Decimal(s).quantize(DEC2, rounding=ROUND_HALF_UP)
    except Exception:
        return default


# =========================================================
# Column detector
# =========================================================
def _detect_col(df, must_include=(), any_include=()):
    cols = list(df.columns)
    for c in cols:
        name = str(c).replace(" ", "")
        low = name.lower()
        ok_must = all(str(k).replace(" ", "").lower() in low for k in must_include)
        ok_any = (not any_include) or any(str(k).replace(" ", "").lower() in low for k in any_include)
        if ok_must and ok_any:
            return c
    return None


def _find_exact_or_space_removed(df: pd.DataFrame, excel_col: str):
    for c in df.columns:
        if str(c).strip() == excel_col:
            return c
    key = excel_col.replace(" ", "")
    for c in df.columns:
        if str(c).replace(" ", "") == key:
            return c
    return None


def _bulk_existing_user_ids(user_ids):
    return set(CustomUser.objects.filter(pk__in=user_ids).values_list("pk", flat=True))


def _update_upload_log(part, upload_type, excel_file_name, count):
    now = timezone.now()
    DepositUploadLog.objects.update_or_create(
        part=part,
        upload_type=upload_type,
        defaults={
            "row_count": count,
            "file_name": excel_file_name,
            "uploaded_at": now,
        },
    )
    return _fmt_date(now)


# =========================================================
# 통산손보 사번 추출
# =========================================================
def _extract_emp7_from_a(raw):
    """
    A열: 오른쪽 8번째~오른쪽 2번째(7자리)
    emp7 = s[-8:-1]
    """
    s = "" if raw is None else str(raw).strip()
    if len(s) < 8:
        return ""
    emp7 = s[-8:-1]
    return emp7 if emp7.isdigit() and len(emp7) == 7 else ""


# =========================================================
# Excel / Text reader
# =========================================================
def _sniff_is_html(file_path: str) -> bool:
    try:
        with open(file_path, "rb") as f:
            head = f.read(512)
    except Exception:
        return False
    head_l = head.lstrip().lower()
    return head_l.startswith(b"<html") or head_l.startswith(b"<!doctype") or head_l.startswith(b"<table")


def _decode_bytes_best_effort(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="replace")


def _parse_first_html_table(file_path: str) -> pd.DataFrame:
    """
    lxml 없이(표준 라이브러리만) HTML <table>을 DataFrame으로 파싱.
    - 첫 번째 table만 사용
    - 첫 번째 row를 header로 간주(빈약하면 다음 row)
    """
    raw = open(file_path, "rb").read()
    text = _decode_bytes_best_effort(raw)

    class TableParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.in_table = False
            self.in_tr = False
            self.in_cell = False
            self.table_found = False
            self.rows = []
            self.cur_row = []
            self.cur_cell = []

        def handle_starttag(self, tag, attrs):
            tag = tag.lower()
            if tag == "table" and not self.table_found:
                self.in_table = True
                self.table_found = True
            elif self.in_table and tag == "tr":
                self.in_tr = True
                self.cur_row = []
            elif self.in_table and self.in_tr and tag in ("td", "th"):
                self.in_cell = True
                self.cur_cell = []

        def handle_endtag(self, tag):
            tag = tag.lower()
            if tag == "table" and self.in_table:
                self.in_table = False
            elif tag == "tr" and self.in_tr:
                self.in_tr = False
                if any(c.strip() for c in self.cur_row):
                    self.rows.append(self.cur_row)
            elif tag in ("td", "th") and self.in_cell:
                self.in_cell = False
                cell_text = "".join(self.cur_cell).strip()
                cell_text = " ".join(cell_text.split())
                self.cur_row.append(cell_text)

        def handle_data(self, data):
            if self.in_cell and data:
                self.cur_cell.append(data)

    p = TableParser()
    p.feed(text)

    if not p.rows:
        raise ValueError("HTML 테이블을 찾지 못했습니다. (table/tr/td 없음)")

    header = p.rows[0]
    data_rows = p.rows[1:]

    def _looks_like_header(r):
        if not r:
            return False
        joined = "".join(r)
        return any(("사원" in c or "번호" in c or "성명" in c) for c in r) or any(ch.isalpha() for ch in joined)

    if not _looks_like_header(header) and len(p.rows) >= 2:
        header = p.rows[1]
        data_rows = p.rows[2:]

    max_len = max(len(header), *(len(r) for r in data_rows)) if data_rows else len(header)
    header = (header + [""] * max_len)[:max_len]
    norm_rows = [(r + [""] * max_len)[:max_len] for r in data_rows]

    df = pd.DataFrame(norm_rows, columns=[str(c).strip() for c in header])

    # duplicate column name safe
    new_cols, used = [], {}
    for i, c in enumerate(df.columns):
        name = (c or "").strip() or f"COL_{i+1}"
        if name in used:
            used[name] += 1
            name = f"{name}_{used[name]}"
        else:
            used[name] = 1
        new_cols.append(name)
    df.columns = new_cols
    return df


def _read_text_table(file_path: str) -> pd.DataFrame:
    """
    .xls 확장자지만 실제는 TSV/CSV(텍스트)인 케이스 대응 (헤더 포함)
    - 탭/콤마/세미콜론 자동 추정
    - 인코딩: utf-8 계열 우선, 실패 시 cp949/euc-kr
    """
    raw = open(file_path, "rb").read()
    text = _decode_bytes_best_effort(raw)

    head = text[:5000]
    tab_cnt = head.count("\t")
    comma_cnt = head.count(",")
    semi_cnt = head.count(";")

    if tab_cnt >= max(comma_cnt, semi_cnt) and tab_cnt > 0:
        sep = "\t"
    elif comma_cnt >= semi_cnt and comma_cnt > 0:
        sep = ","
    elif semi_cnt > 0:
        sep = ";"
    else:
        sep = None

    buf = io.StringIO(text)
    try:
        if sep is None:
            return pd.read_csv(buf, engine="python")
        return pd.read_csv(buf, sep=sep, engine="python")
    except Exception:
        return pd.DataFrame({"COL_1": [line for line in text.splitlines() if line.strip()]})


def _read_text_table_matrix(file_path: str, skiprows: int = 0) -> pd.DataFrame:
    """
    .xls 확장자지만 실제는 TSV/CSV(텍스트)인 케이스를 raw matrix로 읽기
    - header=None
    - skiprows 적용
    """
    raw = open(file_path, "rb").read()
    text = _decode_bytes_best_effort(raw)

    head = text[:5000]
    tab_cnt = head.count("\t")
    comma_cnt = head.count(",")
    semi_cnt = head.count(";")

    if tab_cnt >= max(comma_cnt, semi_cnt) and tab_cnt > 0:
        sep = "\t"
    elif comma_cnt >= semi_cnt and comma_cnt > 0:
        sep = ","
    elif semi_cnt > 0:
        sep = ";"
    else:
        sep = None

    buf = io.StringIO(text)
    if sep is None:
        return pd.read_csv(buf, engine="python", header=None, skiprows=skiprows)
    return pd.read_csv(buf, sep=sep, engine="python", header=None, skiprows=skiprows)


def _read_excel_safely(file_path: str, original_name: str = "") -> pd.DataFrame:
    """
    ✅ 스니핑 기반(헤더 포함 df용)
    - HTML disguised: 표준 파서
    - XLSX(zip): openpyxl
    - XLS(OLE2): xlrd
    - 그 외(.xls 텍스트 등): read_csv fallback
    """
    ext = os.path.splitext((original_name or file_path))[1].lower()

    head = b""
    try:
        with open(file_path, "rb") as f:
            head = f.read(4096)
    except Exception:
        head = b""

    head_l = head.lstrip().lower()
    if head_l.startswith(b"<html") or head_l.startswith(b"<!doctype") or head_l.startswith(b"<table"):
        return _parse_first_html_table(file_path)

    is_zip = head.startswith(b"PK\x03\x04")  # xlsx
    is_ole2 = head.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1")  # xls

    # xlsx 계열 우선
    if is_zip or ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        return pd.read_excel(file_path, header=0, engine="openpyxl")

    # 진짜 xls(OLE2)만 xlrd
    if is_ole2:
        try:
            import xlrd  # noqa: F401
        except Exception:
            raise ValueError(
                "업로드 실패: 현재 서버에 .xls 처리 모듈(xlrd)이 없습니다.\n"
                "엑셀에서 '다른 이름으로 저장' → .xlsx로 저장 후 업로드해주세요."
            )
        return pd.read_excel(file_path, header=0, engine="xlrd")

    # .xls인데 OLE2가 아니면 대부분 텍스트
    if ext == ".xls":
        return _read_text_table(file_path)

    # 그 외는 텍스트로
    return _read_text_table(file_path)


def _read_excel_raw_matrix(file_path: str, original_name: str, skiprows: int, header_none: bool = True) -> pd.DataFrame:
    """
    ✅ 통산손보 전용 raw matrix reader (열 위치 기반)
    - HTML disguised: 표준 파서 → values로 변환 후 skiprows
    - XLSX(zip): openpyxl
    - XLS(OLE2): xlrd
    - 그 외(.xls 텍스트 등): TSV/CSV raw matrix fallback
    """
    ext = os.path.splitext((original_name or file_path))[1].lower()

    if _sniff_is_html(file_path):
        df_html = _parse_first_html_table(file_path)
        values = df_html.to_numpy().tolist()
        values = values[skiprows:] if skiprows else values
        return pd.DataFrame(values)

    head = b""
    try:
        with open(file_path, "rb") as f:
            head = f.read(4096)
    except Exception:
        head = b""

    is_zip = head.startswith(b"PK\x03\x04")
    is_ole2 = head.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1")

    if is_zip or ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        return pd.read_excel(
            file_path,
            header=None if header_none else 0,
            skiprows=skiprows,
            engine="openpyxl",
        )

    if is_ole2:
        try:
            import xlrd  # noqa: F401
        except Exception:
            raise ValueError(
                "업로드 실패: 현재 서버에 .xls 처리 모듈(xlrd)이 없습니다.\n"
                "엑셀에서 '다른 이름으로 저장' → .xlsx로 저장 후 업로드해주세요."
            )
        return pd.read_excel(
            file_path,
            header=None if header_none else 0,
            skiprows=skiprows,
            engine="xlrd",
        )

    # .xls지만 OLE2가 아니면(가짜 xls) 텍스트로 처리
    if ext == ".xls":
        return _read_text_table_matrix(file_path, skiprows=skiprows)

    return _read_text_table_matrix(file_path, skiprows=skiprows)


# =========================================================
# Upload handlers
# =========================================================
def _handle_upload_final_payment(df: pd.DataFrame):
    col_user = _detect_col(df, must_include=("사번",), any_include=())
    col_payment = _detect_col(df, must_include=("최종", "지급"), any_include=())
    if not col_user or not col_payment:
        raise ValueError("엑셀 컬럼을 찾지 못했습니다. (필수: 사번, 최종지급액)")

    df2 = df[[col_user, col_payment]].copy()
    df2.columns = ["user_id", "final_payment"]

    df2["user_id"] = df2["user_id"].apply(_norm_emp_id)
    df2 = df2[df2["user_id"].astype(str).str.len() > 0].copy()
    df2["final_payment"] = df2["final_payment"].apply(_to_int)

    ids = df2["user_id"].tolist()
    existing_ids = _bulk_existing_user_ids(ids)
    missing_sample = [x for x in ids if x not in existing_ids][:10]

    updated = 0
    missing_users = 0

    for _, r in df2.iterrows():
        uid = r["user_id"]
        if uid not in existing_ids:
            missing_users += 1
            continue
        DepositSummary.objects.update_or_create(
            user_id=uid,
            defaults={"final_payment": int(r["final_payment"])},
        )
        updated += 1

    return {
        "updated": updated,
        "missing_users": missing_users,
        "existing_users": len(existing_ids),
        "missing_sample": missing_sample,
    }


def _handle_upload_guarantee_increase(df: pd.DataFrame):
    col_user = (
        _detect_col(df, must_include=("사원", "코드"), any_include=())
        or _detect_col(df, must_include=("사번",), any_include=())
    )
    if not col_user:
        raise ValueError("엑셀 컬럼을 찾지 못했습니다. (필수: 사원코드/사번)")

    col_map = {
        "3개월 장기 총수수료(지급월+직전2개월)": "comm_3m",
        "6개월 장기 총수수료(지급월+직전5개월)": "comm_6m",
        "9개월 장기 총수수료(지급월+직전8개월)": "comm_9m",
        "12개월 장기 총수수료(지급월+직전11개월)": "comm_12m",
        "당월 계속분 인정": "inst_current",
        "전월 계속분 인정": "inst_prev",
        "장기 총실적": "sales_total",
        "손생보 합산 통산유지율": "maint_total",
        "보증/채권 합계": "debt_total",
        "1개월전 분급여부": "div_1m",
        "2개월전 분급여부": "div_2m",
        "3개월전 분급여부": "div_3m",
        "최종 초과금액": "final_excess_amount",
    }

    detected = {}
    for excel_col in col_map.keys():
        found = _find_exact_or_space_removed(df, excel_col)
        if found is None:
            raise ValueError(f"엑셀 컬럼을 찾지 못했습니다: [{excel_col}]")
        detected[excel_col] = found

    use_cols = [col_user] + [detected[k] for k in col_map.keys()]
    df2 = df[use_cols].copy()

    rename_map = {col_user: "user_id"}
    for excel_col, model_field in col_map.items():
        rename_map[detected[excel_col]] = model_field
    df2.rename(columns=rename_map, inplace=True)

    df2["user_id"] = df2["user_id"].apply(_norm_emp_id)
    df2 = df2[df2["user_id"].astype(str).str.len() > 0].copy()

    INT_FIELDS = {
        "comm_3m", "comm_6m", "comm_9m", "comm_12m",
        "inst_current", "inst_prev",
        "sales_total", "debt_total",
        "final_excess_amount",
    }
    DIV_FIELDS = {"div_1m", "div_2m", "div_3m"}
    DEC_FIELDS = {"maint_total"}

    for f in INT_FIELDS:
        if f in df2.columns:
            df2[f] = df2[f].apply(_to_int)

    for f in DIV_FIELDS:
        if f in df2.columns:
            df2[f] = df2[f].apply(_to_div)

    for f in DEC_FIELDS:
        if f in df2.columns:
            df2[f] = df2[f].apply(_to_decimal)

    ids = df2["user_id"].tolist()
    existing_ids = _bulk_existing_user_ids(ids)
    missing_sample = [x for x in ids if x not in existing_ids][:10]

    updated = 0
    missing_users = 0

    for _, r in df2.iterrows():
        uid = r["user_id"]
        if uid not in existing_ids:
            missing_users += 1
            continue

        defaults = {
            "comm_3m": int(r.get("comm_3m", 0)),
            "comm_6m": int(r.get("comm_6m", 0)),
            "comm_9m": int(r.get("comm_9m", 0)),
            "comm_12m": int(r.get("comm_12m", 0)),
            "inst_current": int(r.get("inst_current", 0)),
            "inst_prev": int(r.get("inst_prev", 0)),
            "sales_total": int(r.get("sales_total", 0)),
            "debt_total": int(r.get("debt_total", 0)),
            "final_excess_amount": int(r.get("final_excess_amount", 0)),
            "div_1m": (r.get("div_1m") or ""),
            "div_2m": (r.get("div_2m") or ""),
            "div_3m": (r.get("div_3m") or ""),
            "maint_total": (r.get("maint_total") if r.get("maint_total") is not None else Decimal("0.00")),
        }

        DepositSummary.objects.update_or_create(user_id=uid, defaults=defaults)
        updated += 1

    return {
        "updated": updated,
        "missing_users": missing_users,
        "existing_users": len(existing_ids),
        "missing_sample": missing_sample,
    }


def _handle_upload_ls_due(df: pd.DataFrame):
    col_user = _detect_col(df, must_include=("사원", "코드"), any_include=())
    col_2_6 = _detect_col(df, must_include=("2~6", "합산"), any_include=())
    col_2_13 = _detect_col(df, must_include=("2~13", "합산"), any_include=())

    if not col_user or not col_2_6 or not col_2_13:
        raise ValueError("엑셀 컬럼을 찾지 못했습니다. (필수: 사원코드, 합산(2~6회차), 합산(2~13회차))")

    df2 = df[[col_user, col_2_6, col_2_13]].copy()
    df2.columns = ["user_id", "ls_2_6_due", "ls_2_13_due"]

    df2["user_id"] = df2["user_id"].apply(_norm_emp_id)
    df2 = df2[df2["user_id"].str.len() > 0].copy()

    df2["ls_2_6_due"] = df2["ls_2_6_due"].apply(_to_decimal)
    df2["ls_2_13_due"] = df2["ls_2_13_due"].apply(_to_decimal)

    ids = df2["user_id"].tolist()
    existing_ids = _bulk_existing_user_ids(ids)
    missing_sample = [x for x in ids if x not in existing_ids][:10]

    updated = 0
    missing_users = 0

    for _, r in df2.iterrows():
        uid = r["user_id"]
        if uid not in existing_ids:
            missing_users += 1
            continue

        DepositSummary.objects.update_or_create(
            user_id=uid,
            defaults={
                "ls_2_6_due": r["ls_2_6_due"],
                "ls_2_13_due": r["ls_2_13_due"],
            },
        )
        updated += 1

    return {
        "updated": updated,
        "missing_users": missing_users,
        "existing_users": len(existing_ids),
        "missing_sample": missing_sample,
    }


def _handle_upload_ns_due(df: pd.DataFrame):
    col_user = _detect_col(df, must_include=("사원", "코드"), any_include=())
    col_2_6 = _detect_col(df, must_include=("2~6", "합산"), any_include=())
    col_2_13 = _detect_col(df, must_include=("2~13", "합산"), any_include=())

    if not col_user or not col_2_6 or not col_2_13:
        raise ValueError("엑셀 컬럼을 찾지 못했습니다. (필수: 사원코드, 합산(2~6회차), 합산(2~13회차))")

    df2 = df[[col_user, col_2_6, col_2_13]].copy()
    df2.columns = ["user_id", "ns_2_6_due", "ns_2_13_due"]

    df2["user_id"] = df2["user_id"].apply(_norm_emp_id)
    df2 = df2[df2["user_id"].str.len() > 0].copy()

    df2["ns_2_6_due"] = df2["ns_2_6_due"].apply(_to_decimal)
    df2["ns_2_13_due"] = df2["ns_2_13_due"].apply(_to_decimal)

    ids = df2["user_id"].tolist()
    existing_ids = _bulk_existing_user_ids(ids)
    missing_sample = [x for x in ids if x not in existing_ids][:10]

    updated = 0
    missing_users = 0

    for _, r in df2.iterrows():
        uid = r["user_id"]
        if uid not in existing_ids:
            missing_users += 1
            continue

        DepositSummary.objects.update_or_create(
            user_id=uid,
            defaults={
                "ns_2_6_due": r["ns_2_6_due"],
                "ns_2_13_due": r["ns_2_13_due"],
            },
        )
        updated += 1

    return {
        "updated": updated,
        "missing_users": missing_users,
        "existing_users": len(existing_ids),
        "missing_sample": missing_sample,
    }


def _handle_upload_surety(df: pd.DataFrame):
    col_user = (
        _detect_col(df, must_include=("사원", "코드"), any_include=())
        or _detect_col(df, must_include=("사원", "번호"), any_include=())
        or _detect_col(df, must_include=("사원번호",), any_include=())
        or _detect_col(df, must_include=("사번",), any_include=())
    )
    if not col_user:
        raise ValueError("엑셀 컬럼을 찾지 못했습니다. (필수: 사원코드/사번)")

    required = {
        "보증기호명": "product_name",
        "증권번호": "policy_no",
        "가입금액": "amount",
        "상태": "status",
        "보험시작일": "start_date",
        "보험종료일": "end_date",
    }

    detected = {}
    for excel_col in required.keys():
        found = _find_exact_or_space_removed(df, excel_col)
        if found is None:
            raise ValueError(f"엑셀 컬럼을 찾지 못했습니다: [{excel_col}]")
        detected[excel_col] = found

    use_cols = [col_user] + [detected[k] for k in required.keys()]
    df2 = df[use_cols].copy()

    rename_map = {col_user: "user_id"}
    for excel_col, model_field in required.items():
        rename_map[detected[excel_col]] = model_field
    df2.rename(columns=rename_map, inplace=True)

    df2["user_id"] = df2["user_id"].apply(_norm_emp_id)
    df2 = df2[df2["user_id"].astype(str).str.len() > 0].copy()

    df2["product_name"] = df2["product_name"].fillna("").astype(str).str.strip()
    df2["policy_no"] = df2["policy_no"].fillna("").astype(str).str.strip()
    df2["status"] = df2["status"].fillna("").astype(str).str.strip()
    df2["amount"] = df2["amount"].apply(_to_int)
    df2["start_date"] = df2["start_date"].apply(_to_date)
    df2["end_date"] = df2["end_date"].apply(_to_date)

    ids = df2["user_id"].tolist()
    existing_ids = _bulk_existing_user_ids(ids)
    missing_sample = [x for x in ids if x not in existing_ids][:10]

    valid_df = df2[df2["user_id"].isin(existing_ids)].copy()

    target_ids = valid_df["user_id"].unique().tolist()
    DepositSurety.objects.filter(user_id__in=target_ids).delete()

    objs = []
    for _, r in valid_df.iterrows():
        objs.append(
            DepositSurety(
                user_id=r["user_id"],
                product_name=r["product_name"] or "",
                policy_no=r["policy_no"] or "",
                amount=int(r["amount"] or 0),
                status=r["status"] or "",
                start_date=r["start_date"],
                end_date=r["end_date"],
            )
        )
    DepositSurety.objects.bulk_create(objs, batch_size=1000)

    return {
        "updated": len(objs),
        "missing_users": (len(ids) - len(valid_df)),
        "existing_users": len(existing_ids),
        "missing_sample": missing_sample,
    }


def _handle_upload_other_debt(df: pd.DataFrame):
    # 첫 행이 "헤더가 데이터로 들어온" 케이스만 제거
    if len(df) > 0:
        first_row_text = " ".join([str(x) for x in df.iloc[0].tolist()])
        if ("사번" in first_row_text) and ("상품명" in first_row_text):
            df = df.iloc[1:].copy()

    col_user = (
        _detect_col(df, must_include=("사번",), any_include=())
        or _detect_col(df, must_include=("사원", "번호"), any_include=())
        or _detect_col(df, must_include=("사원번호",), any_include=())
    )
    if not col_user:
        raise ValueError("엑셀 컬럼을 찾지 못했습니다. (필수: 사번)")

    col_map = {
        "번호": "bond_no",
        "상품명": "product_name",
        "보증내용": "product_type",
        "가입금액": "amount",
        "상태": "status",
        "계약일": "start_date",
        "비고": "memo",
    }

    detected = {}
    for k in col_map:
        c = _find_exact_or_space_removed(df, k)
        if not c and k == "계약일":
            c = _find_exact_or_space_removed(df, "보험시작일")
        if not c:
            raise ValueError(f"엑셀 컬럼을 찾지 못했습니다: {k}")
        detected[k] = c

    use_cols = [col_user] + list(detected.values())
    df = df[use_cols].copy()

    rename_map = {col_user: "user_id"}
    for excel_col, model_field in col_map.items():
        rename_map[detected[excel_col]] = model_field
    df.rename(columns=rename_map, inplace=True)

    df["user_id"] = df["user_id"].apply(_norm_emp_id)
    df = df[df["user_id"].astype(str).str.len() > 0].copy()

    df["bond_no"] = df["bond_no"].fillna("").astype(str).str.strip()
    df["product_name"] = df["product_name"].fillna("").astype(str)
    df["product_type"] = df["product_type"].fillna("").astype(str)
    df["status"] = df["status"].fillna("").astype(str)
    df["memo"] = df["memo"].fillna("").astype(str)

    df["amount"] = df["amount"].apply(_to_int)
    df["start_date"] = df["start_date"].apply(_to_date)

    all_ids = df["user_id"].tolist()
    existing_ids = set(_bulk_existing_user_ids(all_ids))
    missing_ids = sorted(set(all_ids) - existing_ids)

    valid_df = df[df["user_id"].isin(existing_ids)].copy()

    DepositOther.objects.filter(user_id__in=valid_df["user_id"].unique()).delete()

    objs = [
        DepositOther(
            user_id=r.user_id,
            product_name=r.product_name,
            product_type=r.product_type,
            amount=r.amount,
            bond_no=r.bond_no or "",
            status=r.status,
            start_date=r.start_date,
            memo=r.memo,
        )
        for r in valid_df.itertuples()
    ]
    DepositOther.objects.bulk_create(objs, batch_size=1000)

    return {
        "updated": len(objs),
        "missing_users": len(missing_ids),
        "existing_users": len(existing_ids),
        "missing_sample": missing_ids[:10],
    }


def _handle_upload_ns_total_from_file(file_path: str, original_name: str):
    """
    ✅ 통산손보 업로드 (소수 지원)
    - 1~5행 drop (skiprows=5)
    - header 없음 (header=None)
    - A열: 오른쪽 8~2번째(7자리) 사번
    - K(10)  -> ns_13_round   (Decimal, 2자리)
    - P(15)  -> ns_18_round   (Decimal, 2자리)
    - AT(45) -> ns_18_total   (Decimal, 2자리)
    - AY(50) -> ns_25_total   (Decimal, 2자리)
    - 동일 사번: DepositSummary 해당 4개 필드만 갱신
    """
    df = _read_excel_raw_matrix(file_path, original_name=original_name, skiprows=5, header_none=True)

    IDX_A = 0
    IDX_K = 10
    IDX_P = 15
    IDX_AT = 45
    IDX_AY = 50

    # 1) 1차 파싱(사번/값 추출) → DB hit 최소화(존재여부 bulk)
    rows = []
    emp_ids = []

    for _, row in df.iterrows():
        raw_a = row[IDX_A] if len(row) > IDX_A else None
        emp7 = _extract_emp7_from_a(raw_a)
        if not emp7:
            continue

        v13 = _safe_decimal_q2(row[IDX_K]) if len(row) > IDX_K else DEC2
        v18 = _safe_decimal_q2(row[IDX_P]) if len(row) > IDX_P else DEC2
        t18 = _safe_decimal_q2(row[IDX_AT]) if len(row) > IDX_AT else DEC2
        t25 = _safe_decimal_q2(row[IDX_AY]) if len(row) > IDX_AY else DEC2

        emp_ids.append(emp7)
        rows.append((emp7, v13, v18, t18, t25))

    if not rows:
        return {"updated": 0, "missing_users": 0, "existing_users": 0, "missing_sample": []}

    existing_ids = _bulk_existing_user_ids(list(set(emp_ids)))

    updated = 0
    skipped = 0

    for emp7, v13, v18, t18, t25 in rows:
        if emp7 not in existing_ids:
            skipped += 1
            continue

        summary, _ = DepositSummary.objects.get_or_create(user_id=emp7)
        summary.ns_13_round = v13
        summary.ns_18_round = v18
        summary.ns_18_total = t18
        summary.ns_25_total = t25
        summary.save(update_fields=["ns_13_round", "ns_18_round", "ns_18_total", "ns_25_total"])
        updated += 1

    return {
        "updated": updated,
        "missing_users": skipped,  # 통산손보는 매칭 실패/파싱 실패를 skipped로 반환
        "existing_users": updated,
        "missing_sample": [],
    }

def _handle_upload_ls_total_from_file(file_path: str, original_name: str):
    """
    ✅ 통산생보 업로드 (통산손보와 동일한 방식)
    - 기존 DepositSummary 유지
    - ls_* 필드만 갱신
    """
    df = _read_excel_raw_matrix(file_path, original_name=original_name, skiprows=5, header_none=True)

    IDX_A = 0
    IDX_K = 10
    IDX_P = 15
    IDX_AT = 45
    IDX_AY = 50

    rows = []
    emp_ids = []

    for _, row in df.iterrows():
        raw_a = row[IDX_A] if len(row) > IDX_A else None
        emp7 = _extract_emp7_from_a(raw_a)
        if not emp7:
            continue

        rows.append((
            emp7,
            _safe_decimal_q2(row[IDX_K]) if len(row) > IDX_K else DEC2,
            _safe_decimal_q2(row[IDX_P]) if len(row) > IDX_P else DEC2,
            _safe_decimal_q2(row[IDX_AT]) if len(row) > IDX_AT else DEC2,
            _safe_decimal_q2(row[IDX_AY]) if len(row) > IDX_AY else DEC2,
        ))
        emp_ids.append(emp7)

    if not rows:
        return {"updated": 0, "missing_users": 0, "existing_users": 0, "missing_sample": []}

    existing_ids = _bulk_existing_user_ids(set(emp_ids))

    updated = 0
    skipped = 0

    for emp7, v13, v18, t18, t25 in rows:
        if emp7 not in existing_ids:
            skipped += 1
            continue

        summary, _ = DepositSummary.objects.get_or_create(user_id=emp7)
        summary.ls_13_round = v13
        summary.ls_18_round = v18
        summary.ls_18_total = t18
        summary.ls_25_total = t25
        summary.save(update_fields=[
            "ls_13_round",
            "ls_18_round",
            "ls_18_total",
            "ls_25_total",
        ])
        updated += 1

    return {
        "updated": updated,
        "missing_users": skipped,
        "existing_users": updated,
        "missing_sample": [],
    }


# =========================================================
# APIs
# =========================================================
@csrf_exempt
@grade_required(["superuser"])
def upload_excel(request):
    if request.method != "POST":
        return _json_error("잘못된 요청 방식입니다.", status=405)

    part = (request.POST.get("part") or "").strip()
    upload_type = (request.POST.get("upload_type") or "").strip()
    excel_file = request.FILES.get("excel_file")

    if not part:
        return _json_error("부서를 선택해주세요.", status=400)

    if upload_type not in SUPPORTED_UPLOAD_TYPES:
        return _json_error(f"현재는 {sorted(SUPPORTED_UPLOAD_TYPES)} 업로드만 지원됩니다.", status=400)

    if not excel_file:
        return _json_error("엑셀 파일이 전달되지 않았습니다.", status=400)

    fs = FileSystemStorage()
    filename = fs.save(excel_file.name, excel_file)
    file_path = fs.path(filename)

    handlers = {
        "최종지급액": ("df", _handle_upload_final_payment, "✅ {n}건 업로드 완료 (final_payment만 반영)"),
        "보증증액": ("df", _handle_upload_guarantee_increase, "✅ {n}건 업로드 완료 (보증증액 필드 반영)"),
        "응당생보": ("df", _handle_upload_ls_due, "✅ {n}건 업로드 완료 (응당생보 반영)"),
        "응당손보": ("df", _handle_upload_ns_due, "✅ {n}건 업로드 완료 (응당손보 반영)"),
        "보증보험": ("df", _handle_upload_surety, "✅ {n}건 업로드 완료 (보증보험 상세 반영)"),
        "기타채권": ("df", _handle_upload_other_debt, "기타채권 {n}건 반영 완료"),
        "통산손보": ("file", _handle_upload_ns_total_from_file, "통산손보 {n}건 반영 완료"),
        "통산생보": ("file", _handle_upload_ls_total_from_file, "통산생보 {n}건 반영 완료"),
    }

    if upload_type not in handlers:
        try:
            fs.delete(filename)
        except Exception:
            pass
        return _json_error("지원하지 않는 업로드 구분입니다.", status=400)

    mode, fn, msg_tpl = handlers[upload_type]

    try:
        with transaction.atomic():
            if mode == "df":
                df = _read_excel_safely(file_path, original_name=excel_file.name)
                result = fn(df)
            else:
                result = fn(file_path, excel_file.name)

            uploaded_date = _update_upload_log(
                part=part,
                upload_type=upload_type,
                excel_file_name=excel_file.name,
                count=result["updated"],
            )

        msg = msg_tpl.format(n=result["updated"])
        return _json_ok(
            msg,
            uploaded=result["updated"],
            missing_users=result.get("missing_users", 0),
            existing_users=result.get("existing_users", 0),
            missing_sample=result.get("missing_sample", []),
            part=part,
            upload_type=upload_type,
            uploaded_date=uploaded_date,
        )

    except ValueError as ve:
        detected_columns = []
        try:
            if mode == "df":
                detected_columns = [str(c) for c in df.columns]  # noqa: F821
        except Exception:
            detected_columns = []
        return _json_error(str(ve), status=400, detected_columns=detected_columns)

    except Exception as e:
        msg = str(e)

        # ✅ 대표적인 포맷 오류는 400으로 안내
        if ("Expected BOF record" in msg) or ("Unsupported format" in msg) or ("XLRDError" in msg):
            return _json_error(
                "업로드 실패: 엑셀 파일 형식이 올바르지 않습니다. "
                "엑셀에서 '다른 이름으로 저장' → .xlsx로 저장 후 업로드해주세요. "
                "(또는 원본이 TSV/CSV면 .csv로 저장 후 업로드 규칙에 맞게 변환)",
                status=400,
            )

        # 나머지는 500
        try:
            with open(file_path, "rb") as f:
                sniff = f.read(32)
        except Exception:
            sniff = b""
        return _json_error(f"⚠️ 업로드 실패: {msg}", status=500, file_head=str(sniff))

    finally:
        try:
            fs.delete(filename)
        except Exception:
            pass


@grade_required(["superuser"])
def search_user(request):
    q = (request.GET.get("q") or "").strip()
    if not q:
        return _json_ok(items=[])

    qs = (
        CustomUser.objects.filter(Q(id__icontains=q) | Q(name__icontains=q) | Q(branch__icontains=q))
        .order_by("branch", "name")[:50]
    )
    items = [{"id": str(u.id), "name": u.name, "branch": u.branch or ""} for u in qs]
    return _json_ok(items=items)


@grade_required(["superuser"])
def api_user_detail(request):
    user_id = (request.GET.get("user") or "").strip()
    if not user_id:
        return _json_error("user 파라미터가 필요합니다.", status=400)

    u = CustomUser.objects.filter(pk=user_id).first()
    if not u:
        return _json_error("대상자를 찾지 못했습니다.", status=404)

    join_disp = "-"
    if hasattr(u, "join_date_display"):
        join_disp = getattr(u, "join_date_display") or "-"
    elif hasattr(u, "enter_display"):
        join_disp = getattr(u, "enter_display") or "-"
    else:
        for f in ("join_date", "enter", "regist"):
            if hasattr(u, f) and getattr(u, f):
                try:
                    join_disp = getattr(u, f).strftime("%Y-%m-%d")
                except Exception:
                    join_disp = str(getattr(u, f))
                break

    retire_disp = ""
    if hasattr(u, "retire_date_display"):
        retire_disp = getattr(u, "retire_date_display") or ""
    elif hasattr(u, "quit_display"):
        retire_disp = getattr(u, "quit_display") or ""
    else:
        for f in ("retire_date", "quit"):
            if hasattr(u, f) and getattr(u, f):
                try:
                    retire_disp = getattr(u, f).strftime("%Y-%m-%d")
                except Exception:
                    retire_disp = str(getattr(u, f))
                break

    return _json_ok(
        user={
            "id": str(u.id),
            "name": u.name,
            "part": u.part or "",
            "branch": u.branch or "",
            "join_date_display": join_disp or "-",
            "retire_date_display": retire_disp,
        }
    )


@grade_required(["superuser"])
def api_deposit_summary(request):
    user_id = (request.GET.get("user") or "").strip()
    if not user_id:
        return _json_error("user 파라미터가 필요합니다.", status=400)

    u = CustomUser.objects.filter(pk=user_id).first()
    if not u:
        return _json_error("대상자를 찾지 못했습니다.", status=404)

    s = DepositSummary.objects.filter(user_id=user_id).first()

    def gi(field, default=0):
        if not s:
            return default
        v = getattr(s, field, None)
        if v is None:
            return default
        try:
            return int(v)
        except Exception:
            return default

    def gs(field, default=""):
        if not s:
            return default
        v = getattr(s, field, None)
        return str(v) if v is not None else default

    def gd(field, default="0.00"):
        if not s:
            return default
        v = getattr(s, field, None)
        if v is None:
            return default
        try:
            return str(v)
        except Exception:
            return default

    other_total = (
        DepositOther.objects
        .filter(user_id=user_id, product_type="수수료", status="유지")
        .aggregate(total=Sum("amount"))
        .get("total")
        or 0
    )

    surety_total = (
        DepositSurety.objects
        .filter(user_id=user_id, product_name="GA개인", status="유지")
        .aggregate(total=Sum("amount"))
        .get("total")
        or 0
    )

    def _parse_date_any(v):
        if not v:
            return None
        if isinstance(v, datetime.datetime):
            return v.date()
        if isinstance(v, datetime.date):
            return v
        try:
            ss = str(v).strip()
            if not ss:
                return None
            ss = ss.replace(".", "-").replace("/", "-")
            return datetime.date.fromisoformat(ss)
        except Exception:
            return None

    join_date = None
    for f in ("join_date", "enter", "regist"):
        if hasattr(u, f):
            join_date = _parse_date_any(getattr(u, f))
            if join_date:
                break

    today = timezone.localdate()
    days_since_join = (today - join_date).days if join_date else None

    comm_3m = gi("comm_3m", 0)
    comm_6m = gi("comm_6m", 0)
    comm_9m = gi("comm_9m", 0)
    comm_12m = gi("comm_12m", 0)

    v_3m_div_13 = (comm_3m * 10) // 13 if comm_3m > 0 else 0
    v_6m_mul_06 = (comm_6m * 3) // 5 if comm_6m > 0 else 0
    v_9m_mul_04 = (comm_9m * 2) // 5 if comm_9m > 0 else 0
    v_12m_mul_025 = comm_12m // 4 if comm_12m > 0 else 0

    if days_since_join is None or days_since_join > 365:
        required_debt = v_3m_div_13
    else:
        required_debt = max(v_3m_div_13, v_6m_mul_06, v_9m_mul_04, v_12m_mul_025)

    debt_total = gi("debt_total", 0)

    summary = {
        "final_payment": gi("final_payment", 0),
        "sales_total": gi("sales_total", 0),
        "refund_expected": gi("refund_expected", 0),
        "pay_expected": gi("pay_expected", 0),
        "maint_total": gd("maint_total", "0.00"),

        "debt_total": debt_total,
        "surety_total": int(surety_total),
        "other_total": int(other_total),
        "required_debt": int(required_debt),
        "final_excess_amount": gi("final_excess_amount", 0),

        "div_1m": gs("div_1m", ""),
        "div_2m": gs("div_2m", ""),
        "div_3m": gs("div_3m", ""),
        "inst_current": gi("inst_current", 0),
        "inst_prev": gi("inst_prev", 0),

        "comm_3m": comm_3m,
        "comm_6m": comm_6m,
        "comm_9m": comm_9m,
        "comm_12m": comm_12m,

        # ✅ 통산손보 업로드로 갱신되는 필드 포함 (문자열로 내려줌)
        "ns_13_round": gd("ns_13_round", "0.00"),
        "ns_18_round": gd("ns_18_round", "0.00"),
        "ls_13_round": gd("ls_13_round", "0.00"),
        "ls_18_round": gd("ls_18_round", "0.00"),

        "ns_2_6_due": gd("ns_2_6_due", "0.00"),
        "ns_2_13_due": gd("ns_2_13_due", "0.00"),
        "ls_2_6_due": gd("ls_2_6_due", "0.00"),
        "ls_2_13_due": gd("ls_2_13_due", "0.00"),

        "ns_18_total": gd("ns_18_total", "0.00"),
        "ns_25_total": gd("ns_25_total", "0.00"),
        "ls_18_total": gd("ls_18_total", "0.00"),
        "ls_25_total": gd("ls_25_total", "0.00"),
    }

    return _json_ok(summary=summary)


@grade_required(["superuser"])
def api_deposit_surety_list(request):
    user_id = (request.GET.get("user") or "").strip()
    if not user_id:
        return _json_error("user 파라미터가 필요합니다.", status=400)

    if not CustomUser.objects.filter(pk=user_id).exists():
        return _json_error("대상자를 찾지 못했습니다.", status=404)

    qs = DepositSurety.objects.filter(user_id=user_id).order_by("-end_date", "-start_date", "-created_at")

    items = [{
        "product_name": x.product_name or "",
        "policy_no": x.policy_no or "",
        "amount": int(x.amount or 0),
        "status": x.status or "",
        "start_date": _fmt_date(x.start_date),
        "end_date": _fmt_date(x.end_date),
    } for x in qs]

    return _json_ok(items=items, count=len(items))


@grade_required(["superuser"])
def api_deposit_other_list(request):
    user_id = (request.GET.get("user") or "").strip()
    if not user_id:
        return _json_error("user 파라미터 누락", status=400)

    qs = DepositOther.objects.filter(user_id=user_id).order_by("-start_date", "-created_at")

    items = [{
        "product_name": x.product_name,
        "product_type": x.product_type,
        "amount": int(x.amount or 0),
        "status": x.status,
        "bond_no": x.bond_no or "",
        "start_date": _fmt_date(x.start_date),
        "memo": x.memo,
    } for x in qs]

    return _json_ok(items=items)


# =========================================================
# Pages
# =========================================================
@grade_required(["superuser"])
def redirect_to_deposit(request):
    return redirect("commission:deposit_home")


@grade_required(["superuser"])
def deposit_home(request):
    parts = list(
        CustomUser.objects.exclude(part__isnull=True)
        .exclude(part__exact="")
        .values_list("part", flat=True)
        .distinct()
        .order_by("part")
    )

    categories = UPLOAD_CATEGORIES[:]

    upload_dates = {}
    for log in DepositUploadLog.objects.all():
        upload_dates.setdefault(log.upload_type, {})
        upload_dates[log.upload_type][log.part] = _fmt_date(log.uploaded_at)

    context = {
        "target": None,
        "parts": parts,
        "categories": categories,
        "upload_dates": upload_dates,
        "supported_upload_types": sorted(SUPPORTED_UPLOAD_TYPES),
    }

    return render(request, "commission/deposit_home.html", context)


@grade_required(["superuser"])
def support_home(request):
    return render(request, "commission/support_home.html")


@grade_required(["superuser"])
def approval_home(request):
    return render(request, "commission/approval_home.html")
