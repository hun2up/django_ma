# commission/upload_utils/upload_utils.py
from __future__ import annotations

import io
import os
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html.parser import HTMLParser
from typing import Iterable, Optional, Sequence

import pandas as pd

# =========================================================
# Constants (SSOT)
# - views/constants 등에 의존하지 않게 유지 (순환 import 방지)
# =========================================================
DEC2 = Decimal("0.00")


# =========================================================
# Convert helpers
# =========================================================
def _to_int(v, default: int = 0) -> int:
    """숫자/문자/NaN 등을 안전하게 int로 변환."""
    try:
        if v is None:
            return default
        if hasattr(pd, "isna") and pd.isna(v):
            return default
        s = str(v).strip().replace(",", "")
        if s.lower() in ("", "nan", "none", "-"):
            return default
        return int(float(s))
    except Exception:
        return default


def _to_decimal(v, default: Decimal = Decimal("0.00")) -> Decimal:
    """숫자/문자/NaN 등을 안전하게 Decimal로 변환."""
    try:
        if v is None:
            return default
        if hasattr(pd, "isna") and pd.isna(v):
            return default
        s = str(v).strip().replace(",", "")
        if s.lower() in ("", "nan", "none", "-"):
            return default
        return Decimal(s)
    except (InvalidOperation, Exception):
        return default


def _safe_decimal_q2(v, default: Decimal = DEC2) -> Decimal:
    """통산손/생보 저장용: Decimal(2) 자리로 안전 quantize."""
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


def _to_date(v):
    """pandas Timestamp / datetime / 문자열 날짜를 date로 안전 변환."""
    try:
        if v is None:
            return None
        if hasattr(pd, "isna") and pd.isna(v):
            return None
        if isinstance(v, pd.Timestamp):
            return v.date()
        if hasattr(v, "date") and callable(v.date):
            return v.date()

        s = str(v).strip()
        if not s or s.lower() in ("nan", "none", "-"):
            return None

        s = s.replace(".", "-").replace("/", "-")
        dt = pd.to_datetime(s, errors="coerce")
        return dt.date() if not pd.isna(dt) else None
    except Exception:
        return None


def _to_div(v, default: str = "") -> str:
    """분급여부/정상 여부 텍스트 정규화."""
    s = ("" if v is None else str(v)).strip()
    if not s or s.lower() in ("nan", "none"):
        return default
    if "분급" in s:
        return "분급"
    if "정상" in s:
        return "정상"
    return default


def _norm_emp_id(v) -> str:
    """사번/사원코드 정규화: '1234567.0' → '1234567'."""
    if v is None:
        return ""
    if hasattr(pd, "isna") and pd.isna(v):
        return ""
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none"):
        return ""
    if s.endswith(".0"):
        s = s[:-2]
    return s.strip()


def _extract_emp7_from_a(raw) -> str:
    """
    통산손/생보 raw matrix A열에서 사번 7자리 추출.
    emp7 = s[-8:-1]
    """
    s = "" if raw is None else str(raw).strip()
    if len(s) < 8:
        return ""
    emp7 = s[-8:-1]
    return emp7 if emp7.isdigit() and len(emp7) == 7 else ""


# =========================================================
# Column detection helpers
# =========================================================
def _norm_col(s: str) -> str:
    """컬럼명 normalize: 소문자/특수문자 제거/0→o(보증(0) 케이스)"""
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = re.sub(r"[^0-9a-z가-힣]", "", s)
    s = s.replace("0", "o")
    return s


def _best_match_col(
    df_cols: Sequence,
    required_tokens: Sequence[str],
    optional_tokens: Optional[Sequence[str]] = None,
    ban_tokens: Optional[Sequence[str]] = None,
):
    """df columns 중 required token 포함 + optional token 점수로 best match."""
    optional_tokens = optional_tokens or []
    ban_tokens = ban_tokens or []

    best = None
    best_score = -10**9

    for c in df_cols:
        nc = _norm_col(c)

        if any(bt and bt in nc for bt in ban_tokens):
            continue
        if not all(rt and rt in nc for rt in required_tokens):
            continue

        score = 100 * len(required_tokens)
        for ot in optional_tokens:
            if ot and ot in nc:
                score += 15
        score -= max(0, len(nc) - 20)

        if score > best_score:
            best_score = score
            best = c

    return best


def _find_col_by_aliases(df: pd.DataFrame, alias_groups, ban_groups=None):
    """여러 alias 후보 중 하나를 찾아 컬럼명 반환."""
    df_cols = list(df.columns)
    ban_groups = ban_groups or []

    ban_tokens = []
    for bg in ban_groups:
        ban_tokens += [_norm_col(x) for x in bg]

    for grp in alias_groups:
        req = [_norm_col(x) for x in grp]
        found = _best_match_col(df_cols, required_tokens=req, optional_tokens=[], ban_tokens=ban_tokens)
        if found:
            return found
    return None


