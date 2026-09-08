# AI 엔지니어링 프로젝트 — 주차별 제품

응용 AI/ML 프로젝트 시리즈의 주차마다 하나씩 만든 풀스택 AI 제품 포트폴리오입니다 — 컴퓨터 비전,
LLM 내부 구조 & 문서 AI, RAG, 에이전틱 AI를 다룹니다. 각각 실제로 동작하는 Docker화된 풀스택 앱
(FastAPI + React/TypeScript)이며, 노트북 데모가 아닙니다 — 인증, 데이터베이스, 관리자 콘솔, 이중언어
(EN/KO) 문서를 갖추고 있습니다.

> 모든 제품은 로컬 우선(HuggingFace 모델, CPU 전용)으로 동작하며, OpenRouter를 통한 예산 제한형
> 선택적 클라우드 에스컬레이션을 지원합니다 — 유료 API 키 없이도 전부 실행됩니다.
> 같은 주차별 주제를 다루는 재작성된 학습 노트 컴패니언 레포:
> [`ai-curriculum`](https://github.com/ShaunKim91/ai-curriculum).

## 🧵 주목할 만한: "Fenwick Mutual" 스위트 (Week 6–8)

가상의 지역 보험사 하나를 위해 만든 서로 연결된 제품 3개로, 하나의 디자인 시스템과 하나의
상용급 보안/관측성 아키텍처(JWT 액세스+리프레시 로테이션, CSRF, 계정 잠금, 해시 체인 기반
변조 탐지 감사 로그, 실측 p50/p95/p99 지표)를 공유합니다 — 각각 일반적인 기능 목록이 아니라
구체적으로 이름이 부여된 페르소나 한 명을 위해 만들어졌습니다.

| 제품 | 대상 | 하는 일 |
|---|---|---|
| **[Verity](week6/PoC_v2/projects/verity/)** | Dana Whitfield, 시니어 클레임 리서치 애널리스트 | 근거 기반 리서치 어시스턴트 — 인용된 판례 요약, 환각 인용 검사, 가상의(실제가 아닌) 규제 코퍼스 대상 사기 신호 탐지 |
| **[Threshold](week7/PoC_v2/projects/threshold/)** | Priya Nakamura, 클레임 처리 팀 리드 | 안전장치를 갖춘 ReAct 에이전트 콘솔 — 금액을 인식하는 휴먼인더루프 승인으로 임계값 이상의 지급은 검토를 우회할 수 없음 |
| **[Throughline](week8/PoC/projects/throughline/)** | Marcus Webb, 보험계약자 서비스 담당자 | LangChain 대화 메모리 코파일럿 — 영속화된 이중 전략 메모리, 구조화된 사실 추출, 메모리 쓰기 충돌 안전장치 |

각각 자체 이중언어 운영 가이드(`docs/guide.html`), Mermaid 다이어그램이 포함된 아키텍처 문서,
수동 테스트로 발견한 실제 버그를 정직하게 기록한 디버그 로그, 실측치 기반 빌드 로그
(`history/v1.0.0.md` — Docker 이미지 크기, 부팅 시간, 엔드투엔드 테스트 결과, 전부 실제 측정값)를
갖추고 있습니다.

## 전체 제품

| 주차 | 주제 | 제품 |
|---|---|---|
| 1 | 컴퓨터 비전 & 생성 이미지 모델 | [CommerceIQ](week1/PoC/projects/commerceiq/) — 커머스 운영: 카탈로그 비전, 생성형 스튜디오, 수요 예측, 시맨틱 검색 |
| 2 | LLM 내부 구조, 임베딩, 오디오 AI | [VoxIQ](week2/PoC/projects/voxiq/) — 회의 & 지식 인텔리전스: 전사, 검색 재정렬, 분석 에이전트 |
| 3 | 멀티모달 문서 AI | [Parchment](week3/PoC/projects/parchment/) — 문서 인텔리전스: 영수증 OCR+VLM, PDF 요약, 표 스크래핑 |
| 4 | RAG | [Lucent](week4/PoC/projects/lucent/) — 인라인 인용과 자동 근거성 검사를 갖춘 스트리밍 RAG 챗 |
| 6 | 검색 기반 리서치 | [Compass](week6/PoC/projects/compass/) → **[Verity](week6/PoC_v2/projects/verity/)** (위 스위트 참고) |
| 7 | 에이전틱 AI 기초 | [Cradle](week7/PoC/projects/cradle/) → **[Threshold](week7/PoC_v2/projects/threshold/)** (위 스위트 참고) |
| 8 | LangChain 에이전트 & 메모리 | **[Throughline](week8/PoC/projects/throughline/)** (위 스위트 참고) |

`PoC/` = 최초 주차 빌드. `PoC_v2/` = 이전 결과물에 대한 직접 피드백("모든 제품에 더 명확한
타깃 설정이 필요하다")을 받은 뒤 처음부터 다시 만든 상용급 재구축 버전이며, 전후 비교가 보이도록
덮어쓰지 않고 나란히 유지했습니다.

## 프로젝트 실행 방법

```bash
cd week<N>/PoC[_v2]/projects/<name>/
./scripts/setup.sh          # 이미지를 빌드하고, 컨테이너를 시작하고, 헬스체크를 기다립니다
./scripts/verify_e2e.sh     # 전체 엔드투엔드 검증 스위트
```

필요 사항: Docker Desktop, 프로젝트당 여유 디스크 ~5GB, 최초 모델 다운로드를 위한 인터넷 연결.
데모 관리자 계정 정보는 `setup.sh` 실행 시 출력되며, 각 프로젝트 자체 README에도 문서화되어 있습니다.

## API 키 관련 안내

이 레포 어디에도 실제 API 키는 포함되어 있지 않습니다. 어떤 프로젝트든 선택적 클라우드
에스컬레이션 기능을 사용해보려면, 자신의 `api_keys/openrouter.md`를 각 프로젝트를 클론한 위치
한 단계 위(해당 프로젝트 자체 `docker-compose.yml`의 볼륨 마운트에 맞춰, 자신의 레이아웃에
맞게 조정)에 만들면 됩니다 — 키가 없어도 모든 프로젝트가 로컬 전용 추론으로 폴백해 완전히
동작합니다.

## 라이선스

원본 포트폴리오 작업물입니다. 언급된 모든 회사, 인물, 데이터("Fenwick Mutual" 등)는 가상입니다.
서드파티 라이브러리와 모델은 각자의 라이선스를 유지하며, 각 제품 자체의 `docs/guide.html`에
문서화되어 있습니다.
