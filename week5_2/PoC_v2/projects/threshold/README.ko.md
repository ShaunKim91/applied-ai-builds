# Threshold

**Fenwick Mutual을 위한 가드레일 기반 ReAct 에이전트 콘솔** — Week5_2 PoC_v2이며, 이전 "Cradle" PoC를
상용화급으로 완전히 새로 만든 버전입니다. Threshold는 Fenwick Mutual Property Claims Payments 부서의
심사역 22명을 이끄는 클레임 처리 팀장 **Priya Nakamura**를 위한 것입니다: 그녀의 팀은 단순 조회를 위해
여러 시스템을 오가며 클레임 처리 시간의 1/3을 낭비하고 있으며, 상한선 이상의 지급이 절대 상급자 검토를
우회할 수 없다는 확실한 보장이 필요합니다.

> 📄 스크린샷, 아키텍처 다이어그램, 하드웨어 요구사항, 비용 추정치를 포함한 전체 이중 언어(영어 기본 /
> 한국어) 운영 가이드: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ 시스템 설계: **[`architecture.md`](architecture.md)** · 🔀 함수 단위 흐름도:
> **[`flowchart.md`](flowchart.md)**
> 🛡️ **Verity와 "Fenwick Ledger" 디자인 시스템을 공유합니다** (Week5_1의 짝 프로젝트) —
> 카퍼를 Threshold 자체 주 액센트로, 보틀그린을 스위트의 공유 보조색으로,
> 동일한 Fraunces + IBM Plex Sans + IBM Plex Mono 타입 시스템, 동일한 "도시에 탭 바인더"
> 내비게이션 — 서로 무관한 두 개의 주간 빌드가 아닌, 하나의 가상 회사를 위한 연결된 제품 스위트입니다.
> `architecture.md` §3 참고.
> 📈 이 패턴의 일반적인 초기 구현보다 의도적으로 더 고도화되어 있습니다 —
> 그런 초기 구현은 대개 가드레일을 잘못된 순서로 검사하고, Human-in-the-Loop 승인을
> 만들어 놓고도 앱에 실제로 연결하지 않습니다. `architecture.md` §2 참고.

## 하는 일

