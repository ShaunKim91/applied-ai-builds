# Verity

**Fenwick Mutual을 위한 근거 기반 클레임 리서치 어시스턴트** — AI 엔지니어링 포트폴리오 프로젝트의
Week6 PoC_v2이며, 이전 "Compass" PoC를 완전히 새로 만든 상용화급 리빌드입니다. Verity는
Fenwick Mutual SIU·컴플라이언스팀의 시니어 클레임 리서치 애널리스트 **Dana Whitfield**를 위한
제품입니다: 클레임이 일선 손해사정사를 넘어 에스컬레이션되면, 그녀는 보험계약자의 항소나 보험감독국
감사를 견딜 수 있을 만큼 실제 관할 규정과 판례를 인용한 선례 브리프를 며칠이 아닌 몇 시간 안에
작성해야 합니다.

> 📄 스크린샷, 아키텍처 다이어그램, 하드웨어 요구사항, 비용 추정까지 포함된 완전한 이중언어(기본
> 영어 / 한국어) 운영 가이드: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ 시스템 설계: **[`architecture.md`](architecture.md)** · 🔀 함수 단위 플로우차트:
> **[`flowchart.md`](flowchart.md)**
> 📗 **여섯 번째로 다른 시각 아이덴티티 — "Fenwick Ledger"**: 따뜻한 아이보리/에스프레소 배경 위의
> 딥 보틀그린 + 카퍼, Fraunces + IBM Plex Sans + IBM Plex Mono, 그리고 선택 시 앞으로 당겨지는
> 오버랩된 마닐라지 스타일 탭 디바이더로 구성된 "도시에 탭 바인더" 내비게이션 — 매주 독립된
> 아이덴티티 대신, 하나의 가상 회사를 위한 연결된 제품 스위트로서 Threshold(Week7의 짝 프로젝트)와
> 의도적으로 공유합니다. `architecture.md` §3 참고.
> 🎯 **"이건 누구를 위한 제품인가"에 명시적으로 답하도록 설계** — 이 시리즈의 이전 모든 제품
> (CommerceIQ, VoxIQ, Parchment, Lucent, 그리고 Verity의 전신인 Compass)은 명명된 구매자 페르소나
> 없이 일반적인 기능 카테고리명만 사용했습니다. 이번 리빌드는 바로 그 문제를 해결하기 위한 것입니다.

## 무엇을 하는가

| 모듈 | AI 모델 | 무엇을 해볼 수 있는가 |
|---|---|---|
| ◈ **리서치** | `multilingual-e5-small` + `ms-marco-MiniLM-L-6-v2`(가상 관할 코퍼스 재순위화) + 로컬 `Qwen2.5-0.5B` 또는 OpenRouter 경유 `qwen/qwen3-8b`(옵트인) | 클레임 관련 질문을 하면, 인용이 달린 Quick Answer 또는 구조화된 Precedent Brief(쟁점 / 근거 법령 / 적용 사실 / 권고 / 출처)를 받습니다. 사기 신호 하이라이트와 출처 신뢰도 배지가 함께 표시됩니다 |
| 📚 **라이브러리** | `multilingual-e5-small`(의미 기반 검색) | 키워드가 아닌 의미로 과거 모든 리서치 리포트를 검색 |
| ⛈ **CAT 이벤트** | — | 명명된 재해·기상 이벤트를 1급 객체로 추적; 관련된 모든 리서치 리포트가 그 아래에 자동으로 정리됨 |
| 📡 **벤더 레이더** | `Qwen2.5-0.5B` 구조화 추출, 실시간 웹 검색 | 실제 웹 결과에 근거하여 AI/InsurTech 벤더 도구를 비용/보안/승인 마찰 기준으로 평가 |
| ⚙ **관리자** | — | 사용자 관리, 실시간 무결성 검증 기능이 있는 **해시체인 기반 변조 감지 감사로그**, 실측 p50/p95/p99 지연 지표, 구조화된 에러 로그, 일일 OpenRouter 예산 거버넌스 |
| 🌐 **공개 상태 페이지** | — | `/api/status` — 모델 워밍 상태, 벡터스토어/OpenRouter 연결성, 가동시간, 현재 p95 — 로그인 불필요 |

## 여기서 "상용화급"이 구체적으로 의미하는 것

