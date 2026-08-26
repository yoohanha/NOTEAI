# NOTEAI - 프로젝트 기획 문서

## 1. 프로젝트 개요

### 프로젝트명
**NOTEAI** - AI 기반 노트 큐레이션 및 협업 플랫폼

### 프로젝트 목표
연구원과 개발자를 위한 **지능형 노트 관리 시스템**을 구축합니다. 사용자는 효율적으로 노트를 작성, 관리, 공유할 수 있으며, AI를 활용하여 자동 요약, 키워드 추출, 내용 분류, 시맨틱 검색 등의 고급 기능을 제공합니다.

### 대상 사용자
- 🔬 **연구원**: 논문, 연구 노트, 아이디어 정리
- 💻 **개발자**: 코드 스니펫, 기술 문서, 레퍼런스 관리
- 📚 **학생**: 강의 노트, 학습 자료
- 💼 **지식 근로자**: 프로젝트 관리, 회의 기록, 지식 축적

### 핵심 가치 제안
| 기능 | 설명 |
|------|------|
| 📝 **구조화된 노트 작성** | 마크다운 지원, 카테고리/태그 기반 조직화 |
| 🤖 **AI 기반 처리** | 자동 요약, 키워드 추출, 자동 분류 |
| 🔗 **노트 간 연결성** | 그래프 구조로 관련 노트 자동 연결 |
| 👥 **팀 협업** | 권한 관리, 댓글, 실시간 협업 |
| 🔍 **강력한 검색** | 전문 검색, 필터링, 시맨틱 검색 |
| 📊 **인사이트 대시보드** | 통계, 활동 추적, 추천 기능 |
| 📤 **버전 관리** | 노트 변경 이력 추적 및 복원 |

---

## 2. 핵심 기능 정의

### 2.1 사용자 관리 (User Management)

#### 회원가입 / 로그인
- 이메일 기반 가입
- 비밀번호 해싱 (bcrypt)
- JWT 토큰 기반 인증
- 선택적 소셜 로그인 (향후)

#### 프로필 관리
- 사용자 정보 (이름, 이메일, 소개)
- 프로필 이미지 업로드
- 개인 선호 설정 (테마, 언어)
- 계정 보안 설정 (비밀번호 변경, 세션 관리)

#### 권한 관리
- 개인 노트 (비공개/공개)
- 팀 노트 (팀 멤버 공유)
- 권한 레벨: Owner, Admin, Editor, Viewer

### 2.2 노트 관리 (Note Management)

#### CRUD 작업
- **생성**: 마크다운 에디터에서 새 노트 작성
- **읽기**: 노트 조회 및 렌더링
- **수정**: 콘텐츠 편집 및 자동 저장
- **삭제**: 논리적 삭제 (소프트 삭제) - 복구 가능

#### 노트 조직화
- **카테고리**: 사용자 정의 카테고리 생성/관리
- **태그**: 다중 태그 지정 (자동 완성)
- **마크다운 지원**: 제목, 리스트, 코드 블록, 이미지 등
- **첨부파일**: 이미지, 문서 첨부 가능

#### 버전 관리
- 모든 변경사항 저장
- 버전 히스토리 조회
- 이전 버전으로 복원 가능
- 변경 시간, 작성자 추적

### 2.3 AI 기능 (AI Features)

#### 자동 요약 (Auto Summarize)
- 노트 내용을 짧은 문장으로 요약
- 핵심 포인트 추출
- 저장 및 재사용 가능
- 요약 옵션 선택 가능 (짧음/중간/길음)

#### 키워드 추출 (Keyword Extraction)
- 노트에서 중요한 키워드 자동 추출
- 추출된 키워드를 태그로 자동 추가
- 키워드 가중치 표시
- 중복 제거

#### 자동 분류 (Auto Classification)
- 노트 내용을 분석하여 자동 카테고리 제안
- 다중 카테고리 가능
- 사용자 피드백으로 정확도 개선
- 사용자 정의 분류 규칙 설정

#### 시맨틱 검색 (Semantic Search)
- 의미 기반 검색 (단순 키워드 검색 이상)
- 관련 노트 추천
- 검색 결과 랭킹
- 자주 찾는 내용 학습

### 2.4 협업 기능 (Collaboration)

#### 노트 공유
- 공개/비공개 설정
- 개별 사용자와 공유
- 팀과 공유
- 공유 링크 생성 (보기 전용)
- 만료 기한 설정 가능

