# Phase 3: HQ(Hazard Quotient) 계산
# HQ = (MHI + 사용자 섭취량) / UL
from pathlib import Path

import pandas as pd


# ── 나이 → 세부연령 문자열 매핑 ──────────────────────────────────────────────
# (UL/MHI 엑셀의 '세부연령' 컬럼 값과 동일해야 함)
_AGE_RANGES: list[tuple[int, int, str]] = [
    (1,   2,  "1-2(세)"),
    (3,   5,  "3-5"),
    (6,   8,  "6-8"),
    (9,  11,  "9-11"),
    (12, 14,  "12-14"),
    (15, 18,  "15-18"),
    (19, 29,  "19-29"),
    (30, 49,  "30-49"),
    (50, 64,  "50-64"),
    (65, 74,  "65-74"),
    (75, 999, "75 이상"),
]

def _age_to_group(age: int) -> str:
    """나이(세) → 세부연령 문자열. 범위 밖이면 가장 가까운 끝단 반환."""
    for lo, hi, label in _AGE_RANGES:
        if lo <= age <= hi:
            return label
    return "75 이상" if age > 75 else "1-2(세)"


def _get_row(df: pd.DataFrame, sex: str, age: int,
             pregnant: bool, nursing: bool) -> pd.Series:
    """성별·나이·임산부여부로 해당 행을 반환한다."""
    # 임산부/수유부는 세부연령 특수값으로 직접 조회
    if sex == "여성" and pregnant:
        age_label = "임신부"
    elif sex == "여성" and nursing:
        age_label = "수유부"
    else:
        age_label = _age_to_group(age)

    mask = (df["성별"] == sex) & (df["세부연령"] == age_label)
    rows = df[mask]

    if rows.empty:
        raise ValueError(
            f"해당 조건의 데이터 없음: 성별={sex}, 세부연령={age_label}"
        )
    return rows.iloc[0]


# ── Excel 파일 캐시 ──────────────────────────────────────────────────────────
# [문제]
#   calculate_hq()가 호출될 때마다 pd.read_excel()을 2번 실행했다.
#   사용자가 '다시 시작'을 선택해 루프를 반복할수록 파일을 반복해서 읽게 되어
#   속도가 느려지는 문제가 있었다.
#
# [해결]
#   calculate_hq가 호출될 때마다 Excel을 2번 읽는다. 속도가 느려질 수 있는
#   이 문제를 해결하기 위해서 --data_processor.py 내부에서 경로 기준으로 캐시
#   (@lru_cache 또는 모듈 변수)--하는 방식으로 바꾸었다.
#
#   구체적으로는 모듈 수준의 딕셔너리 _DF_CACHE 를 사용한다.
#   key: Path 객체 (파일 경로), value: 이미 읽어 둔 DataFrame
#   같은 경로로 두 번 이상 호출되면 캐시에서 꺼내므로 파일 I/O가 1회로 줄어든다.
#
# [검증]
#   2회 호출해도 캐시 크기 2 고정 — 파일 I/O는 최초 1회만 발생한다.
_DF_CACHE: dict[Path, pd.DataFrame] = {}

def _load(path: Path) -> pd.DataFrame:
    """Excel 파일을 읽어 반환한다. 같은 경로는 캐시에서 꺼낸다."""
    if path not in _DF_CACHE:
        _DF_CACHE[path] = pd.read_excel(path)
    return _DF_CACHE[path]


# ── 공개 API ─────────────────────────────────────────────────────────────────

def calculate_hq(parsed: dict, ul_path: Path, mhi_path: Path) -> dict:
    """사용자 섭취량 + 평균 식이 섭취량(MHI)을 상한섭취량(UL)으로 나눠 HQ를 계산한다.

    Args:
        parsed:   parse_input() 반환값 (sex / age / pregnant / nursing / 영양소키: float)
        ul_path:  01_UL_Sex-Age_cleaned.xlsx 경로
        mhi_path: 02_MHI_Sex-Age_cleaned.xlsx 경로

    Returns:
        {영양소명: HQ값, ...}   — 사용자가 입력한 영양소만 포함
        HQ < 1  → 안전
        HQ ≥ 1  → 상한섭취량 초과, 주의
    """
    df_ul  = _load(ul_path)
    df_mhi = _load(mhi_path)

    sex      = parsed["sex"]
    age      = parsed["age"]
    pregnant = parsed["pregnant"]
    nursing  = parsed["nursing"]

    row_ul  = _get_row(df_ul,  sex, age, pregnant, nursing)
    row_mhi = _get_row(df_mhi, sex, age, pregnant, nursing)

    # 사용자가 입력한 영양소 키만 추출 (메타 필드 제외)
    meta_keys = {"sex", "age", "pregnant", "nursing"}
    nutrient_keys = [k for k in parsed if k not in meta_keys]

    result: dict[str, float] = {}
    for key in nutrient_keys:
        user_intake = float(parsed[key])

        ul_val  = row_ul.get(key)
        mhi_val = row_mhi.get(key)

        # UL 또는 MHI 값이 없으면 건너뜀
        if ul_val is None or pd.isna(ul_val):
            print(f"  [건너뜀] {key}: UL 데이터 없음 (상한섭취량 미설정 영양소)")
            continue
        if mhi_val is None or pd.isna(mhi_val):
            print(f"  [건너뜀] {key}: MHI 데이터 없음")
            continue

        ul_val  = float(ul_val)
        mhi_val = float(mhi_val)

        if ul_val == 0:
            print(f"  [건너뜀] {key}: UL = 0 (나누기 불가)")
            continue

        hq = (mhi_val + user_intake) / ul_val
        result[key] = round(hq, 4)

    return result
