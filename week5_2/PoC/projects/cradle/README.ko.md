# Cradle

[English](README.md) | **한국어**

**실제 안전장치를 갖춘 로컬 ReAct 에이전트 콘솔** — Week5_2 PoC로, AI 엔지니어링 프로젝트 포트폴리오의 일부입니다. 에이전틱 AI의 기본 개념(Thought→Action→Observation 루프, 에이전트 자신의 "두뇌" 역할을 하는 로컬 LLM, 자율 에이전트를 안전하게 지키는 4가지 안전장치)을 실제로 동작하는 제품으로 구현했습니다. 도구를 실제로 호출하는 로컬 Qwen2.5-0.5B 에이전트, 자신의 추론 과정을 층층이 쌓아 보여주는 3D 트레이스, 일반적인 초기 구현에서는 만들어놓고도 실제로 연결하지 않는 Human-in-the-Loop 승인 큐를 진짜로 배선한 구현, 순서를 정확히 지킨 안전장치 검사(단순한 구현에서는 여기서 실수하기 쉬움), 그리고 로컬 모델이 막혔을 때를 위한 선택적 클라우드 에스컬레이션입니다.

> 📄 스크린샷, 아키텍처 다이어그램, 하드웨어 요구 사항, 클라우드 비용 추정치를 포함한 전체 이중 언어(한국어 기본/영어) 운영 가이드: **[`docs/guide.html`](docs/guide.html)**
> 🏗️ 시스템 설계: **[`architecture.md`](architecture.md)** · 🔀 함수 수준 흐름도: **[`flowchart.md`](flowchart.md)**
> 🧸 **다섯 번째로 구별되는 비주얼 아이덴티티이자, 실제 3D/공간감을 처음으로 도입한 버전** — 명도는 높고 채도는 낮은 파스텔 톤 "클레이모피즘" 팔레트(부드러운 오프화이트 바탕에 더스티 라일락 + 세이지 그린), 3계열 타입 시스템(둥근 디스플레이용 Quicksand + UI 크롬용 Plus Jakarta Sans + 감사 데이터용 Space Mono), 떠 있는 필(pill) 형태의 내비게이션 바, 몇몇 핵심 화면에만 적용한 마우스 반응형 `perspective`/`rotateX`/`rotateY` 틸트 컴포넌트, 그리고 에이전트 자신의 추론 단계를 층층이 살짝 회전시켜 시각화한 "카드 스택" 표현. 무엇이 실제로 공간적이고 무엇이 장식에 불과한지는 `architecture.md` §3을 참고하세요.
> 📈 이 패턴의 일반적인 초기 구현보다 의도적으로 더 발전시켰습니다 — 단순한 구현에서는 안전장치를 잘못된 순서로 검사하거나, Human-in-the-Loop 승인을 클래스 기능으로만 만들어두고 앱에 실제로 연결하지 않는 실수를 하기 쉽습니다 — 정확히 무엇을 더 다듬었고 왜인지는 `architecture.md` §2를 참고하세요.

## 주요 기능

| 모듈 | AI 모델 | 체험할 수 있는 기능 |
|---|---|---|
| ◈ **콘솔** | 로컬 `Qwen2.5-0.5B-Instruct`(기본) 또는 OpenRouter의 `qwen/qwen3-8b`(선택적 에스컬레이션) | 에이전트에게 질문을 던지고, 생각하고·행동하고·관찰하는 과정을 층층이 쌓인 3D 카드 스택으로 한 단계씩 실시간으로 지켜보기 |
| ✓ **승인** | — | 실제 Human-in-the-Loop 큐: 승인이 필요한 도구 호출(`issue_refund`)이 실제로 실행을 멈추고, 여기서 승인하거나 거부하면 실행이 실제로 재개됩니다 |
| ▤ **이력** | `multilingual-e5-small`(과거 실행 색인) | 과거 모든 에이전트 실행 기록에 대한 시맨틱 검색 — 키워드가 아니라 의미로 찾습니다 |
| ⚙ **관리자** | — | 실시간 안전장치 설정(허용 도구/스텝 한도/비용 한도, 런타임에 수정 가능), 사용자 관리, 전체 AI 호출 + 도구 실행 감사 추적, 사용량 분석, 선택적 에스컬레이션을 위한 일일 OpenRouter 지출 한도 |

**AI 모델 2개는 API 키 없이 100% 로컬에서 실행됩니다**(이력 검색용 임베딩, 로컬 ReAct 에이전트의 두뇌). 세 번째 모델인 OpenRouter의 `qwen/qwen3-8b`는 철저히 선택 사용으로, 로컬 에이전트가 막히거나 사용자가 다른 의견을 원할 때 최선을 다해 최종 답변을 한 번 합성하는 용도로만 쓰이며, 독립적인 두 번째 도구 호출 루프가 아닙니다. 이전 모든 주차의 PoC와 달리 이번에는 살아있는 외부 의존성이 없습니다(웹 검색도, 고정 코퍼스도 없음) — 에이전트의 "세계"는 실제로 로컬에서 실행되는 작은 도구 집합(계산기, 날짜 조회, 환율 변환, FAQ 조회, 환불 처리)뿐입니다.

