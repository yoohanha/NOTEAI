# NOTEAI - 데이터베이스 설계

**Database Design Document**

---

## 1. 개요

### 데이터베이스 정보
- **DBMS**: SQLite (개발), PostgreSQL (프로덕션)
- **인코딩**: UTF-8
- **타임존**: UTC
- **ORM**: SQLAlchemy

### 설계 원칙
1. **정규화**: 3정규형 준수
2. **일관성**: 데이터 무결성 보장
3. **성능**: 인덱싱 및 쿼리 최적화
4. **확장성**: 향후 기능 추가 용이

---

## 2. Entity Relationship Diagram (ERD)

```
┌─────────────────────────────────────────────────────────────────┐
│                         USERS                                    │
├─────────────────────────────────────────────────────────────────┤
│ PK  id: INTEGER                                                  │
│     username: VARCHAR(50) UNIQUE NOT NULL                        │
│     email: VARCHAR(100) UNIQUE NOT NULL                          │
│     password_hash: VARCHAR(255) NOT NULL                         │
│     full_name: VARCHAR(100)                                      │
│     bio: TEXT                                                    │
│     avatar_url: VARCHAR(255)                                     │
│     is_active: BOOLEAN DEFAULT 1                                 │
│     created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP              │
│     updated_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP              │
└─────────────────────────────────────────────────────────────────┘
              │
              │ 1:N
              │
         ┌────┴──────────────────┬──────────────────────────┐
         │                       │                          │
         ▼                       ▼                          ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│      NOTES       │  │    COMMENTS      │  │ NOTE_COLLABORATORS   │
├──────────────────┤  ├──────────────────┤  ├──────────────────────┤
│ PK  id           │  │ PK  id           │  │ PK  id               │
│ FK  user_id      │  │ FK  note_id      │  │ FK  note_id          │
│     title        │  │ FK  user_id      │  │ FK  user_id          │
│     content      │  │     content      │  │     permission       │
│     category     │  │ FK  parent_id    │  │     added_at         │
│     tags (JSON)  │  │     created_at   │  └──────────────────────┘
│     is_public    │  │     updated_at   │
│     view_count   │  └──────────────────┘
│     created_at   │
│     updated_at   │  ┌──────────────────┐
│     deleted_at   │  │  AI_SUMMARIES    │
└──────────────────┘  ├──────────────────┤
         │            │ PK  id           │
         │            │ FK  note_id      │
         └────────────┤     summary_text │
                      │     keywords (J) │
                      │     category     │
                      │     generated_at │
                      └──────────────────┘

┌──────────────────┐  ┌──────────────────────┐
│      TEAMS       │  │   TEAM_MEMBERS       │
├──────────────────┤  ├──────────────────────┤
│ PK  id           │  │ PK  id               │
│     name         │  │ FK  team_id          │
│ FK  owner_id     │  │ FK  user_id          │
│     description  │  │     role             │
│     created_at   │  │     joined_at        │
└──────────────────┘  └──────────────────────┘
         │
         │ 1:N
         │
         ▼
┌──────────────────────────┐
│  TEAM_NOTES              │
├──────────────────────────┤
│ PK  id                   │
│ FK  team_id              │
│ FK  note_id              │
│     added_at             │
└──────────────────────────┘

┌──────────────────────────┐
│   NOTE_VERSIONS          │
├──────────────────────────┤
│ PK  id                   │
│ FK  note_id              │
│     title                │
│     content              │
│     version_number       │
│ FK  created_by           │
│     created_at           │
└──────────────────────────┘
```

---

## 3. 테이블 상세 정의

