# Throughline

**Fenwick Mutual을 위한 LangChain 기반 대화 메모리 코파일럿** — Week8 PoC이자 AI 엔지니어링 프로젝트
포트폴리오의 일부로서, Week6의 Verity(클레임 리서치)와 Week7의 Threshold(안전장치 내장 지급
에이전트)에 이어 "Fenwick Mutual" 제품군의 세 번째 제품입니다. Throughline은 하루 50~70건의 청구서·
보장내역·계약변경 문의 전화를 처리하는 계약자 서비스 담당자 **Marcus Webb**을 위한 것입니다: 그는
현재 같은 통화 안에서도 고객이 이미 말한 내용을 다시 설명해야 하거나, 다음 주 재통화 시 이전 대화
기록이 전혀 남아있지 않은 문제를 겪고 있습니다.

> 📄 스크린샷, 아키텍처 다이어그램, 하드웨어 요구사항, 비용 추정까지 포함한 전체 이중언어(영어 기본 /
> 한국어) 운영 가이드: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ 시스템 설계: **[`architecture.md`](architecture.md)** · 🔀 기능 단위 플로우차트:
> **[`flowchart.md`](flowchart.md)**
> 🧵 **Verity·Threshold와 "Fenwick Ledger" 디자인 시스템을 공유합니다** — "레저 잉크" 인디고를
> Throughline 고유의 주 액센트로, 카퍼를 제품군 공통 보조색으로 사용하며, 동일한 Fraunces + IBM Plex
> Sans + IBM Plex Mono 타이포 시스템과 동일한 "도시에 탭 바인더" 내비게이션을 씁니다 — 세 개의 개별
> 주간 빌드가 아니라 하나의 가상 회사를 위한 하나의 연결된 제품군입니다. `architecture.md` §3 참고.
> 📈 동일한 LangChain 에이전트 패턴의 일반적인 초기 구현 수준을 의도적으로 뛰어넘습니다 — 그런
> 기본형은 대화 메모리를 영속화하지 않고(그런 종류의 베이스라인 빌드에서 스스로 문서화한 한계),
> 취약한 정규식 매처로 도구를 라우팅하며, 순수 `eval()` 계산기를 사용합니다. `architecture.md` §2
> 참고.

## 무엇을 할 수 있나

| 모듈 | AI 모델 | 체험할 수 있는 것 |
|---|---|---|
| 🗂 **케이스** | `multilingual-e5-small`(의미 기반 검색) | 걸려온 전화에 대한 케이스를 열거나, 키워드가 아닌 의미로 과거 케이스를 검색 |
| 🧵 **워크스페이스** | 로컬 `Qwen2.5-0.5B-Instruct`(기본) 또는 OpenRouter의 `qwen/qwen3-8b`(옵트인 에스컬레이션) | 실제 통화를 중계하듯 코파일럿과 대화 — 실제 도구로 라우팅되는 과정, "인덱스 카드" 사이드바에 실시간으로 추출되는 구조화된 사실, 여러 턴 전에 언급된 사실을 정확히 기억해내는 모습을 확인 |
| ⚙ **관리자** | — | 실시간 메모리 거버넌스(윈도우 크기 / 레드액션 토글, 런타임에 수정 가능), 전체 메모리 충돌 로그, 보존/삭제 이력, 사용자 관리, **해시 체인 기반의 변조 감지 감사 추적**과 실시간 무결성 검증 액션, 실측 p50/p95/p99 지연시간 지표, 일일 OpenRouter 지출 한도 |
| 🌐 **공개 상태 페이지** | — | `/api/status` — 모델 준비 상태, 벡터 저장소/OpenRouter 연결 상태, 가동 시간, 현재 p95 — 로그인 불필요 |

## 여기서 "상용 등급"이 구체적으로 의미하는 것

이번 라운드의 명시적 요청에 따라 Verity·Threshold의 상용 등급 체크리스트를 그대로 공유합니다:
`Organization` 데이터 모델, 액세스+로테이팅 리프레시 토큰 인증(CSRF 방어 및 계정 잠금 포함),
해시 체인 감사 로그, 직접 구현한 레이트 리미터, 그리고 실질적인 관찰가능성(p50/p95/p99 지연시간,
구조화된 에러 로그, 공개 상태 페이지) — 세 번째로 다시 설계하는 대신 의도적으로 그대로 재사용했습니다
(`architecture.md` §0 참고).

**일반적인 초기 구현 대비 Throughline만의 엔지니어링 업그레이드**:
- **실제 LangChain LCEL 조합** (`langchain-core==0.3.86`, 이에 의존하는 코드를 작성하기 전에 실제
  설치된 패키지로 검증): 라우팅·구조화된 메모리 추출·요약을 위한 `ChatPromptTemplate | Runnable |
  StrOutputParser()` 체인 — 일반적인 베이스라인 구현은 `PromptTemplate`을 임포트만 하고 `.format()`만
  호출할 뿐, 실제 `|` 파이프는 한 번도 쓰지 않습니다.
