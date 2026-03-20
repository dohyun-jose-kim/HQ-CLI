# Phase 2: 파싱 — raw string → 표준화 딕셔너리
#
# ── 변경 이력 ────────────────────────────────────────────────────────────────
# [2026-03-09] fuzzy cutoff 강화: 0.55 → 0.70
#   이유: 낮은 threshold 에서 alias 테이블에 없는 무관한 단어가
#         영양소로 잘못 추천되는 경우를 차단. 
#         직접 만든 alias 테이블(_ALIAS_GROUPS)이 충분히 촘촘하므로
#         정말 엄밀한 상황이 아니라면 추천하지 않는 것이 낫겠다고 판단.
# ─────────────────────────────────────────────────────────────────────────────
import re
import sys
import difflib


def _input_or_quit(prompt: str) -> str:
    """input() 래퍼. 'q' 입력 시 즉시 종료."""
    val = input(prompt).strip()
    if val.lower() == "q":
        print("프로그램을 종료합니다.")
        sys.exit(0)
    return val

# ── 내부 표준 키 목록 (UL/MHI 컬럼명과 동일) ────────────────────────────────
SUPP_15 = [
    "Vitamin_A(µgRAE)", "Vitamin_B6(mg)",  "Vitamin_C(mg)",
    "Vitamin_D(µg)",    "Vitamin_E(mg)",   "Calcium(mg)",
    "Copper(µg)",       "Iodine(µg)",      "Iron(mg)",
    "Manganese(mg)",    "Molybdenum(µg)",  "Phosphorus(mg)",
    "Selenium(µg)",     "Sodium(mg)",      "Zinc(mg)",
]

# 내부 키 → 기본 단위 ("mg" 또는 "µg")
_INTERNAL_UNIT: dict[str, str] = {}
for _k in SUPP_15:
    _raw_unit = re.search(r'\((.*?)\)', _k).group(1)
    _INTERNAL_UNIT[_k] = _raw_unit.replace("RAE", "").replace("DFE", "")


# ── 영양소 이름 매핑 테이블 ──────────────────────────────────────────────────
# 형식: ([별칭, ...], 내부 표준 키)  →  런타임에 alias→std_key dict 로 펼침
_ALIAS_GROUPS: list[tuple[list[str], str]] = [
    (["비타민a", "비타민 a", "vitamina", "vitamin_a", "vitamin a", "vit a"],
     "Vitamin_A(µgRAE)"),
    (["비타민b6", "비타민 b6", "vitaminb6", "vitamin_b6", "vitamin b6", "vit b6"],
     "Vitamin_B6(mg)"),
    (["비타민c", "비타민 c", "vitaminc", "vitamin_c", "vitamin c", "vit c"],
     "Vitamin_C(mg)"),
    (["비타민d", "비타민 d", "vitamind", "vitamin_d", "vitamin d", "vit d"],
     "Vitamin_D(µg)"),
    (["비타민e", "비타민 e", "vitamine", "vitamin_e", "vitamin e", "vit e"],
     "Vitamin_E(mg)"),
    (["칼슘", "calcium", "ca"],                             "Calcium(mg)"),
    (["구리", "copper", "cu"],                              "Copper(µg)"),
    (["요오드", "아이오딘", "iodine"],                       "Iodine(µg)"),
    (["철분", "철", "iron", "fe"],                          "Iron(mg)"),
    (["망간", "manganese", "mn"],                           "Manganese(mg)"),
    (["몰리브덴", "몰리브데넘", "molybdenum", "mo"],          "Molybdenum(µg)"),
    (["인", "phosphorus", "p"],                             "Phosphorus(mg)"),
    (["셀레늄", "selenium", "se"],                          "Selenium(µg)"),
    (["나트륨", "소금", "sodium", "na"],                     "Sodium(mg)"),
    (["아연", "zinc", "zn"],                                "Zinc(mg)"),
]

_NAME_MAP: dict[str, str] = {
    alias: std_key
    for aliases, std_key in _ALIAS_GROUPS
    for alias in aliases
}

# ug / mcg → µg 정규화 + IU 지원
_UNIT_ALIASES: dict[str, str] = {
    "ug": "µg", "mcg": "µg", "µg": "µg",
    "mg": "mg", "g": "g",
    "iu": "IU",
}

# IU → 내부 단위 변환 계수 (보충제 기준 근사값)
_IU_FACTOR: dict[str, float] = {
    "Vitamin_A(µgRAE)": 0.3,    # 1 IU retinol = 0.3 µgRAE
    "Vitamin_D(µg)":    0.025,  # 1 IU = 0.025 µg
    "Vitamin_E(mg)":    0.67,   # 1 IU d-alpha-tocopherol = 0.67 mg
}


# ── 내부 헬퍼 ────────────────────────────────────────────────────────────────

def _normalize_name(raw: str) -> str:
    """소문자 변환 + 앞뒤 공백 제거 (내부 공백은 유지)."""
    return raw.lower().strip()


