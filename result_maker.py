# Phase 4: 결과 시각화 — HQ 가로 막대그래프 PNG 생성
from datetime import datetime
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")   # GUI 없이 파일로만 저장 (CLI 환경)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

plt.rcParams["font.family"]        = ["AppleGothic", "DejaVu Sans"]  # AppleGothic: 한글, DejaVu: µ 등 특수문자 폴백
plt.rcParams["axes.unicode_minus"] = False  # 마이너스 부호 깨짐 방지


def make_result(result: dict, result_dir: Path) -> Path:
    """HQ 결과를 가로 막대그래프로 시각화하고 PNG로 저장한다.

    Args:
        result:     calculate_hq() 반환값 {영양소명: HQ값, ...}
        result_dir: 결과 저장 폴더 경로 (없으면 자동 생성)

    Returns:
        저장된 PNG 파일 경로
    """
    result_dir = Path(result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    # ── 데이터 정렬: HQ 값 오름차순 ─────────────────────────────────────────
    # barh 는 리스트 순서대로 아래 → 위로 그려진다.
    # 오름차순(reverse=False)으로 정렬하면 HQ 가 높은(위험한) 영양소가
    # 리스트 끝 → 그래프 맨 위(시선이 먼저 가는 위치)에 표시된다.
    nutrients = list(result.keys())
    hq_values = [result[n] for n in nutrients]
    paired    = sorted(zip(hq_values, nutrients), reverse=False)
    hq_values, nutrients = zip(*paired) if paired else ([], [])

    # 표시용 레이블: 단위 괄호 제거 (예: "Iron(mg)" → "Iron")
    labels = [re.sub(r"\(.*?\)", "", n).strip() for n in nutrients]

    # ── 색상: HQ < 1 → 초록, HQ ≥ 1 → 빨강 ────────────────────────────────
    colors = ["#e05c5c" if v >= 1 else "#5cae5c" for v in hq_values]

    # ── 그래프 ──────────────────────────────────────────────────────────────
    fig_height = max(3, len(nutrients) * 0.6 + 1.5)
    fig, ax = plt.subplots(figsize=(9, fig_height))

    bars = ax.barh(labels, hq_values, color=colors, edgecolor="white", height=0.6)

    # HQ=1 기준선
    ax.axvline(x=1.0, color="red", linestyle="--", linewidth=1.4, label="HQ = 1 (상한)")

    # 막대 끝에 수치 표시
    for bar, val in zip(bars, hq_values):
        ax.text(
            val + 0.01, bar.get_y() + bar.get_height() / 2,
            f"{val:.2f}",
            va="center", ha="left", fontsize=8.5
        )

    # 범례
    safe_patch = mpatches.Patch(color="#5cae5c", label="안전 (HQ < 1)")
    warn_patch = mpatches.Patch(color="#e05c5c", label="주의 (HQ ≥ 1)")
    # 범례를 그래프 영역 밖 우상단(제목 오른쪽)에 배치
    # bbox_to_anchor=(1.01, 1.0): axes 우측 상단 바깥
    # loc="upper left": 범례 박스의 좌상단 꼭짓점을 그 좌표에 맞춤
    # bbox_inches="tight" (savefig)가 있어 잘림 없이 저장됨
    ax.legend(handles=[safe_patch, warn_patch, ax.get_lines()[0]],
              bbox_to_anchor=(1.01, 1.0), loc="upper left",
              borderaxespad=0, fontsize=8)

    ax.set_xlabel("HQ (위험지수)", fontsize=10)
    ax.set_title("영양소 과잉섭취 위험지수 (HQ)\n"
                 "HQ = (평균 식이 섭취량 + 보충제 섭취량) / 상한섭취량",
                 fontsize=11, pad=10)
    ax.set_xlim(left=0)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()

    # ── 저장 ────────────────────────────────────────────────────────────────
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = result_dir / f"HQ_{ts}.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return out_path