- **영속화된 이중 전략 메모리**: SQL 기반 `BaseChatMessageHistory` 구현 + `trim_messages` 윈도우 +
  전용 LCEL 요약 체인 — 그런 종류의 베이스라인 빌드에 흔한 "메모리가 영속화되지 않아 재시작 시
  사라진다"는 잘 알려진 한계를 해소합니다.
- **정규식 매처를 대체하는 구조화된 출력 기반 도구 라우팅**, 제한된 재시도와 정직한 폴백(절대 조용히
  추측하지 않음) 포함 — 이번 빌드에서 실측한 첫 시도 성공률은 `debug/` 참고.
- **메모리 조건부 도구 자동 채우기**: 앞서 언급된 선호값(예: 콜백 희망 시간대)이 이후 도구 호출을
  자동으로 채울 수 있습니다 — Verity에도 Threshold에도 없는 유일한 구조적 기능으로, 둘 다 세션을
  넘나들며 반복되는 동일 외부 상대방이라는 개념 자체가 없기 때문입니다.
- **메모리 쓰기 충돌 가드레일**: 새로운 사실이 확신도 높은 기존 값을 조용히 덮어쓰는 일이 없습니다 —
  불일치는 사람이 확인하도록 플래그되고, 어느 쪽이든 로그로 남습니다. Threshold가 지급을 게이팅하는
  방식과 구조적으로 유사하지만, 이 프로젝트만의 가드레일 축은 메모리 쓰기를 게이팅하는 데 적용됩니다.
- **실제 `ast` 화이트리스트 기반 안전 평가기**: 일반적인 베이스라인 구현과 Threshold의 이전 계산기
  도구 모두가 갖고 있던 `eval()` 지름길을 닫으면서, `ast.literal_eval`을 수정안으로 권장하는 흔한
  입문용 조언을 바로잡습니다 — 실제로는 `12 * 8`조차 계산하지 못한다는 사실을 직접 검증했습니다.
- **모든 신뢰 경계에서의 레드액션**: 영속화, OpenRouter 에스컬레이션 호출, 실시간 워크스페이스
  사이드바가 모두 동일한 패턴 기반 PII 레드액션을 거칩니다 — 인증된 PII 탐지 정확도를 주장하지 않는다는
  명시적이고 정직한 고지 포함(`docs/guide.html` 참고).

## 빠른 시작

