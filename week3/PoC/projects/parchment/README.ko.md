# Parchment

**AI 문서 인텔리전스 워크스페이스** — AI 엔지니어링 포트폴리오 프로젝트 중 하나인 Week3 PoC로, 세 가지 기술(이미지/멀티모달 정보추출, PDF 파싱 + 요약, HTML 표 스크래핑)이 서로 분리된 세 개의 데모 탭이 아니라, 하나의 상용 수준 백오피스 도구로 통합되는 과정을 보여줍니다.

> 📄 스크린샷, 아키텍처 다이어그램, 하드웨어 요구사항, 클라우드 비용 추정치까지 담은 전체 이중언어(한국어 기본 / 영어) 운영 가이드: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ 시스템 설계: **[`architecture.md`](architecture.md)** · 🔀 함수 단위 플로우차트: **[`flowchart.md`](flowchart.md)**
> 🧭 Week1/2 PoC와 동일하게 검증된 템플릿 위에 구축했습니다 — 처음부터 물려받은 견고화 내용은 `architecture.md` §5 참고.
> 🎨 **이번 라운드는 요청에 따라 시각적으로 확실히 구별되는 UI를 적용했습니다** — 따뜻한 "파치먼트" 팔레트, 세리프 제목 폰트(Newsreader), 상단 탭 레이아웃으로 Week1/2 PoC의 차가운 회색 사이드바 대시보드 룩을 대체했습니다. 전체 근거는 `architecture.md`의 UI 섹션 참고.

## 무엇을 하는가

| 모듈 | AI 모델 | 무엇을 해볼 수 있나 |
|---|---|---|
| 🧾 **영수증** | Tesseract(OCR) + Qwen2.5-0.5B(구조화) *vs.* SmolVLM-256M(직접 읽기) | 영수증 사진을 업로드하거나 합성 샘플을 선택 — 고전적인 OCR+구조화 파이프라인과 로컬 비전-언어 모델의 직접 답변을 나란히 비교 |
| 📄 **PDF 요약** | `distilbart-cnn-12-6`(로컬) 또는 OpenRouter의 `qwen/qwen3-8b`(옵션) | PDF를 업로드하거나 번들된 실제 연준 보고서를 사용 — 요약문의 모든 숫자를 원문과 교차검증 |
| 🌐 **HTML 표** | BeautifulSoup + pandas (AI 불필요) | 표가 있는 아무 URL이나 붙여넣거나 실제 위키백과 샘플을 사용 — 파싱, 미리보기, CSV로 내보내기 |
| 🗂️ **문서 라이브러리** | `all-MiniLM-L6-v2`(임베딩) + Chroma | 처리된 모든 문서와 자동으로 표시되는 근접 중복(임베딩 유사도 — 검색/RAG 기능 아님, 아래 참고) 확인 |
| 🛠️ **관리자 콘솔** | — | 사용자 관리, AI 호출 감사 로그 열람, 실시간 모델/데이터 상태 확인 |

**6개의 AI 모델**이 연결되어 있습니다 — 다섯 개는 API 키 없이 100% 로컬로 동작하고("로컬 모델을 기본 접근 방식으로" 라는 프로젝트 브리프에 따름), 하나(OpenRouter의 `qwen/qwen3-8b`)는 사용자가 명시적으로 켜야 하는 순수 옵트인 업그레이드입니다 — 이 프로젝트 시리즈(그리고 Week1/2 PoC) 전반에서 쓰인 것과 동일한 "로컬 기본, 클라우드는 선택, 실패해도 독립적으로 격리" 하이브리드 패턴을 따릅니다.

## 빠른 시작

요구사항: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS 또는 Windows), 여유 디스크 약 10GB, 최초 1회 모델/데이터 다운로드를 위한 인터넷 연결.

```bash
cd week3/PoC/projects/parchment
./scripts/setup.sh      # 최초 1회: 이미지 빌드, 빈 포트 탐색, 컨테이너 시작
```

이게 끝입니다 — API가 응답하면 스크립트가 URL을 출력합니다(예: `http://localhost:8740`). 다섯 개의 로컬 AI 모델과 샘플 데이터는 최초 부팅 시 백그라운드에서 계속 다운로드/워밍업됩니다(`docker compose logs -f`로 확인 가능). UI는 즉시 사용할 수 있으며, 모델이 아직 준비되지 않았다면 첫 사용 시 단순히 대기합니다.

