# Fix need - 영양소 입력 방법: 단위 무엇을 하던 변환이 되는지 , 사용가능한 단위는 무엇무엇이 있는지 제시해줄 필요가 있음.

# Phase 1: 초기 반응 - 안내 메시지 출력 및 사용자 입력 수집
import datetime
import sys

# ── 상수 ───────────────────────────────────────────────────────────────────────
_W = 70  # 배너 너비

BANNER = (
    "━" * _W + "\n"
    "  영양제 섭취 위험도 평가  |  HQ Analyzer\n"
    + "━" * _W + "\n"
    "  현재 드시는 영양제 정보를 입력하시면\n"
    "  영양소 과잉 복용 여부를 확인할 수 있습니다.\n"
    "  * 각 항목 입력 중 --help 를 입력하면 상세 안내를 볼 수 있습니다.\n"
    + "━" * _W
)

HELP_TEXT = """
[도움말] """ + "─" * 44 + """
성별    : 남성 또는 여성 중 하나를 입력하세요.
출생년도: 4자리 숫자로 입력하세요 (예: 1994, 2005). (년 나이로 인식 됩니다. age = 당해년도 - 출생년도)
임산부/수유부 여부:
  "임산부"  ← 임산부, 임신중, 임신 (관계 없이 인식 됩니다.)
  "수유부"  ← 수유부, 수유중, 수유 
  "해당없음" ← 해당없음, 없음, 아니오, 아니요, N, No
  (남성인 경우 이 항목은 자동으로 건너뜁니다)

영양소 입력 방법:
  영양소명: 용량단위 형식으로 쉼표(,)로 구분합니다.
  예) 비타민D: 10ug, 비타민C: 500mg, 아연: 8mg
  ※ ug 은 µg (마이크로그램) 으로 인식합니다.                    

사용 가능한 영양소 (15종):  영양소 목록 확인은 --vv 를 입력하세요.
""" + "─" * 44


# 임산부여부 동의어 매핑 (소문자로 비교)
_PREG_MAP = {
    "임산부": "임산부",
    "임신중": "임산부", 
    "임신": "임산부",
        "수유부": "수유부", 
        "수유중": "수유부", 
        "수유": "수유부",
            "해당없음": "해당없음", 
            "없음": "해당없음",
            "아니오": "해당없음", 
            "아니요": "해당없음",
            "n": "해당없음", 
            "no": "해당없음",
}

# 성별 동의어 매핑
_SEX_MAP = {
    "남성": "남성",
    "남": "남성",
        "여성": "여성", 
        "여": "여성",
}


# ── 내부 헬퍼 ──────────────────────────────────────────────────────────────────

def _show_help() -> None:
    print(HELP_TEXT)


def _show_aliases() -> None:
    """지원 영양소 카테고리별 목록 출력."""
    print()
    print("[지원 영양소 목록 (15종)] " + "─" * 22)
    print("  [비타민]")
    print("    비타민A, 비타민B6, 비타민C, 비타민D, 비타민E")
    print("  [다량 미네랄]")
    print("    칼슘, 인, 나트륨")
    print("  [미량 미네랄]")
    print("    아연, 철분, 구리, 망간, 셀레늄, 몰리브덴, 요오드")
    print("─" * 46)
    print("  한글·영문·원소기호 모두 입력 가능합니다. (--help 참고)")


def _ask(prompt: str) -> str:
    """입력 받기. --help 이면 도움말 출력 후 재질문. 빈 입력은 재질문. q 이면 종료."""
    while True:
        val = input(prompt).strip()
        if val.lower() == "q":
            print("프로그램을 종료합니다.")
            sys.exit(0)
        if val.lower() == "--help":
            _show_help()
        elif val:
            return val


def _ask_sex() -> str:
    """남성/여성 입력 + 유효성 검증. 반환: '남성' | '여성'"""
    while True:
        val = _ask("성별 (남성 / 여성): ")
        normalized = _SEX_MAP.get(val)
        if normalized:
            return normalized
        print("  '남성' 또는 '여성' 으로 입력해 주세요.")


def _ask_age() -> str:
    """출생년도 입력(1001~2999) → 올해 - 출생년도 = 나이. 반환: str(int)"""
    today_year = datetime.date.today().year
    while True:
        val = _ask("출생 년도 (예: 1994): ")
        if val.isdigit():
            birth = int(val)
            if 1001 <= birth <= 2999:
                age = today_year - birth
                if age > 0:
                    return str(age)
        print(f"  1001~2999 사이의 출생년도를 입력해 주세요.")


def _ask_preg(sex: str) -> str:
    """임산부/수유부/해당없음 입력. 남성이면 즉시 '해당없음' 반환."""
    if sex == "남성":
        return "해당없음"

    while True:
        val = _ask("임산부/수유부 여부 (임산부 / 수유부 / 해당없음): ")
        normalized = _PREG_MAP.get(val.lower())
        if normalized:
            if normalized in ("임산부", "수유부"):
                print("  * 임산부/수유부로 설정 시 입력하신 연령은 반영되지 않습니다.")
            return normalized
        print("  '임산부', '수유부', '해당없음' 중 하나를 입력해 주세요.")


def _ask_nutrients() -> str:
    """영양소 입력 안내 출력 후 한 줄 입력 받기. 최소 1개 이상 필수."""
    print()
    print("[영양제 섭취 정보]")
    print("아래와 같은 형식으로 영양제 섭취량을 입력해 주세요.")
    print("  형식: 영양소명: 용량단위, 영양소명: 용량단위, ...")
    print("  예시: 비타민D: 10ug, 철분: 8mg, 칼슘: 200mg")
    print("단위는 자동 변환 됩니다 ※ ug = µg(마이크로그램)")
    print("입력하지 않은 영양소는 자동 0 처리됩니다.")
    print("  --help: 도움말  |  --vv: 지원 영양소 목록")

    while True:
        val = input("영양소 입력: ")
        if val.lower() == "q":
            print("프로그램을 종료합니다.")
            sys.exit(0)
        if val.lower() == "--help":
            _show_help()
            print()
            print("[영양제 섭취 정보]")
            print("  형식: 영양소명: 용량단위, 영양소명: 용량단위, ...")
            print("  예시: 비타민D: 10ug, 철분: 8mg, 칼슘: 200mg")
        elif val.lower() == "--vv":
            _show_aliases()
        elif val:
            return val
        else:
            print("  영양소를 최소 1개 이상 입력해 주세요.")


# ── 외부 임포팅 할 때 쓰게되는 함수 ───────────────────────────────────────────────────────────────────
# 외부에서 호출할 함수는 이 부분에 작성합니다. (Phase 1의 메인 함수인 상황입니다)


def get_user_input() -> str:
    """배너 출력 → 단계별 입력 수집 → raw string 반환.

    Returns:
        str: "성별, 나이, 임산부여부, 영양소A: 10ug, 영양소B: 8mg"
    """
    print(BANNER)
    print()

    sex       = _ask_sex()
    age       = _ask_age()
    preg      = _ask_preg(sex)
    nutrients = _ask_nutrients()

    return f"{sex}, {age}, {preg}, {nutrients}"
