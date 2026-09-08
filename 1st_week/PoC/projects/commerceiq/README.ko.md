# CommerceIQ

[English](README.md) | **한국어**

**AI 커머스 운영 플랫폼** — 세 가지 AI 영역(비전 트랜스포머, 확산 기반 이미지 생성, 시계열 예측/이상 탐지)이 서로 분리된 데모가 아니라 하나의 상용 수준 제품 안에서 어떻게 결합되는지 보여주는 PoC입니다.

> 📄 스크린샷, 아키텍처 다이어그램, 하드웨어 요구 사항, 클라우드 비용 추정치를 포함한 전체 이중 언어(한국어 기본/영어) 운영 가이드: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ 시스템 설계: **[`architecture.ko.md`](architecture.ko.md)** · 🔀 함수 수준 흐름도: **[`flowchart.md`](flowchart.md)**

## 주요 기능

| 모듈 | AI 모델 | 체험할 수 있는 기능 |
|---|---|---|
| 🖼️ **카탈로그 비전** | `WinKawaks/vit-tiny-patch16-224` (ViT) | 업로드한 상품 사진을 분류하거나 Grocery Store Dataset의 샘플을 클릭 한 번으로 분류 |
| 🎨 **생성형 스튜디오** | `segmind/tiny-sd` (경량화된 Stable Diffusion) | 텍스트 프롬프트로 상품/마케팅 이미지 생성 |
| 📈 **수요 예측 및 이상 탐지 레이더** | `statsmodels` (Holt-Winters) + 로컬 `Qwen/Qwen2.5-0.5B-Instruct` 또는 OpenRouter의 `qwen/qwen3-8b`(선택 사용) | 실제 영국 전자상거래 거래 데이터(UCI Online Retail)의 일별 매출 예측, 이상치 확인, AI가 작성한 비즈니스 인사이트 열람 |
| 🔎 **시맨틱 카탈로그 검색** | `intfloat/multilingual-e5-small` + Chroma 벡터 저장소 | 분류된 카탈로그 상품을 한국어나 영어의 자연어로 검색 |
| 🛠️ **관리자 콘솔** | — | 사용자 관리, AI 호출 감사 추적 조회, 실시간 모델/데이터 상태 확인 |

**총 5개의 AI 모델**이 연결되어 있습니다. 이 중 4개는 API 키 없이 100% 로컬에서 실행되며(프로젝트 요구 사항인 "로컬 모델 우선 접근 방식"), OpenRouter의 `qwen/qwen3-8b` 모델 하나만 사용자가 직접 활성화하는 선택적 업그레이드로 제공됩니다. 이는 이 프로젝트 시리즈 전반에서 일관되게 사용한 "로컬 기본, 클라우드 선택 사용, 개별 장애 격리" 하이브리드 패턴입니다.

## 빠른 시작

