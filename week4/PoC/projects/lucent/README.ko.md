# Lucent

**AI 지식 어시스턴트** — Week4 PoC이자, AI 엔지니어링 프로젝트 포트폴리오의 일부로서, 이번 주 핵심 주제(문서 임베딩, VectorDB 검색, 근거 기반 답변 생성)를 실제 스트리밍 RAG 채팅 제품으로 구현했습니다. 단순한 단발성 검색창이 아니라, 실시간 토큰 스트리밍·인라인 인용·모든 답변에 대한 자동 근거검증을 갖춘 다중턴 어시스턴트입니다.

> 📄 스크린샷, 아키텍처 다이어그램, 하드웨어 요구사항, 클라우드 비용 추정까지 포함한 전체 이중언어(한국어 기본 / 영어) 운영 가이드: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ 시스템 설계: **[`architecture.md`](architecture.md)** · 🔀 기능 단위 플로우차트: **[`flowchart.md`](flowchart.md)**
> 🎨 **세 번째로 완전히 다른 시각 정체성** — 그라데이션 메시 배경 위에 반투명 "유리" 패널, 굵기만으로 위계를 표현하는 단일 기하학적 산세리프(Manrope), 그리고 떠 있는 둥근 사이드바 — 더 투명하고 세련된 UI를 명시적으로 요구한 이번 라운드의 요청에 따라 Week1-3 PoC들의 불투명 서페이스 대시보드에서 한 단계 더 나아간 디자인입니다. `architecture.md`의 UI 섹션 참고.
> 🧭 이 패턴의 일반적인 초기 구현(first-pass implementation) 수준을 의도적으로 뛰어넘도록 설계했습니다 — 무엇이, 왜 업그레이드되었는지는 `architecture.md` §2 참고.

## 무엇을 할 수 있나

| 모듈 | AI 모델 | 체험할 수 있는 것 |
|---|---|---|
| ◈ **채팅** | `multilingual-e5-small`(검색) + 선택적 `ms-marco-MiniLM-L-6-v2`(재정렬) + 로컬 `Qwen2.5-0.5B` 또는 OpenRouter의 `qwen/qwen3-8b`(옵트인) | 질문을 입력하고 답변이 토큰 단위로 스트리밍되는 것을 확인, `[n]` 인용 표시를 클릭해 출처로 이동, 실시간 근거검증 배지 확인 |
| ▤ **문서** | `multilingual-e5-small`(색인) | 번들로 제공되는 이중언어 지식베이스(영어 연방주의자 논집 85편 + 동일 주제의 한국어 위키백과 문서)를 둘러보거나 직접 txt/md/pdf 업로드 |
| ⬡ **검색 실험실** | 두 검색 모델을 나란히 표시 | 동일 질의에 대해 cross-encoder 재정렬이 bi-encoder의 최상위 결과를 어떻게 바꾸는지(혹은 바꾸지 않는지) 확인 |
| ⚙ **관리자** | — | 사용자 관리, AI 호출 감사 로그, 실시간 모델 상태, 실제 사용량 분석 대시보드(지연시간 차트, 근거검증 통과율, 검색 모드 비율) |

**4개의 AI 모델**이 연동되어 있습니다 — 3개는 API 키 없이 100% 로컬로 동작하고, 1개(OpenRouter의 `qwen/qwen3-8b`)는 사용자가 직접 켜는 순수 옵트인 업그레이드입니다. 이 프로젝트 시리즈 전반(그리고 Week1-3 PoC들)에서 사용된 "로컬 기본, 클라우드 옵트인, 독립적으로 실패" 하이브리드 패턴을 그대로 따릅니다.

## 빠른 시작

