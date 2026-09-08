# 디버그 로그 — Throughline (Week8 PoC)

실제 수동 테스트(개발 중에는 실제 로컬 모델을 대상으로 로컬 FastAPI `TestClient` 실행, 이후
실제 Docker 컨테이너를 대상으로 한 전체 `verify_e2e.py` 스위트)와 직접적인 트레이스백 검사를
통해 발견한 이슈만 기록합니다 — 지어낸 내용은 없습니다. 각 항목은 실제로 관측된 증상을 코드에서
실제로 확인된 근본 원인과 연결합니다.

| # | 제목 | 심각도 | 상태 |
|---|---|---|---|
| [01](issue-01-detached-orm-instance-across-sse-session-boundary.md) | 한 `SessionLocal()` 세션에서 만든 `MemoryConflictLog` 행을 그 세션이 닫힌 뒤 다시 읽으려다, 메모리 충돌이 발생한 모든 턴의 후반부가 크래시함 | 높음 | 수정, 회귀 테스트 완료 |
| [02](issue-02-memory-facts-never-reached-the-reply-prompt.md) | 구조화된 `MemoryFact` 행이 추출되고 저장되고 UI 사이드바에 표시까지 되었지만, 실제로는 답변 생성 프롬프트에 전혀 주입되지 않음 — 메모리 기능이 사이드바를 장식하는 것 외에 실질적으로 아무 역할도 하지 않았음 | 높음 | 수정, 회귀 테스트 완료 |
| [03](issue-03-chatpromptvalue-not-subscriptable-in-summarization.md) | 실제 `ChatPromptTemplate`을 공유 로컬 모델 `Runnable`에 직접 파이핑하자 메시지 리스트가 아닌 `ChatPromptValue`가 전달됨 — 실제로 처음 실행될 때 윈도우-요약 전환 단계가 크래시함 | 높음 | 수정, 회귀 테스트 완료 |
| [04](issue-04-callback-window-preference-never-matched-fixed-slots.md) | 발신자의 "오전"/"오후" 선호가 도구 호출에 올바르게 자동 채워졌지만, 도구 자체의 `"...AM"`/`"...PM"` 표기 슬롯 대상 리터럴 부분 문자열 매칭이 실제로는 전혀 작동하지 않았음 | 낮음 | 수정, E2E로 커버됨 |

## 이번 라운드에 실제 버그가 0건이 아니라 4건 나온 이유

Verity는 자체적으로 새로운 버그 3건을 발견했고, Threshold는 전작 Cradle PoC의 모든 버그 유형을
처음부터 올바르게 물려받았으며 자기 고유의 더 풍부한 도구 인자 표면에 특화된 새로운 버그를
(두 가지 형태로) 하나 발견했습니다. Throughline의 진짜로 새로운 영역 — SSE 제너레이터에 걸친
실제 다중 세션 경계 SQLAlchemy 사용, 손으로 만든 메시지 리스트가 아닌 두 번째 독립적인 LCEL
구성 형태(`ChatPromptTemplate | Runnable`), 그리고 저장되는 데 그치지 않고 실제로 모델에 도달해야
하는 구조화된 메모리 — 은 자기만의 새로운 실패 유형을 만들어냈고, 두 자매 제품 중 어느 쪽의
테스트도 이를 겪을 이유가 없었습니다. 네 건 모두 직접적이고 의도적인 다중 턴 대화 테스트(먼저
빠른 반복을 위해 로컬 `TestClient` 프로세스 대상, 이후 실제 Docker 컨테이너에서 재확인)를 통해
발견되었으며 `verify_e2e.py` 단독으로 발견한 것이 아닙니다 — 스위트 자체의 관련 회귀 스텝은
각 수정 *이후에* 작성되어 그것을 고정시켰으며, 이는 Fenwick Mutual 스위트 전체에서 유지해 온
관례를 따른 것입니다.

## 제품 버그가 아닌 실제 발견 사항

전체 컨테이너 재빌드에 들어가기 전 빠른 피드백을 얻기 위해 로컬에서(Docker 밖, 이 개발 머신의
Python 가상환경을 대상으로 직접) 반복 작업하던 중, 한 테스트 실행에서 `RuntimeError:
unsupported scalarType`과 `transformers`의 "model on `meta` device" 경고가 발생했고, 별개의
실행에서는 Python 프로세스 종료 시점에 `libc++abi: ... recursive_mutex lock failed`로
크래시했습니다. 두 현상 모두 이 macOS 개발 환경 자체로 원인이 좁혀졌습니다: 로컬 프로브 가상환경에
설치된 기본(CPU 제한 없는) `torch` 빌드가 Apple Silicon의 `mps` 백엔드를 자동 감지했고(해당
실행 자체의 로그 라인 `Use pytorch device_name: mps`에서 확인됨), 이는 이 앱의 코드가 명시적으로
요청한 적이 없고 실제 Docker 배포 환경(Linux, `docker/Dockerfile`에 고정된 CPU 전용
`torch==2.8.0+cpu` 휠)에서는 애초에 사용할 수조차 없는 디바이스입니다. 실제 Docker 컨테이너에서는
같은 종류의 다중 턴, 모델 로딩, 백그라운드 스레드 활동이 3회의 완전한 클린 재빌드 내내 두 증상
모두 0건으로 깔끔하게 실행되었고, 컨테이너 대상 `verify_e2e.py` 실행도 매번 문제없이 통과해,
이것이 그 혼재된 CPU/MPS 로컬 환경의 아티팩트일 뿐 제품 결함이 아님을 확인했습니다.