def _resolve_name(name_raw: str) -> str | None:
    """사용자 입력 영양소명 → 내부 표준 키. 매핑 실패 시 fuzzy 추천."""
    normalized = _normalize_name(name_raw)

    if normalized in _NAME_MAP:
        return _NAME_MAP[normalized]

    # fuzzy match
    candidates = list(_NAME_MAP.keys())
    matches = difflib.get_close_matches(normalized, candidates, n=1, cutoff=0.70)
    if matches:
        suggested_key = _NAME_MAP[matches[0]]
        ans = _input_or_quit(
            f"  [추천] '{name_raw}' → '{suggested_key}' 로 인식했습니다. "
            f"맞으면 Enter, 건너뜀은 n, 재입력은 r: "
        ).lower()
        if ans == "r":
            return "__reinput__"
        if ans != "n":
            return suggested_key

    print(f"  [오류] '{name_raw}' 은(는) 지원 영양소가 아닙니다. 건너뜁니다.")
    return None


def _parse_value_unit(val_raw: str) -> tuple[float, str] | None:
    """'10ug', '500 mg', '10.5µg' → (10.0, 'µg'). 실패 시 None."""
    m = re.match(r'^([\d.]+)\s*([a-zA-Zµ]*)', val_raw.strip())
    if not m:
        return None
    value = float(m.group(1))
    unit_raw = m.group(2).lower() if m.group(2) else ""
    return value, unit_raw


def _convert_unit(value: float, unit_raw: str, std_key: str) -> float:
    """사용자 단위 → 내부 단위로 변환."""
    unit = _UNIT_ALIASES.get(unit_raw, unit_raw)
    internal = _INTERNAL_UNIT[std_key]

    if unit == "" or unit == internal:
        return value

    # IU 변환
    if unit == "IU":
        factor = _IU_FACTOR.get(std_key)
        if factor:
            return value * factor
        print(f"  [경고] {std_key} 의 IU 변환 계수가 없습니다. 원래 값 사용.")
        return value

    # 스케일 변환
    conversions = {
        ("g",  "mg"): 1_000,
        ("g",  "µg"): 1_000_000,
        ("mg", "µg"): 1_000,
        ("µg", "mg"): 1 / 1_000,
        ("mg", "g"):  1 / 1_000,
        ("µg", "g"):  1 / 1_000_000,
    }
    factor = conversions.get((unit, internal))
    if factor:
        return value * factor

    print(f"  [경고] '{std_key}' 단위 변환 불가 ({unit} → {internal}). 원래 값 사용.")
    return value


# ── 공개 API ─────────────────────────────────────────────────────────────────

def parse_input(raw_input: str) -> dict:
    """raw string → 표준화 딕셔너리.

    Args:
        raw_input: get_user_input() 반환값
                   예) "남성, 32, 해당없음, 비타민D: 10ug, 철분: 8mg"

    Returns:
        {
            "sex": "남성" | "여성",
            "age": int,
            "pregnant": bool,
            "nursing": bool,
            "Vitamin_D(µg)": float,   # 입력된 영양소만 포함
            ...
        }
    """
    parts = [p.strip() for p in raw_input.split(",")]

    if len(parts) < 4:
        raise ValueError(f"raw_input 형식 오류 (최소 4개 필드 필요): {raw_input!r}")

    sex_raw, age_raw, preg_raw = parts[0], parts[1], parts[2]
    nutrient_raw = ", ".join(parts[3:])  # 재입력 시 표시용 원본 보존

    while True:
        nutrient_parts = [p.strip() for p in nutrient_raw.split(",")]
        result: dict = {
            "sex":      sex_raw,
            "age":      int(age_raw),
            "pregnant": preg_raw == "임산부",
            "nursing":  preg_raw == "수유부",
        }
        reinput = False

        for part in nutrient_parts:
            part = part.strip()
            if not part or ":" not in part:
                continue

            name_raw, val_raw = part.split(":", 1)
            name_raw = name_raw.strip()
            val_raw  = val_raw.strip()

            parsed = _parse_value_unit(val_raw)
            if parsed is None:
                print(f"  [경고] 값 파싱 실패: '{part}' — 건너뜁니다.")
                continue
            value, unit_raw = parsed

            # 단위 누락 확인
            if unit_raw == "":
                print(f"  [경고] '{part}' — 단위가 없습니다.")
                ans = _input_or_quit("  단위 없이 계속하려면 Enter, 다시 입력하려면 r: ").lower()
                if ans == "r":
                    print(f"  이전 입력: {nutrient_raw}")
                    nutrient_raw = _input_or_quit("영양소 재입력: ")
                    reinput = True
                    break

            std_key = _resolve_name(name_raw)
            if std_key == "__reinput__":
                print(f"  이전 입력: {nutrient_raw}")
                nutrient_raw = _input_or_quit("영양소 재입력: ")
                reinput = True
                break
            if std_key is None:
                continue

            converted = _convert_unit(value, unit_raw, std_key)
            result[std_key] = converted

        if not reinput:
            break

    return result