## 빠른 시작

요구 사항: [Docker Desktop](https://www.docker.com/products/docker-desktop/)(macOS 또는 Windows), 약 6GB의 여유 디스크 공간, 인터넷 연결(모델 최초 다운로드용; 실행 중인 앱 자체는 선택적 OpenRouter 에스컬레이션을 제외하면 네트워크가 필요하지 않습니다).

```bash
cd week5_2/PoC/projects/cradle
./scripts/setup.sh      # 최초 실행: 이미지 빌드, 빈 포트 선택, 컨테이너 시작
```

이것으로 준비가 끝납니다 — API가 응답하면 스크립트가 접속 URL(예: `http://localhost:8770`)을 출력합니다. 로컬 AI 모델 2개는 최초 부팅 시 백그라운드에서 계속 다운로드/로딩됩니다(`docker compose logs -f`로 확인). UI는 즉시 사용할 수 있으며, 아직 준비되지 않은 모델을 처음 사용할 때만 완료될 때까지 기다립니다.

```bash
./scripts/run.sh              # 이후 실행 시 사용 — 빌드한 이미지를 재사용하므로 빠름
./scripts/stop.sh             # 컨테이너와 데이터를 삭제하지 않고 중지
./scripts/verify_e2e.sh       # 전체 엔드투엔드 검사 실행(아래 참고) — 실제로 소액의 OpenRouter 요금이 한 번 발생합니다
./scripts/download_models.sh  # (선택) CLI에서 로컬 AI 모델 2개를 강제 다운로드/검증
```

모델 다운로드를 포함한 모든 작업은 셸 스크립트만으로 수행됩니다. 수동 `docker exec`, 노트북, UI 클릭은 필요하지 않습니다.

**데모 관리자 로그인**: `admin@cradle.local` / `ChangeMe123!`(실제 환경에서 사용하기 전에 `.env`의 `ADMIN_PASSWORD`를 변경하세요). 로그인 페이지에서 직접 일반 계정을 만들어도 됩니다.

Windows에서는 Git Bash 또는 WSL2에서 이 `.sh` 스크립트를 실행하세요(이 프로젝트 시리즈의 다른 `env_set_up.sh`/`run.sh` 스크립트에서도 같은 셸을 사용합니다).

## 프로젝트 구조

```
cradle/
├── backend/            FastAPI 앱(Python 3.11) — backend/app/ 참고
│   ├── app/
│   │   ├── main.py           진입점, 시작 초기화, SPA 정적 파일 제공
│   │   ├── config.py         모든 설정, *_api_key_file 참조 포함(비밀값 하드코딩 없음)
│   │   ├── models.py         SQLAlchemy ORM — AgentRun, AgentStep, ApprovalRequest, GuardrailSetting, BudgetSetting
│   │   ├── vectorstore.py    Chroma PersistentClient 래퍼 — 이력 검색을 위해 과거 실행을 색인
│   │   ├── security.py       JWT + bcrypt 인증
│   │   ├── agent/             tools.py · react_loop.py(Thought/Action/Observation, 퓨샷, 스트리밍) ·
│   │   │                      guardrails.py(수정된 검사 순서) · orchestrator.py(재개 가능한 루프)
│   │   ├── ml/                embeddings.py · llm.py(OpenRouter 에스컬레이션)
│   │   └── routers/            auth · agent(스트리밍) · approvals(HITL) · archive(이력) · admin · health
│   └── verify_e2e.py    엔드투엔드 스모크 테스트(scripts/verify_e2e.sh 참고)
├── frontend/            React + TypeScript + Vite + Tailwind SPA
│   └── src/             pages/(Dashboard, Console, Approvals, History, Admin, Login), components/TiltCard.tsx
├── docker/Dockerfile    다단계 빌드(Node 빌드 단계 → Python 전용 런타임 이미지)
├── docker-compose.yml   단일 서비스, 명명된 볼륨, 호스트 포트 자동 선택
├── scripts/             setup.sh · run.sh · stop.sh · verify_e2e.sh · download_models.sh
├── architecture.md      시스템 다이어그램(Mermaid) + 초기 구현 비교표 + 프로덕션 확장 참고 사항
├── flowchart.md         기능별 함수 수준 흐름도(Mermaid)
└── docs/guide.html      일체형 이중 언어 운영 가이드(아래 참고)
```

## Streamlit 대신 FastAPI + React를 선택한 이유

Week1-5_1 PoC들과 같은 이유이며, 이번에는 그 이유가 두 배로 분명합니다. 이 패턴의 일반적인 초기 구현은 2개 탭짜리 Streamlit 데모로, ReAct 에이전트 탭과 안전장치 클래스 탭이 서로 소통하지 않고, 지속성도 인증도 없으며, HITL 승인은 사용되지 않는 클래스 기능으로만 존재합니다. Cradle은 실제 사람의 결정을 기다리며 멈출 수 있는 재개 가능한 실행이 필요합니다 — 원래의 HTTP 요청이 이미 끝난 뒤에도 한참 지나서일 수 있으므로, 단일 Streamlit 스크립트의 로컬 변수가 아니라 진짜 데이터베이스와 진짜 승인 큐 엔드포인트가 필요합니다. 그 초기 구현을 넘어서는 구체적인 엔지니어링 내용은 `architecture.md` §2를 참고하세요.

## 이번 주에는 시드 코퍼스가 없는 이유

Week4의 Lucent(고정된 문서 코퍼스)나 Week5_1의 Compass(실시간 웹 검색)와 달리, 이번 주의 검색 대상은 에이전트가 도구로 호출하는 작고 고정된 로컬 Python 함수 집합입니다 — 미리 색인화할 것이 없습니다. `data/README.md`에 `data/`가 대신 무엇을 담고 있는지 설명되어 있습니다(런타임 SQLite DB와 과거 실행에 대한 Chroma 아카이브 색인으로, 둘 다 최초 부팅 시 새로 생성됩니다).

## 안전장치 검사 순서에 관한 참고 사항

4가지 안전장치(스텝 한도 → 권한 → 비용 한도 → HITL)는 정확히 이 순서로 검사됩니다 — 의도적인 순서이며, 그 이유가 명확히 문서화되어 있습니다. 단순한 구현에서는 비용 한도를 권한 검사 *이전에* 확인할 수 있는데, 그러면 비용 한도도 초과하는 허가되지 않은 도구 호출 시도가 감사 추적에서 `BLOCKED_PERMISSION`이 아니라 `STOPPED_COST_CAP`으로 잘못 기록됩니다 — 감사 추적이 애초에 존재하는 이유인 이상 탐지 신호 자체를 왜곡시키는 문제입니다. 전체 설명은 `debug/issue-01`을, 코드 내 설명은 `agent/guardrails.py`의 docstring을 참고하세요.

## 엔드투엔드 검증

`scripts/verify_e2e.sh`는 실행 중인 컨테이너 내부에서 `backend/verify_e2e.py`를 실제 HTTP로 실행하며 모의 객체를 사용하지 않습니다 — 실제 클라이언트처럼 스트리밍되는 에이전트 실행을 그대로 소비하고, 승인 대기로 멈춘 실행을 실제로 재개까지 실행하는 과정도 포함합니다. 로컬 모델 2개가 모두 준비 완료 상태가 될 때까지 대기 → 회원가입 → JWT 인증 → 계산기 실행이 정확한 숫자 답을 내는지 확인 → 안전장치 순서 버그 패턴에 대한 직접 회귀 테스트 → 방치된 실행 리퍼(reaper)에 대한 직접 회귀 테스트(`debug/issue-03` 참고) → 실제 HITL 일시정지-승인-재개 흐름 및 실제 일시정지-거부-재개 흐름 → 스텝 한도 및 비용 한도 안전장치 정지 → 이력 시맨틱 검색 → $0 예산 한도가 OpenRouter 에스컬레이션을 차단하는지 확인 → 실제 OpenRouter 에스컬레이션 호출 1회 → 관리자 권한 경계 확인. 이 빌드의 실제 결과는 [`../../history/v1.0.0.md`](../../history/v1.0.0.md)에 기록되어 있습니다.

## 저작권 및 출처

이 PoC는 독창적인 작업이며, `docs/guide.html` 전반에 인용된 공개 문서에 명시된 모델 ID, API, 라이브러리를 사용했습니다. 다른 저장소의 애플리케이션 코드를 복사하지 않았습니다 — 다만 아키텍처 면에서는 이 프로젝트 시리즈 자체의 Week1-5_1 PoC들에서 검증된 패턴(인증, 부트스트랩 격리, 준비 상태 프로빙, 스트리밍 SSE 인프라, 일일 예산 한도 거버넌스 패턴)을 의도적으로 재사용했으며, ReAct 루프 설계와 로컬 에이전트 모델 선택은 소형 모델 ReAct 에이전트에 대해 널리 문서화되고 공개적으로 알려진 패턴을 따랐습니다.

## 라이선스

포트폴리오 PoC입니다. 라이선스 맥락은 최상위 저장소를 참고하세요. 제3자 라이브러리/모델에는 `docs/guide.html`에 명시된 각각의 라이선스가 그대로 적용됩니다.
