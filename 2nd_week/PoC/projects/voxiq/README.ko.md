# VoxIQ

**AI 회의·지식 인텔리전스 플랫폼** — AI 엔지니어링 포트폴리오 프로젝트의 일부로, 네 가지 서로 다른 AI 기술(임베딩·리랭킹, 오디오 음성인식, 코드 실행 샌드박스, LLM 내부구조)이 네 개의 개별 데모가 아니라 하나의 상용급 제품 안에서 어떻게 결합되는지 보여줍니다.

> 📄 스크린샷·아키텍처 다이어그램·하드웨어 요구사항·클라우드 비용 추정까지 담은 전체 이중언어(한국어 기본 / 영어) 운영 가이드: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ 시스템 설계: **[`architecture.md`](architecture.md)** · 🔀 함수 단위 플로우차트: **[`flowchart.md`](flowchart.md)**
> 🧭 이 시리즈의 이전 제품인 CommerceIQ와 동일한 검증된 템플릿 위에 구축했습니다 — 이 빌드가 처음부터 적용하는 하드닝 내역은 그 프로젝트의 `debug/`를 참고하세요.

## 무엇을 하는가

| 모듈 | AI 모델 | 무엇을 해볼 수 있는가 |
|---|---|---|
| 🎙️ **회의 전사** | Whisper (`tiny`) | 직접 오디오를 업로드하거나, 공개 도메인 샘플(JFK 연설 + LibriSpeech 클립 5개)을 원클릭으로 전사 |
| 🔎 **지식 검색** | `all-MiniLM-L6-v2` (bi-encoder) + `ms-marco-MiniLM-L-6-v2` (cross-encoder) | 실제 미국 연방준비제도(FOMC) 회의록 7건과 사용자가 전사한 회의록을 대상으로, bi-encoder와 cross-encoder 순위를 나란히 비교 검색 |
| 🧮 **분석 에이전트** | `Qwen2.5-0.5B-Instruct` (로컬) 또는 OpenRouter의 `qwen/qwen3-8b` (옵션) | 자연어로 질문하면 LLM이 Python 코드를 작성하고, 격리된 로컬 샌드박스에서 회의 데이터를 대상으로 실행 |
| 🔤 **토크나이저 & 어텐션 탐색기** | GPT-2 | 입력한 텍스트에 대한 실제 토큰화 결과 + 셀프어텐션 히트맵 확인 |
| 🛠️ **관리자 콘솔** | — | 사용자 관리, 모든 AI 호출의 감사 로그, 실시간 모델/데이터 상태 확인 |

**6개의 AI 모델**이 연결되어 있습니다 — 5개는 API 키 없이 100% 로컬로 동작하며(프로젝트 브리프의 "로컬 모델을 기본 접근 방식으로" 요구사항), 하나(OpenRouter의 `qwen/qwen3-8b`)는 사용자가 명시적으로 켜야만 사용되는 순수 옵션 업그레이드로, 이 프로젝트 시리즈 전반(CommerceIQ PoC 포함)에서 이미 쓰이는 "로컬 기본, 클라우드는 선택, 독립적으로 실패" 하이브리드 패턴을 그대로 따릅니다.

## 빠른 시작

요구사항: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS 또는 Windows), 여유 디스크 약 10GB, 최초 1회 모델/데이터 다운로드를 위한 인터넷 연결.

```bash
cd 2nd_week/PoC/projects/voxiq
./scripts/setup.sh      # 최초 1회: 이미지 빌드, 빈 포트 탐색, 컨테이너 시작
```

이것으로 끝입니다 — API가 응답하면 스크립트가 URL을 출력합니다(예: `http://localhost:8730`). 5개의 로컬 AI 모델과 2개의 공개 데이터셋은 최초 부팅 시 백그라운드에서 계속 다운로드/워밍업되며(`docker compose logs -f`로 확인 가능), UI는 즉시 사용 가능하고 모델이 아직 준비되지 않았다면 첫 사용 시 자동으로 대기합니다.

```bash
./scripts/run.sh              # 이후 재시작 — 빠름, 빌드된 이미지 재사용
./scripts/stop.sh             # 컨테이너 정지 (삭제나 데이터 손실 없음)
./scripts/verify_e2e.sh       # 전체 end-to-end 검증 실행 (아래 참고)
./scripts/download_models.sh  # (옵션) CLI로 5개 로컬 AI 모델 강제 다운로드/검증
./scripts/download_data.sh    # (옵션) 공개 데이터셋 + FOMC 색인 강제 재다운로드
```

모델 다운로드를 포함한 모든 과정은 오직 셸 스크립트로만 이루어집니다 — 수동 `docker exec`, 노트북, UI 클릭이 전혀 필요 없습니다.

**데모 관리자 계정**: `admin@voxiq.local` / `ChangeMe123!` (실제 사용 전 `.env`의 `ADMIN_PASSWORD`를 변경하세요). 또는 로그인 페이지에서 직접 계정을 만들어도 됩니다.

Windows에서는 Git Bash 또는 WSL2에서 이 `.sh` 스크립트들을 실행하세요 (이 프로젝트 시리즈의 다른 `env_set_up.sh`/`run.sh` 스크립트와 동일한 관례입니다).

## 프로젝트 구조

