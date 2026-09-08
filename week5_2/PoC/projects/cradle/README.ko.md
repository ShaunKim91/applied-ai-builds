# Cradle

**실제로 작동하는 안전장치를 갖춘 로컬 ReAct 에이전트 콘솔** — AI 엔지니어링 포트폴리오 프로젝트의 Week5_2 PoC로,
에이전트형 AI의 기본기(Thought→Action→Observation 루프, 에이전트의 "두뇌" 역할을 하는 로컬 LLM, 자율 에이전트를
안전하게 지키는 네 가지 가드레일)를 실제로 동작하는 제품으로 구현했습니다: 도구를 실제로 호출하는 로컬
Qwen2.5-0.5B 에이전트, 자신의 추론 과정을 3D로 층층이 시각화하는 트레이스, 일반적인 초기 구현에서는 만들어만 두고
실제로 연결하지 않는 Human-in-the-Loop 승인 큐를 진짜로 배선한 구현, 순서가 올바른 가드레일 체크(순진한 구현은
여기서 순서를 틀리기 쉽습니다), 그리고 로컬 모델이 막힐 때를 위한 선택적 클라우드 에스컬레이션까지 포함합니다.

> 📄 스크린샷, 아키텍처 다이어그램, 하드웨어 요구사항, 클라우드 비용 추정치를 담은 완전한 이중언어(한국어 기본 /
> 영어) 운영 가이드: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ 시스템 설계: **[`architecture.md`](architecture.md)** · 🔀 함수 단위 플로우차트:
> **[`flowchart.md`](flowchart.md)**
> 🧸 **이 시리즈의 다섯 번째 독자적 비주얼 아이덴티티이자, 처음으로 진짜 3D/공간감을 도입한 버전** — 고명도·
> 저채도 파스텔 "클레이모피즘" 팔레트(더스티 라일락 + 세이지 그린을 은은한 오프화이트 배경 위에), 3단 타이포그래피
> 체계(둥근 디스플레이용 Quicksand + UI 크롬용 Plus Jakarta Sans + 감사 데이터용 Space Mono), 떠 있는 필(pill)
> 형태의 내비게이션 바, 몇몇 핵심 표면에만 한정한 마우스 반응형 `perspective`/`rotateX`/`rotateY` 틸트 컴포넌트,
> 에이전트 자신의 추론 단계를 층층이 살짝 회전시켜 표현한 "스택 카드" 시각화까지. 무엇이 진짜 공간감이고 무엇이
> 장식인지는 `architecture.md` §3 참고.
> 📈 이 패턴의 일반적인 기본 구현보다 의도적으로 한 단계 더 발전시켰습니다 — 순진한 구현은 가드레일 체크 순서를
> 잘못 두거나, Human-in-the-Loop 승인을 클래스 기능으로만 만들고 앱에는 실제로 연결하지 않기 쉽습니다. 무엇을
> 어떻게 더 다듬었는지는 `architecture.md` §2 참고.

## 무엇을 할 수 있나

| 모듈 | AI 모델 | 체험해볼 수 있는 것 |
|---|---|---|
| ◈ **콘솔** | 로컬 `Qwen2.5-0.5B-Instruct`(기본) 또는 OpenRouter의 `qwen/qwen3-8b`(선택적 에스컬레이션) | 에이전트에게 질문을 던지고, 생각하고·행동하고·관찰하는 과정을 한 단계씩 실시간으로, 3D 카드 스택으로 지켜보세요 |
| ✓ **승인** | — | 진짜 Human-in-the-Loop 큐: 게이트가 걸린 도구 호출(`issue_refund`)이 실제로 실행을 멈추고, 여기서 승인/거부하면 실행이 진짜로 재개됩니다 |
| ▤ **히스토리** | `multilingual-e5-small`(과거 실행 인덱싱) | 과거 모든 에이전트 실행에 대한 의미 기반 검색 — 키워드가 아니라 의미로 찾습니다 |
| ⚙ **관리자** | — | 실시간 가드레일 설정(허용 도구 / 스텝 한도 / 비용 상한을 런타임에 수정), 사용자 관리, AI 호출·도구 실행 전체 감사 로그, 사용량 분석, 선택적 에스컬레이션을 위한 일일 OpenRouter 지출 상한 |

**두 개의 AI 모델은 API 키 없이 100% 로컬에서 동작**합니다(히스토리 검색용 임베딩, 로컬 ReAct 에이전트 두뇌) —
세 번째인 OpenRouter의 `qwen/qwen3-8b`는 철저히 선택적으로만 쓰이며, 로컬 에이전트가 막히거나 사용자가 다른
의견을 원할 때 한 번의 최종 답변 합성을 위해서만 호출됩니다(두 번째 독립적인 도구 호출 루프가 아닙니다). 이전
주차의 PoC들과 달리 이번에는 실시간 외부 의존성이 없습니다(웹 검색도, 고정 코퍼스도 없음) — 에이전트의 "세상"은
로컬에서 실행되는 실제 도구 몇 가지(계산기, 날짜 조회, 환율 변환, FAQ 조회, 환불 처리)뿐입니다.

