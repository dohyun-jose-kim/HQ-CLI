# HQ Analyzer — 영양제 섭취 위험도 평가 CLI

영양제 섭취량을 입력하면 **위험지수(HQ, Hazard Quotient)** 를 계산하고 시각화 결과를 저장합니다.

---

## Overview

건강기능식품 시장이 성장하면서 영양제를 일상적으로 섭취하는 인구가 늘고 있으나, 과잉 섭취 위험에 대한 인식은 부족합니다. 특히 여러 제품을 병용할 경우 동일 영양소가 중복되어 상한섭취량(UL)을 초과할 수 있습니다.

이 도구는 환경독성학의 위험지수(HQ) 개념을 식품안전 맥락으로 변환하여, 사용자의 영양제 섭취가 안전 범위 내인지를 정량적으로 평가합니다.

> **HQ = (MHI + 보충제 섭취량) / UL**
>
> - **UL** (Tolerable Upper Intake Level): 건강에 악영향 없이 섭취 가능한 최대량
> - **MHI** (Minimum Hazard Intake): 식이를 통한 평균 섭취량 (그룹별)
> - HQ >= 1 → 주의 (상한 초과) / HQ < 1 → 안전

데이터 출처: **국민건강영양조사** (전처리 후 사용)

---

## Quick Start

**실행 환경**: Python 3.10 이상

```bash
# 1. 저장소 클론
git clone https://github.com/dohyun-jose-kim/HQ-CLI.git
cd HQ-CLI

# 2. 가상환경 생성 및 활성화 (uv 사용 권장)
uv venv .venv --python 3.10
source .venv/bin/activate

# 3. 라이브러리 설치
uv pip install -r requirements.txt

# 4. 실행
python main.py
```

필요 라이브러리:

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `pandas` | 3.0.1 | 데이터 로드 및 행 조회 |
| `openpyxl` | 3.1.5 | Excel 읽기/쓰기 |
| `scikit-learn` | 1.8.0 | TF-IDF 코사인 유사도 파싱 |
| `matplotlib` | 3.10.8 | HQ 막대 그래프 시각화 |

---

## Usage

실행하면 아래 순서로 입력을 요청합니다.

```
성별 (남성 / 여성): 남성
출생 년도 (예: 1994): 1993

영양소 입력: 철분: 15mg, 비타민D: 10ug, 아연: 20mg
```

- 영양소는 `영양소명: 용량단위` 형식으로 쉼표(`,`)로 구분해 한 줄에 입력합니다.
- `ug` 은 µg(마이크로그램)으로 자동 인식합니다.
- `--help` — 상세 안내 / `--vv` — 지원 영양소 목록 / `q` — 즉시 종료

> **파싱 방식:** 하드코딩된 영양소 별칭 테이블로 1차 매핑하고, 매핑 실패 시에만 **TF-IDF 코사인 유사도 ML** 로 추정합니다. `main.py` 의 `DEV_MODE = True` 로 변경하면 개발 모드가 활성화됩니다.

---

## Input / Output

### 입력 데이터

| 파일 | 설명 |
|------|------|
| `data/preprocessed/01_UL_Sex-Age_cleaned.xlsx` | 상한섭취량(UL) — 성별/연령별 24행 x 20영양소 |
| `data/preprocessed/02_MHI_Sex-Age_cleaned.xlsx` | 평균 식이 섭취량(MHI) — 성별/연령별 24행 x 17영양소 |

### 출력 결과

실행 후 `results/` 폴더에 저장됩니다.

![예시 결과](assets/example_result.png)

| 파일 | 설명 |
|------|------|
| `HQ_(timestamp).png` | 영양소별 HQ 막대 그래프 (실행마다 생성) |
| `result_accumulation.xlsx` | 누적 결과 — timestamp / 성별 / 나이 / 연령범주 / 영양소별 HQ |
| `report_accumulation.csv` | 오류 보고서 — timestamp / 원본입력 / 파싱결과 / 메모 / 자동태그 |

---

## Supported Nutrients (15종)

| 분류 | 영양소 |
|------|--------|
| 비타민 | 비타민A, 비타민B6, 비타민C, 비타민D, 비타민E |
| 다량 미네랄 | 칼슘, 인, 나트륨 |
| 미량 미네랄 | 아연, 철분, 구리, 망간, 셀레늄, 몰리브덴, 요오드 |

한글/영문/원소기호 모두 입력 가능합니다.

---

## Project Structure

![파이프라인 다이어그램](assets/diagram_overview.png)

```
HQ-CLI/
├── main.py                # 메인 실행 파일
├── initial_reaction.py    # 사용자 입력 수집
├── parsing.py             # 입력 파싱 (딕셔너리 매핑)
├── parsing_v1.py          # difflib 기반 fuzzy 매핑
├── parsing_v2.py          # TF-IDF 코사인 유사도 ML
├── data_processor.py      # HQ 계산
├── result_maker.py        # 시각화
├── requirements.txt
├── data/
│   └── preprocessed/
│       ├── 01_UL_Sex-Age_cleaned.xlsx
│       └── 02_MHI_Sex-Age_cleaned.xlsx
├── results/               # 실행 시 자동 생성
└── docs/                  # 상세 문서
```

---

## Documentation

상세 문서는 `docs/` 폴더에 있습니다.

| 문서 | 내용 |
|------|------|
| [background.md](docs/background.md) | 영양 과잉 평가 배경, HQ 개념, 데이터 설명 |
| [goals.md](docs/goals.md) | 프로젝트 목표 & 버전별 갱신 내역 |
| [requirements_and_capabilities.md](docs/requirements_and_capabilities.md) | 요구사항 & 기능 상세 |
| [limitations.md](docs/limitations.md) | 약점 & 팀 논의 포인트 |
| [analysis.md](docs/analysis.md) | 분석 결과 & 출력 해석 |

---

*개발: 김도현 · 2026*