```bash
./scripts/run.sh              # 이후 재시작 시 — 빌드된 이미지를 재사용해 빠름
./scripts/stop.sh             # 컨테이너 정지 (데이터·컨테이너 삭제 아님)
./scripts/verify_e2e.sh       # 전체 end-to-end 검증 실행 (아래 참고)
./scripts/download_models.sh  # (옵션) CLI로 로컬 AI 모델 5개 강제 다운로드/검증
./scripts/download_data.sh    # (옵션) 샘플 문서 강제 재준비
```

모델 다운로드를 포함한 모든 과정이 오직 셸 스크립트만으로 이루어집니다 — 수동 `docker exec`, 노트북, UI 클릭이 전혀 필요 없습니다.

**데모 관리자 계정**: `admin@parchment.local` / `ChangeMe123!` (실제로 사용하기 전 `.env`의 `ADMIN_PASSWORD`를 변경하세요). 아니면 로그인 페이지에서 직접 계정을 만들어도 됩니다.

Windows에서는 Git Bash 또는 WSL2에서 이 `.sh` 스크립트들을 실행하세요(이 프로젝트 시리즈의 다른 `env_set_up.sh`/`run.sh` 스크립트에서도 이미 쓰인 것과 동일한 셸입니다).

## 프로젝트 구조

```
parchment/
├── backend/           FastAPI 앱 (Python 3.11) — backend/app/ 참고
│   ├── app/
│   │   ├── main.py          엔트리포인트, 시작 부트스트랩, SPA 정적 파일 서빙
│   │   ├── config.py        모든 설정, *_api_key_file 참조 포함 (하드코딩된 시크릿 없음)
│   │   ├── models.py        SQLAlchemy ORM (SQL 저장소)
│   │   ├── vectorstore.py   Chroma 래퍼 + 순수 Python 폴백 (벡터 저장소)
│   │   ├── security.py      JWT + bcrypt 인증
│   │   ├── ml/               ocr.py · vlm.py · llm.py · summarizer.py · embeddings.py · dedupe.py
│   │   ├── etl/               sample_receipts.py · sample_pdf.py · pdf_utils.py · html_utils.py
│   │   └── routers/          auth · receipts · pdfs · tables · library · admin · health
│   └── verify_e2e.py   end-to-end 스모크 테스트 (scripts/verify_e2e.sh 참고)
├── frontend/           React + TypeScript + Vite + Tailwind SPA
│   └── src/            pages/ (Dashboard, Receipts, Pdfs, Tables, Library, Admin, Login)
├── docker/Dockerfile   멀티스테이지 빌드 (Node 빌드 스테이지 -> Python 전용 런타임 이미지,
│                       + OCR/PDF용 tesseract-ocr/-kor + poppler-utils)
├── docker-compose.yml  단일 서비스, 네임드 볼륨, 자동 선택된 호스트 포트
├── scripts/            setup.sh · run.sh · stop.sh · verify_e2e.sh · download_data.sh · download_models.sh
├── data/SOURCES.md     데이터셋 출처, 라이선스, 직접 다운로드 링크
├── architecture.md     시스템 다이어그램(Mermaid) + 상용 확장 노트 + 비용 추정
├── flowchart.md        기능별 함수 단위 플로우차트(Mermaid)
└── docs/guide.html     올인원 이중언어 운영 가이드 (아래 참고)
```

## Streamlit 대신 FastAPI + React를 선택한 이유

Week1/2 PoC와 동일한 이유입니다: 이런 종류의 도구를 빠르게 처음 만들면 보통 Streamlit 기반(탭 몇 개, 인증 없음, 관리자 없음)이 됩니다 — 짧은 단발성 실습용으로는 괜찮은 선택이지만, 이 PoC는 상용 수준의 완성도를 목표로 합니다: 지속되는 인증, 역할 기반 관리자 콘솔, 타입이 있는 REST API(FastAPI 덕분에 `/docs`가 무료로 제공), 그리고 — 이번 라운드에서 특히 — 완전한 디자인 시스템 제어(Streamlit의 컴포넌트 세트로는 표현할 수 없는 커스텀 세리프/파치먼트 비주얼 아이덴티티). 자세한 내용은 `architecture.md` §2 참고.