### 3.1 users (사용자)

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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (length(username) >= 3),
    CHECK (length(email) >= 5)
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
```

**컬럼 설명:**
| 컬럼명 | 타입 | 설명 | 제약사항 |
|--------|------|------|---------|
| id | INTEGER | 사용자 고유 ID | PK, AUTO |
| username | VARCHAR(50) | 사용자명 | UNIQUE, NOT NULL |
| email | VARCHAR(100) | 이메일 주소 | UNIQUE, NOT NULL |
| password_hash | VARCHAR(255) | 암호화된 비밀번호 | NOT NULL |
| full_name | VARCHAR(100) | 전체 이름 | Optional |
| bio | TEXT | 소개 | Optional |
| avatar_url | VARCHAR(255) | 프로필 이미지 URL | Optional |
| is_active | BOOLEAN | 활성 여부 | DEFAULT 1 |
| created_at | TIMESTAMP | 생성 시간 | DEFAULT NOW() |
| updated_at | TIMESTAMP | 수정 시간 | DEFAULT NOW() |

---

### 3.2 notes (노트)

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
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CHECK (length(title) >= 1 AND length(title) <= 255),
    CHECK (length(content) >= 1)
);

CREATE INDEX idx_notes_user_id ON notes(user_id);
CREATE INDEX idx_notes_created_at ON notes(created_at);
CREATE INDEX idx_notes_deleted_at ON notes(deleted_at);
CREATE INDEX idx_notes_is_public ON notes(is_public);
CREATE INDEX idx_notes_category ON notes(category);
```

**컬럼 설명:**
| 컬럼명 | 타입 | 설명 | 제약사항 |
|--------|------|------|---------|
| id | INTEGER | 노트 고유 ID | PK, AUTO |
| user_id | INTEGER | 작성자 사용자 ID | FK, NOT NULL |
| title | VARCHAR(255) | 노트 제목 | NOT NULL |
| content | TEXT | 노트 내용 (마크다운) | NOT NULL |
| category | VARCHAR(50) | 카테고리 | Optional |
| tags | JSON | 태그 배열 | Optional, JSON 형식 |
| is_public | BOOLEAN | 공개 여부 | DEFAULT 0 |
| view_count | INTEGER | 조회수 | DEFAULT 0 |
| created_at | TIMESTAMP | 생성 시간 | DEFAULT NOW() |
| updated_at | TIMESTAMP | 수정 시간 | DEFAULT NOW() |
| deleted_at | TIMESTAMP | 삭제 시간 (소프트 삭제) | NULL = 활성 |

**예제 JSON (tags):**
```json
["ai", "machine-learning", "research"]
```

---

### 3.3 note_collaborators (노트 협업자)

```sql
CREATE TABLE note_collaborators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    permission VARCHAR(20) NOT NULL DEFAULT 'read',
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(note_id, user_id),
    CHECK (permission IN ('read', 'edit', 'admin'))
);

CREATE INDEX idx_collaborators_note_id ON note_collaborators(note_id);
CREATE INDEX idx_collaborators_user_id ON note_collaborators(user_id);
```

**컬럼 설명:**
| 컬럼명 | 타입 | 설명 | 제약사항 |
|--------|------|------|---------|
| id | INTEGER | 고유 ID | PK, AUTO |
| note_id | INTEGER | 노트 ID | FK, NOT NULL |
| user_id | INTEGER | 협업자 사용자 ID | FK, NOT NULL |
| permission | VARCHAR(20) | 권한 레벨 | read/edit/admin |
| added_at | TIMESTAMP | 공유 시간 | DEFAULT NOW() |

**권한 레벨:**
- `read`: 읽기만 가능
- `edit`: 읽기, 편집, 댓글
- `admin`: 모든 권한 (권한 변경 가능)

---

### 3.4 comments (댓글)

```sql
CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    parent_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE,
    CHECK (length(content) >= 1 AND length(content) <= 2000)
);

CREATE INDEX idx_comments_note_id ON comments(note_id);
CREATE INDEX idx_comments_user_id ON comments(user_id);
CREATE INDEX idx_comments_parent_id ON comments(parent_id);
CREATE INDEX idx_comments_created_at ON comments(created_at);
```

