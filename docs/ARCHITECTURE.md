# NOTEAI - 아키텍처 및 데이터 흐름 분석

## 📁 디렉토리 구조 분석

### Feature-Based Architecture

```
noteai/
├── backend/                 # FastAPI 백엔드
│   ├── core/                # 핵심 모듈 (공유)
│   │   ├── config.py        # 환경 설정 (싱글톤)
│   │   ├── database.py      # SQLAlchemy 초기화
│   │   ├── security.py      # JWT, bcrypt
│   │   └── __init__.py
│   │
│   ├── features/            # 기능별 독립 모듈
│   │   ├── auth/            # 인증 기능
│   │   │   ├── models.py    # User ORM
│   │   │   ├── schemas.py   # Pydantic 스키마
│   │   │   ├── routes.py    # FastAPI 라우터
│   │   │   ├── service.py   # 비즈니스 로직
│   │   │   ├── deps.py      # 의존성 (get_current_user)
│   │   │   └── __init__.py
│   │   │
│   │   ├── notes/           # 노트 관리 (핵심)
│   │   │   ├── models.py    # Note, NoteVersion, AISummary
│   │   │   ├── schemas.py   # 요청/응답
│   │   │   ├── routes.py    # CRUD 엔드포인트
│   │   │   ├── service.py   # 검색, 버전 관리
│   │   │   └── __init__.py
│   │   │
│   │   ├── users/
│   │   ├── comments/
│   │   ├── teams/
│   │   ├── collaborators/
│   │   ├── ai/
│   │   └── __init__.py
│   │
│   ├── utils/               # 공유 유틸
│   │   ├── helpers.py
│   │   ├── validators.py
│   │   ├── exceptions.py
│   │   └── __init__.py
│   │
│   ├── middleware/          # 미들웨어
│   │   ├── auth.py
│   │   ├── error_handler.py
│   │   └── __init__.py
│   │
│   ├── uploads/             # 파일 저장소
│   ├── main.py              # FastAPI 앱 진입점
│   ├── requirements.txt      # 의존성
│   ├── .env.example         # 환경 설정 예제
│   └── BACKEND_README.md    # 빌드 가이드
│
├── frontend/                # 프론트엔드 (React/Vue)
│   ├── index.html
│   ├── pages/
│   ├── components/
│   └── assets/
│
├── tests/                   # 자동화 테스트
│   ├── conftest.py          # pytest 설정
│   ├── features/
│   │   ├── test_auth.py     # 인증 테스트
│   │   ├── test_notes.py    # 노트 테스트
│   │   └── test_users.py
│   ├── test_file_upload.py  # 파일 업로드 테스트
│   └── integration/
│       └── test_workflows.py
│
├── docs/                    # 문서
│   ├── planning.md          # 기획 문서
│   ├── requirements.md      # 요구사항 정의서
│   ├── api.md               # API 명세
│   ├── database.md          # DB 설계
│   └── ARCHITECTURE.md      # 이 파일
│
├── CLAUDE.md                # 개발 가이드
└── README.md                # 프로젝트 개요
```

---

## 🔄 데이터 흐름 분석

### 1️⃣ 사용자 인증 흐름

```
클라이언트                          FastAPI 백엔드                         데이터베이스
    │                                   │                                      │
    ├─ POST /api/auth/register          │                                      │
    │      (username, email, pwd)        │                                      │
    ├──────────────────────────────────>│                                      │
    │                                   │ routes.py: register()                │
    │                                   │ ├─ 유효성 검사 (Pydantic)            │
    │                                   │ ├─ service.register_user()           │
    │                                   ├─────────────────────────────────────>│
    │                                   │                                      │ INSERT users
    │                                   │<─────────────────────────────────────┤
    │                                   │ security.hash_password()             │
    │                                   │ ├─ bcrypt 해싱                       │
    │                                   │ ├─ JWT 토큰 생성                     │
    │                                   │ 응답: {token, user_info}            │
    │<──────────────────────────────────┤                                      │
    │      201 Created                   │                                      │
    │
```