로컬 Docker 데모 인프라 제약을 그대로 유지하면서 PoC급이 아닌 상용화급 품질로 만들어 달라는
이번 라운드의 명시적 요청에 따라:

- **로그인 전 공개 마케팅 랜딩 페이지** — 이전 모든 PoC의 기본값이던 "바로 로그인 화면"과 달리,
  이 제품이 정확히 누구를 위한 것이고 왜인지 명시.
- **`Organization` 데이터 모델**(Fenwick Mutual을 한 행으로 시드) — 하드코딩된 싱글턴 `id=1`
  설정 행 대신, 테넌트 스위처 없이도 구조적으로 멀티테넌트에 대응 가능.
- **httpOnly/SameSite=Strict 쿠키에 담긴 액세스 + 회전형 리프레시 토큰**(JS에서 접근 가능한
  저장소에 토큰 없음), 모든 변경 요청에 대한 CSRF 이중 제출 보호, 반복 로그인 실패 시 계정
  잠금 — 이전 모든 PoC의 단일 24시간 고정 JWT를 대체.
- **해시체인 감사로그**: 모든 행이 자신의 콘텐츠와 이전 행의 해시를 합친 SHA-256 해시를 저장하며,
  관리자 액션이 체인을 순회하며 변조 지점을 정확히 보고.
- **직접 구현한 단일 프로세스 속도 제한기** — 인증 및 AI 호출 엔드포인트에 적용(데모 규모의
  한계로 명시적으로 문서화됨 — 실제 다중 인스턴스 배포에는 공유 상태가 필요).
- **실측 관측성**: 단순 요청 카운터가 아닌 라우트별 p50/p95/p99 지연, 요청 상관관계 ID가 포함된
  구조화된 에러 로그, 공개 상태 페이지.

전체 체크리스트와 명시적 범위 제외 항목(실제 클라우드 배포, 결제 연동, 작동하는 테넌트
스위처)은 `architecture.md` §4 참고.

## 빠른 시작