**컬럼 설명:**
| 컬럼명 | 타입 | 설명 | 제약사항 |
|--------|------|------|---------|
| id | INTEGER | 댓글 고유 ID | PK, AUTO |
| note_id | INTEGER | 노트 ID | FK, NOT NULL |
| user_id | INTEGER | 작성자 사용자 ID | FK, NOT NULL |
| content | TEXT | 댓글 내용 | NOT NULL, 최대 2000자 |
| parent_id | INTEGER | 부모 댓글 ID (대댓글) | FK, Optional |
| created_at | TIMESTAMP | 생성 시간 | DEFAULT NOW() |
| updated_at | TIMESTAMP | 수정 시간 | DEFAULT NOW() |
| deleted_at | TIMESTAMP | 삭제 시간 (소프트 삭제) | Optional |

---

### 3.5 ai_summaries (AI 요약)

```sql
CREATE TABLE ai_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL UNIQUE,
    summary_text TEXT NOT NULL,
    keywords JSON,
    category VARCHAR(50),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
);

CREATE INDEX idx_summaries_note_id ON ai_summaries(note_id);
CREATE INDEX idx_summaries_generated_at ON ai_summaries(generated_at);
```

**컬럼 설명:**
| 컬럼명 | 타입 | 설명 | 제약사항 |
|--------|------|------|---------|
| id | INTEGER | 고유 ID | PK, AUTO |
| note_id | INTEGER | 노트 ID | FK, NOT NULL, UNIQUE |
| summary_text | TEXT | 요약 텍스트 | NOT NULL |
| keywords | JSON | 추출된 키워드 배열 | JSON 형식 |
| category | VARCHAR(50) | 자동 분류 카테고리 | Optional |
| generated_at | TIMESTAMP | 생성 시간 | DEFAULT NOW() |

**예제 JSON (keywords):**
```json
[
    {"word": "machine learning", "weight": 0.95},
    {"word": "neural networks", "weight": 0.87}
]
```

---

### 3.6 teams (팀)

```sql
CREATE TABLE teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    owner_id INTEGER NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    CHECK (length(name) >= 1 AND length(name) <= 100)
);

CREATE INDEX idx_teams_owner_id ON teams(owner_id);
CREATE INDEX idx_teams_created_at ON teams(created_at);
```

**컬럼 설명:**
| 컬럼명 | 타입 | 설명 | 제약사항 |
|--------|------|------|---------|
| id | INTEGER | 팀 고유 ID | PK, AUTO |
| name | VARCHAR(100) | 팀 이름 | NOT NULL |
| owner_id | INTEGER | 팀 소유자 ID | FK, NOT NULL |
| description | TEXT | 팀 설명 | Optional |
| created_at | TIMESTAMP | 생성 시간 | DEFAULT NOW() |

---

### 3.7 team_members (팀 멤버)

```sql
CREATE TABLE team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(team_id, user_id),
    CHECK (role IN ('member', 'admin'))
);

CREATE INDEX idx_team_members_team_id ON team_members(team_id);
CREATE INDEX idx_team_members_user_id ON team_members(user_id);
```

**컬럼 설명:**
| 컬럼명 | 타입 | 설명 | 제약사항 |
|--------|------|------|---------|
| id | INTEGER | 고유 ID | PK, AUTO |
| team_id | INTEGER | 팀 ID | FK, NOT NULL |
| user_id | INTEGER | 사용자 ID | FK, NOT NULL |
| role | VARCHAR(20) | 역할 (member/admin) | DEFAULT 'member' |
| joined_at | TIMESTAMP | 참여 시간 | DEFAULT NOW() |

---

### 3.8 note_versions (노트 버전)

```sql
CREATE TABLE note_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE(note_id, version_number)
);

CREATE INDEX idx_versions_note_id ON note_versions(note_id);
CREATE INDEX idx_versions_created_at ON note_versions(created_at);
```