### 2️⃣ 노트 생성 흐름 (인증 필수)

```
클라이언트                          FastAPI 백엔드                         데이터베이스
    │                                   │                                      │
    ├─ POST /api/notes                  │                                      │
    │      + Authorization: Bearer token│                                      │
    │      {title, content, tags}       │                                      │
    ├──────────────────────────────────>│                                      │
    │                                   │ deps.get_current_user()              │
    │                                   │ ├─ JWT 검증 → User 객체            │
    │                                   ├─────────────────────────────────────>│
    │                                   │                                      │ SELECT users
    │                                   │<─────────────────────────────────────┤
    │                                   │ routes.create_note()                 │
    │                                   │ ├─ 유효성 검사                       │
    │                                   │ ├─ service.create_note()             │
    │                                   ├─────────────────────────────────────>│
    │                                   │                                      │ INSERT notes
    │                                   │                                      │ INSERT note_versions (v1)
    │                                   │<─────────────────────────────────────┤
    │                                   │ 응답: {note_id, ...}                │
    │<──────────────────────────────────┤                                      │
    │      201 Created                   │                                      │
```

### 3️⃣ 노트 수정 및 버전 관리 흐름

```
클라이언트                          FastAPI 백엔드                         데이터베이스
    │                                   │                                      │
    ├─ PUT /api/notes/{note_id}         │                                      │
    │      {new_title, new_content}     │                                      │
    ├──────────────────────────────────>│                                      │
    │                                   │ 현재 사용자 검증                     │
    │                                   │ service.update_note()                │
    │                                   │ ├─ 최신 버전 번호 조회               │
    │                                   ├─────────────────────────────────────>│
    │                                   │                                      │ SELECT max(version_number)
    │                                   │<─────────────────────────────────────┤
    │                                   │ ├─ 이전 내용을 버전에 저장           │
    │                                   ├─────────────────────────────────────>│
    │                                   │                                      │ INSERT note_versions (v+1)
    │                                   │ ├─ 노트 업데이트                     │
    │                                   ├─────────────────────────────────────>│
    │                                   │                                      │ UPDATE notes
    │                                   │<─────────────────────────────────────┤
    │<──────────────────────────────────┤                                      │
    │      200 OK                        │                                      │
```

### 4️⃣ 노트 검색 흐름

```
클라이언트                          FastAPI 백엔드                         데이터베이스
    │                                   │                                      │
    ├─ GET /api/notes/search/q?q=AI     │                                      │
    ├──────────────────────────────────>│                                      │
    │                                   │ routes.search_notes()                │
    │                                   │ ├─ 검색어 검증                       │
    │                                   │ ├─ service.search_notes()            │
    │                                   ├─────────────────────────────────────>│
    │                                   │                                      │ SELECT * FROM notes
    │                                   │                                      │ WHERE (title LIKE '%AI%'
    │                                   │                                      │    OR content LIKE '%AI%')
    │                                   │                                      │ AND (is_public OR owner)
    │                                   │<─────────────────────────────────────┤
    │                                   │ 응답: {notes: [...], total: N}      │
    │<──────────────────────────────────┤                                      │
    │      200 OK                        │                                      │
```

### 5️⃣ 파일 업로드 흐름

```
클라이언트                          FastAPI 백엔드                      파일 시스템
    │                                   │                                      │
    ├─ POST /api/upload                 │                                      │
    │      (multipart/form-data)        │                                      │
    │      + Authorization: Bearer      │                                      │
    ├──────────────────────────────────>│                                      │
    │                                   │ routes.upload_file()                 │
    │                                   │ ├─ 현재 사용자 검증                  │
    │                                   │ ├─ 파일 타입 검증                    │
    │                                   │ ├─ 파일 크기 검증                    │
    │                                   │ ├─ UUID 기반 파일명 생성             │
    │                                   ├──────────────────────────────────────>│
    │                                   │                                      │ SAVE file
    │                                   │<──────────────────────────────────────┤
    │                                   │ DB에 파일 정보 저장 (선택)           │
    │                                   │ 응답: {file_url, file_id}           │
    │<──────────────────────────────────┤                                      │
    │      201 Created                   │                                      │
```