## Python뿐 아니라 TypeScript를 쓰는 이유

Week1/2 PoC와 동일한 이유입니다 — 프런트엔드가 TypeScript(React + Vite + Tailwind)인 것은 실제 상용 제품들이 Python AI 백엔드와 짝을 이루는 방식이기 때문입니다. Node는 배포된 컨테이너 안에서 전혀 실행되지 않습니다(멀티스테이지 `docker/Dockerfile` 참고).

## 문서 라이브러리의 "중복 탐지"에 대한 참고 (RAG 아님)

문서 라이브러리는 처리된 모든 문서를 임베딩해 근접 중복을 확인합니다 — 진짜 벡터 데이터베이스 기반 기능이지만, 검색이나 검색증강생성(RAG) 기능은 의도적으로 **아닙니다**. 완전한 embeddings + ChromaDB + retrieve-then-answer 검색 기능은 그 자체로 상당한 규모의 프로젝트입니다. 이 PoC는 "비정형 문서를 구조화된 데이터로 바꾼다"는 본래 목표에 범위를 맞추고, 벡터 스토어는 좁고 뚜렷이 다른 목적(재제출된 영수증/보고서 포착)에만 사용해, 슬그머니 절반만 완성된 두 번째 제품이 되지 않도록 했습니다. 전체 근거는 `architecture.md` 참고.

## End-to-end 검증

`scripts/verify_e2e.sh`는 실행 중인 컨테이너에 대해 `backend/verify_e2e.py`를 실제 HTTP로(목킹 없이) 실행합니다: 5개 로컬 모델이 모두 워밍업될 때까지 대기 → 회원가입 → JWT 인증 → 샘플 영수증 추출(OCR+구조화 vs. VLM 나란히 비교) → 동일 샘플 재처리 시 중복으로 표시되는지 확인 → 업로드된 영수증 추출 → 샘플 PDF 요약(숫자 교차검증 포함) → 샘플 HTML 표 파싱 → 문서 라이브러리에 표시된 중복이 반영되는지 확인 → 일반 사용자가 `/api/admin/*`에서 올바르게 거부되는지 확인 → 관리자 계정은 정상적으로 읽을 수 있는지 확인. 이 빌드의 실제 실행 결과는 [`../../history/v1.0.0.md`](../../history/v1.0.0.md)에 기록되어 있습니다.

## 데이터 & 라이선스

실제 데이터와 합성 데이터 모두 자동으로 준비됩니다(수동 단계, 계정, API 키 불필요) — 전체 인용 정보와 직접 다운로드 링크는 [`data/SOURCES.md`](data/SOURCES.md)에 있습니다:

- **영수증**: Pillow로 생성한 합성 데모 영수증 (실제 PII 없음 — 실제 영수증 이미지에는 잘 알려진 PII 위험이 있기 때문에, 이 프로젝트는 실제 영수증을 사용하는 대신 문제 자체를 완전히 피해갑니다).
- **PDF**: 실제 연방준비제도 통화정책보고서 (`federalreserve.gov`, 공개 도메인 미국 정부 간행물).
- **HTML 표**: 실제 위키백과 페이지 (CC BY-SA 4.0, 출처 표기) — 진짜 구조화된 `<table>` 데이터.

## 크레딧

이 PoC는 원본 저작물로, 공개적으로 문서화된 모델 ID, API, 데이터셋을 사용하며 `docs/guide.html`과 `data/SOURCES.md`에 전체 출처가 인용되어 있습니다. 다른 저장소에서 애플리케이션 코드를 복사한 부분은 없습니다 — 아키텍처는 동일 저자의 Week1/2 PoC에서 검증된 패턴(인증, 부트스트랩 격리, 준비 상태 프로빙)을 의도적으로 재사용했고, 탭 구조(이미지 추출·PDF 요약·HTML 표 스크래핑을 세 개의 탭으로 구성)는 이런 종류의 문서-인테이크 도구에 흔히 쓰이는 범용적인 형태를 따랐습니다.

## 라이선스

포트폴리오 프로젝트 — 라이선스 관련 맥락은 최상위 저장소를 참고하세요. 서드파티 데이터셋/모델은 `data/SOURCES.md`에 문서화된 대로 각자의 라이선스를 따릅니다.