요구 사항: [Docker Desktop](https://www.docker.com/products/docker-desktop/)(macOS 또는 Windows), 약 10GB의 여유 디스크 공간, 최초 모델/데이터 다운로드를 위한 인터넷 연결.

```bash
cd 1st_week/PoC/projects/commerceiq
./scripts/setup.sh      # 최초 실행: 이미지 빌드, 빈 포트 선택, 컨테이너 시작
```

이것으로 준비가 끝납니다. API가 응답하면 스크립트가 접속 URL(예: `http://localhost:8720`)을 출력합니다. 최초 부팅 시 로컬 AI 모델 4개와 공개 데이터셋 2개가 백그라운드에서 계속 다운로드되고 준비됩니다(`docker compose logs -f`로 확인). UI는 즉시 사용할 수 있으며, 아직 준비되지 않은 모델을 처음 사용할 때만 완료될 때까지 기다립니다.

```bash
./scripts/run.sh             # 이후 실행 시 사용 — 빌드한 이미지를 재사용하므로 빠름
./scripts/stop.sh            # 컨테이너와 데이터를 삭제하지 않고 중지
./scripts/verify_e2e.sh      # 전체 엔드투엔드 검사 실행(아래 참고)
./scripts/download_data.sh   # (선택) 공개 데이터셋 2개 강제 새로고침
./scripts/download_models.sh # (선택) UI 없이 CLI에서 로컬 AI 모델 4개 강제 다운로드/검증
```

모델 다운로드를 포함한 모든 작업은 이 셸 스크립트만으로 수행됩니다. 수동 `docker exec`, 노트북, UI 클릭은 필요하지 않습니다. `setup.sh`와 `run.sh`가 최초 부팅 시 이미 백그라운드 모델 다운로드를 자동으로 시작합니다. `download_models.sh`는 같은 단계를 명시적인 동기식 CLI 명령으로 제공할 뿐이며, 데모 전에 모델을 미리 준비하거나 4개 모델이 모두 존재하는지 확인할 때 유용합니다.

**데모 관리자 로그인**: `admin@commerceiq.local` / `ChangeMe123!` (실제 환경에서 사용하기 전에 `.env`의 `ADMIN_PASSWORD`를 변경하세요). 로그인 페이지에서 직접 일반 계정을 만들어도 됩니다.

Windows에서는 Git Bash 또는 WSL2에서 이 `.sh` 스크립트를 실행하세요. 이 프로젝트 시리즈의 다른 `env_set_up.sh`/`run.sh` 스크립트에서도 같은 셸을 사용합니다.

## 프로젝트 구조

```text
commerceiq/
├── backend/           FastAPI 앱(Python 3.11) — backend/app/ 참고
│   ├── app/
│   │   ├── main.py          진입점, 시작 초기화, SPA 정적 파일 제공
│   │   ├── config.py        모든 설정과 *_api_key_file 참조(비밀값 하드코딩 없음)
│   │   ├── models.py        SQLAlchemy ORM(SQL 저장소)
│   │   ├── vectorstore.py   순수 Python 대체 구현을 포함한 Chroma 래퍼(벡터 저장소)
│   │   ├── security.py      JWT + bcrypt 인증
│   │   ├── jobs.py          백그라운드 작업 관리자(확산 이미지 생성)
│   │   ├── ml/              vision.py · diffusion.py · embeddings.py · llm.py · forecast.py
│   │   ├── etl/             online_retail.py · sample_catalog.py(공개 데이터셋 다운로드)
│   │   └── routers/         auth · vision · generate · forecast · search · admin · health
│   └── verify_e2e.py   엔드투엔드 스모크 테스트(scripts/verify_e2e.sh 참고)
├── frontend/           React + TypeScript + Vite + Tailwind SPA
│   └── src/            pages/(Dashboard, CatalogVision, GenerativeStudio, Forecasting, Search, Admin, Login)
├── docker/Dockerfile   다단계 빌드(Node 빌드 단계 → Python 전용 런타임 이미지)
├── docker-compose.yml  단일 서비스, 명명된 볼륨, 호스트 포트 자동 선택
├── scripts/            setup.sh · run.sh · stop.sh · find_free_port.sh · download_data.sh · verify_e2e.sh
├── data/SOURCES.md     데이터셋 출처, 라이선스, 직접 다운로드 링크
├── architecture.md     시스템 다이어그램(Mermaid), 프로덕션 확장 참고 사항, 비용 추정
├── architecture.ko.md  시스템 아키텍처 한국어판
├── flowchart.md        기능별 함수 수준 흐름도(Mermaid)
└── docs/guide.html     일체형 이중 언어 운영 가이드(아래 참고)
```

## Streamlit 대신 FastAPI + React를 선택한 이유

Streamlit은 간단한 단일 목적 데모에는 좋은 선택입니다. 그러나 이 PoC는 요구 사항에서 상용 수준 UI/UX를 명시했기 때문에 한 단계 더 나아갑니다. 서로 다른 6개 화면 간 클라이언트 측 라우팅, Streamlit 기본 차트로 표현하기 어려운 설계형 차트(예측값 + 신뢰 구간 + 이상치 표시), 지속되는 인증 세션, 모바일 클라이언트나 다른 내부 서비스가 나중에 재사용할 수 있는 타입 기반 REST API(FastAPI가 `/docs`를 자동 제공)가 필요하기 때문입니다. 자세한 근거는 `architecture.ko.md` §2를 참고하세요.

## Python만 사용하지 않고 TypeScript를 선택한 이유

프로젝트 요구 사항은 GenAI/AX 작업이 한 가지 언어에 갇혀 있지 않음을 보여주도록 권장합니다. 프런트엔드에 TypeScript(React + Vite + Tailwind)를 사용한 이유는 실제 상용 제품에서 Python AI 백엔드와 함께 흔히 사용하는 조합이기 때문입니다. 타입이 지정된 컴포넌트 계층, 핫 리로드 개발 서버, 정적 파일로 배포되는 프로덕션 빌드를 제공합니다. 배포된 컨테이너에서는 Node가 전혀 실행되지 않습니다. 자세한 내용은 다단계 `docker/Dockerfile`을 참고하세요.

## 엔드투엔드 검증

`scripts/verify_e2e.sh`는 실행 중인 컨테이너 내부에서 `backend/verify_e2e.py`를 실제 HTTP로 실행하며 모의 객체를 사용하지 않습니다. 검사 순서는 다음과 같습니다: `GET /api/health/ready`로 로컬 모델 4개가 모두 준비될 때까지 대기 → 회원가입 → JWT 인증 → 샘플 이미지 분류(ViT) → 업로드 이미지 분류 → 확산 이미지 생성 작업 제출 및 폴링(tiny-sd) → 로컬 LLM 인사이트를 포함한 예측 실행(Qwen2.5-0.5B) → 시맨틱 검색(e5-small + Chroma) → 일반 사용자의 `/api/admin/*` 접근이 올바르게 거부되는지 확인 → 관리자 계정의 접근 가능 여부 확인. 각 단계마다 PASS/FAIL을 출력합니다. 이 빌드의 실제 결과는 [`../../history/v1.0.0.md`](../../history/v1.0.0.md)에 기록되어 있습니다.

## 데이터 및 라이선스

공개 데이터셋 2개를 자동으로 다운로드하며, 수동 작업이나 계정/API 키가 필요하지 않습니다. 전체 인용 정보와 직접 다운로드 링크는 [`data/SOURCES.md`](data/SOURCES.md)를 참고하세요.

- **UCI "Online Retail"**(CC BY 4.0) — 영국의 실제 전자상거래 거래 데이터로, 수요 예측에 사용합니다.
- **GroceryStoreDataset 샘플 이미지**(MIT License, Klasson 외, WACV 2019) — 카탈로그 비전 데모에 사용하는 상품 사진 20장입니다.

## 저작권 및 출처

이 PoC는 독창적인 작업입니다. 공개 문서에 명시된 모델 ID, API, 데이터셋을 사용했으며, 출처는 `docs/guide.html`과 `data/SOURCES.md` 전반에 기재되어 있습니다. 다른 저장소의 애플리케이션 코드를 복사하지 않았습니다.

## 라이선스

포트폴리오 PoC입니다. 라이선스 맥락은 최상위 저장소를 참고하세요. 제3자 데이터셋과 모델에는 `data/SOURCES.md`에 명시된 각각의 라이선스가 그대로 적용됩니다.