---

## 🗂️ 계층별 역할 분석

### 1. Routes 계층 (API 엔드포인트)
```python
# features/notes/routes.py
@router.post("")
async def create_note(note_data: NoteCreate, ...):
    # 1. 요청 검증 (Pydantic 스키마)
    # 2. 의존성 주입 (현재 사용자, DB 세션)
    # 3. 서비스 호출
    # 4. 응답 반환
```

**역할:**
- HTTP 요청 처리
- Pydantic 유효성 검사
- 의존성 주입
- 응답 포맷팅

---

### 2. Service 계층 (비즈니스 로직)
```python
# features/notes/service.py
class NoteService:
    @staticmethod
    def create_note(db, note_data, user):
        # 1. 데이터 준비
        # 2. DB 쿼리
        # 3. 비즈니스 로직 적용
        # 4. 트랜잭션 커밋
```

**역할:**
- 비즈니스 로직 구현
- DB 조작
- 데이터 변환
- 예외 처리

---

### 3. Model 계층 (데이터 구조)
```python
# features/notes/models.py
class Note(Base):
    __tablename__ = "notes"
    id = Column(...)
    # ORM 매핑
```

**역할:**
- SQLAlchemy ORM 정의
- 테이블 매핑
- 관계 설정 (FK, 역참조)

---

### 4. Schema 계층 (요청/응답)
```python
# features/notes/schemas.py
class NoteCreate(BaseModel):
    title: str
    content: str
    # Pydantic 검증
```

**역할:**
- 요청 검증
- 응답 직렬화
- 타입 힌팅

---

### 5. Deps 계층 (의존성)
```python
# features/auth/deps.py
async def get_current_user(credentials, db):
    # JWT 검증 → User 객체 반환
```

**역할:**
- 인증/인가
- 의존성 주입
- 권한 검증

---

## 🔐 인증/인가 흐름

### JWT 토큰 생명 주기

```
1. 토큰 발급 (로그인)
   └─ create_access_token({"user_id": 1, "username": "john"})
      └─ jwt.encode() → "eyJhbGc..."

2. 클라이언트 저장
   └─ LocalStorage 또는 Cookie

3. API 요청 시 전달
   └─ Header: Authorization: Bearer eyJhbGc...

4. 서버 검증 (매 요청마다)
   └─ decode_token()
      └─ JWT 검증
      └─ 만료 시간 확인
      └─ user_id 추출

5. 토큰 만료 (24시간)
   └─ 401 Unauthorized
   └─ 클라이언트에서 재로그인
```

---

## 📊 데이터 흐름 다이어그램 (전체)

