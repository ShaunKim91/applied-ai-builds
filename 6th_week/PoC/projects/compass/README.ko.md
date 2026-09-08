# Compass

**웹 검색 기반 리서치 어시스턴트** — AI 엔지니어링 포트폴리오 프로젝트의 일부인 Week6 PoC로, 이번 주 주제(검색 API, 임베딩 기반 재정렬, 검색+LLM 그라운딩)를 실제 스트리밍 리서치 제품으로 완성했습니다: 실시간 웹 검색, 크로스 인코더 재정렬, 스트리밍되는 인용 포함 리포트, 자동화된 "고스트 인용" 검사, 과거 리서치를 찾을 수 있는 아카이브, OpenRouter의 완전관리형 웹검색 제품과의 실시간 비교, 그리고 이 패턴의 일반적인 기준 구현에서는 흔히 빠지는 비용 통제(예산 상한) 기능까지 담았습니다.

> 📄 스크린샷, 아키텍처 다이어그램, 하드웨어 요구사항, 클라우드 비용 추정치를 포함한 전체 이중언어(한국어 기본 / English) 운영 가이드: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ 시스템 설계: **[`architecture.md`](architecture.md)** (영문) · 🔀 기능 단위 플로우차트: **[`flowchart.md`](flowchart.md)**
> 🧭 **네 번째 독자적인 비주얼 아이덴티티** — 네이비 "차트룸" 팔레트(짙은 네이비 위 브라스 + 틸, 은은한 차트지 그리드), 3단 타입 시스템(세리프 헤드라인, 지오메트릭 산세리프 UI, 모노스페이스 인용 메타데이터), 고정된 "커맨드 콘솔" 검색바 + 접이식 아이콘 레일, 그리고 실제 모션(레이더 스윕 로딩 인디케이터, 스켈레톤-시머 소스 카드) — 이 시리즈에서 처음으로 다크 테마를 기본값으로 채택한 앱입니다. 자세한 내용은 `architecture.md`의 UI 섹션 참고.
> 📈 이 패턴의 일반적인 기준 구현보다 의도적으로 더 발전된 형태입니다 — 그 기준 구현의 기본 경로는 **LLM을 전혀 호출하지 않는** 규칙 기반 템플릿입니다 — 정확히 무엇이, 왜 개선되었는지는 `architecture.md` §2 참고.

## 무엇을 할 수 있나요

| 모듈 | AI 모델 | 체험 포인트 |
|---|---|---|
| ◈ **리서치** | `multilingual-e5-small` + `ms-marco-MiniLM-L-6-v2` (실시간 검색 결과 재정렬) + 로컬 `Qwen2.5-0.5B` 또는 OpenRouter의 `qwen/qwen3-8b`(옵트인) | 질문을 입력하면 Compass가 실시간 웹을 검색하고 인용이 달린 리포트를 스트리밍으로 생성 — 모든 답변에 근거충실도 배지와 고스트 인용 검사가 함께 표시됩니다 |
| ▤ **아카이브** | `multilingual-e5-small` (과거 리포트 인덱싱) | 모든 과거 리서치 리포트에 대한 의미 기반 검색 — 키워드가 아니라 뜻으로 찾습니다 |
| ⬡ **그라운딩 랩** | Compass 자체 파이프라인 vs OpenRouter 관리형 웹검색 플러그인 | 단순히 재정렬기 두 개를 비교하는 게 아니라, 두 개의 완전히 다른 검색 전략을 지연시간·비용·인용 기준으로 나란히 비교 |
| ◎ **트렌드 레이더** | `Qwen2.5-0.5B` 구조화 추출 | AI 도구/트렌드를 비용 / 보안 / 승인 난이도 세 가지 렌즈로, 실제로 찾은 근거에 엄격히 기반해 평가 |
| ⚙ **관리자** | — | 사용자 관리, AI 호출 감사 로그, 실시간 모델·웹검색 상태, 사용 분석, 그리고 도달 시 유료 경로를 자동 차단하는 일일 OpenRouter 지출 상한 |

**4개의 AI 모델**이 연결되어 있습니다 — 3개는 API 키 없이 100% 로컬로 동작(임베딩, 재정렬기, 로컬 LLM)하고, 나머지 하나(OpenRouter)는 두 가지 방식으로, 둘 다 철저히 옵트인으로 사용됩니다: Compass가 이미 검색해 둔 소스를 종합하는 일반 채팅 완성 호출, 그리고 OpenRouter 자체의 완전관리형 웹검색 플러그인입니다. 실시간 웹 검색 자체도 키가 필요 없습니다 — `ddgs`는 무료이며, 표준적인 모의(mock)-우선 복원 패턴을 따라 레이트리밋 시 결정론적인 모의 결과로 폴백합니다.

