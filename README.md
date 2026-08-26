# NOTEAI - AI 기반 노트 큐레이션 및 협업 플랫폼

**연구원과 개발자를 위한 지능형 노트 관리 시스템**

---

## 📌 프로젝트 개요

NOTEAI는 사용자가 효율적으로 노트를 작성, 관리, 공유할 수 있으며, AI를 활용하여 자동 요약, 키워드 추출, 내용 분류, 시맨틱 검색 등의 고급 기능을 제공합니다.

### 핵심 기능
- **📝 구조화된 노트 작성**: 마크다운 기반 에디터
- **🤖 AI 기반 처리**: 자동 요약, 키워드 추출, 자동 분류
- **🔗 협업 기능**: 노트 공유, 댓글, 팀 관리
- **🔍 강력한 검색**: 전문 검색 + 시맨틱 검색
- **📊 대시보드**: 통계, 추천, 활동 추적

---

## 🛠 기술 스택

### Backend
- **FastAPI**: 빠른 웹 프레임워크
- **SQLAlchemy**: ORM
- **SQLite**: 개발용 데이터베이스
- **PyJWT**: 토큰 기반 인증
- **Hugging Face**: AI/NLP 모델

### Frontend
- **HTML5**: 구조
- **Tailwind CSS**: 스타일
- **Vanilla JavaScript**: 인터랙션

### Tools
- **Python 3.10+**: 런타임
- **pytest**: 테스트
- **Git**: 버전 관리

---

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 가상 환경 생성
python -m venv .venv

# 가상 환경 활성화 (Windows)
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

### 2. 의존성 설치

```bash
cd backend
pip install -r requirements.txt
```

### 3. 데이터베이스 초기화

```bash
python database.py
```

### 4. 서버 실행

```bash
python main.py
```

### 5. 브라우저에서 접속

```
http://localhost:8000
```

### API 문서 확인
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📂 프로젝트 구조

```
noteai/
├── docs/
│   ├── planning.md              # 전체 기획 문서
│   ├── requirements.md          # 요구사항 정의서
│   ├── api.md                   # API 엔드포인트
│   └── database.md              # 데이터베이스 설계
│
├── backend/
│   ├── main.py                  # FastAPI 진입점
│   ├── requirements.txt
│   │
│   ├── core/                    # 핵심 설정 및 DB
│   │   ├── __init__.py
│   │   ├── config.py            # 환경 설정
│   │   ├── database.py          # DB 세션 및 Base
│   │   ├── security.py          # JWT, 해싱
│   │   └── constants.py         # 상수 정의
│   │
│   ├── features/                # 기능별 모듈 (핵심!)
│   │   ├── __init__.py
│   │   ├── auth/                # 인증
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   ├── service.py
│   │   │   └── deps.py
│   │   ├── users/               # 사용자
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   └── service.py
│   │   ├── notes/               # 노트
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   └── service.py
│   │   ├── collaborators/       # 협업자
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   └── service.py
│   │   ├── comments/            # 댓글
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   └── service.py
│   │   ├── teams/               # 팀
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   └── service.py
│   │   └── ai/                  # AI
│   │       ├── schemas.py
│   │       ├── routes.py
│   │       ├── service.py
│   │       └── nlp_utils.py
│   │
│   ├── utils/                   # 공유 유틸
│   │   ├── helpers.py
│   │   ├── validators.py
│   │   ├── formatters.py
│   │   └── exceptions.py
│   │
│   ├── middleware/              # 미들웨어
│   │   ├── auth.py
│   │   ├── error_handler.py
│   │   └── logging.py
│   │
│   └── uploads/                 # 파일 저장소
│
├── frontend/
│   ├── index.html               # 진입점
│   ├── script.js                # 메인 로직
│   ├── style.css                # 커스텀 스타일
│   │
│   ├── pages/                   # 페이지
│   │   ├── home.html
│   │   ├── auth.html
│   │   ├── dashboard.html
│   │   ├── notes.html
│   │   ├── editor.html
│   │   ├── search.html
│   │   ├── teams.html
│   │   └── settings.html
│   │
│   ├── components/              # 컴포넌트
│   │   ├── navbar.html
│   │   ├── sidebar.html
│   │   ├── modals.html
│   │   └── editor.html
│   │
│   └── assets/
│       ├── css/
│       └── js/
│           ├── api.js
│           ├── auth.js
│           ├── notes.js
│           └── utils.js
│
├── tests/                       # 테스트
│   ├── features/
│   │   ├── test_auth.py
│   │   ├── test_notes.py
│   │   └── ...
│   └── integration/
│       └── test_workflows.py
│
├── CLAUDE.md                    # 개발 가이드
├── README.md                    # 이 파일
└── requirements.txt
```

### 📌 구조 설명