요구사항: [Docker Desktop](https://www.docker.com/products/docker-desktop/)(macOS 또는 Windows), 여유 디스크 ~10GB, 최초 1회 모델/데이터 다운로드를 위한 인터넷 연결.

```bash
cd week4/PoC/projects/lucent
./scripts/setup.sh      # 최초 1회: 이미지 빌드, 빈 포트 자동 탐색, 컨테이너 시작
```

이게 전부입니다 — API가 응답하는 즉시 스크립트가 URL을 출력합니다(예: `http://localhost:8750`). 3개의 로컬 AI 모델과 시드 코퍼스는 최초 부팅 시 백그라운드에서 계속 다운로드/색인됩니다(`docker compose logs -f`로 확인 가능). UI는 즉시 사용 가능하며, 모델이 아직 준비되지 않았다면 최초 사용 시 자동으로 대기합니다.

```bash
./scripts/run.sh              # 이후 매번 — 빌드된 이미지를 재사용해 빠르게 실행
./scripts/stop.sh             # 데이터를 삭제하지 않고 컨테이너만 중지
./scripts/verify_e2e.sh       # 전체 엔드투엔드 검증 실행 (아래 참고)
./scripts/download_models.sh  # (선택) CLI로 로컬 AI 모델 3개를 강제 재다운로드/검증
./scripts/download_data.sh    # (선택) 시드 코퍼스 색인을 강제로 새로고침
```

모델 다운로드를 포함한 모든 과정이 셸 스크립트로 완전히 구동됩니다 — 수동 `docker exec`, 노트북, UI 클릭 조작이 전혀 필요하지 않습니다.

**데모 관리자 로그인**: `admin@lucent.local` / `ChangeMe123!` (실제 사용 전에 `.env`의 `ADMIN_PASSWORD`를 변경하세요). 또는 로그인 페이지에서 직접 계정을 만들 수도 있습니다.

Windows에서는 Git Bash 또는 WSL2에서 이 `.sh` 스크립트들을 실행하세요(이런 셸 스크립트 기반 설정에서 흔히 쓰이는 셸입니다).

## 프로젝트 구조

```
lucent/
├── backend/           FastAPI 앱 (Python 3.11) — backend/app/ 참고
│   ├── app/
│   │   ├── main.py          엔트리포인트, 부트스트랩, SPA 정적 파일 서빙
│   │   ├── config.py        전체 설정, *_api_key_file 참조 포함 (하드코딩된 비밀값 없음)
│   │   ├── models.py        SQLAlchemy ORM (SQL 저장소)
│   │   ├── vectorstore.py   Chroma PersistentClient 래퍼 (벡터 저장소)
│   │   ├── rag.py           채팅 + 검색 실험실이 공유하는 retrieve(-then-rerank) 파이프라인
│   │   ├── security.py      JWT + bcrypt 인증
│   │   ├── ml/               embeddings.py · reranker.py · llm.py (+ 스트리밍) · groundedness.py
│   │   ├── etl/               seed_corpus.py · chunking.py
│   │   └── routers/          auth · documents · chat(스트리밍) · retrieval · admin · health
│   └── verify_e2e.py   엔드투엔드 스모크 테스트 (scripts/verify_e2e.sh 참고)
├── frontend/           React + TypeScript + Vite + Tailwind SPA
│   └── src/            pages/ (Dashboard, Chat, Documents, RetrievalLab, Admin, Login)
├── docker/Dockerfile   멀티스테이지 빌드 (Node 빌드 단계 -> Python 전용 런타임 이미지)
├── docker-compose.yml  단일 서비스, named volume, 호스트 포트 자동 선택
├── scripts/            setup.sh · run.sh · stop.sh · verify_e2e.sh · download_data.sh · download_models.sh
├── data/SOURCES.md     데이터셋 출처, 라이선스, 직접 다운로드 링크
├── architecture.md     시스템 다이어그램(Mermaid) + 상용/클라우드 확장 노트 + 비용 추정
├── flowchart.md         기능별 함수 단위 플로우차트 (Mermaid)
└── docs/guide.html     올인원 이중언어 운영 가이드 (아래 참고)
```

## Streamlit 대신 FastAPI + React를 선택한 이유

Week1-3 PoC들과 동일한 이유이며, 여기서는 특히 더 그렇습니다: 이 RAG 패턴의 일반적인 초기 구현은 단일 세션 실습용으로는 충분한 Streamlit 앱이지만, Lucent에는 진짜 토큰 단위 스트리밍(클라이언트에서 `StreamingResponse` + `fetch()`/`ReadableStream` 조합으로 구현 — Streamlit의 상호작용 시 전체 재실행 모델로는 네이티브하게 불가능), 다중턴 채팅 이력, 그리고 유리 디자인 시스템에 대한 완전한 제어가 필요합니다. 그 기준선 대비 구체적으로 무엇이 업그레이드되었는지는 `architecture.md` §2 참고.

## Python뿐 아니라 TypeScript를 쓰는 이유

Week1-3 PoC들과 동일한 이유입니다 — 프론트엔드가 TypeScript(React + Vite + Tailwind)인 것은 실제 상용 제품이 Python AI 백엔드와 짝을 이룰 때 흔히 선택하는 조합이기 때문입니다. Node 자체는 배포된 컨테이너 안에서 전혀 실행되지 않습니다(멀티스테이지 `docker/Dockerfile` 참고).

## 근거검증(Groundedness Checking)에 대하여

모든 채팅 답변은 "근거 있음"으로 표시되기 전에 두 가지 방식으로 검증됩니다: 모든 `[n]` 인용 표시는 실제로 검색된 출처를 가리켜야 하고(구조적 검사, AI 모델 불필요), 답변의 모든 문장은 검색된 청크 중 최소 하나와 의미적으로 충분히 유사해야 합니다(검색에 사용한 것과 동일한 bi-encoder를 재사용하는 임베딩 유사도 검사). 이는 정적인 배지가 아니라 실제로 계산되는 신호이며, 출처에서 벗어난 실제 생성 결과에 대해서는 실제로 "부분적으로 근거 있음"을 표시하기도 합니다. 이 검사가 무엇을 잡아내고 무엇을 잡아내지 못하는지는 `backend/app/ml/groundedness.py`와 `docs/guide.html`의 한계 섹션 참고.

## 엔드투엔드 검증

`scripts/verify_e2e.sh`는 실제 컨테이너 안에서 `backend/verify_e2e.py`를 진짜 HTTP로 실행합니다(목(mock) 없음) — 실제 클라이언트처럼 스트리밍 응답을 실제로 소비하는 과정까지 포함하며, 단순히 엔드포인트가 200을 반환하는지만 확인하지 않습니다: 로컬 모델 3개가 모두 준비 완료 상태를 보고할 때까지 대기 → 회원가입 → JWT 인증 → 시드 코퍼스(연방주의자 논집 85편 + 한국어 위키백과 문서)가 색인되었는지 확인 → 문서 업로드 → 채팅 세션 생성 → 스트리밍 메시지 전송 후 토큰 조립 → cross-encoder 재정렬을 켠 메시지 전송 → 실제 한국어 질문을 보내 진짜 교차언어 검색이 되는지 확인 → bi-encoder와 cross-encoder 검색 결과 비교 → 일반 사용자가 `/api/admin/*`에서 올바르게 차단되는지 확인 → 관리자 계정이 시스템 상태와 분석 데이터를 읽을 수 있는지 확인. 이 빌드의 실제 결과는 [`../../history/v1.0.0.md`](../../history/v1.0.0.md)에 기록되어 있습니다.

## 데이터 & 라이선스

수동 단계나 계정/API 키 없이 자동으로 다운로드되는 두 개의 실제 공개 출처 지식베이스 시드입니다 — 전체 출처와 직접 다운로드 링크는 [`data/SOURCES.md`](data/SOURCES.md) 참고:

- **영어**: *The Federalist Papers*(85편), Project Gutenberg #18 — 미국 건국 시대의 저작, 퍼블릭 도메인.
- **한국어**: 한국어 위키백과 문서 "연방주의자 논집"(CC BY-SA 4.0) — 영어 코퍼스와 직접적으로 동일한 주제를 다루며, 다국어 임베딩 모델의 교차언어 검색 주장을 실제 질문으로 증명할 수 있도록 특별히 선택했습니다.

## 크레딧

이 PoC는 `docs/guide.html`과 `data/SOURCES.md` 전반에 명시된, 공개적으로 문서화된 모델 ID·API·데이터셋을 사용한 원본 작업물입니다. 다른 저장소에서 복사한 애플리케이션 코드는 없습니다 — 다만 아키텍처 측면에서는 이 저자의 이전 Week1-3 PoC들에서 검증된 패턴(인증, 부트스트랩 단계 분리, readiness probing, retrieve-then-rerank 비교 UX)을 의도적으로 재사용했으며, 임베딩 모델 선택은 다국어 지원(교차언어 검색 데모의 핵심 근거) 때문에 이루어졌습니다.

## 라이선스

포트폴리오 PoC — 라이선스 관련 맥락은 최상위 저장소를 참고하세요. 서드파티 데이터셋/모델은 `data/SOURCES.md`에 명시된 각자의 라이선스를 따릅니다.