## 빠른 시작

요구사항: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS 또는 Windows), 여유 디스크 ~8GB, 인터넷 연결(최초 모델 다운로드 + 실시간 웹 검색).

```bash
cd 6th_week/PoC/projects/compass
./scripts/setup.sh      # 최초 1회: 이미지 빌드, 빈 포트 자동 선택, 컨테이너 시작
```

이게 전부입니다 — API가 응답하면 스크립트가 URL을 출력합니다(예: `http://localhost:8760`). 3개의 로컬 AI 모델은 최초 부팅 시 백그라운드에서 계속 다운로드/로딩됩니다(`docker compose logs -f`로 확인 가능). UI는 즉시 사용할 수 있으며, 모델이 아직 준비되지 않았다면 첫 사용 시 자동으로 대기합니다.

```bash
./scripts/run.sh              # 이후 실행 시 — 빌드된 이미지를 재사용하므로 빠름
./scripts/stop.sh             # 컨테이너와 데이터를 삭제하지 않고 중지
./scripts/verify_e2e.sh       # 전체 엔드투엔드 검증 실행(아래 참고) — 실제 소액 OpenRouter 과금 발생
./scripts/download_models.sh  # (선택) CLI로 로컬 AI 모델 3개를 강제 다운로드/검증
```

모델 다운로드를 포함한 모든 과정이 셸 스크립트로 자동화되어 있습니다. 수동 `docker exec`, 노트북, UI 클릭 조작이 전혀 필요 없습니다.

**데모 관리자 로그인**: `admin@compass.local` / `ChangeMe123!` (실사용 전 `.env`의 `ADMIN_PASSWORD`를 반드시 변경하세요). 또는 로그인 페이지에서 직접 계정을 만들어도 됩니다.

Windows에서는 이 `.sh` 스크립트들을 Git Bash나 WSL2에서 실행하세요(이 프로젝트 시리즈의 다른 `env_set_up.sh`/`run.sh` 스크립트들과 동일한 셸 환경입니다).

## 프로젝트 구조

```
compass/
├── backend/            FastAPI 앱 (Python 3.11) — backend/app/ 참고
│   ├── app/
│   │   ├── main.py           엔트리포인트, 부트스트랩, SPA 정적 파일 서빙
│   │   ├── config.py         모든 설정, *_api_key_file 참조 포함(하드코딩된 비밀값 없음)
│   │   ├── models.py         SQLAlchemy ORM(SQL 저장소) — ReportEntry, BudgetSetting 등
│   │   ├── vectorstore.py    Chroma PersistentClient 래퍼 — 아카이브 검색용 과거 리포트 인덱싱
│   │   ├── pipeline.py       공유 검색-후-재정렬 + 프롬프트 구성(리서치 + 트렌드 레이더)
│   │   ├── security.py       JWT + bcrypt 인증
│   │   ├── ml/                embeddings.py · reranker.py · llm.py(+스트리밍+OpenRouter 웹검색) · groundedness.py · ghost_citation.py
│   │   ├── search/             web_search.py(ddgs + 모의 폴백) · rerank_pipeline.py
│   │   └── routers/            auth · research(스트리밍) · archive · grounding_lab · trend_radar · admin · health
│   └── verify_e2e.py    엔드투엔드 스모크 테스트(scripts/verify_e2e.sh 참고)
├── frontend/            React + TypeScript + Vite + Tailwind SPA
│   └── src/             pages/(Dashboard, Research, Archive, GroundingLab, TrendRadar, Admin, Login)
├── docker/Dockerfile    멀티스테이지 빌드(Node 빌드 단계 -> Python 전용 런타임 이미지)
├── docker-compose.yml   단일 서비스, 네임드 볼륨, 자동 선택 호스트 포트
├── scripts/             setup.sh · run.sh · stop.sh · verify_e2e.sh · download_models.sh
├── architecture.md      시스템 다이어그램(Mermaid) + 프로덕션 확장 노트 + 비용 추정
├── flowchart.md         기능별 함수 단위 플로우차트(Mermaid)
└── docs/guide.html      올인원 이중언어 운영 가이드(아래 참고)
```

## Streamlit 대신 FastAPI + React를 선택한 이유