| 모듈 | AI 모델 | 무엇을 해볼 수 있는가 |
|---|---|---|
| 🛡️ **콘솔** | 로컬 `Qwen2.5-0.5B-Instruct`(기본) 또는 OpenRouter의 `qwen/qwen3-8b`(옵션 에스컬레이션) | 에이전트에게 무언가를 물어보고, 실시간으로 한 단계씩 생각(Thought)·행동(Action)·관찰(Observation)하는 과정을 지켜보세요 |
| ✓ **승인** | — | 진짜 Human-in-the-Loop 큐: 관리자가 설정한 상한선을 초과하는 지급은 실제로 실행을 멈추고, 여기서 승인 또는 거부하면 실행이 실제로 재개됩니다 |
| 📜 **이력** | `multilingual-e5-small`(과거 실행 색인) | 과거의 모든 에이전트 실행에 대한 의미 기반 검색 — 키워드가 아닌 의미로 찾습니다 |
| ⚙ **관리자** | — | 실시간 가드레일 설정(허용 도구/스텝 제한/비용 상한/**금액 인식 지급 상한선**, 런타임에 수정 가능), 사용자, 실시간 무결성 검증 기능이 있는 **해시체인 기반 변조 감지 감사 트레일**, 실제 p50/p95/p99 지연시간 지표, 일일 OpenRouter 지출 상한 |
| 🌐 **공개 상태 페이지** | — | `/api/status` — 모델 예열 상태, 벡터스토어/OpenRouter 접근 가능 여부, 가동 시간, 현재 p95 — 로그인 불필요 |

## "상용화급"이 여기서 구체적으로 의미하는 것

이번 라운드의 명시적 요청에 따라, Verity의 상용화급 체크리스트를 그대로 공유합니다(전체 목록은 그
프로젝트의 README 참고): `Organization` 데이터 모델, 액세스+회전형 리프레시 토큰 인증(CSRF 보호 및
계정 잠금 포함), 해시체인 감사 로그, 직접 구현한 속도 제한기, 그리고 실제 관측 가능성(p50/p95/p99
지연시간, 구조화된 오류 로그, 공개 상태 페이지) — 이전 Cradle PoC(또는 이 프로젝트 시리즈의 그 어떤
이전 PoC)도 구현하지 않았던 것들입니다.

**Cradle 대비 Threshold만의 엔지니어링 업그레이드**:
- **금액 인식 HITL**: Cradle의 Human-in-the-Loop 게이트는 도구 이름별 플랫(flat) 집합이었습니다 —
  게이트된 도구는 금액과 무관하게 *항상* 일시정지되었습니다. Threshold의 `issue_claim_payout`은
  요청 금액이 관리자가 설정 가능한 상한선(기본값 $2,500, 예시용)을 초과할 때만 일시정지됩니다 — 소액
  지급은 바로 통과되고, 고액 지급은 실제로 사람을 기다립니다.
- **단순 구현이 아니라 눈에 보이도록 만든, 수정된 가드레일 순서**: 관리자 → 가드레일 탭에서 비용
  상한보다 권한을 먼저 검사하는 *이유*를 명시적으로 설명합니다 — 조용한 수정이 아니라 투명성 기능입니다.

## 빠른 시작

요구사항: [Docker Desktop](https://www.docker.com/products/docker-desktop/), 여유 디스크 ~5GB,
인터넷 연결(최초 1회 모델 다운로드; 실행 중인 앱 자체는 옵션인 OpenRouter 에스컬레이션 외에는
네트워크가 필요 없습니다).

```bash
cd week5_2/PoC_v2/projects/threshold
./scripts/setup.sh
```

API가 응답하면 스크립트가 URL을 출력합니다(예: `http://localhost:8790`). 두 로컬 AI 모델은 최초
부팅 시 백그라운드에서 계속 로딩되며 — UI는 즉시 사용 가능합니다.

```bash
./scripts/run.sh              # 이후 매번 — 빠름
./scripts/stop.sh             # 컨테이너나 데이터를 삭제하지 않고 중지
./scripts/verify_e2e.sh       # 전체 26개 체크 검증 — 실제로 작은 OpenRouter 호출 1회 발생
./scripts/download_models.sh  # (선택) CLI로 두 로컬 모델을 강제 다운로드/검증
```

**데모 관리자 로그인**: `admin@fenwickmutual.example` / `ChangeMe123!` (실제 사용 전에 `.env`의
`ADMIN_PASSWORD`를 변경하세요). 또는 로그인 페이지에서 직접 계정을 만드세요.

## 프로젝트 구조

```
threshold/
├── backend/             FastAPI 앱 (Python 3.11) — backend/app/ 참고
│   ├── app/
│   │   ├── main.py           진입점, 부트스트랩, 보안 기본값 미설정 방지 가드, SPA 서빙
│   │   ├── config.py         모든 설정, 도구별 비용 및 금액 인식 지급 상한선 포함
│   │   ├── models.py         SQLAlchemy ORM — Organization, User, RefreshToken, AgentRun/AgentStep, ApprovalRequest, GuardrailSetting, 해시체인 AuditLog, ErrorLog
│   │   ├── security.py       JWT 액세스+리프레시 토큰, CSRF, 계정 잠금 (Verity와 동일한 아키텍처)
│   │   ├── rate_limit.py     직접 구현한 인메모리 슬라이딩 윈도우 제한기
│   │   ├── audit.py          해시체인 감사 로깅 + 체인 검증
│   │   ├── metrics.py        실제 p50/p95/p99 지연시간 추적
│   │   ├── agent/             tools.py (클레임 처리 도구 7개 + 따옴표 인식 인자 파싱) · react_loop.py (ReAct 메커니즘) · guardrails.py (수정된 순서 + 금액 인식 HITL) · orchestrator.py (재개 가능한 루프)
│   │   ├── ml/llm.py          OpenRouter 에스컬레이션 (설계상 도구 호출 능력 없음)
│   │   └── routers/            auth · agent(스트리밍) · approvals(HITL) · history · admin · status · health
│   └── verify_e2e.py    26개 체크 엔드투엔드 스모크 테스트 (scripts/verify_e2e.sh 참고)
├── frontend/            React + TypeScript + Vite + Tailwind SPA — "Fenwick Ledger" 디자인 시스템
├── docker/Dockerfile    멀티스테이지 빌드
├── docker-compose.yml   단일 서비스, 네임드 볼륨, 자동 선택 호스트 포트 (8790+)
├── scripts/             setup.sh · run.sh · stop.sh · verify_e2e.sh · download_models.sh
├── architecture.md      시스템 다이어그램(Mermaid) + 엔지니어링 완성도 비교표 + 보안 상세
├── flowchart.md         기능별 함수 단위 흐름도(Mermaid)
└── docs/guide.html      올인원 이중 언어 운영 가이드
```

## 수정된 가드레일 검사 순서

네 가지 안전 가드레일(스텝 제한 → 권한 → 비용 상한 → HITL)은 정확히 이 순서로 검사됩니다 —
의도적이며, 문서화된 이유가 있습니다: 이 패턴을 단순하게 구현하면 흔히 비용 상한을 권한 *이전에*
검사하여, 예산이 이미 소진된 시점에 발생한 미승인 도구 호출을 권한 위반이 아닌 예산 이벤트로 잘못
기록하는 버그가 생깁니다. 전체 내용은 이전 Cradle PoC의 `debug/issue-01`을 참고하세요(이번 라운드에서
변경 없음 — 근본적인 버그 패턴도, 그 수정도 달라지지 않았습니다), 그리고 이 프로젝트 자체의 관리자 →
가드레일 탭에서 그 이유를 UI에서 직접 설명합니다.

## 엔드투엔드 검증

`scripts/verify_e2e.sh`는 실행 중인 컨테이너 내부에서 `backend/verify_e2e.py`를 실제 HTTP로
실행합니다(목(mock) 없음): 헬스체크/예열 대기 → 회원가입 → CSRF 강제 → 올바른 답에 도달하는 실제
도구 호출 실행 → 따옴표 인자 회귀 테스트(이번 빌드에서 발견한 실제 버그, `debug/issue-01` 참고) →
가드레일 순서 및 금액 인식 HITL 회귀 테스트 → 실제 HITL 일시정지→승인→재개 흐름과 실제
일시정지→거부→재개 흐름 → 스텝 제한/비용 상한 정지 → 이력 의미 검색 → $0 예산 상한 차단 → 실제
OpenRouter 에스컬레이션 → 해시체인 감사 로그 + 직접적인 변조 감지 회귀 테스트 → 속도 제한기 회귀
테스트 → 계정 잠금 → 리프레시 토큰 회전 → 공개 상태 페이지 → 실제 지표/오류 로그 엔드포인트 → 관리자
권한 경계. 이번 빌드의 실제 결과는 [`../../history/v1.0.0.md`](../../history/v1.0.0.md)에 있습니다.

## 크레딧

공개적으로 문서화된 모델 ID, API, 라이브러리를 사용한 원작입니다(`docs/guide.html`에 출처 명시).
아키텍처는 검증된 패턴(인증 기반, 부트스트랩 격리, 준비 상태 프로빙, 스트리밍 SSE, 재개 가능한 실행
패턴)을 이 프로젝트 시리즈의 이전 PoC들과 이번 라운드의 Verity 빌드에서 의도적으로 재사용했으며,
이번 라운드의 상용화급 요구사항에 맞게 대폭 강화·확장했습니다. ReAct 루프 설계는 표준적인
생각(Thought)→행동(Action)→관찰(Observation) 패턴을 따르며, 로컬 에이전트 모델 선택
(Qwen2.5-0.5B-Instruct)은 온디바이스 도구 호출에 적합한, 작고 공개 라이선스인 instruct 모델을
반영한 것입니다.

## 라이선스

교육 과정 PoC — 라이선스 관련 맥락은 최상위 저장소를 참고하세요. 서드파티 라이브러리/모델은
`docs/guide.html`에 문서화된 대로 각자의 라이선스를 유지합니다.