```
┌─────────────────────────────────────────────────────────────────┐
│                       클라이언트 (브라우저)                        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ • HTML/CSS/JS                                               │ │
│  │ • LocalStorage (토큰)                                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬──────────────────────────────────────┘
                             │ HTTP/HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              FastAPI 백엔드 (main.py)                             │
├─────────────────────────────────────────────────────────────────┤
│ Middleware (CORS, Error Handler)                                 │
├─────────────────────────────────────────────────────────────────┤
│ Routes (auth, notes, users, ...)                                 │
│  ├─ deps.get_current_user (의존성)                              │
│  ├─ deps.get_db (의존성)                                        │
│  └─ Service 호출                                                │
├─────────────────────────────────────────────────────────────────┤
│ Service (비즈니스 로직)                                          │
│  ├─ auth_service.register_user()                               │
│  ├─ note_service.create_note()                                 │
│  └─ note_service.search_notes()                                │
├─────────────────────────────────────────────────────────────────┤
│ Models (SQLAlchemy ORM)                                          │
│  ├─ User, Note, Comment, Team, ...                             │
│  └─ 관계 설정                                                    │
├─────────────────────────────────────────────────────────────────┤
│ Security (core/security.py)                                      │
│  ├─ hash_password() / verify_password()                         │
│  ├─ create_access_token() / decode_token()                     │
│  └─ bcrypt, JWT                                                 │
└────────────────────┬──────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SQLite / PostgreSQL                            │
├─────────────────────────────────────────────────────────────────┤
│ users                                                             │
│ notes                                                             │
│ note_versions                                                     │
│ ai_summaries                                                      │
│ comments                                                          │
│ note_collaborators                                               │
│ teams                                                             │
│ team_members                                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Request-Response 사이클

### 요청 처리 단계

```
1. HTTP 요청 도착
   └─ POST /api/notes
      └─ Authorization: Bearer token
      └─ Body: {title, content}

2. CORS 미들웨어
   └─ Origin 검증
   └─ 요청 허용 여부 판단

3. 라우트 매칭
   └─ create_note() 함수 호출

4. 의존성 주입 (DI)
   ├─ get_current_user()
   │  └─ JWT 검증 → User 객체
   └─ get_db()
      └─ DB 세션 생성

5. Pydantic 검증
   └─ NoteCreate 스키마로 검증
   └─ 실패 시 422 Validation Error

6. 비즈니스 로직 실행
   └─ service.create_note()
      ├─ Note 객체 생성
      ├─ DB INSERT
      ├─ NoteVersion 생성
      └─ DB COMMIT

7. 응답 생성
   └─ NoteResponse 스키마로 직렬화
   └─ JSON 반환

8. HTTP 응답 전송
   └─ 201 Created
   └─ Content-Type: application/json
   └─ Body: {status, data, message}
```

---

## 💾 트랜잭션 관리

### DB 세션 라이프사이클

```python
@router.post("/notes")
async def create_note(..., db: Session = Depends(get_db)):
    # get_db() 호출 시
    # ├─ SessionLocal() 생성
    # └─ db = DB 세션 객체
    
    # 라우트 함수 실행
    note = service.create_note(db, ...)
    # ├─ db.add()
    # ├─ db.commit()
    # └─ db.refresh()
    
    # 함수 반환 후
    # └─ finally: db.close()
    #    └─ 세션 종료, 연결 반환
```

---

## 🧪 테스트 전략

### 단위 테스트 (Unit Tests)

```
tests/features/test_auth.py
├─ test_register_user_success
├─ test_register_user_duplicate_username
├─ test_login_success
├─ test_login_invalid_credentials
└─ test_get_current_user

tests/features/test_notes.py
├─ test_create_note
├─ test_get_note
├─ test_update_note
├─ test_delete_note
├─ test_search_notes
└─ test_note_versioning
```

### 통합 테스트 (Integration Tests)

```
tests/integration/test_workflows.py
├─ test_user_registration_to_note_creation
├─ test_note_modification_with_versioning
└─ test_search_and_filter_notes
```

---

## 🔌 확장 포인트

### 새로운 Feature 추가 시

```
1. features/new_feature/ 폴더 생성
2. models.py (ORM)
3. schemas.py (Pydantic)
4. routes.py (API)
5. service.py (로직)
6. main.py에 라우터 등록
7. tests/features/test_new_feature.py 작성
```

**예: AI 요약 기능**
```python
# features/ai/routes.py
@router.post("/notes/{note_id}/summarize")
async def summarize_note(...):
    pass

# main.py
from features.ai.routes import router as ai_router
app.include_router(ai_router, prefix="/api")
```

---

**문서 버전**: 1.0  
**최종 업데이트**: 2026-08-26  
**상태**: Architecture Analysis 완료
