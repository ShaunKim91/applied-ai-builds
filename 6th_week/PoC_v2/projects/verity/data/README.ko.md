# data/

레포지토리 안에서는 비어 있습니다 — Docker 볼륨 `verity_data` 안에서 런타임에 채워집니다:

- `app.db` — SQLite 데이터베이스(조직, 사용자, 리프레시 토큰, 리서치 세션/엔트리, CAT 이벤트, 예산 설정, 해시 체인 기반 감사 로그, 오류 로그)
- `chroma/` — Chroma `PersistentClient` 벡터 스토어(Claim Research Library 시맨틱 검색을 위한 과거 리포트 임베딩)

이번 라운드의 Verity는 정적 시드 코퍼스가 없습니다 — 클레임/관할권 리서치는 인덱싱된 문서 세트가
아니라 완전히 가상의, 코드로 정의된 코퍼스(`backend/app/search/jurisdictions.py`)에 근거를
둡니다. 이유는 해당 파일의 모듈 docstring을 참고하세요.