def _detect_emp_id_col(df: pd.DataFrame):
    """사번/사원코드/등록번호/FC코드 컬럼 자동 탐지."""
    alias_groups = [
        ["사번"],
        ["사원", "코드"],
        ["사원", "번호"],
        ["사원번호"],
        ["등록", "번호"],
        ["등록번호"],
        ["fc", "코드"],
        ["설계사", "코드"],
        ["설계사", "번호"],
        ["id"],
    ]
    ban_groups = [["계약"], ["증권"], ["주민"], ["연락"], ["전화"], ["휴대"], ["메일"], ["email"]]
    return _find_col_by_aliases(df, alias_groups, ban_groups=ban_groups)


# ---------------------------------------------------------
# ✅ SSOT 추가 1) 기본 컬럼 탐지 유틸 (_detect_col)
# ---------------------------------------------------------
def _detect_col(
    df: pd.DataFrame,
    must_include: Sequence[str],
    any_include: Sequence[str] = (),
    ban: Sequence[str] = (),
):
    """
    DataFrame에서 컬럼명을 토큰 기반으로 탐지한다.

    - must_include: 모두 포함되어야 함 (AND)
    - any_include: 하나라도 포함되면 가산점 (OR)
    - ban: 포함되면 제외

    반환: 원본 df.columns 중 매칭된 컬럼명 (없으면 None)
    """
    if df is None or df.empty:
        return None

    required = [_norm_col(x) for x in (must_include or []) if x]
    optional = [_norm_col(x) for x in (any_include or []) if x]
    ban_tokens = [_norm_col(x) for x in (ban or []) if x]

    if not required:
        return None

    return _best_match_col(list(df.columns), required_tokens=required, optional_tokens=optional, ban_tokens=ban_tokens)


# ---------------------------------------------------------
# ✅ SSOT 추가 2) exact-or-space-removed 매칭
# ---------------------------------------------------------
def _find_exact_or_space_removed(columns: Sequence, target: str):
    """
    컬럼명이 '정확히' 맞거나(공백/특수문자 제거 후) 동일하면 컬럼명을 반환한다.
    - deposit.handle_upload_guarantee_increase 등에서 사용

    예:
      "3개월 장기 총수수료(지급월+직전2개월)" == "3개월장기총수수료(지급월+직전2개월)" (공백 제거)
    """
    if not columns:
        return None
    if target is None:
        return None

    target_raw = str(target).strip()
    if not target_raw:
        return None

    # 1) 완전 일치 우선
    for c in columns:
        if str(c).strip() == target_raw:
            return c

    # 2) 공백 제거 일치
    def strip_spaces(x: str) -> str:
        return re.sub(r"\s+", "", x.strip())

    t2 = strip_spaces(target_raw)
    for c in columns:
        if strip_spaces(str(c)) == t2:
            return c

    # 3) 더 강한 normalize(공백/특수문자 제거) 일치
    t3 = _norm_col(target_raw)
    for c in columns:
        if _norm_col(str(c)) == t3:
            return c

    return None


# ---------------------------------------------------------
# ✅ SSOT 추가 3) 환수/지급예상 컬럼 탐지 (_detect_refundpay_col)
# ---------------------------------------------------------
def _detect_refundpay_col(df: pd.DataFrame, flag: Optional[str], kind: str, line: str):
    """
    환수/지급예상 업로드 컬럼 탐지 SSOT.

    - flag: None(일반), "o"(보증 O), "x"(보증 X)
    - kind: "refund" | "pay"
    - line: "ns"(손보) | "ls"(생보) | "total"(합계)

    엑셀 컬럼명 케이스가 다양해서 토큰 기반 점수 매칭으로 찾는다.
    """
    if df is None or df.empty:
        return None

    # kind tokens
    kind_tokens = ("환수",) if kind == "refund" else ("지급",)
    # line tokens
    if line == "ns":
        line_tokens = ("손", "손보")
        ban_line = ("생", "생보")
    elif line == "ls":
        line_tokens = ("생", "생보")
        ban_line = ("손", "손보")
    else:
        line_tokens = ("합", "합계", "total")
        ban_line = ()

    # flag tokens
    flag_tokens = ()
    if flag == "o":
        # 보증(O), 보증o, 보증-Ｏ 등 다양한 표기 흡수
        flag_tokens = ("보증", "o")
    elif flag == "x":
        flag_tokens = ("보증", "x")

    # must = kind + (line 최소 토큰 1개는 required 성격) + (flag가 있으면 포함)
    # line의 경우 토큰이 ("손","손보") 처럼 다중이라 required로 모두 넣으면 너무 빡세서,
    # required에는 kind + (line의 대표 토큰 1개) + flag 정도로 두고,
    # 나머지는 optional로 점수 가산한다.
    line_rep = line_tokens[0] if line_tokens else ""
    required = tuple([*kind_tokens, *(flag_tokens or ()), line_rep] if line_rep else [*kind_tokens, *(flag_tokens or ())])

    optional = tuple(set([*line_tokens, *kind_tokens, *(flag_tokens or ())]))
    ban = tuple(set(ban_line))

    col = _detect_col(df, must_include=required, any_include=optional, ban=ban)
    return col


