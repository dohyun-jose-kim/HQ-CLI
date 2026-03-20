"""
###############################################################
## 배포 전 체크리스트
###############################################################
배포 모드로 전환 시 아래 두 줄만 수정하면 됩니다:

    DEV_MODE       = False   # True → 실행 시 파싱 버전 선택 메뉴 표시
    DEPLOY_VERSION = "v2"    # 배포에 사용할 버전 ("v1" 또는 "v2")

파싱 버전 설명: 초기 수기로 세팅한 딕셔너리 실패시에 각 버전의 반응이 다름. 이것이 차이. 
    v1  —  "difflib" 기반 fuzzy 매핑  (규칙 기반, 외부 의존성 없음)
    v2  —  "TF-IDF" 코사인 유사도 ML  (sklearn 필요, 오타에 더 강함)
###############################################################

<<<영양제 섭취 위험도 평가 CLI>>>
생성일시 : 2026-03-06
생성자 : 김도현
생성목적: 영양제 섭취 위험도를 평가하기 위한 CLI 도구
사용 대상자: 영양제를 섭취하는 일반 소비자

실행방법: "python main.py" 를 터미널에서 실행.
사용 요령:
    1. 안내 메시지에 따라 섭취하는 영양제와 섭취량을 입력한다.
    2. 결과 해석 메시지를 참고하여 자신의 섭취 위험도를 확인한다.
    3. 필요에 따라 결과 파일을 열어 상세 정보를 확인한다.
    4. 프로그램 종료 또는 새 데이터로 다시 시작할 수 있다.


* 본 파일(main.py)은 시작부터 종료까지 관장합니다. 각 Phase에서 필요한 모듈과 함수를 가져와서 사용합니다.
본 스크립트를 실행하는데에 있어 연계된 파일:
    - initial_reaction.py : 사용자 입력 수집 및 안내 메시지
    - parsing.py          : 입력 문자열 → 표준화 딕셔너리 변환
    - data_processor.py   : HQ 계산 로직
    - result_maker.py     : HQ 시각화 파일 생성

    
###############################################################
## 디렉토리 구조 설명
###############################################################

week_2/
├── CLI/
│   ├── main.py                    # 메인 실행 파일 (현재 활성화된 파일)
│   ├── initial_reaction.py           # Phase 1: 사용자 입력 수집 모듈
│   ├── parsing.py                    # Phase 2: 입력 파싱 모듈
│   ├── data_processor.py             # Phase 3: HQ 계산 모듈
│   ├── result_maker.py               # Phase 4: 결과 시각화 모듈
│   └── results/                      # 결과 파일 저장 폴더 (프로그램 실행 시 자동 생성)
└── data/
    ├── 01_UL_Sex-Age.xlsx           # UL(상한섭취량) 데이터 파일
    ├── 02_MHI_Sex-Age.xlsx          # MHI(최소위해섭취량) 데이터 파일
    └── ...                          # 기타 데이터 파일들

###############################################################
## 파이프라인 설명
###############################################################
    
파이프라인:
    Phase 1 - initial_reaction : 안내 메시지 출력 + 사용자 입력 수집
    Phase 2 - parsing          : 입력 문자열 → 표준화 딕셔너리 (키·단위 변환)
    Phase 3 - data_processor   : HQ = (MHI + 섭취량) / UL 계산
    Phase 4 - result_maker     : HQ 시각화 파일 생성
    Phase 5 - (여기)           : 결과 출력 + 종료/재시작/오류보고서 선택
"""


###############################################################
###############################################################
## 파이프라인 시작
###############################################################
###############################################################

## 필요 모든 모듈과 함수를 여기서 가져옴

import csv
import importlib
import sys
from datetime import datetime
from pathlib import Path
import openpyxl


## 각 Phase에서 필요한 함수들을 가져옵니다. (직접 만든 것들임 - 실제 가서 그 구현을 확인핼 수 있음) 
## From 과 import 차이는 사용자가 사용을 할 때 차이가 남.
from initial_reaction import get_user_input ## initial_reaction.py 파일 안에 정의된 get_user_input이라는 함수만 꺼내와
from data_processor import calculate_hq, _age_to_group
from result_maker import make_result