#### 권한 관리
| 권한 | 읽기 | 편집 | 삭제 | 공유 | 권한 변경 |
|------|------|------|------|------|---------|
| **Viewer** | ✓ | ✗ | ✗ | ✗ | ✗ |
| **Editor** | ✓ | ✓ | ✓ 자신의 것 | ✓ | ✗ |
| **Admin** | ✓ | ✓ | ✓ | ✓ | ✓ |

#### 댓글 & 토론
- 노트 내 댓글 작성/편집/삭제
- 댓글 스레드 (대댓글)
- @ 멘션 기능
- 댓글 알림

#### 실시간 협업
- 동시 편집 표시 (누가 지금 편집 중인지)
- 변경 충돌 해결 (Last Write Wins)

### 2.5 대시보드 & 분석 (Dashboard & Analytics)

#### 메인 대시보드
- 최근 작성 노트 (5개)
- 최근 수정 노트 (5개)
- 팀 활동 피드
- 저장 공간 사용량

#### 통계
- 총 노트 수
- 카테고리별 노트 분포
- 월별 작성 수
- 가장 많이 참고한 노트
- 협업자별 활동도

#### 추천 기능
- 사용자의 관심사 기반 추천
- 유사한 노트 추천
- 팀 인기 노트
- 트렌딩 태그

---

## 3. 기술 스택

### 백엔드 (Backend)
- **프레임워크**: FastAPI
- **데이터베이스**: SQLite (개발) → PostgreSQL (프로덕션)
- **ORM**: SQLAlchemy
- **인증**: JWT (PyJWT)
- **해싱**: bcrypt
- **유효성 검사**: Pydantic
- **AI/NLP**: 
  - TextRank (키워드 추출)
  - BERT/KoBERT (분류 및 요약)
  - Hugging Face Transformers
- **CORS**: python-multipart

### 프론트엔드 (Frontend)
- **마크업**: HTML5
- **스타일**: Tailwind CSS
- **스크립트**: Vanilla JavaScript (ES6+)
- **마크다운 에디터**: EasyMDE 또는 CodeMirror
- **마크다운 렌더러**: Marked.js
- **API 통신**: Fetch API
- **상태 관리**: LocalStorage + Session

### 개발 환경
- **언어**: Python 3.10+
- **패키지 관리**: pip + requirements.txt
- **버전 관리**: Git
- **배포**: Docker (선택)

---

## 4. 데이터베이스 설계

### 4.1 Entity Relationship Diagram (ERD)

```
┌──────────────┐         ┌──────────────┐
│    users     │─────────│    notes     │
├──────────────┤1        └──────────────┘
│ id (PK)      │              │
│ username     │              │ N
│ email        │              │
│ password_hash│              └────────┐
│ full_name    │                       │
│ bio          │         ┌──────────────────────┐
│ avatar_url   │         │  note_collaborators  │
│ created_at   │         ├──────────────────────┤
│ updated_at   │         │ id (PK)              │
└──────────────┘         │ note_id (FK)         │
       │                 │ user_id (FK)         │
       │ 1                │ permission (read/... │
       │                 │ added_at             │
       └─────────────┐   └──────────────────────┘
                     N
        ┌───────────────────────┐
        │   comments            │
        ├───────────────────────┤
        │ id (PK)               │
        │ note_id (FK) → notes  │
        │ user_id (FK) → users  │
        │ content               │
        │ parent_id (FK)        │
        │ created_at            │
        │ updated_at            │
        └───────────────────────┘

┌──────────────┐         ┌──────────────────────┐
│    teams     │─────────│   team_members       │
├──────────────┤1        ├──────────────────────┤
│ id (PK)      │         │ id (PK)              │
│ name         │         │ team_id (FK)         │
│ owner_id (FK)          │ user_id (FK)         │
│ description  │         │ role (member/admin)  │
│ created_at   │         │ joined_at            │
└──────────────┘         └──────────────────────┘

┌──────────────────────┐
│  ai_summaries        │
├──────────────────────┤
│ id (PK)              │
│ note_id (FK)         │
│ summary_text         │
│ keywords (JSON)      │
│ category             │
│ generated_at         │
└──────────────────────┘

┌──────────────────────┐
│  note_versions       │
├──────────────────────┤
│ id (PK)              │
│ note_id (FK)         │
│ content              │
│ title                │
│ version_number       │
│ created_by (FK)      │
│ created_at           │
└──────────────────────┘
```

### 4.2 테이블 상세 정의