**컬럼 설명:**
| 컬럼명 | 타입 | 설명 | 제약사항 |
|--------|------|------|---------|
| id | INTEGER | 고유 ID | PK, AUTO |
| note_id | INTEGER | 노트 ID | FK, NOT NULL |
| title | VARCHAR(255) | 버전 제목 | NOT NULL |
| content | TEXT | 버전 내용 | NOT NULL |
| version_number | INTEGER | 버전 번호 | NOT NULL |
| created_by | INTEGER | 수정한 사용자 ID | FK |
| created_at | TIMESTAMP | 생성 시간 | DEFAULT NOW() |

---

### 3.9 team_notes (팀 노트)

```sql
CREATE TABLE team_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    note_id INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
    UNIQUE(team_id, note_id)
);

CREATE INDEX idx_team_notes_team_id ON team_notes(team_id);
CREATE INDEX idx_team_notes_note_id ON team_notes(note_id);
```

---

## 4. 인덱싱 전략

### 성능 최적화 인덱스

```sql
-- 검색 성능
CREATE INDEX idx_notes_title ON notes(title);
CREATE INDEX idx_notes_full_text ON notes(title, content);

-- 시간 기반 정렬
CREATE INDEX idx_notes_created_updated ON notes(created_at, updated_at);

-- 권한 확인
CREATE INDEX idx_collab_note_user ON note_collaborators(note_id, user_id);

-- 댓글 조회
CREATE INDEX idx_comments_note_created ON comments(note_id, created_at);

-- 팀 멤버 조회
CREATE INDEX idx_team_members_team_user ON team_members(team_id, user_id);
```

### 인덱싱 가이드

1. **WHERE 절**: 자주 필터링되는 컬럼
2. **JOIN 조건**: 외래키 컬럼
3. **ORDER BY**: 정렬 컬럼
4. **복합 인덱스**: 함께 쿼리되는 컬럼들

---

## 5. 데이터 관계

### 1:N 관계
- users → notes (한 사용자가 여러 노트)
- users → comments (한 사용자가 여러 댓글)
- notes → comments (한 노트가 여러 댓글)
- notes → note_versions (한 노트가 여러 버전)
- notes → ai_summaries (한 노트당 하나의 요약)

### M:N 관계
- users ↔ notes (협업자): note_collaborators
- users ↔ teams (팀 멤버): team_members
- teams ↔ notes (팀 노트): team_notes

### 계층 관계
- comments (부모 댓글 → 자식 댓글): parent_id

---

## 6. 데이터 무결성

### 제약사항

```sql
-- 외래키 제약
PRAGMA foreign_keys = ON;

-- 체크 제약
CHECK (permission IN ('read', 'edit', 'admin'))
CHECK (role IN ('member', 'admin'))
CHECK (length(username) >= 3)
CHECK (length(content) >= 1)
```

### 트리거 (선택)

```sql
-- 노트 수정 시 updated_at 자동 갱신
CREATE TRIGGER update_note_timestamp
AFTER UPDATE ON notes
BEGIN
    UPDATE notes SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

-- 노트 생성 시 버전 1 자동 저장
CREATE TRIGGER create_note_version
AFTER INSERT ON notes
BEGIN
    INSERT INTO note_versions (note_id, title, content, version_number, created_by)
    VALUES (NEW.id, NEW.title, NEW.content, 1, NEW.user_id);
END;
```

---

## 7. 쿼리 예제

### 예제 1: 사용자의 모든 노트 조회

```sql
SELECT n.*, u.username, u.full_name
FROM notes n
JOIN users u ON n.user_id = u.id
WHERE n.user_id = ? AND n.deleted_at IS NULL
ORDER BY n.created_at DESC
LIMIT 10 OFFSET 0;
```

### 예제 2: 공유된 노트 조회

```sql
SELECT n.*, u.username, nc.permission
FROM notes n
JOIN users u ON n.user_id = u.id
LEFT JOIN note_collaborators nc ON n.id = nc.note_id
WHERE (n.is_public = 1 OR nc.user_id = ?) AND n.deleted_at IS NULL
ORDER BY n.updated_at DESC;
```