**Feature-Based Architecture** (기능별 계층적 구조):
- **core/**: 모든 기능이 공유하는 핵심 (설정, DB, 보안)
- **features/**: 각 기능이 독립적으로 동작 (auth, users, notes 등)
  - 각 기능 폴더는 models, schemas, routes, service 포함
- **utils/**: 전체에서 사용하는 헬퍼 함수
- **middleware/**: HTTP 미들웨어
- **frontend/**: UI (pages, components, assets)
- **tests/**: 기능별 단위 테스트

**장점**:
- 각 기능이 완전히 독립적
- 새 기능 추가가 쉬움 (폴더 추가만으로 완성)
- 팀원들이 다른 기능을 동시에 개발 가능
- 버그 수정이 특정 기능에만 영향

---

## 📋 주요 API 엔드포인트

### 인증
```
POST   /api/auth/register        회원가입
POST   /api/auth/login           로그인
POST   /api/auth/logout          로그아웃
GET    /api/auth/me              현재 사용자
```

### 노트
```
GET    /api/notes                노트 목록
POST   /api/notes                노트 생성
GET    /api/notes/{id}           노트 상세
PUT    /api/notes/{id}           노트 수정
DELETE /api/notes/{id}           노트 삭제
GET    /api/notes/search         검색
```

### AI 기능
```
POST   /api/notes/{id}/summarize        자동 요약
POST   /api/notes/{id}/extract-keywords 키워드 추출
POST   /api/notes/{id}/classify         자동 분류
POST   /api/notes/semantic-search       시맨틱 검색
```

### 팀
```
GET    /api/teams                팀 목록
POST   /api/teams                팀 생성
GET    /api/teams/{id}           팀 상세
POST   /api/teams/{id}/members   멤버 추가
```

**전체 API 문서**: [docs/api.md](docs/api.md)

---

## 📚 문서

- [기획 문서](docs/planning.md) - 전체 프로젝트 기획 및 아키텍처
- [요구사항 정의서](docs/requirements.md) - 상세 기능 요구사항
- [API 문서](docs/api.md) - 모든 엔드포인트 정의
- [데이터베이스 설계](docs/database.md) - 스키마 및 ERD
- [개발 가이드](CLAUDE.md) - 코딩 표준 및 개발 방법

---

## 🧪 테스트

### 단위 테스트 실행

```bash
pytest -v
```

### 테스트 커버리지 확인

```bash
pytest --cov=backend tests/
```

---

## 🔒 보안

### 구현된 보안 기능
- JWT 토큰 기반 인증
- 비밀번호 해싱 (bcrypt)
- SQL Injection 방지 (SQLAlchemy)
- CORS 설정
- 입력 유효성 검사
- 접근 제어 (권한 검증)

### 보안 체크리스트
- [ ] HTTPS/TLS 활성화
- [ ] 환경 변수 설정 (.env)
- [ ] 데이터베이스 암호화
- [ ] 로깅 및 모니터링
- [ ] 정기적인 백업

---

## 📈 성능

### 목표
- API 응답 시간: < 200ms
- 동시 사용자: 100명
- 데이터베이스 크기: 100GB

### 최적화
- 쿼리 인덱싱
- 캐싱 (향후 Redis)
- 페이지네이션
- 이미지 최적화

---

## 🐛 문제 해결

### 포트 오류 ("Address already in use")

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :8000
kill -9 <PID>
```

### 데이터베이스 오류

```bash
# 데이터베이스 초기화
rm noteai.db
python database.py
```

### 의존성 오류

```bash
# 의존성 재설치
pip install --upgrade -r requirements.txt
```

---

## 🔄 개발 단계

| Phase | 상태 | 설명 |
|-------|------|------|
| Phase 1 | ✅ 완료 | 기획 및 문서화 |
| Phase 2 | ⏳ 진행 중 | 백엔드 개발 |
| Phase 3 | 📋 예정 | 프론트엔드 개발 |
| Phase 4 | 📋 예정 | AI 기능 통합 |
| Phase 5 | 📋 예정 | 협업 기능 |
| Phase 6 | 📋 예정 | 테스트 및 배포 |

---

## 📝 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

---

## 👤 저자

**작성자**: Planner Team  
**이메일**: o12hana@gmail.com  
**프로젝트 관리자**: Claude Code

---

## 🤝 기여

프로젝트 개선에 대한 제안이나 버그 리포트는 이슈 트래커를 통해 제출해주세요.

---

## 📞 연락처

- **GitHub**: [NOTEAI Repository](#)
- **이메일**: o12hana@gmail.com
- **문제 보고**: [Issue Tracker](#)

---

## 📊 프로젝트 통계

- **시작일**: 2026-08-26
- **예상 완료일**: 2026-09-30
- **문서 수**: 5개
- **API 엔드포인트**: 30+
- **데이터베이스 테이블**: 9개

---

**마지막 업데이트**: 2026-08-26  
**버전**: 1.0 (Planner Phase)

---

### 다음 단계
Phase 2 (Backend Developer)에서 FastAPI 구현이 시작됩니다.