# ── 파싱 버전 선택 ─────────────────────────────────────────────────────────
# 배포 시: DEV_MODE = False 로 변경, DEPLOY_VERSION 에 사용할 버전 지정
DEV_MODE       = True
DEPLOY_VERSION = "v2"   # DEV_MODE=False 일 때 고정 사용 버전

_PARSING_VERSIONS: dict[str, dict] = {
    "v1": {
        "module": "parsing_v1",
        "desc":   "difflib 기반 fuzzy 매핑  (규칙 기반, 외부 의존성 없음)",
    },
    "v2": {
        "module": "parsing_v2",
        "desc":   "TF-IDF 코사인 유사도 ML  (sklearn 필요, 오타에 더 강함)",
    },
}

def _select_parsing_version() -> str:
    """개발 모드에서 파싱 버전을 선택하고 버전 키('v1'|'v2')를 반환한다."""
    print("─" * 50)
    print("[개발 모드] 사용할 파싱 버전을 선택하세요:")
    print("  1. v1  —  difflib 기반 fuzzy 매핑  (규칙 기반, 외부 의존성 없음)")
    print("  2. v2  —  TF-IDF 코사인 유사도 ML  (sklearn 필요, 오타에 더 강함)")
    while True:
        choice = input("선택 (번호): ").strip()
        if choice.lower() == "q":
            print("프로그램을 종료합니다.")
            sys.exit(0)
        if choice == "1": return "v1"
        if choice == "2": return "v2"
        print("  1 또는 2를 입력하세요.")

# 버전 결정 및 parse_input 동적 로드
if DEV_MODE:
    _version_key = _select_parsing_version()
else:
    _version_key = DEPLOY_VERSION

_parsing_module = importlib.import_module(_PARSING_VERSIONS[_version_key]["module"])
parse_input = _parsing_module.parse_input
print(f"[파싱] {_version_key} 로드 완료 — {_PARSING_VERSIONS[_version_key]['desc']}")
print("─" * 50)
###############################################################
## 경로 상대적으로 세팅하기
###############################################################
# ── 경로 상수 ──────────────────────────────────────────────────────────────────
# 현재 파일(main.py) 기준으로 경로를 설정합니다.
# __file__ = 현재 파일의 경로 "/Users/inco/.../week_2/CLI/main.py" 로 고정

_CLI_DIR   = Path(__file__).parent
DATA_DIR   = _CLI_DIR / "data"
RESULT_DIR = _CLI_DIR / "results"

# 데이터 파일 경로 + 추가 예정
UL_PATH  = DATA_DIR / "preprocessed/01_UL_Sex-Age_cleaned.xlsx"
MHI_PATH = DATA_DIR / "preprocessed/02_MHI_Sex-Age_cleaned.xlsx"

# ── result_accumulation.xlsx 컬럼 정의 ─────────────────────────────────────
SUPP_15 = [
    "Vitamin_A(µgRAE)", "Vitamin_B6(mg)",  "Vitamin_C(mg)",
    "Vitamin_D(µg)",    "Vitamin_E(mg)",   "Calcium(mg)",
    "Copper(µg)",       "Iodine(µg)",      "Iron(mg)",
    "Manganese(mg)",    "Molybdenum(µg)",  "Phosphorus(mg)",
    "Selenium(µg)",     "Sodium(mg)",      "Zinc(mg)",
]
_ACCUM_HEADER = ["timestamp", "성별", "나이", "연령범주"] + SUPP_15

###############################################################
## 도우미 함수 수립
###############################################################
# for Phase 5

## 번호 선택 메뉴를 출력하고 유효한 입력을 받을 때까지 반복하는 함수입니다.
## options: 선택지 텍스트 리스트 (예: ["종료", "재시작", "오류 보고서 작성"])
def _prompt_choice(options: list) -> str:
    """번호로 선택지를 제시하고 유효한 번호를 반환한다."""
    for i, text in enumerate(options, start=1):
        print(f"  {i}. {text}")

    valid = {str(i) for i in range(1, len(options) + 1)}

    while True:
        choice = input("선택: ").strip()
        if choice.lower() == "q":
            print("프로그램을 종료합니다.")
            sys.exit(0)
        if choice in valid:
            return choice
        print(f"  {', '.join(sorted(valid))} 중 하나를 입력하세요.")

## 맨 마지막에 사용자에게 종료/재시작/오류보고서 작성 중 하나를 선택하도록 하는 함수입니다.
## def _prompt_choice(options: list) -> str: 를 세부적으로 사용하는 함수들

