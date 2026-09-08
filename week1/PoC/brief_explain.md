현재 폴더는 AI 커머스 PoC와 관련 문서를 모아둔 구조입니다.

- `projects/commerceiq`: 실제 FastAPI + React 애플리케이션
- `plan`: 구현 계획
- `history`: 버전별 작업 및 검증 기록
- `debug`: 문제 원인과 해결 기록
- `prompts`: 개발 프롬프트와 비용 산정 자료
- `etc`: 용어집 등 보조 문서

주요 AI 기능은 다음과 같습니다.

- ViT 기반 상품 이미지 분류
- Stable Diffusion 기반 마케팅 이미지 생성
- Holt-Winters 기반 매출 예측 및 이상 탐지
- Qwen LLM 기반 한국어/영어 비즈니스 인사이트 생성
- multilingual-e5와 Chroma를 이용한 다국어 시맨틱 검색
- 기본적으로 로컬 모델을 사용하고, OpenRouter 모델은 선택적으로 사용