요구사항: [Docker Desktop](https://www.docker.com/products/docker-desktop/), 여유 디스크
~5GB, 인터넷 연결(최초 1회 모델 다운로드; 옵트인 OpenRouter 에스컬레이션이 그 외의 유일한
런타임 네트워크 의존성 — 클레임 리서치 자체는 완전히 오프라인, 아래 참고).

```bash
cd week6/PoC_v2/projects/verity
./scripts/setup.sh
```

스크립트는 API가 응답하는 즉시 URL을 출력합니다(예: `http://localhost:8780`). 최초 부팅 시
로컬 AI 모델 3개가 백그라운드에서 계속 로딩되지만, UI는 즉시 사용 가능합니다.

```bash
./scripts/run.sh              # 이후 매번 사용 — 빠름
./scripts/stop.sh             # 컨테이너나 데이터를 삭제하지 않고 중지
./scripts/verify_e2e.sh       # 25개 항목 전체 검증 — 실제 소규모 OpenRouter 호출 1회 포함
./scripts/download_models.sh  # (선택) CLI로 로컬 모델 3개를 강제 다운로드/검증
```

**데모 관리자 로그인**: `admin@fenwickmutual.example` / `ChangeMe123!`(실사용 전 `.env`의
`ADMIN_PASSWORD` 변경 필요). 또는 로그인 페이지에서 직접 계정을 생성할 수 있습니다.

## 클레임/관할 리서치가 실시간 웹에 절대 접근하지 않는 이유

실제 실시간 웹을 `ddgs`로 검색했던 예전 Compass PoC와 달리, Verity의 클레임 리서치는
**오직** 코드에 정의된 완전히 가상의 코퍼스(`backend/app/search/jurisdictions.py`)에만
근거합니다. 이 코퍼스는 가상의 법령, 판례, DOI 회람이 있는 6개의 가상 관할을 다룹니다. 실제
주(state)의 실제 보험법에 관한 실제 스크레이핑 웹 콘텐츠는 가상의 보험사에게 논리적으로
모순되며, LLM이 실제 규제 텍스트를 마치 Verity가 검증한 것처럼 그대로 옮길 위험이 있습니다 —
이 프로젝트의 표준 규칙상 반드시 피해야 하는 환각 인접 위험입니다. **별개의** Vendor Adoption
Radar 기능은 실제 AI/InsurTech 벤더 도구 평가가 실질적으로 실세계 리서치이기 때문에 실제
실시간 웹 검색을 사용합니다. 전체 이유는 해당 모듈 자체의 문서 주석 참고.

## 프로젝트 구조

```
verity/
├── backend/             FastAPI 앱 (Python 3.11) — backend/app/ 참고
│   ├── app/
│   │   ├── main.py           엔트리포인트, 부트스트랩, 안전하지 않은 기본값 가드, SPA 서빙
│   │   ├── config.py         전체 설정, *_api_key_file 참조 포함 (하드코딩된 시크릿 없음)
│   │   ├── models.py         SQLAlchemy ORM — Organization, User, RefreshToken, ResearchSession/ReportEntry, CatEvent, 해시체인 AuditLog, ErrorLog
│   │   ├── security.py       JWT 액세스+리프레시 토큰, CSRF, 계정 잠금
│   │   ├── rate_limit.py     직접 구현한 인메모리 슬라이딩 윈도우 제한기
│   │   ├── audit.py          해시체인 감사 로깅 + 체인 검증
│   │   ├── metrics.py        실측 p50/p95/p99 지연 추적
│   │   ├── vectorstore.py    Chroma PersistentClient 래퍼
│   │   ├── ml/                embeddings.py · reranker.py · llm.py · ghost_citation.py (+ 개체명 검사) · groundedness.py · fraud_signals.py
│   │   ├── search/             jurisdictions.py (가상 코퍼스) · web_search.py (실제, Radar 전용) · rerank_pipeline.py
│   │   └── routers/            auth · research (스트리밍) · archive · cat_events · radar · admin · status · health
│   └── verify_e2e.py    25개 항목 엔드투엔드 스모크 테스트 (scripts/verify_e2e.sh 참고)
├── frontend/            React + TypeScript + Vite + Tailwind SPA — "Fenwick Ledger" 디자인 시스템
├── docker/Dockerfile    멀티스테이지 빌드
├── docker-compose.yml   단일 서비스, 네임드 볼륨, 자동 선택 호스트 포트 (8780+)
├── scripts/             setup.sh · run.sh · stop.sh · verify_e2e.sh · download_models.sh
├── architecture.md      시스템 다이어그램(Mermaid) + 엔지니어링 완성도 비교표 + 보안/관측성 상세
├── flowchart.md         기능별 함수 단위 플로우차트(Mermaid)
└── docs/guide.html      올인원 이중언어 운영 가이드
```

## 엔드투엔드 검증

`scripts/verify_e2e.sh`는 실행 중인 컨테이너 안에서 `backend/verify_e2e.py`를 실제 HTTP로
실행합니다(모킹 없음): 헬스체크/워밍 대기 → 회원가입 → CSRF 강제 → 실제 근거 기반 Quick Answer
쿼리 → 실제 Precedent Brief 쿼리 → 고스트인용/사기신호/개체명환각/출처신뢰도 회귀 테스트 →
CAT 이벤트 → 시맨틱 라이브러리 검색 → 실제 실시간 웹 벤더 평가 → 비용 거버넌스 $0 차단 →
실제 OpenRouter 호출 → 해시체인 감사로그 + 직접 변조 감지 회귀 → 속도 제한 회귀 → 계정 잠금
흐름 → 리프레시 토큰 회전(재사용 거부 포함) → 공개 상태 페이지 → 실측 지표/에러로그
엔드포인트 → 관리자 권한 경계. 이 빌드의 실제 결과는
[`../../history/v1.0.0.md`](../../history/v1.0.0.md)에 있습니다.

## 저작권 표기

공개적으로 문서화된 모델 ID, API, `docs/guide.html`에 인용된 라이브러리를 사용한 오리지널
작업입니다. 아키텍처는 인증 기반 설계, 부트스트랩 격리, 준비 상태 프로빙, 스트리밍 SSE, 일일
예산 상한 거버넌스 패턴 등 검증된 패턴을 이 프로젝트 시리즈 자체의 Week1-7 PoC들로부터
의도적으로 재사용했으며, 이번 라운드의 상용화급 요구사항에 맞춰 대폭 강화하고 확장했습니다.

## 라이선스

포트폴리오 프로젝트 — 라이선스 관련 맥락은 최상위 저장소를 참고하세요. 서드파티
라이브러리/모델은 `docs/guide.html`에 문서화된 자체 라이선스를 따릅니다.
