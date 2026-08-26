# NOTEAI Backend - 빌드 및 실행 가이드

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env

# (선택) .env 파일 수정 (프로덕션 설정)
# - JWT_SECRET_KEY 변경
# - DATABASE_URL 변경 (PostgreSQL)
```

### 2. 가상 환경 설정

```bash
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS/Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 데이터베이스 초기화 (자동)

데이터베이스는 애플리케이션 실행 시 자동으로 초기화됩니다.

### 5. 서버 실행

```bash
python main.py
```

또는

```bash
uvicorn main:app --reload --port 8000
```

### 6. API 문서 확인

브라우저에서 다음 주소로 접속:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📁 프로젝트 구조

```
backend/
├── core/                    # 핵심 모듈
│   ├── config.py           # 설정
│   ├── database.py         # DB
│   └── security.py         # JWT, 해싱
│
├── features/               # 기능별 모듈
│   ├── auth/               # 인증
│   ├── users/              # 사용자
│   ├── notes/              # 노트 (핵심)
│   ├── comments/           # 댓글
│   ├── teams/              # 팀
│   ├── collaborators/      # 협업자
│   └── ai/                 # AI 기능
│
├── utils/                  # 공유 유틸
├── middleware/             # 미들웨어
├── main.py                 # 진입점
├── requirements.txt        # 의존성
└── .env.example           # 환경 설정 예제
```

---

## 🔑 주요 API 엔드포인트

### 인증
```
POST   /api/auth/register     회원가입
POST   /api/auth/login        로그인
POST   /api/auth/logout       로그아웃
GET    /api/auth/me           현재 사용자
```

### 노트 (핵심)
```
GET    /api/notes             노트 목록
POST   /api/notes             노트 생성
GET    /api/notes/{id}        노트 상세
PUT    /api/notes/{id}        노트 수정
DELETE /api/notes/{id}        노트 삭제
GET    /api/notes/search/q    검색
POST   /api/notes/{id}/summarize  AI 요약
```

### 상태 확인
```
GET    /api/health            헬스 체크
GET    /                      루트 경로
```

---

## 🗄️ 데이터베이스

### SQLite (개발)
- 파일: `noteai.db`
- 자동 생성됨

### PostgreSQL (프로덕션)
```bash
# .env 수정
DATABASE_URL=postgresql://user:password@localhost/noteai

# 데이터베이스 생성 (PostgreSQL)
createdb noteai

# 실행
python main.py
```

### 테이블 목록
- `users` - 사용자
- `notes` - 노트
- `note_versions` - 노트 버전
- `ai_summaries` - AI 요약
- `comments` - 댓글
- `note_collaborators` - 협업자
- `teams` - 팀
- `team_members` - 팀 멤버

---

## 🔐 인증 방식

### JWT Bearer Token

모든 인증이 필요한 요청에 헤더 추가:

```bash
Authorization: Bearer <your_jwt_token>
```

### 토큰 획득

```bash
# 로그인
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"john_doe","password":"password123"}'

# 응답
{
  "status": 200,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {...}
  }
}
```

---

## 🧪 테스트

### pytest 실행

```bash
# 모든 테스트 실행
pytest

# 특정 파일 테스트
pytest tests/features/test_auth.py

# 커버리지 확인
pytest --cov=features tests/
```

---

## 📝 주요 기능 구현 상황

### 완료 ✅
- [x] 인증 시스템 (회원가입, 로그인)
- [x] 노트 CRUD
- [x] 사용자 관리
- [x] 데이터베이스 스키마
- [x] JWT 토큰
- [x] API 엔드포인트

### 진행 중 ⏳
- [ ] AI 요약 (현재 더미 구현)
- [ ] 키워드 추출
- [ ] 자동 분류
- [ ] 시맨틱 검색

### 예정 📋
- [ ] 댓글 API
- [ ] 팀 API
- [ ] 협업자 권한 관리
- [ ] 파일 업로드

---

## 🐛 문제 해결

### "ModuleNotFoundError"
```bash
# 가상 환경 확인
# Windows
.\.venv\Scripts\Activate.ps1

# 의존성 재설치
pip install -r requirements.txt
```

### "Address already in use"
```bash
# 포트 변경
python main.py --port 8001

# 또는 기존 프로세스 종료 (Windows)
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### "SQLite database is locked"
```bash
# 데이터베이스 파일 삭제 후 재실행
rm noteai.db
python main.py
```

---

## 📚 개발 참고

### 새로운 Feature 추가

1. `features/새기능/` 폴더 생성
2. 다음 파일 생성:
   - `models.py` - SQLAlchemy 모델
   - `schemas.py` - Pydantic 스키마
   - `routes.py` - API 엔드포인트
   - `service.py` - 비즈니스 로직

3. `main.py`에 라우터 등록:
```python
from features.새기능.routes import router as new_router
app.include_router(new_router, prefix="/api")
```

### 데이터베이스 마이그레이션 (향후)

```bash
# Alembic 초기화 (처음 한 번)
alembic init alembic

# 마이그레이션 파일 생성
alembic revision --autogenerate -m "Add new table"

# 마이그레이션 적용
alembic upgrade head
```

---

## 🚀 배포

### Docker (선택)

```bash
# Dockerfile 생성 후
docker build -t noteai-backend .
docker run -p 8000:8000 noteai-backend
```

### 프로덕션 체크리스트
- [ ] DEBUG=False 설정
- [ ] JWT_SECRET_KEY 변경
- [ ] DATABASE_URL을 PostgreSQL로 변경
- [ ] CORS_ORIGINS 업데이트
- [ ] 로깅 설정
- [ ] HTTPS 설정

---

## 📞 지원

- **문서**: `docs/` 폴더 참고
- **API 문서**: http://localhost:8000/docs
- **프로젝트**: CLAUDE.md 참고

---

**마지막 업데이트**: 2026-08-26  
**버전**: 1.0 (Phase 2)