요구사항: [Docker Desktop](https://www.docker.com/products/docker-desktop/), 여유 디스크 ~5GB,
인터넷 연결(모델 최초 1회 다운로드; 실행 중인 앱 자체는 옵트인 OpenRouter 에스컬레이션을 제외하면
네트워크가 필요 없음).

```bash
cd week8/PoC/projects/throughline
./scripts/setup.sh
```

API가 응답하는 즉시 스크립트가 URL을 출력합니다(예: `http://localhost:8800`). 두 로컬 AI 모델은 최초
부팅 시 백그라운드에서 계속 로딩됩니다 — UI는 즉시 사용 가능합니다.

```bash
./scripts/run.sh              # 이후 매번 — 빠름
./scripts/stop.sh             # 컨테이너나 데이터를 삭제하지 않고 중지
./scripts/verify_e2e.sh       # 전체 31개 항목 검증 — 실제 OpenRouter 호출 1회 포함(소액)
./scripts/download_models.sh  # (선택) CLI로 두 로컬 모델을 강제 다운로드/검증
```

**데모 관리자 로그인**: `admin@fenwickmutual.example` / `ChangeMe123!` (실제 사용 전에 `.env`의
`ADMIN_PASSWORD`를 변경하세요). 또는 로그인 페이지에서 직접 계정을 만들 수도 있습니다.

## 프로젝트 구조

```
throughline/
├── backend/             FastAPI 앱 (Python 3.11) — backend/app/ 참고
│   ├── app/
│   │   ├── main.py           엔트리포인트, 시작 부트스트랩, 안전하지 않은 기본값 가드, SPA 서빙
│   │   ├── config.py         전체 설정, 메모리 윈도우 기본값 + 레드액션 토글 포함
│   │   ├── models.py         SQLAlchemy ORM — Organization, User, RefreshToken, CallerCase, ConversationTurn, MemoryFact, MemoryConflictLog, RetentionRequest, MemorySetting, 해시 체인 AuditLog, ErrorLog
│   │   ├── security.py       JWT 액세스+리프레시 토큰, CSRF, 계정 잠금(Verity/Threshold와 공유하는 아키텍처)
│   │   ├── rate_limit.py     직접 구현한 인메모리 슬라이딩 윈도우 리미터
│   │   ├── audit.py          해시 체인 감사 로깅 + 체인 검증
│   │   ├── metrics.py        실측 p50/p95/p99 지연시간 추적
│   │   ├── chains/            llm_runnable.py(공유 로컬 모델 Runnable) · memory_store.py(SQL 이력 + 윈도우/요약) · router.py(구조화된 출력 도구 라우팅) · extraction.py(구조화된 메모리 추출 + 충돌 가드레일) · tools.py(안전한 도구 5종) · orchestrator.py(prepare/stream/finalize)
│   │   ├── ml/llm.py          OpenRouter 에스컬레이션(경계에서 레드액션, 설계상 도구 호출 능력 0)
│   │   ├── ml/redaction.py    패턴 기반 PII 레드액션, 함수 1개, 호출 지점 3곳
│   │   ├── ml/safe_eval.py    ast 화이트리스트 기반 산술 평가기
│   │   └── routers/            auth · cases(생성/목록/검색/메시지 SSE/에스컬레이션/삭제/해결) · admin · status · health
│   └── verify_e2e.py    31개 항목 엔드투엔드 스모크 테스트 (scripts/verify_e2e.sh 참고)
├── frontend/            React + TypeScript + Vite + Tailwind SPA — "Fenwick Ledger" 디자인 시스템
├── docker/Dockerfile    멀티스테이지 빌드
├── docker-compose.yml   단일 서비스, named volume, 호스트 포트 자동 선택(8800+)
├── scripts/             setup.sh · run.sh · stop.sh · verify_e2e.sh · download_models.sh
├── architecture.md      시스템 다이어그램(Mermaid) + 베이스라인 비교표 + 보안 상세
├── flowchart.md         기능별 함수 단위 플로우차트 (Mermaid)
└── docs/guide.html      올인원 이중언어 운영 가이드
```

## 메모리 쓰기 충돌 가드레일

새로 추출된 값은 이미 확신도 높은 `MemoryFact`를 조용히 덮어쓰지 않습니다 — `chains/extraction.py`
참고. `stated` 값이 다른 `stated` 값과 충돌하면 기존 값을 유지하고, 사람이 워크스페이스 UI에서
해결할 수 있도록 보류 항목으로 로그를 남깁니다; 그 외의 모든 덮어쓰기(더 높은 확신도 값이 낮은 값을
대체하거나, 반대로 올바르게 거부되는 경우)도 항상 로그로 남으며 절대 조용히 처리되지 않습니다. 이는
Threshold의 지급 방식 HITL 게이트를 그대로 가져온 것이 아니라(이 제품의 모든 도구는 안전한 정보성
도구이며, 그 위험 영역은 Threshold의 몫입니다) Throughline만의 가드레일 축으로, 이 제품이 실제로 하는
일에 고유한 메모리 무결성 게이트입니다.

## 엔드투엔드 검증

`scripts/verify_e2e.sh`는 실제 컨테이너 안에서 `backend/verify_e2e.py`를 진짜 HTTP로 실행합니다
(목(mock) 없음): 헬스체크/워밍업 대기 → 회원가입 → CSRF 강제 → 정답에 도달하는 실제 도구 호출 실행
→ 메모리 회상 회귀 테스트(이번 빌드에서 발견한 실제 버그, `debug/issue-02` 참고) → 구조화된 사실
영속화 → 메모리 조건부 도구 자동 채우기 → 충돌 가드레일 → 충돌 해결 → 실제 윈도우-요약 전환(이번
빌드에서 발견한 또 다른 실제 버그, `debug/issue-03` 참고) → 레드액션 경계 검증 → 안전 평가기(올바른
산술 연산 AND 안전하지 않은 입력 거부) → 삭제 캐스케이드 → 의미 기반 케이스 검색 → 관리자 메모리
설정/충돌 로그/보존 로그 → $0 예산 한도 차단 → 실제 OpenRouter 에스컬레이션 → 해시 체인 감사 로그 +
직접적인 변조 탐지 회귀 → 레이트 리미터 회귀 → 계정 잠금 → 리프레시 토큰 로테이션 → 공개 상태 페이지
→ 실측 지표/에러 로그 엔드포인트 → 관리자 권한 경계. 이번 빌드의 실제 결과는
[`../../history/v1.0.0.md`](../../history/v1.0.0.md)에 기록되어 있습니다.

## 크레딧

`docs/guide.html`에 명시된 공개적으로 문서화된 모델 ID·API·라이브러리를 사용한 원본 작업물입니다.
아키텍처 측면에서는 이 프로젝트 시리즈의 이전 PoC들과 이번 라운드의 Verity/Threshold 빌드에서 검증된
패턴(인증 기반, 부트스트랩 단계 분리, readiness probing, 스트리밍 SSE)을 의도적으로 재사용했으며,
이번 라운드의 초점에 맞춰 실제 `langchain-core` LCEL 조합으로 대폭 확장했습니다. 로컬 모델 선택과
그 튜닝된 생성 설정은 추측이 아니라 실제 모델의 문서화된 동작을 직접 검증해 결정했습니다.

## 라이선스

포트폴리오 프로젝트 — 라이선스 관련 맥락은 최상위 저장소를 참고하세요. 서드파티 라이브러리/모델은
`docs/guide.html`에 명시된 각자의 라이선스를 따릅니다.