def get_final_choice() -> str:
    """종료 / 재시작 / 오류보고서 중 선택 → '1' | '2' | '3'"""
    print("\n다음 중 선택하세요:")
    return _prompt_choice(["종료", "새 데이터로 다시 시작", "오류 보고서 작성"])

## 오류 보고서 작성시, 작성 후 사용자에게 종료/재시작 중 하나를 선택하도록 하는 함수입니다.
def get_post_report_choice() -> str:
    """오류보고서 작성 후 선택 → '1'(종료) | '2'(재시작)"""
    print("\n오류 보고서를 저장했습니다. 이후 동작을 선택하세요:")
    return _prompt_choice(["종료", "새 데이터로 다시 시작"])

## raw_input vs parsed 비교로 에러 유형을 자동 추정하는 함수입니다.
def _auto_error_type(raw_input: str, parsed: dict) -> str:
    """raw_input과 parsed를 비교해 error_type을 자동 추정한다."""
    meta_keys = {"sex", "age", "pregnant", "nursing"}
    parsed_nutrients = [k for k in parsed if k not in meta_keys]

    parts = [p.strip() for p in raw_input.split(",")]
    raw_nutrients = [p for p in parts[3:] if ":" in p]

    if len(parsed_nutrients) == 0:
        return "파싱_전체실패"
    elif len(parsed_nutrients) < len(raw_nutrients):
        return "파싱_일부누락"
    else:
        return "결과_의심"

## 오류 보고서 작성 함수입니다. 누적 CSV 파일에 한 행씩 추가합니다.
def write_error_report(raw_input: str, parsed: dict) -> None:
    """오류 보고서를 results/report_accumulation.csv 에 누적 저장한다."""
    RESULT_DIR.mkdir(parents=True, exist_ok=True)                       ## make if needed
    csv_path = RESULT_DIR / "report_accumulation.csv"

    # 기존 행 수 파악 (헤더 제외) → 몇 번째 보고서인지 계산
    header_needed = not csv_path.exists()       ## 파일 없으면 바로 header_needed 구동
    existing_rows = 0
    if not header_needed:
        with csv_path.open("r", encoding="utf-8") as f:
            existing_rows = sum(1 for _ in f) - 1  # 헤더 제외
    report_no = existing_rows + 1
    data_row  = report_no + 1  # 헤더가 1행이므로

    # 앞서 입력한 정보를 비고로 표시
    error_type = _auto_error_type(raw_input, parsed)    ## 자동 분류
    print(f"\n  ─── 입력 정보 확인 (비고) ───")
    print(f"  [원본 입력] {raw_input}")
    print(f"  [파싱 결과] {parsed}")
    print(f"  [에러 자동 분류] {error_type}")
    print(f"  ────────────────────────────")

    # 사용자 입력: 라벨 + 버그 설명 → user_input 컬럼 하나에 합산
    label = input("  라벨 입력 (예: 버그A, 단위오류 등): ").strip()
    if label.lower() == "q":
        print("프로그램을 종료합니다.")
        sys.exit(0)
    memo  = input("  버그/메모 입력: ").strip()
    if memo.lower() == "q":
        print("프로그램을 종료합니다.")
        sys.exit(0)
    user_input = f"[{label}] {memo}"

    with csv_path.open("a", newline="", encoding="utf-8") as f:         ## add 모드로 열람
        writer = csv.writer(f)
        if header_needed:                       ## header_needed -- 없으면 만들자.
            writer.writerow(["timestamp", "raw_input", "parsed", "user_input", "auto-tag"])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), raw_input, parsed, user_input, error_type])

    print(f"  오류 보고서 저장 완료: {csv_path}")
    print(f"  → {report_no}번째 오류 보고서 / CSV {data_row}행에 저장됨")

## HQ 결과를 누적 Excel 파일에 저장하는 함수입니다.          에러 말고 진짜 경로
## CSV와 Excel은 동작 방식이 달라서 else 가 필요
## 에러 모음집은 어차피 CSV로 누적하는게 편해서 CSV로 했지만, 결과 누적은 일반 사용자가 사용할 수도 있기 때문에 Excel로 하는게 편해서 Excel로 했음. 사용 대상에 따라 저장 방식을 달리 하는게 적절하다고 판단했음. 속도도 엑셀이 아마 압축파일 처럼 구동하는거라서 느리다고 생각함. 그래서 결과는 엑셀로, 에러 보고서는 CSV로 누적 저장하는 방식으로 구현했음.