```
voxiq/
├── backend/           FastAPI 앱 (Python 3.11) — backend/app/ 참고
│   ├── app/
│   │   ├── main.py          엔트리포인트, 부트스트랩, SPA 정적 파일 서빙
│   │   ├── config.py        모든 설정, *_api_key_file 참조 포함 (하드코딩된 시크릿 없음)
│   │   ├── models.py        SQLAlchemy ORM (SQL 저장소)
│   │   ├── vectorstore.py   순수 Python 폴백을 갖춘 Chroma 래퍼 (벡터 저장소)
│   │   ├── security.py      JWT + bcrypt 인증
│   │   ├── ml/               embeddings.py · reranker.py · whisper_asr.py · llm.py · sandbox.py · tokenizer_explorer.py
│   │   ├── etl/               audio_samples.py · fomc_minutes.py (공개 데이터셋 다운로드 + 청킹)
│   │   └── routers/          auth · meetings · search · sandbox · tokenizer · admin · health
│   └── verify_e2e.py   end-to-end 스모크 테스트 (scripts/verify_e2e.sh 참고)
├── frontend/           React + TypeScript + Vite + Tailwind SPA
│   └── src/            pages/ (Dashboard, Meetings, Search, Sandbox, Tokenizer, Admin, Login)
├── docker/Dockerfile   멀티스테이지 빌드 (Node 빌드 스테이지 -> Python 전용 런타임 이미지, Whisper용 ffmpeg 포함)
├── docker-compose.yml  단일 서비스, 네임드 볼륨, 자동 호스트 포트 선택
├── scripts/            setup.sh · run.sh · stop.sh · find_free_port.sh · download_data.sh · download_models.sh · verify_e2e.sh
├── data/SOURCES.md     데이터셋 출처, 라이선스, 직접 다운로드 링크
├── architecture.md     시스템 다이어그램(Mermaid) + 프로덕션 확장 노트 + 비용 추정
├── flowchart.md        기능별 함수 단위 플로우차트(Mermaid)
└── docs/guide.html     올인원 이중언어 운영 가이드 (아래 참고)
```

## Streamlit 대신 FastAPI + React를 택한 이유

CommerceIQ PoC와 동일한 이유입니다: 6개의 서로 다른 화면에 걸친 클라이언트 사이드 라우팅, Streamlit의 기본 컴포넌트로는 깔끔하게 표현하기 어려운 실제 비교 UI(bi- vs. cross-encoder 결과)와 어텐션 히트맵, 영속적인 인증 세션, 그리고 FastAPI가 무료로 제공하는 타입 있는 REST API(`/docs`). `architecture.md` §2 참고.

## Python뿐 아니라 TypeScript를 쓴 이유

CommerceIQ PoC와 동일한 이유입니다 — 프론트엔드가 TypeScript(React + Vite + Tailwind)인 이유는 실제 상용 제품이 Python AI 백엔드와 이런 조합을 사용하기 때문입니다. Node 자체는 배포된 컨테이너에서 전혀 실행되지 않습니다(멀티스테이지 `docker/Dockerfile` 참고).

## 로컬 코드 샌드박스에 대한 참고

분석 에이전트의 코드 실행은 **교육용(teaching-grade)** 격리 경계입니다(subprocess + OS 리소스 제한 + 제한된 `__builtins__` 세트) — 이런 코드 실행 기능에서 흔히 쓰이는 "로컬 폴백" 설계를 이 프로젝트에서 충실히 재현한 것으로, 기본이자(이 빌드에는 E2B API 키가 없으므로) *유일하게 검증된* 실행 경로입니다. 이는 명시적으로 프로덕션 보안 경계가 **아닙니다** — 실제 격리를 위해 무엇이 필요한지는 `backend/app/ml/sandbox.py`의 모듈 docstring과 `docs/guide.html`의 한계 섹션을 참고하세요.

## End-to-end 검증

`scripts/verify_e2e.sh`는 실행 중인 컨테이너에 대해 실제 HTTP로(모킹 없이) `backend/verify_e2e.py`를 실행합니다: 5개 로컬 모델 워밍업 대기 → 회원가입 → JWT 인증 → 샘플 오디오 목록/전사(Whisper) → 업로드 파일 전사 → 지식 검색(bi- vs. cross-encoder) → 분석 에이전트(샌드박스에서 LLM 생성 코드 실행) → 토크나이저/어텐션 탐색기 → 일반 사용자가 `/api/admin/*`에서 올바르게 차단되는지 확인 → 관리자 계정이 접근 가능한지 확인. 이 빌드의 실제 결과는 [`../../history/v1.0.0.md`](../../history/v1.0.0.md)에 기록되어 있습니다.

## 데이터 & 라이선스

두 개의 공개 데이터 소스 모두 자동으로 다운로드됩니다(수동 작업, 계정/API 키 불필요) — 전체 인용 정보와 직접 다운로드 링크는 [`data/SOURCES.md`](data/SOURCES.md)에 있습니다:

- **샘플 오디오**: `openai/whisper`의 공식 `jfk.flac` 테스트 자산(공개 도메인, 미국 대통령 연설) + `hf-internal-testing/librispeech_asr_dummy`(LibriSpeech, CC BY 4.0)에서 가져온 클립 5개.
- **FOMC 회의록**: 실제 미국 연방준비제도 회의 기록 7건(`federalreserve.gov`, 공개 도메인 정부 발간물).

## 크레딧

이 PoC는 원저작물이며, `docs/guide.html`과 `data/SOURCES.md` 전반에 인용된 공개적으로 문서화된 모델 ID, API, 데이터셋을 사용합니다. 외부 저장소에서 복사한 애플리케이션 코드는 없습니다.

## 라이선스

포트폴리오 PoC — 라이선스 관련 맥락은 최상위 저장소를 참고하세요. 서드파티 데이터셋/모델은 `data/SOURCES.md`에 문서화된 대로 각자의 라이선스를 따릅니다.