#### users 테이블
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    bio TEXT,
    avatar_url VARCHAR(255),
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### notes 테이블
```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(50),
    tags JSON,
    is_public BOOLEAN DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### note_collaborators 테이블
```sql
CREATE TABLE note_collaborators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    permission VARCHAR(20) NOT NULL DEFAULT 'read',
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (note_id) REFERENCES notes(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(note_id, user_id)
);
```

#### ai_summaries 테이블
```sql
CREATE TABLE ai_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL,
    summary_text TEXT NOT NULL,
    keywords JSON,
    category VARCHAR(50),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (note_id) REFERENCES notes(id)
);
```

#### comments 테이블
```sql
CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    parent_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (note_id) REFERENCES notes(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (parent_id) REFERENCES comments(id)
);
```

#### teams 테이블
```sql
CREATE TABLE teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    owner_id INTEGER NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id)
);
```

#### team_members 테이블
```sql
CREATE TABLE team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(team_id, user_id)
);
```

#### note_versions 테이블
```sql
CREATE TABLE note_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (note_id) REFERENCES notes(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

---

## 5. API 엔드포인트 설계

### 5.1 인증 (Authentication)

#### POST /api/auth/register
사용자 회원가입

**요청:**
```json
{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure_password123",
    "full_name": "John Doe"
}
```

**응답 (201 Created):**
```json
{
    "status": 201,
    "data": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "full_name": "John Doe"
    },
    "message": "User registered successfully"
}
```

#### POST /api/auth/login
사용자 로그인

**요청:**
```json
{
    "username": "john_doe",
    "password": "secure_password123"
}
```

**응답 (200 OK):**
```json
{
    "status": 200,
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer",
        "user": {
            "id": 1,
            "username": "john_doe",
            "email": "john@example.com"
        }
    },
    "message": "Login successful"
}
```

#### POST /api/auth/logout
사용자 로그아웃

**응답 (200 OK):**
```json
{
    "status": 200,
    "message": "Logout successful"
}
```

#### GET /api/auth/me
현재 사용자 정보 조회

**응답 (200 OK):**
```json
{
    "status": 200,
    "data": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "full_name": "John Doe",
        "bio": "Software Developer",
        "avatar_url": "https://..."
    }
}
```

### 5.2 사용자 (Users)

#### GET /api/users/{user_id}
특정 사용자 정보 조회

**응답 (200 OK):**
```json
{
    "status": 200,
    "data": {
        "id": 1,
        "username": "john_doe",
        "full_name": "John Doe",
        "bio": "Software Developer",
        "avatar_url": "https://..."
    }
}
```

#### PUT /api/users/{user_id}
사용자 정보 수정 (본인만 가능)

**요청:**
```json
{
    "full_name": "John Smith",
    "bio": "Senior Developer",
    "avatar_url": "https://..."
}
```

**응답 (200 OK):**
```json
{
    "status": 200,
    "data": {
        "id": 1,
        "username": "john_doe",
        "full_name": "John Smith",
        "bio": "Senior Developer"
    },
    "message": "User updated successfully"
}
```

#### GET /api/users/{user_id}/notes
사용자의 노트 목록 조회

**쿼리 파라미터:**
- `page`: 페이지 번호 (기본값: 1)
- `limit`: 페이지당 아이템 수 (기본값: 10)
- `category`: 카테고리 필터
- `tag`: 태그 필터

**응답 (200 OK):**
```json
{
    "status": 200,
    "data": {
        "notes": [
            {
                "id": 1,
                "title": "Note Title",
                "content": "Note content...",
                "category": "Research",
                "tags": ["ai", "ml"],
                "created_at": "2026-08-26T10:00:00Z"
            }
        ],
        "total": 42,
        "page": 1,
        "limit": 10
    }
}
```

### 5.3 노트 (Notes)

#### GET /api/notes
모든 노트 조회 (공개 노트 + 사용자의 노트)

**쿼리 파라미터:**
- `page`: 페이지 번호
- `limit`: 페이지당 아이템 수
- `category`: 카테고리 필터
- `tag`: 태그 필터
- `sort`: 정렬 (created_at, updated_at, title)
- `order`: 정렬 순서 (asc, desc)

**응답 (200 OK):**
```json
{
    "status": 200,
    "data": {
        "notes": [...],
        "total": 100,
        "page": 1,
        "limit": 10
    }
}
```

#### POST /api/notes
새 노트 작성

**요청:**
```json
{
    "title": "My First Note",
    "content": "# Heading\n\nContent here...",
    "category": "Research",
    "tags": ["ai", "learning"],
    "is_public": false
}
```

**응답 (201 Created):**
```json
{
    "status": 201,
    "data": {
        "id": 1,
        "user_id": 1,
        "title": "My First Note",
        "content": "# Heading\n\nContent here...",
        "category": "Research",
        "tags": ["ai", "learning"],
        "is_public": false,
        "created_at": "2026-08-26T10:00:00Z"
    },
    "message": "Note created successfully"
}
```

#### GET /api/notes/{note_id}
특정 노트 조회

**응답 (200 OK):**
```json
{
    "status": 200,
    "data": {
        "id": 1,
        "user_id": 1,
        "title": "My First Note",
        "content": "# Heading\n\nContent here...",
        "category": "Research",
        "tags": ["ai", "learning"],
        "is_public": false,
        "view_count": 5,
        "created_at": "2026-08-26T10:00:00Z",
        "updated_at": "2026-08-26T11:00:00Z",
        "author": {
            "id": 1,
            "username": "john_doe",
            "full_name": "John Doe"
        },
        "collaborators": [...],
        "comments": [...]
    }
}
```

#### PUT /api/notes/{note_id}
노트 수정 (작성자 또는 편집 권한자)

**요청:**
```json
{
    "title": "Updated Title",
    "content": "Updated content...",
    "category": "Development",
    "tags": ["coding", "python"],
    "is_public": true
}
```

**응답 (200 OK):**
```json
{
    "status": 200,
    "data": {
        "id": 1,
        "title": "Updated Title",
        "updated_at": "2026-08-26T12:00:00Z"
    },
    "message": "Note updated successfully"
}
```

#### DELETE /api/notes/{note_id}
노트 삭제 (작성자만)

**응답 (200 OK):**
```json
{
    "status": 200,
    "message": "Note deleted successfully"
}
```

#### GET /api/notes/search
노트 검색 (전문 검색 + 필터링)

**쿼리 파라미터:**
- `q`: 검색어
- `type`: 검색 타입 (full_text, semantic)
- `category`: 카테고리 필터
- `tag`: 태그 필터
- `from_date`: 시작 날짜
- `to_date`: 종료 날짜

**응답 (200 OK):**
```json
{
    "status": 200,
    "data": {
        "notes": [...],
        "total": 25
    }
}
```

#### POST /api/notes/{note_id}/share
노트 공유

**요청:**
```json
{
    "users": [2, 3],
    "permission": "read",
    "expires_at": "2026-09-26T00:00:00Z"
}
```

**응답 (200 OK):**
```json
{
    "status": 200,
    "message": "Note shared successfully"
}
```

### 5.4 AI 기능 (AI Features)

#### POST /api/notes/{note_id}/summarize
노트 요약

**요청:**
```json
{
    "length": "medium"
}
```

**응답 (200 OK):**
```json
{
    "status": 200,
    "data": {
        "summary": "This note discusses...",
        "generated_at": "2026-08-26T12:00:00Z"
    }
}
```

#### POST /api/notes/{note_id}/extract-keywords
키워드 추출

**응답 (200 OK):**
```json
{
    "status": 200,
    "data": {
        "keywords": [
            {"word": "artificial intelligence", "weight": 0.95},
            {"word": "machine learning", "weight": 0.87},
            {"word": "neural networks", "weight": 0.82}
        ]
    }
}
```

#### POST /api/notes/{note_id}/classify
자동 분류

**응답 (200 OK):**
```json
{
    "status": 200,
    "data": {
        "categories": [
            {"name": "Research", "confidence": 0.92},
            {"name": "Technology", "confidence": 0.85}
        ]
    }
}
```

#### POST /api/notes/semantic-search
시맨틱 검색

**요청:**
```json
{
    "query": "machine learning algorithms"
}
```

**응답 (200 OK):**
```json
{
    "status": 200,
    "data": {
        "notes": [...],
        "total": 15
    }
}
```

### 5.5 댓글 (Comments)

#### GET /api/notes/{note_id}/comments
특정 노트의 댓글 조회

**응답 (200 OK):**
```json
{
    "status": 200,
    "data": {
        "comments": [
            {
                "id": 1,
                "note_id": 1,
                "user_id": 2,
                "content": "Great note!",
                "author": {
                    "id": 2,
                    "username": "jane_doe",
                    "full_name": "Jane Doe"
                },
                "created_at": "2026-08-26T10:00:00Z",
                "replies": [...]
            }
        ]
    }
}
```

#### POST /api/notes/{note_id}/comments
댓글 작성

**요청:**
```json
{
    "content": "This is helpful!",
    "parent_id": null
}
```

**응답 (201 Created):**
```json
{
    "status": 201,
    "data": {
        "id": 1,
        "note_id": 1,
        "user_id": 2,
        "content": "This is helpful!",
        "created_at": "2026-08-26T10:00:00Z"
    }
}
```

#### PUT /api/comments/{comment_id}
댓글 수정

**요청:**
```json
{
    "content": "Updated comment text"
}
```

**응답 (200 OK):**
```json
{
    "status": 200,
    "message": "Comment updated"
}
```

#### DELETE /api/comments/{comment_id}
댓글 삭제

**응답 (200 OK):**
```json
{
    "status": 200,
    "message": "Comment deleted"
}
```

### 5.6 팀 (Teams)

#### GET /api/teams
모든 팀 조회 (사용자가 속한 팀)

**응답 (200 OK):**
```json
{
    "status": 200,
    "data": {
        "teams": [
            {
                "id": 1,
                "name": "Research Team",
                "owner_id": 1,
                "description": "Team for research projects",
                "member_count": 5,
                "created_at": "2026-08-26T10:00:00Z"
            }
        ]
    }
}
```

#### POST /api/teams
새 팀 생성

**요청:**
```json
{
    "name": "Research Team",
    "description": "Team for research projects"
}
```

**응답 (201 Created):**
```json
{
    "status": 201,
    "data": {
        "id": 1,
        "name": "Research Team",
        "owner_id": 1,
        "description": "Team for research projects"
    }
}
```

#### GET /api/teams/{team_id}
특정 팀 정보 조회

**응답 (200 OK):**
```json
{
    "status": 200,
    "data": {
        "id": 1,
        "name": "Research Team",
        "owner_id": 1,
        "description": "Team for research projects",
        "members": [
            {
                "id": 1,
                "username": "john_doe",
                "role": "admin"
            }
        ]
    }
}
```

#### POST /api/teams/{team_id}/members
팀에 멤버 추가

**요청:**
```json
{
    "user_id": 2,
    "role": "member"
}
```

**응답 (201 Created):**
```json
{
    "status": 201,
    "message": "Member added to team"
}
```

---

## 6. 프론트엔드 페이지 설계

### 6.1 페이지 구조

#### 공개 페이지

**홈페이지** (`/`)
- 서비스 소개 및 기능 설명
- 사용 통계 (전체 노트 수, 활성 사용자 수)
- CTA 버튼 (회원가입, 로그인)
- 주요 기능 카드
- 사용자 리뷰

#### 인증 페이지

**회원가입** (`/auth/register`)
- 이메일, 사용자명, 비밀번호 입력
- 약관 동의
- 회원가입 버튼
- 로그인 링크

**로그인** (`/auth/login`)
- 사용자명/이메일, 비밀번호 입력
- 로그인 버튼
- 비밀번호 찾기 링크
- 회원가입 링크

#### 메인 대시보드

**대시보드 홈** (`/dashboard`)
- **좌측 사이드바**:
  - 사용자 프로필
  - 메뉴 (홈, 노트, 검색, 팀, 설정)
  - 카테고리 리스트
  - 즐겨찾기 노트

- **메인 패널**:
  - 최근 노트 (5개)
  - 최근 편집 노트 (5개)
  - 추천 노트 (3개)

- **우측 패널**:
  - 통계 (총 노트, 작성 수 이번달)
  - 팀 활동 피드
  - 저장 공간 사용량

#### 노트 작성/편집

**노트 에디터** (`/notes/new`, `/notes/{id}/edit`)
- **좌측**: 마크다운 에디터 (EasyMDE)
- **우측**: 미리보기 패널
- **상단**:
  - 제목 입력
  - 카테고리 선택
  - 태그 입력 (자동 완성)
  - AI 기능 버튼 (요약, 키워드, 분류)
  - 저장 버튼
  - 공유 버튼

#### 노트 조회

**노트 상세** (`/notes/{id}`)
- **헤더**:
  - 제목
  - 작성자 정보
  - 작성일, 수정일
  - 액션 버튼 (편집, 공유, 삭제)

- **메인**:
  - 마크다운 렌더링된 내용
  - AI 요약 (사이드패널)
  - AI 추출 키워드

- **하단**:
  - 댓글 섹션
  - 관련 노트

#### 검색

**검색 페이지** (`/search`)
- **검색 입력**: 전문 검색 입력창
- **필터**:
  - 카테고리
  - 태그
  - 작성자
  - 날짜 범위
  - 공개/비공개

- **결과**:
  - 노트 리스트
  - 검색 용어 하이라이트
  - 정렬 옵션

#### 팀 페이지

**팀 목록** (`/teams`)
- 팀 카드 리스트
- 팀 생성 버튼
- 팀별 멤버 수, 노트 수

**팀 상세** (`/teams/{id}`)
- 팀 정보
- 팀 멤버 리스트
- 팀 노트 리스트
- 멤버 초대 버튼
- 팀 설정 (소유자만)

#### 설정

**프로필 설정** (`/settings/profile`)
- 사용자명 (읽기 전용)
- 이메일
- 이름
- 소개
- 프로필 이미지

**계정 설정** (`/settings/account`)
- 비밀번호 변경
- 세션 관리
- 계정 삭제

**알림 설정** (`/settings/notifications`)
- 댓글 알림
- 공유 알림
- 팀 활동 알림

---

## 7. 구현 계획

### Phase 1: 기초 구축 (1-2주)
- [x] 프로젝트 기획 문서 완성
- [ ] 데이터베이스 스키마 구현
- [ ] FastAPI 프로젝트 초기화
- [ ] 기본 프론트엔드 템플릿

### Phase 2: 핵심 기능 (2-3주)
- [ ] 사용자 관리 (가입, 로그인, 프로필)
- [ ] 노트 CRUD 기능
- [ ] 마크다운 에디터 통합
- [ ] 기본 대시보드

### Phase 3: AI 기능 (2주)
- [ ] 자동 요약
- [ ] 키워드 추출
- [ ] 자동 분류
- [ ] 시맨틱 검색 (선택)

### Phase 4: 협업 기능 (1-2주)
- [ ] 노트 공유
- [ ] 권한 관리
- [ ] 댓글 기능
- [ ] 팀 관리

### Phase 5: 고급 기능 (1주)
- [ ] 버전 관리
- [ ] 고급 검색 필터
- [ ] 통계 및 대시보드
- [ ] 추천 기능

### Phase 6: 테스트 & 배포 (1주)
- [ ] 단위 테스트
- [ ] 통합 테스트
- [ ] 배포 준비
- [ ] 문서화

---

## 8. 디렉토리 구조 (Feature-Based Architecture)

**기능별 계층적 구조**: 각 기능이 독립적으로 동작하는 모듈식 설계

```
noteai/
├── docs/
│   ├── planning.md              # 전체 기획 문서
│   ├── requirements.md          # 요구사항 정의서
│   ├── api.md                   # API 엔드포인트 문서
│   └── database.md              # 데이터베이스 설계
│
├── backend/
│   ├── main.py                  # FastAPI 진입점
│   ├── requirements.txt
│   │
│   ├── core/                    # 핵심 공유 모듈
│   │   ├── __init__.py
│   │   ├── config.py            # 환경 설정 및 구성
│   │   ├── database.py          # SQLAlchemy 세션, Base
│   │   ├── security.py          # JWT, 비밀번호 해싱
│   │   └── constants.py         # 상수 정의
│   │
│   ├── features/                # 기능별 독립 모듈 (핵심!)
│   │   ├── __init__.py
│   │   │
│   │   ├── auth/                # 인증 기능
│   │   │   ├── __init__.py
│   │   │   ├── models.py        # User 모델
│   │   │   ├── schemas.py       # 요청/응답 스키마
│   │   │   ├── routes.py        # /api/auth/* 엔드포인트
│   │   │   ├── service.py       # 비즈니스 로직
│   │   │   └── deps.py          # get_current_user 의존성
│   │   │
│   │   ├── users/               # 사용자 관리
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   └── service.py
│   │   │
│   │   ├── notes/               # 노트 관리
│   │   │   ├── __init__.py
│   │   │   ├── models.py        # Note, NoteVersion
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   └── service.py       # CRUD, 버전 관리
│   │   │
│   │   ├── collaborators/       # 협업자 관리
│   │   │   ├── __init__.py
│   │   │   ├── models.py        # NoteCollaborator
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   └── service.py       # 권한 검증
│   │   │
│   │   ├── comments/            # 댓글 기능
│   │   │   ├── __init__.py
│   │   │   ├── models.py        # Comment
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   └── service.py
│   │   │
│   │   ├── teams/               # 팀 관리
│   │   │   ├── __init__.py
│   │   │   ├── models.py        # Team, TeamMember
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   └── service.py
│   │   │
│   │   └── ai/                  # AI 기능
│   │       ├── __init__.py
│   │       ├── schemas.py       # AI 요청/응답
│   │       ├── routes.py        # /api/notes/{id}/summarize 등
│   │       ├── service.py       # AI 로직
│   │       └── nlp_utils.py     # NLP/AI 유틸
│   │
│   ├── utils/                   # 공유 유틸리티
│   │   ├── __init__.py
│   │   ├── helpers.py           # 헬퍼 함수
│   │   ├── validators.py        # 유효성 검사
│   │   ├── formatters.py        # 데이터 포매팅
│   │   └── exceptions.py        # 커스텀 예외
│   │
│   ├── middleware/              # 미들웨어
│   │   ├── __init__.py
│   │   ├── auth.py              # 인증 미들웨어
│   │   ├── error_handler.py     # 에러 처리
│   │   └── logging.py           # 로깅 미들웨어
│   │
│   └── uploads/                 # 파일 저장소
│       └── .gitkeep
│
├── frontend/
│   ├── index.html               # 메인 진입점
│   ├── script.js                # 메인 JavaScript
│   ├── style.css                # 커스텀 스타일
│   │
│   ├── pages/                   # 라우트별 페이지
│   │   ├── home.html
│   │   ├── auth.html            # 로그인/가입
│   │   ├── dashboard.html
│   │   ├── notes.html
│   │   ├── editor.html
│   │   ├── search.html
│   │   ├── teams.html
│   │   └── settings.html
│   │
│   ├── components/              # 재사용 가능 컴포넌트
│   │   ├── navbar.html
│   │   ├── sidebar.html
│   │   ├── modals.html
│   │   ├── forms.html
│   │   ├── cards.html
│   │   └── editor.html
│   │
│   └── assets/
│       ├── css/
│       │   ├── tailwind.css
│       │   └── custom.css
│       └── js/
│           ├── api.js           # API 호출
│           ├── auth.js          # 인증 관리
│           ├── notes.js         # 노트 기능
│           ├── search.js        # 검색
│           ├── ui.js            # UI 상호작용
│           └── utils.js         # 유틸
│
├── tests/                       # 자동화 테스트
│   ├── __init__.py
│   ├── conftest.py              # pytest 설정
│   │
│   ├── features/                # 기능별 단위 테스트
│   │   ├── test_auth.py
│   │   ├── test_users.py
│   │   ├── test_notes.py
│   │   ├── test_comments.py
│   │   ├── test_teams.py
│   │   └── test_ai.py
│   │
│   └── integration/             # 통합 테스트
│       └── test_workflows.py
│
├── .gitignore
├── README.md
├── CLAUDE.md
└── requirements.txt
```

### 📌 기능별 구조의 핵심 개념

**각 기능 폴더의 표준 구조**:
```
features/notes/
├── models.py      # SQLAlchemy ORM 모델
├── schemas.py     # Pydantic 요청/응답 스키마
├── routes.py      # FastAPI 엔드포인트
├── service.py     # 비즈니스 로직
└── deps.py        # 의존성 주입 (선택)
```

**main.py 예시**:
```python
from fastapi import FastAPI
from features.auth import routes as auth_routes
from features.notes import routes as notes_routes
# 기타 feature import...

app = FastAPI()

# 각 기능의 라우터 등록
app.include_router(auth_routes.router, prefix="/api")
app.include_router(notes_routes.router, prefix="/api")
# 기타 router include...
```

### 🎯 이 구조의 장점

| 항목 | 효과 |
|------|------|
| **독립성** | 각 기능이 완전히 독립적 - 팀원 병렬 개발 가능 |
| **확장성** | 새 기능 추가 = `features/new_feature/` 폴더 생성 |
| **유지보수** | 버그 수정이 해당 기능에만 영향 |
| **테스트** | 기능별 단위 테스트 명확 |
| **재사용성** | 다른 프로젝트로 기능 이식 가능 |

---

## 9. 개발 체크리스트

### Backend Development

**데이터베이스**
- [ ] SQLite 스키마 작성 (database.py)
- [ ] 모든 테이블 마이그레이션
- [ ] 인덱스 추가 (성능 최적화)
- [ ] 테스트 데이터 생성

**인증 & 사용자**
- [ ] 회원가입 엔드포인트
- [ ] 로그인/로그아웃 엔드포인트
- [ ] JWT 토큰 검증
- [ ] 비밀번호 해싱 (bcrypt)
- [ ] 프로필 관리 엔드포인트
- [ ] 권한 검증 미들웨어

**노트 관리**
- [ ] CRUD 엔드포인트 (생성, 읽기, 수정, 삭제)
- [ ] 페이지네이션 구현
- [ ] 필터링 & 정렬
- [ ] 소프트 삭제 구현
- [ ] 버전 관리 로직

**AI 기능**
- [ ] 자동 요약 엔드포인트
- [ ] 키워드 추출 엔드포인트
- [ ] 자동 분류 엔드포인트
- [ ] 시맨틱 검색 (선택)
- [ ] AI 모델 통합

**협업 & 공유**
- [ ] 노트 공유 엔드포인트
- [ ] 권한 관리 로직
- [ ] 댓글 CRUD 엔드포인트
- [ ] 팀 관리 엔드포인트
- [ ] 팀 멤버 관리

**API**
- [ ] 에러 처리 통일
- [ ] API 문서 (Swagger/OpenAPI)
- [ ] CORS 설정
- [ ] 요청/응답 유효성 검사

### Frontend Development

**레이아웃 & 스타일**
- [ ] Tailwind CSS 설정
- [ ] 반응형 디자인 구현
- [ ] 명암 테마 지원
- [ ] 컴포넌트화

**페이지**
- [ ] 홈페이지
- [ ] 로그인/회원가입 페이지
- [ ] 대시보드
- [ ] 노트 에디터
- [ ] 노트 조회 페이지
- [ ] 검색 페이지
- [ ] 팀 페이지
- [ ] 설정 페이지

**기능**
- [ ] 마크다운 에디터 통합 (EasyMDE)
- [ ] 마크다운 렌더링 (Marked.js)
- [ ] API 통신 (Fetch API)
- [ ] 인증 로직 (JWT 토큰)
- [ ] 로컬 스토리지 관리
- [ ] 자동 저장 기능
- [ ] 실시간 업데이트

### Testing

**단위 테스트**
- [ ] 인증 로직 테스트
- [ ] 데이터베이스 모델 테스트
- [ ] API 엔드포인트 테스트
- [ ] AI 기능 테스트
- [ ] 프론트엔드 컴포넌트 테스트

**통합 테스트**
- [ ] 사용자 생성부터 노트 작성까지 E2E
- [ ] 협업 기능 테스트
- [ ] 공유 및 권한 검증
- [ ] 검색 기능 테스트

**성능 테스트**
- [ ] API 응답 시간
- [ ] 데이터베이스 쿼리 성능
- [ ] 프론트엔드 로딩 시간

---

## 10. 성공 기준

### 기능 완성도
- [ ] 모든 Must-Have 기능 완성
- [ ] 70% 이상의 Nice-to-Have 기능 완성
- [ ] API 테스트 커버리지 80% 이상

### 품질 지표
- [ ] 코드 가독성 및 유지보수성
- [ ] 에러 처리 및 유효성 검사 완전
- [ ] 보안 (SQL Injection, XSS, CSRF 방지)
- [ ] 성능 (API 응답 < 200ms)

### 사용자 경험
- [ ] 직관적인 인터페이스
- [ ] 빠른 응답 시간
- [ ] 모바일 반응형 디자인
- [ ] 접근성 준수 (WCAG)

---

## 11. 참고 사항

### 기술 선택 이유

**FastAPI**
- 빠른 개발 속도
- 자동 API 문서화 (Swagger)
- 비동기 지원
- 타입 안정성 (Pydantic)

**SQLite**
- 개발 단계에 적합
- 설정 불필요
- 나중에 PostgreSQL로 마이그레이션 가능

**Vanilla JavaScript**
- 외부 프레임워크 없이 가볍게
- 학습 목적에 적합
- 나중에 React/Vue로 마이그레이션 가능

**Tailwind CSS**
- 빠른 스타일링
- 반응형 디자인 용이
- 프리뷰 카드 및 컴포넌트 템플릿

---

## 최종 업데이트

**작성일**: 2026-08-26
**버전**: 1.0
**상태**: 완성 (Planner Phase)

---

다음 단계: **Phase 2 - Backend Developer**로 진행합니다.
