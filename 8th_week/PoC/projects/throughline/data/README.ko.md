# data/

Docker 볼륨으로 마운트된 영속 스토리지(`throughline_data`):

- `app.db` — SQLite, 시스템 오브 레코드(조직, 사용자, 케이스, 대화 턴, 메모리 사실, 감사 로그 등)
- `chroma/` — Chroma의 영속 벡터 스토어(Workspace 디렉터리 시맨틱 검색을 위한 케이스 요약)

이 디렉터리의 어떤 것도 버전 관리에 커밋되지 않습니다(`.gitignore` 참고) — 실제 런타임
데이터이며, 컨테이너가 처음 시작될 때 채워지고 `docker compose stop`/`up` 사이클을 거쳐도
유지됩니다.