def save_result_to_excel(result: dict, parsed: dict) -> None:
    """HQ 결과를 'results/result_accumulation.xlsx'에 누적 저장한다.
    실행당 1행: timestamp + 성별/나이/연령범주 + 15개 영양소 HQ (미입력은 빈 셀).
    """
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    xlsx_path = RESULT_DIR / "result_accumulation.xlsx"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sex      = parsed["sex"]
    pregnant = parsed.get("pregnant", False)
    nursing  = parsed.get("nursing",  False)

    if pregnant:
        age_val, age_label = "-", "임신부"
    elif nursing:
        age_val, age_label = "-", "수유부"
    else:
        age_val   = parsed["age"]
        age_label = _age_to_group(age_val)

    if xlsx_path.exists():
        wb = openpyxl.load_workbook(xlsx_path)
        ws = wb.active
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(_ACCUM_HEADER)

    row = [ts, sex, age_val, age_label] + [
        round(result[k], 4) if k in result else None for k in SUPP_15
    ]
    ws.append(row)
    wb.save(xlsx_path)

###############################################################
###############################################################
## main 함수 수립 -- 일종의 조립 공장 처럼 작동 #######################
###############################################################
###############################################################

def main() -> None:
    while True:
        # Phase 1: 입력 수집
        raw_input = get_user_input()

        # Phase 2: 파싱
        parsed = parse_input(raw_input)

        # Phase 3: HQ 계산
        result = calculate_hq(parsed, UL_PATH, MHI_PATH)

        # Phase 4: 시각화 저장
        out_path = make_result(result, RESULT_DIR)

        # Phase 5: 결과 출력
        summary_lines = [
            f"  {nutrient}: HQ={hq:.2f}  →  {'안전' if hq < 1 else '⚠ 주의'}"
            for nutrient, hq in result.items()
        ]
        summary = "\n".join(summary_lines)

        print(f"\n{'─' * 50}")
        print(f"결과 저장 위치: {out_path}")
        print()
        print(f"[결과 요약]\n{summary}")
        print()

        danger = {k: v for k, v in result.items() if v >= 1}
        if danger:
            print("  ┌─ ⚠ 주의 필요 영양소 " + "─" * 28)
            for nutrient in sorted(danger, key=lambda x: danger[x], reverse=True):
                print(f"  │  {nutrient.split('(')[0].strip()}")
            print("  └" + "─" * 38)
            print()

        print("  자세한 내용은 결과 파일을 확인하세요.")
        print(f"  결과 파일 위치: {out_path}")
        print(f"  내부적으로 누계: {RESULT_DIR / 'result_accumulation.xlsx'}")

        print(f"{'─' * 50}")

        save_result_to_excel(result, parsed)

        # Phase 5: 선택
        choice = get_final_choice()

### While 안에서도 각 변수(파일) 에 다녀오고 나서 main 통하여 구동하는 섹션 여기서 시작

        if choice == "1":
            print("프로그램을 종료합니다.")
            sys.exit(0)

        elif choice == "2":
            print("새 데이터 입력으로 돌아갑니다.\n")
            continue

        elif choice == "3":
            write_error_report(raw_input, parsed)
            sub_choice = get_post_report_choice()
            if sub_choice == "1":
                print("프로그램을 종료합니다.")
                sys.exit(0)
            # sub_choice == "2" → 루프 처음으로
            print("새 데이터 입력으로 돌아갑니다.\n")


if __name__ == "__main__":
    main()

    ## 지금 본 파일 자체를 import 할 때 실행 안되게 하는 거임. main() 함수는 이 파일이 직접 실행될 때만 구동되고, 다른 파일에서 import 할 때는 구동되지 않음. 그래서 다른 파일에서 get_final_choice() 같은 함수를 import 해서 사용할 때, main() 함수가 실행되는 것을 방지하는 역할을 함. 그 때 갑자기 인터페이스 입력 창이 뜨면 곤란하니까.

    ## 지금 상황에서는 위에 def 해둔 메인으로 가게 되는 것. 실제 구동 시작점은 여기임.
    