# =========================================================
# Excel readers (xlsx/xls/html/tsv/csv)
# =========================================================
def _decode_bytes_best_effort(raw: bytes) -> str:
    """utf-8/cp949 등으로 최대한 텍스트 복원."""
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="replace")


def _parse_first_html_table(file_path: str) -> pd.DataFrame:
    """엑셀이 HTML 테이블로 내려오는 케이스 대응(첫 table 파싱)."""
    with open(file_path, "rb") as f:
        raw = f.read()
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
                cell_text = " ".join("".join(self.cur_cell).split())
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

    max_len = max(len(header), *(len(r) for r in data_rows)) if data_rows else len(header)
    header = (header + [""] * max_len)[:max_len]
    norm_rows = [(r + [""] * max_len)[:max_len] for r in data_rows]

    df = pd.DataFrame(norm_rows, columns=[str(c).strip() for c in header])

    # 컬럼명 중복 방지
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
    """csv/tsv/세미콜론 등 텍스트 테이블 추정 로딩."""
    with open(file_path, "rb") as f:
        raw = f.read()
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
    """텍스트 테이블을 header=None 형태의 matrix로 로딩."""
    with open(file_path, "rb") as f:
        raw = f.read()
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


def _read_head_bytes(file_path: str, n: int = 4096) -> bytes:
    try:
        with open(file_path, "rb") as f:
            return f.read(n)
    except Exception:
        return b""


def _is_html_bytes(head: bytes) -> bool:
    head_l = head.lstrip().lower()
    return head_l.startswith(b"<html") or head_l.startswith(b"<!doctype") or head_l.startswith(b"<table")


def _read_excel_safely(file_path: str, original_name: str = "") -> pd.DataFrame:
    """
    업로드 파일을 안전하게 DataFrame(header=0)로 읽는다.
    """
    ext = os.path.splitext((original_name or file_path))[1].lower()
    head = _read_head_bytes(file_path)

    if _is_html_bytes(head):
        return _parse_first_html_table(file_path)

    is_zip = head.startswith(b"PK\x03\x04")
    is_ole2 = head.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1")

    if is_zip or ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        return pd.read_excel(file_path, header=0, engine="openpyxl")

    if is_ole2:
        try:
            import xlrd  # noqa: F401
        except Exception:
            raise ValueError(
                "업로드 실패: 현재 서버에 .xls 처리 모듈(xlrd)이 없습니다.\n"
                "엑셀에서 '다른 이름으로 저장' → .xlsx로 저장 후 업로드해주세요."
            )
        return pd.read_excel(file_path, header=0, engine="xlrd")

    return _read_text_table(file_path)


def _read_excel_raw_matrix(
    file_path: str,
    original_name: str,
    skiprows: int,
    header_none: bool = True,
) -> pd.DataFrame:
    """
    업로드 파일을 header=None 형태의 matrix(DataFrame)로 읽는다.
    """
    ext = os.path.splitext((original_name or file_path))[1].lower()
    head = _read_head_bytes(file_path)

    if _is_html_bytes(head):
        df_html = _parse_first_html_table(file_path)
        values = df_html.to_numpy().tolist()
        values = values[skiprows:] if skiprows else values
        return pd.DataFrame(values)

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

    return _read_text_table_matrix(file_path, skiprows=skiprows)


# =========================================================
# DB helpers
# =========================================================
def _bulk_existing_user_ids(ids: Iterable[str]):
    """CustomUser 존재하는 PK들을 bulk로 조회."""
    from accounts.models import CustomUser

    ids = [str(x).strip() for x in ids if x is not None and str(x).strip()]
    if not ids:
        return set()
    qs = CustomUser.objects.filter(pk__in=ids).values_list("pk", flat=True)
    return set(str(x) for x in qs)


def _update_upload_log(part: str, upload_type: str, excel_file_name: str, count: int):
    """
    ⚠️ Deprecated wrapper.
    업로드 로그 SSOT는 commission.upload_handlers.deposit._update_upload_log 를 사용.
    """
    from commission.upload_handlers.deposit import _update_upload_log as _ssot_update

    return _ssot_update(
        part=part,
        upload_type=upload_type,
        excel_file_name=excel_file_name,
        count=count,
    )


# =========================================================
# Public exports (SSOT)
# =========================================================
__all__ = [
    "DEC2",
    "_to_int",
    "_to_decimal",
    "_safe_decimal_q2",
    "_to_date",
    "_to_div",
    "_norm_emp_id",
    "_extract_emp7_from_a",
    "_norm_col",
    "_best_match_col",
    "_find_col_by_aliases",
    "_detect_emp_id_col",
    "_detect_col",
    "_find_exact_or_space_removed",
    "_detect_refundpay_col",
    "_decode_bytes_best_effort",
    "_parse_first_html_table",
    "_read_text_table",
    "_read_text_table_matrix",
    "_read_excel_safely",
    "_read_excel_raw_matrix",
    "_bulk_existing_user_ids",
    "_update_upload_log",
]