Week1-4 PoC들과 같은 이유이지만, 이번엔 그 이유가 두 배로 강합니다: 이 패턴의 일반적인 기준 구현은 영속성도, 인증도, (기본값으로는) 생성 기능조차 없는 Streamlit 앱입니다. Compass는 실제 토큰 단위 스트리밍(`StreamingResponse` + 클라이언트의 `fetch()`/`ReadableStream`), 영속적이고 검색 가능한 과거 리서치 아카이브, 그리고 네이비/브라스/틸 디자인 시스템에 대한 완전한 통제가 필요합니다. 이 기준 구현 대비 구체적으로 무엇이 개선되었는지는 `architecture.md` §2 참고.

## 검색 소스에 시드 코퍼스가 없는 이유

고정된 로컬 문서 코퍼스를 쓰는 Week4의 Lucent와 달리, 이번 주의 핵심은 *실시간* 웹 검색 그라운딩입니다 — 미리 색인할 대상 자체가 없습니다. `data/README.md`에 `data/` 디렉터리가 대신 무엇을 담는지 설명되어 있습니다(최초 부팅 시 새로 생성되는 런타임 SQLite DB와 Chroma 아카이브 인덱스).

## 두 검증 계층에 대한 안내

모든 리서치 리포트는 두 가지 독립적인 방식으로 검증됩니다: `ml/groundedness.py`(Week4에서 재사용)는 모든 `[n]` 인용 인덱스가 유효한지, 그리고 모든 문장이 검색된 소스와 임베딩상 유사한지를 확인합니다. `ml/ghost_citation.py`(이번 주 신규, 일반적인 URL 검증 입문 기법을 일반화한 것)는 모델이 답변에서 실제로 작성한 모든 URL을 추출해 실제 검색 결과에 없던 URL을 표시합니다 — 이는 문장 유사도 검사만으로는 반드시 잡아내지 못하는, 검색 특유의 실패 유형(패러프레이즈되거나 지어낸 인용 URL)을 잡아냅니다. 두 검사가 잡아내지 못하는 부분은 `docs/guide.html`의 한계 섹션을 참고하세요.

## 엔드투엔드 검증

`scripts/verify_e2e.sh`는 실제 컨테이너 안에서 `backend/verify_e2e.py`를 실제 HTTP로(모킹 없이) 실행합니다 — 실제 클라이언트처럼 스트리밍 리포트를 직접 소비하는 것까지 포함합니다: 로컬 모델 3개 + 실시간 웹검색 연결이 준비될 때까지 대기 → 회원가입 → JWT 인증 → 리서치 세션 생성 → 스트리밍 쿼리 전송(바이 인코더만, 이후 크로스 인코더 재정렬 포함) → 히스토리 리로드 후에도 근거충실도가 유지되는지 확인(Week4의 Lucent PoC에서 실제로 발생했던 버그에 대한 회귀 검사, `../../debug/` 참고) → 고스트 인용 감지기와 트렌드 레이더 JSON 추출기를 실제로 관측된 엣지 케이스로 유닛 검사 → 아카이브 의미 검색이 방금 생성한 리포트를 찾는지 확인 → 실제 트렌드 레이더 주제 평가 → $0 예산 상한이 실제로 유료 OpenRouter 호출을 막는지 확인 → 실제 OpenRouter 웹검색 비교 호출 1회 → 관리자/일반 사용자 권한 경계 확인. 이 빌드의 실제 결과는 [`../../history/v1.0.0.md`](../../history/v1.0.0.md)에 기록되어 있습니다.

## 크레딧

이 PoC는 `docs/guide.html` 전반에 인용된, 공개적으로 문서화된 모델 ID·API·라이브러리를 사용한 독자적인 작업물입니다. 다른 저장소에서 복사한 애플리케이션 코드는 없습니다 — 다만 아키텍처는 이 프로젝트 시리즈 자체의 Week1-4 PoC들에서 검증된 패턴(인증, 부트스트랩 격리, 준비 상태 프로빙, 스트리밍 SSE 인프라, 근거충실도 검증)을 의도적으로 재사용했으며, 재정렬 모델 선택은 이 패턴의 일반적인 기준 구현이 사용하는 재정렬기와 일치합니다.

## 라이선스

포트폴리오 프로젝트 — 라이선스 관련 맥락은 최상위 저장소를 참고하세요. 서드파티 라이브러리/모델은 `docs/guide.html`에 문서화된 대로 각자의 라이선스를 따릅니다.
