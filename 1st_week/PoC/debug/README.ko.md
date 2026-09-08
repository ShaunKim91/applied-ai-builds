# 디버그 로그 — CommerceIQ (PoC)

이 폴더는 이 프로젝트를 만들고 검증하는 과정에서 실제로 겪은 이슈를 기록합니다 — 근본 원인, 수정
내용, (관련 있는 경우) 어떤 기반 개념이 이를 설명하는지까지 — 그래서 이 PoC를 확장하거나 비슷한
빌드를 반복하려는 사람을 위한 트러블슈팅 레퍼런스 역할도 합니다.

각 이슈는 자체 `issue-NN-short-slug.md` 파일로 기록됩니다. 이 README는 인덱스이며, 이슈가 발견될
때마다 갱신되고 미리 가정해서 작성되지 않습니다.

| # | 제목 | 근본 원인 카테고리 |
|---|---|---|
| [01](issue-01-chromadb-posthog-telemetry-error.md) | 모든 컬렉션 호출마다 chromadb posthog 텔레메트리 오류 발생 | 업스트림 의존성 버전 불일치(chromadb ↔ posthog) — 겉보기 문제일 뿐 기능적 영향 없음 |
| [02](issue-02-email-validator-rejects-local-tld.md) | 관리자 로그인 실패: `.local` 이메일이 "배달 불가"로 거부됨 | 용도에 맞지 않는 검증 도구 사용(배달가능성 검사용 `EmailStr`을 로그인 ID 필드에 사용) — **실제 버그, 수정됨** |
| [03](issue-03-cold-start-timeout-and-readiness-probe.md) | 최초 부팅 시 기능 타임아웃이 실제로는 "아직 다운로드 중"이었던 문제 | 테스트 설계 공백(readiness probe 부재) — `/api/health/ready`와 대기 스텝 추가로 **수정됨** |
| [04](issue-04-docker-build-arg-cache-invalidation.md) | 재빌드할 때마다 캐시를 히트하지 못하고 ~1GB의 패키지를 계속 재다운로드 | 공유 개발 머신(기존 캐시 약 24GB)에서 Docker 빌드 캐시 GC 압박으로 추정 — 정확성 문제는 전혀 아니고 재빌드 속도 문제일 뿐; 그럼에도 compose.yml의 build-arg 관리를 개선함 |
| [05](issue-05-mape-blows-up-on-zero-revenue-days.md) | 실제 예측 실행에서 MAPE가 131,574.8%로 보고됨 | MAPE의 교과서적인 실측값-0 약점(실데이터의 매출 $0 토요일들) — **실제 버그, 수정됨**(MAPE 계산에서 제외 + sMAPE 추가) |
| [06](issue-06-bootstrap-steps-not-isolated.md) | 데이터셋 다운로드 하나가 실패하자 4개 AI 모델 워밍업 전체가 조용히 건너뛰어짐 | 서로 무관한 단계들이 하나의 try/except를 공유(최종 클린 재빌드 테스트 중 일시적 DNS 장애로 발견) — **실제 버그, 수정됨**(시작 6단계 각각을 독립적으로 격리) |
| [07](issue-07-run-sh-unnecessary-port-switch.md) | 컨테이너가 이미 실행 중인데도 `run.sh`가 불필요하게 포트를 전환함 | 포트 점유 여부 확인이 "다른 무언가가 점유 중"과 "이미 올바르게 실행 중인 내 컨테이너가 점유 중"을 구분하지 못함 — **실제 버그, 수정됨**(`docker compose ps`를 먼저 확인) |