### 예제 3: 노트의 모든 댓글 조회 (트리 구조)

```sql
SELECT * FROM comments
WHERE note_id = ? AND deleted_at IS NULL
ORDER BY parent_id, created_at;
```

### 예제 4: 팀의 멤버 조회

```sql
SELECT u.*, tm.role
FROM users u
JOIN team_members tm ON u.id = tm.user_id
WHERE tm.team_id = ?
ORDER BY tm.joined_at;
```

### 예제 5: 최근 노트 버전 조회

```sql
SELECT * FROM note_versions
WHERE note_id = ?
ORDER BY version_number DESC
LIMIT 1;
```

---

## 8. 마이그레이션 가이드

### 개발 → 프로덕션 (SQLite → PostgreSQL)

```python
# SQLAlchemy를 사용한 마이그레이션
from sqlalchemy import create_engine
from alembic import command
from alembic.config import Config

# 1. 기존 데이터 내보내기
def export_sqlite_data():
    # sqlite_engine을 사용하여 모든 데이터 추출
    pass

# 2. PostgreSQL 스키마 생성
pg_engine = create_engine('postgresql://user:pass@host/noteai')

# 3. 데이터 마이그레이션
def migrate_data():
    # sqlite 데이터를 PostgreSQL로 이동
    pass

# 4. 유효성 검사
def validate_migration():
    # 데이터 일관성 확인
    pass
```

---

## 9. 백업 및 복구

### 백업 전략

```bash
# SQLite 백업
sqlite3 noteai.db ".backup noteai_backup.db"

# PostgreSQL 백업
pg_dump -U user -h host noteai > noteai_dump.sql

# 일일 자동 백업 (Cron)
0 2 * * * /usr/bin/pg_dump -U user noteai | gzip > /backups/noteai_$(date +\%Y\%m\%d).sql.gz
```

### 복구

```bash
# SQLite 복구
sqlite3 noteai.db ".restore noteai_backup.db"

# PostgreSQL 복구
psql -U user -h host noteai < noteai_dump.sql
```

---

## 10. 성능 최적화

### 쿼리 최적화

1. **N+1 문제 해결**: eager loading 사용
```python
# SQLAlchemy: joinedload 사용
notes = db.query(Note).options(joinedload(Note.author)).all()
```

2. **페이지네이션**: 대량 데이터 조회
```python
page = 1
limit = 10
offset = (page - 1) * limit
notes = db.query(Note).offset(offset).limit(limit).all()
```

3. **캐싱**: 자주 조회되는 데이터
```python
# Redis 캐싱 (향후)
@cache.cached(timeout=300)
def get_popular_notes():
    return db.query(Note).filter_by(is_public=True).order_by(Note.view_count).limit(10)
```

### 데이터베이스 최적화

```sql
-- 테이블 크기 확인
SELECT name, page_count * page_size as size 
FROM pragma_page_count(), pragma_page_size();

-- VACUUM 실행 (공간 정리)
VACUUM;

-- 통계 업데이트 (PostgreSQL)
ANALYZE;
```

---

## 11. 보안 고려사항

### SQL Injection 방지
```python
# ❌ 잘못된 예
query = f"SELECT * FROM notes WHERE user_id = {user_id}"

# ✅ 올바른 예
from sqlalchemy import text
query = text("SELECT * FROM notes WHERE user_id = :user_id")
result = db.execute(query, {"user_id": user_id})
```

### 민감 정보 암호화
```python
# 비밀번호 해싱
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed_password = pwd_context.hash("password123")
```

### 감사 로깅
```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(50),
    table_name VARCHAR(50),
    record_id INTEGER,
    changes JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

**데이터베이스 설계 문서 버전**: 1.0  
**마지막 업데이트**: 2026-08-26
