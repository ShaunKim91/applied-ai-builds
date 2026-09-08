# 디버그 로그 — VoxIQ (Week2 PoC)

이 폴더는 이 프로젝트를 만들고 검증하는 과정에서 실제로 겪은 이슈를 기록합니다 — 근본 원인, 수정
내용, (관련 있는 경우) 어떤 기반 개념과 맞닿아 있는지까지 — 그래서 이 PoC를 확장하거나 비슷한
빌드를 반복하려는 사람을 위한 트러블슈팅 레퍼런스 역할도 합니다.

각 이슈는 자체 `issue-NN-short-slug.md` 파일로 기록됩니다. 이 README는 인덱스이며, 이슈가 발견될
때마다 갱신되고 미리 가정해서 작성되지 않습니다.

Week1 PoC("CommerceIQ")에 비해 이번 빌드에서는 이슈가 훨씬 적게 나왔습니다 — 의도된 결과입니다:
VoxIQ의 스캐폴딩은 처음부터 CommerceIQ에서 이미 디버깅이 끝난 `security.py`, 인증 라우터,
`_warm_step()` 부트스트랩 격리, readiness-probe 엔드포인트, `run.sh` 멱등성 체크를 그대로
재사용했기 때문에(`../architecture.md` §5 참고), Week1에서 후속 조치가 필요했던 유형의 버그가
여기서는 애초에 재발할 기회가 없었습니다. VoxIQ에 대한 최초의 `verify_e2e.sh` 실행은 실제 버그
0건으로 12/12를 통과했습니다.

| # | 제목 | 근본 원인 카테고리 |
|---|---|---|
| [01](issue-01-setup-sh-stale-model-count.md) | `setup.sh`가 "로컬 AI 모델 4개"라고 출력(VoxIQ는 실제로 5개) | CommerceIQ 스크립트를 복사해 수정하는 과정에서 남은 리터럴 값 — 겉보기 문제일 뿐, **수정됨** |
| [02](issue-02-local-llm-misreads-dict-shape.md) | Analytics Agent의 로컬 모델(Qwen2.5-0.5B)이 `ValueError: too many values to unpack`로 크래시하는 코드를 꾸준히 생성 | 소형 모델의 프롬프트 이해 공백 — 시스템 프롬프트가 데이터 형태는 설명했지만 순회 방법은 설명하지 않음; 8B OpenRouter 모델은 같은 실수를 하지 않았음 — **실제 버그, 수정됨**(프롬프트에 명시적 반례와 올바른 사용 예시 추가) |

## 이 이슈들을 발견한 방법

두 이슈 모두 코드를 읽어서가 아니라 실제로 실행 중인 앱을 사용하다가 발견했습니다: 이슈 01은
`setup.sh` 자체의 출력 내용을 `README.md` 및 `download_models.sh`와 대조하는 일상적인 일관성
점검 중에; 이슈 02는 문서화 목적으로 찍은 Playwright 스크린샷을 읽다가 "Sandbox output" 패널에
Python 스택 트레이스가 그대로 보이는 것을 발견하고, 이를 직접 `curl` 호출로 결정론적으로
재현한 뒤 수정하고 재검증했습니다.