## 빠른 시작

요구사항: [Docker Desktop](https://www.docker.com/products/docker-desktop/)(macOS 또는 Windows), 여유 디스크
~6GB, 인터넷 연결(모델은 최초 1회만 다운로드하며, 실행 중인 앱 자체는 선택적 OpenRouter 에스컬레이션을 제외하고
네트워크가 필요 없습니다).

```bash
cd week5_2/PoC/projects/cradle
./scripts/setup.sh      # 최초 1회: 이미지를 빌드하고, 빈 포트를 선택하고, 컨테이너를 시작합니다
```

이게 전부입니다 — API가 응답하면 스크립트가 URL을 출력합니다(예: `http://localhost:8770`). 두 로컬 AI 모델은
최초 부팅 시 백그라운드에서 계속 다운로드/로딩되며(`docker compose logs -f`로 확인 가능), UI는 즉시 사용
가능하고 모델이 아직 준비되지 않았다면 첫 사용 시점에 자동으로 대기합니다.

```bash
./scripts/run.sh              # 이후 매번 — 빌드된 이미지를 재사용하므로 빠릅니다
./scripts/stop.sh             # 데이터를 삭제하지 않고 컨테이너만 중지
./scripts/verify_e2e.sh       # 전체 엔드투엔드 검증 실행(아래 참고) — 실제로 소액의 OpenRouter 과금이 한 번 발생합니다
./scripts/download_models.sh  # (선택) CLI로 두 로컬 AI 모델을 강제 다운로드/검증
```

모델 다운로드를 포함해 모든 과정이 셸 스크립트로 자동화되어 있습니다 — 수동 `docker exec`도, 노트북도, UI를
일일이 클릭할 필요도 없습니다.

**데모 관리자 로그인**: `admin@cradle.local` / `ChangeMe123!` (실제로 사용하기 전에는 `.env`의 `ADMIN_PASSWORD`를
반드시 변경하세요). 아니면 로그인 페이지에서 직접 계정을 만들어도 됩니다.

Windows에서는 이 `.sh` 스크립트들을 Git Bash나 WSL2에서 실행하세요(다른 `env_set_up.sh`/`run.sh` 스크립트에서
이미 사용해온 것과 같은 셸입니다).

## 프로젝트 구조

```
cradle/
├── backend/            FastAPI 앱 (Python 3.11) — backend/app/ 참고
│   ├── app/
│   │   ├── main.py           엔트리포인트, 시작 부트스트랩, SPA 정적 파일 서빙
│   │   ├── config.py         모든 설정, *_api_key_file 참조 포함(하드코딩된 시크릿 없음)
│   │   ├── models.py         SQLAlchemy ORM — AgentRun, AgentStep, ApprovalRequest, GuardrailSetting, BudgetSetting
│   │   ├── vectorstore.py    Chroma PersistentClient 래퍼 — 히스토리 검색을 위해 과거 실행을 인덱싱
│   │   ├── security.py       JWT + bcrypt 인증
│   │   ├── agent/             tools.py · react_loop.py(Thought/Action/Observation, few-shot, 스트리밍) ·
│   │   │                      guardrails.py(순서가 올바른 체크) · orchestrator.py(재개 가능한 루프)
│   │   ├── ml/                embeddings.py · llm.py(OpenRouter 에스컬레이션)
│   │   └── routers/            auth · agent(스트리밍) · approvals(HITL) · archive(히스토리) · admin · health
│   └── verify_e2e.py    엔드투엔드 스모크 테스트(scripts/verify_e2e.sh 참고)
├── frontend/            React + TypeScript + Vite + Tailwind SPA
│   └── src/             pages/(Dashboard, Console, Approvals, History, Admin, Login), components/TiltCard.tsx
├── docker/Dockerfile    멀티스테이지 빌드(Node 빌드 스테이지 -> Python 전용 런타임 이미지)
├── docker-compose.yml   단일 서비스, 네임드 볼륨, 호스트 포트 자동 선택
├── scripts/             setup.sh · run.sh · stop.sh · verify_e2e.sh · download_models.sh
├── architecture.md      시스템 다이어그램(Mermaid) + 기준 구현 비교표 + 프로덕션 확장 노트
├── flowchart.md         기능별 함수 단위 플로우차트(Mermaid)
└── docs/guide.html      올인원 이중언어 운영 가이드(아래 참고)
```

## Streamlit 대신 FastAPI + React를 선택한 이유

Week1-14_1 PoC들과 같은 이유이지만, 이번에는 그 이유가 두 배로 명확합니다: 이 패턴의 일반적인 기본 구현은
ReAct 에이전트 탭과 가드레일 클래스 탭이 서로 대화하지 않는 2탭짜리 Streamlit 데모이며, 영속성도 인증도 없고
HITL 승인은 쓰이지 않는 클래스 기능으로만 존재합니다. Cradle은 실제 사람의 결정을 위해 실행을 진짜로 멈출 수
있어야 하고 — 원래 HTTP 요청이 끝난 뒤에도 오랫동안 — 이를 위해서는 진짜 데이터베이스와 진짜 승인 큐
엔드포인트가 필요하지, 단일 Streamlit 스크립트의 지역 변수로는 부족합니다. 그 기준 구현을 넘어 구체적으로 어떤
엔지니어링을 더했는지는 `architecture.md` §2 참고.

## 이번 주에 시드 코퍼스가 없는 이유

고정 문서 코퍼스를 쓰는 Week4의 Lucent나 실시간 웹 검색을 쓰는 Week5_1의 Compass와 달리, 이번 주의 검색
대상은 에이전트가 도구로 호출하는 작고 고정된 로컬 Python 함수 집합뿐입니다 — 미리 인덱싱할 것이 없습니다.
`data/` 디렉터리가 대신 무엇을 담고 있는지는 `data/README.md`에서 설명합니다(런타임 SQLite DB와 과거 실행에
대한 Chroma 아카이브 인덱스로, 둘 다 최초 부팅 시 새로 생성됩니다).

## 가드레일 체크 순서에 대하여

네 가지 안전 가드레일(스텝 한도 → 권한 → 비용 상한 → HITL)은 정확히 이 순서로 체크됩니다 — 의도적이며,
문서화된 이유가 있습니다: 순진한 구현은 권한보다 비용 상한을 *먼저* 체크하기 쉬운데, 그렇게 되면 비용 상한도
초과한 미승인 도구 호출 시도가 감사 로그에 `BLOCKED_PERMISSION`이 아니라 `STOPPED_COST_CAP`으로 잘못
기록됩니다 — 감사 로그가 본래 제공해야 할 이상 징후 탐지 신호 자체를 오염시키는 셈입니다. 전체 설명은
`debug/issue-01`을, 코드 내 설명은 `agent/guardrails.py`의 docstring을 참고하세요.

## 엔드투엔드 검증

`scripts/verify_e2e.sh`는 살아있는 컨테이너 안에서 `backend/verify_e2e.py`를 실제 HTTP로 실행합니다(목킹
없음) — 실제 클라이언트처럼 스트리밍되는 에이전트 실행을 실제로 소비하고, 승인 대기 상태로 멈춘 실행을 재개까지
실제로 진행시킵니다: 두 로컬 모델이 준비 완료를 보고할 때까지 대기 → 회원가입 → JWT 인증 → 계산기 실행이
정확한 숫자 답에 도달하는지 확인 → 가드레일 순서 버그 패턴에 대한 직접 회귀 테스트 → 방치된 실행 리퍼에 대한
직접 회귀 테스트(`debug/issue-03` 참고) → 진짜 HITL 승인-재개 흐름과 거부-재개 흐름 → 스텝 한도·비용 상한
가드레일 정지 → 히스토리 의미 검색 → OpenRouter 에스컬레이션을 막는 $0 예산 상한 → 실제 OpenRouter
에스컬레이션 호출 1회 → 관리자 권한 경계. 이번 빌드의 실제 결과는
[`../../history/v1.0.0.md`](../../history/v1.0.0.md)에 기록되어 있습니다.

## 크레딧

이 PoC는 원본 작업물이며, `docs/guide.html` 전반에 명시된 공개 문서화된 모델 ID·API·라이브러리를 사용합니다.
다른 저장소에서 애플리케이션 코드를 복사한 적은 없습니다 — 다만 아키텍처는 이 같은 프로젝트 시리즈의
Week1-14_1 PoC들이 검증한 패턴(인증, 부트스트랩 격리, 준비상태 프로빙, 스트리밍 SSE 인프라, 일일 예산 상한
거버넌스 패턴)을 의도적으로 재사용했으며, ReAct 루프 설계와 로컬 에이전트 모델 선택은 소형 모델 기반 ReAct
에이전트에 대해 널리 공개된 문서화된 패턴을 따랐습니다.

## 라이선스

포트폴리오 PoC — 라이선스 관련 맥락은 최상위 저장소를 참고하세요. 서드파티 라이브러리/모델은 `docs/guide.html`에
문서화된 대로 각자의 라이선스를 따릅니다.
