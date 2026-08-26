# NOTEAI - API 문서

**REST API Specification**

---

## 개요

### 기본 정보
- **Base URL**: `http://localhost:8000/api`
- **API Version**: v1
- **Response Format**: JSON
- **Authentication**: JWT Bearer Token

### 응답 형식 (Standard Response)

모든 API 응답은 다음 형식을 따릅니다:

```json
{
    "status": 200,
    "data": {
        // 응답 데이터
    },
    "message": "Success message"
}
```

**상태 코드:**
- `200 OK`: 성공
- `201 Created`: 생성 완료
- `400 Bad Request`: 잘못된 요청
- `401 Unauthorized`: 인증 필요
- `403 Forbidden`: 접근 금지
- `404 Not Found`: 리소스 없음
- `500 Internal Server Error`: 서버 오류

### 인증

**모든 인증이 필요한 엔드포인트에서:**
```
Authorization: Bearer <access_token>
```

---

## 1. 인증 API (Authentication)

### 1.1 회원가입

**Endpoint**: `POST /auth/register`

**설명**: 새로운 사용자 계정을 생성합니다.

**요청:**
```json
{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePass123",
    "full_name": "John Doe"
}
```

**응답** (201 Created):
```json
{
    "status": 201,
    "data": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "full_name": "John Doe",
        "created_at": "2026-08-26T10:00:00Z"
    },
    "message": "User registered successfully. Please log in."
}
```

**오류 응답** (400 Bad Request):
```json
{
    "status": 400,
    "data": null,
    "message": "Username already exists"
}
```

**유효성 검사:**
- `username`: 3-50자, 영문/숫자/밑줄만 허용
- `email`: 유효한 이메일 형식
- `password`: 최소 8자, 대문자+소문자+숫자 포함
- `full_name`: 선택 사항, 최대 100자

---

### 1.2 로그인

**Endpoint**: `POST /auth/login`

**설명**: 사용자를 인증하고 액세스 토큰을 발급합니다.

**요청:**
```json
{
    "username": "john_doe",
    "password": "SecurePass123"
}
```

**응답** (200 OK):
```json
{
    "status": 200,
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 86400,
        "user": {
            "id": 1,
            "username": "john_doe",
            "email": "john@example.com",
            "full_name": "John Doe"
        }
    },
    "message": "Login successful"
}
```

**오류 응답** (401 Unauthorized):
```json
{
    "status": 401,
    "data": null,
    "message": "Invalid credentials"
}
```

---

### 1.3 로그아웃

**Endpoint**: `POST /auth/logout`

**설명**: 현재 세션을 종료합니다.

**인증**: 필수 (Authorization: Bearer token)

**요청**: (본문 없음)

**응답** (200 OK):
```json
{
    "status": 200,
    "data": null,
    "message": "Logout successful"
}
```

---

### 1.4 현재 사용자 정보

**Endpoint**: `GET /auth/me`

**설명**: 현재 인증된 사용자의 정보를 조회합니다.

**인증**: 필수

**응답** (200 OK):
```json
{
    "status": 200,
    "data": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "full_name": "John Doe",
        "bio": "Software Developer",
        "avatar_url": "https://api.example.com/avatars/1.jpg",
        "created_at": "2026-08-26T10:00:00Z",
        "updated_at": "2026-08-26T11:00:00Z"
    },
    "message": "User information retrieved"
}
```

---

## 2. 사용자 API (Users)

### 2.1 사용자 정보 조회

**Endpoint**: `GET /users/{user_id}`

**설명**: 특정 사용자의 공개 정보를 조회합니다.

**경로 매개변수:**
- `user_id` (정수): 사용자 ID

**응답** (200 OK):
```json
{
    "status": 200,
    "data": {
        "id": 2,
        "username": "jane_doe",
        "full_name": "Jane Doe",
        "bio": "Researcher",
        "avatar_url": "https://api.example.com/avatars/2.jpg"
    },
    "message": "User information retrieved"
}
```

---

### 2.2 사용자 정보 수정

**Endpoint**: `PUT /users/{user_id}`

**설명**: 현재 사용자의 정보를 수정합니다. (본인만 가능)

**인증**: 필수

**경로 매개변수:**
- `user_id` (정수): 사용자 ID (현재 사용자 ID와 일치해야 함)

**요청:**
```json
{
    "full_name": "John Smith",
    "bio": "Senior Developer",
    "avatar_url": "https://api.example.com/avatars/1.jpg"
}
```

**응답** (200 OK):
```json
{
    "status": 200,
    "data": {
        "id": 1,
        "username": "john_doe",
        "full_name": "John Smith",
        "bio": "Senior Developer",
        "avatar_url": "https://api.example.com/avatars/1.jpg",
        "updated_at": "2026-08-26T12:00:00Z"
    },
    "message": "User updated successfully"
}
```

---

### 2.3 사용자의 노트 목록

**Endpoint**: `GET /users/{user_id}/notes`

**설명**: 특정 사용자의 공개 노트 목록을 조회합니다.

**경로 매개변수:**
- `user_id` (정수): 사용자 ID

**쿼리 매개변수:**
- `page` (정수, 기본값: 1): 페이지 번호
- `limit` (정수, 기본값: 10, 최대: 100): 페이지당 아이템 수
- `category` (문자열): 카테고리 필터
- `tag` (문자열): 태그 필터
- `sort` (문자열): 정렬 기준 (created_at, updated_at, title)
- `order` (문자열): 정렬 순서 (asc, desc)

**예제 요청:**
```
GET /users/2/notes?page=1&limit=10&category=Research&sort=created_at&order=desc
```

**응답** (200 OK):
```json
{
    "status": 200,
    "data": {
        "notes": [
            {
                "id": 1,
                "title": "ML Basics",
                "content": "# Machine Learning...",
                "category": "Research",
                "tags": ["ai", "ml"],
                "is_public": true,
                "view_count": 125,
                "created_at": "2026-08-26T10:00:00Z",
                "updated_at": "2026-08-26T10:30:00Z"
            }
        ],
        "pagination": {
            "total": 42,
            "page": 1,
            "limit": 10,
            "total_pages": 5
        }
    },
    "message": "User notes retrieved"
}
```

---

## 3. 노트 API (Notes)

### 3.1 모든 노트 조회

**Endpoint**: `GET /notes`

**설명**: 공개 노트 및 현재 사용자의 노트를 조회합니다.

**인증**: 선택 (미인증 사용자는 공개 노트만)

**쿼리 매개변수:**
- `page` (정수, 기본값: 1)
- `limit` (정수, 기본값: 10, 최대: 100)
- `category` (문자열): 카테고리 필터
- `tag` (문자열): 태그 필터
- `sort` (문자열): created_at, updated_at, title
- `order` (문자열): asc, desc
- `is_public` (불린): 공개 노트만 조회 (기본값: true)

**응답** (200 OK):
```json
{
    "status": 200,
    "data": {
        "notes": [
            {
                "id": 1,
                "title": "Note Title",
                "content": "# Heading\n\nContent here...",
                "category": "Research",
                "tags": ["ai", "learning"],
                "is_public": true,
                "view_count": 50,
                "author": {
                    "id": 2,
                    "username": "jane_doe",
                    "full_name": "Jane Doe"
                },
                "created_at": "2026-08-26T10:00:00Z",
                "updated_at": "2026-08-26T10:30:00Z"
            }
        ],
        "pagination": {
            "total": 100,
            "page": 1,
            "limit": 10,
            "total_pages": 10
        }
    },
    "message": "Notes retrieved"
}
```

---

### 3.2 새 노트 생성

**Endpoint**: `POST /notes`

**설명**: 새로운 노트를 생성합니다.

**인증**: 필수

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

**응답** (201 Created):
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
        "view_count": 0,
        "created_at": "2026-08-26T10:00:00Z",
        "updated_at": "2026-08-26T10:00:00Z"
    },
    "message": "Note created successfully"
}
```

**유효성 검사:**
- `title`: 필수, 1-200자
- `content`: 필수, 최소 1자
- `category`: 선택, 최대 50자
- `tags`: 선택, 최대 10개, 각 최대 30자

---

### 3.3 노트 상세 조회

**Endpoint**: `GET /notes/{note_id}`

**설명**: 특정 노트의 상세 정보를 조회합니다.

**인증**: 선택 (권한이 있는 경우만)

**경로 매개변수:**
- `note_id` (정수): 노트 ID

**응답** (200 OK):
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
        "author": {
            "id": 1,
            "username": "john_doe",
            "full_name": "John Doe",
            "avatar_url": "https://..."
        },
        "collaborators": [
            {
                "id": 2,
                "username": "jane_doe",
                "permission": "read"
            }
        ],
        "created_at": "2026-08-26T10:00:00Z",
        "updated_at": "2026-08-26T11:00:00Z",
        "comment_count": 3
    },
    "message": "Note retrieved"
}
```

**오류 응답** (403 Forbidden):
```json
{
    "status": 403,
    "data": null,
    "message": "You don't have permission to view this note"
}
```

---

### 3.4 노트 수정

**Endpoint**: `PUT /notes/{note_id}`

**설명**: 노트를 수정합니다. (소유자 또는 편집 권한자만)

**인증**: 필수

**경로 매개변수:**
- `note_id` (정수): 노트 ID

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

**응답** (200 OK):
```json
{
    "status": 200,
    "data": {
        "id": 1,
        "title": "Updated Title",
        "category": "Development",
        "tags": ["coding", "python"],
        "is_public": true,
        "updated_at": "2026-08-26T12:00:00Z"
    },
    "message": "Note updated successfully"
}
```

---

### 3.5 노트 삭제

**Endpoint**: `DELETE /notes/{note_id}`

**설명**: 노트를 삭제합니다. (소유자만)

**인증**: 필수

**경로 매개변수:**
- `note_id` (정수): 노트 ID

**응답** (200 OK):
```json
{
    "status": 200,
    "data": null,
    "message": "Note deleted successfully"
}
```

---

### 3.6 노트 검색

**Endpoint**: `GET /notes/search`

**설명**: 노트를 검색합니다.

**인증**: 선택

**쿼리 매개변수:**
- `q` (문자열, 필수): 검색어
- `type` (문자열): 검색 타입 (full_text, semantic) - 기본값: full_text
- `category` (문자열): 카테고리 필터
- `tag` (문자열): 태그 필터
- `from_date` (ISO 8601): 시작 날짜
- `to_date` (ISO 8601): 종료 날짜
- `page` (정수, 기본값: 1)
- `limit` (정수, 기본값: 10)

**예제 요청:**
```
GET /notes/search?q=machine+learning&type=full_text&category=Research&page=1&limit=10
```

**응답** (200 OK):
```json
{
    "status": 200,
    "data": {
        "notes": [
            {
                "id": 1,
                "title": "Machine Learning Basics",
                "content_snippet": "Machine Learning is... (first 100 chars)",
                "category": "Research",
                "tags": ["ai", "ml"],
                "relevance_score": 0.95
            }
        ],
        "pagination": {
            "total": 25,
            "page": 1,
            "limit": 10
        }
    },
    "message": "Search completed"
}
```

---

### 3.7 노트 공유

**Endpoint**: `POST /notes/{note_id}/share`

**설명**: 노트를 다른 사용자와 공유합니다.

**인증**: 필수

**경로 매개변수:**
- `note_id` (정수): 노트 ID

**요청:**
```json
{
    "users": [2, 3],
    "permission": "read",
    "expires_at": "2026-09-26T00:00:00Z"
}
```

**응답** (200 OK):
```json
{
    "status": 200,
    "data": {
        "note_id": 1,
        "shared_with": [
            {
                "user_id": 2,
                "username": "jane_doe",
                "permission": "read"
            },
            {
                "user_id": 3,
                "username": "bob_smith",
                "permission": "read"
            }
        ],
        "expires_at": "2026-09-26T00:00:00Z"
    },
    "message": "Note shared successfully"
}
```

---

## 4. AI 기능 API (AI Features)

### 4.1 노트 요약

**Endpoint**: `POST /notes/{note_id}/summarize`

**설명**: AI가 노트를 요약합니다.

**인증**: 필수

**경로 매개변수:**
- `note_id` (정수): 노트 ID

**요청:**
```json
{
    "length": "medium"
}
```

**요청 매개변수:**
- `length` (문자열): 요약 길이 (short, medium, long) - 기본값: medium

**응답** (200 OK):
```json
{
    "status": 200,
    "data": {
        "note_id": 1,
        "summary": "This note discusses the fundamentals of machine learning, including supervised and unsupervised learning paradigms...",
        "length": 150,
        "generated_at": "2026-08-26T12:00:00Z"
    },
    "message": "Summary generated successfully"
}
```

---

### 4.2 키워드 추출

**Endpoint**: `POST /notes/{note_id}/extract-keywords`

**설명**: 노트에서 키워드를 추출합니다.

**인증**: 필수

**경로 매개변수:**
- `note_id` (정수): 노트 ID

**응답** (200 OK):
```json
{
    "status": 200,
    "data": {
        "note_id": 1,
        "keywords": [
            {
                "word": "artificial intelligence",
                "weight": 0.95
            },
            {
                "word": "machine learning",
                "weight": 0.87
            },
            {
                "word": "neural networks",
                "weight": 0.82
            }
        ],
        "generated_at": "2026-08-26T12:00:00Z"
    },
    "message": "Keywords extracted successfully"
}
```

---

### 4.3 자동 분류

**Endpoint**: `POST /notes/{note_id}/classify`

**설명**: 노트를 자동으로 분류합니다.

**인증**: 필수

**경로 매개변수:**
- `note_id` (정수): 노트 ID

**응답** (200 OK):
```json
{
    "status": 200,
    "data": {
        "note_id": 1,
        "categories": [
            {
                "name": "Research",
                "confidence": 0.92
            },
            {
                "name": "Technology",
                "confidence": 0.85
            },
            {
                "name": "AI",
                "confidence": 0.78
            }
        ],
        "generated_at": "2026-08-26T12:00:00Z"
    },
    "message": "Classification completed"
}
```

---

### 4.4 시맨틱 검색

**Endpoint**: `POST /notes/semantic-search`

**설명**: 의미 기반으로 노트를 검색합니다.

**인증**: 선택

**요청:**
```json
{
    "query": "machine learning algorithms",
    "limit": 10
}
```

**응답** (200 OK):
```json
{
    "status": 200,
    "data": {
        "results": [
            {
                "id": 1,
                "title": "ML Algorithms Overview",
                "similarity_score": 0.95
            },
            {
                "id": 5,
                "title": "Deep Learning Basics",
                "similarity_score": 0.87
            }
        ],
        "total": 15
    },
    "message": "Semantic search completed"
}
```

---

## 5. 댓글 API (Comments)

### 5.1 댓글 목록 조회

**Endpoint**: `GET /notes/{note_id}/comments`

**설명**: 특정 노트의 모든 댓글을 조회합니다.

**인증**: 선택

**경로 매개변수:**
- `note_id` (정수): 노트 ID

**쿼리 매개변수:**
- `page` (정수, 기본값: 1)
- `limit` (정수, 기본값: 10)

**응답** (200 OK):
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
                    "full_name": "Jane Doe",
                    "avatar_url": "https://..."
                },
                "created_at": "2026-08-26T10:00:00Z",
                "updated_at": null,
                "replies": []
            }
        ],
        "pagination": {
            "total": 5,
            "page": 1,
            "limit": 10
        }
    },
    "message": "Comments retrieved"
}
```

---

### 5.2 댓글 작성

**Endpoint**: `POST /notes/{note_id}/comments`

**설명**: 노트에 댓글을 작성합니다.

**인증**: 필수

**경로 매개변수:**
- `note_id` (정수): 노트 ID

**요청:**
```json
{
    "content": "This is very helpful!",
    "parent_id": null
}
```

**응답** (201 Created):
```json
{
    "status": 201,
    "data": {
        "id": 1,
        "note_id": 1,
        "user_id": 1,
        "content": "This is very helpful!",
        "author": {
            "id": 1,
            "username": "john_doe",
            "full_name": "John Doe"
        },
        "created_at": "2026-08-26T10:00:00Z",
        "parent_id": null
    },
    "message": "Comment created successfully"
}
```

---

### 5.3 댓글 수정

**Endpoint**: `PUT /comments/{comment_id}`

**설명**: 댓글을 수정합니다. (작성자만)

**인증**: 필수

**경로 매개변수:**
- `comment_id` (정수): 댓글 ID

**요청:**
```json
{
    "content": "Updated comment text"
}
```

**응답** (200 OK):
```json
{
    "status": 200,
    "data": {
        "id": 1,
        "content": "Updated comment text",
        "updated_at": "2026-08-26T11:00:00Z"
    },
    "message": "Comment updated"
}
```

---

### 5.4 댓글 삭제

**Endpoint**: `DELETE /comments/{comment_id}`

**설명**: 댓글을 삭제합니다. (작성자 또는 노트 소유자)

**인증**: 필수

**경로 매개변수:**
- `comment_id` (정수): 댓글 ID

**응답** (200 OK):
```json
{
    "status": 200,
    "data": null,
    "message": "Comment deleted"
}
```

---

## 6. 팀 API (Teams)

### 6.1 팀 목록 조회

**Endpoint**: `GET /teams`

**설명**: 현재 사용자가 속한 팀 목록을 조회합니다.

**인증**: 필수

**쿼리 매개변수:**
- `page` (정수, 기본값: 1)
- `limit` (정수, 기본값: 10)

**응답** (200 OK):
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
                "note_count": 20,
                "created_at": "2026-08-26T10:00:00Z"
            }
        ],
        "pagination": {
            "total": 3,
            "page": 1,
            "limit": 10
        }
    },
    "message": "Teams retrieved"
}
```

---

### 6.2 새 팀 생성

**Endpoint**: `POST /teams`

**설명**: 새로운 팀을 생성합니다.

**인증**: 필수

**요청:**
```json
{
    "name": "Research Team",
    "description": "Team for research projects"
}
```

**응답** (201 Created):
```json
{
    "status": 201,
    "data": {
        "id": 1,
        "name": "Research Team",
        "owner_id": 1,
        "description": "Team for research projects",
        "created_at": "2026-08-26T10:00:00Z"
    },
    "message": "Team created successfully"
}
```

---

### 6.3 팀 상세 조회

**Endpoint**: `GET /teams/{team_id}`

**설명**: 특정 팀의 상세 정보를 조회합니다.

**인증**: 필수 (팀 멤버만)

**경로 매개변수:**
- `team_id` (정수): 팀 ID

**응답** (200 OK):
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
            },
            {
                "id": 2,
                "username": "jane_doe",
                "role": "member"
            }
        ],
        "member_count": 2,
        "created_at": "2026-08-26T10:00:00Z"
    },
    "message": "Team retrieved"
}
```

---

### 6.4 팀 멤버 추가

**Endpoint**: `POST /teams/{team_id}/members`

**설명**: 팀에 새로운 멤버를 추가합니다. (팀 관리자만)

**인증**: 필수

**경로 매개변수:**
- `team_id` (정수): 팀 ID

**요청:**
```json
{
    "user_id": 3,
    "role": "member"
}
```

**응답** (201 Created):
```json
{
    "status": 201,
    "data": {
        "team_id": 1,
        "user_id": 3,
        "username": "bob_smith",
        "role": "member",
        "joined_at": "2026-08-26T12:00:00Z"
    },
    "message": "Member added to team"
}
```

---

## 에러 처리

### 공통 에러 코드

| 코드 | 상태 | 설명 |
|------|------|------|
| INVALID_REQUEST | 400 | 잘못된 요청 형식 |
| UNAUTHORIZED | 401 | 인증이 필요함 |
| FORBIDDEN | 403 | 접근 권한 없음 |
| NOT_FOUND | 404 | 리소스를 찾을 수 없음 |
| CONFLICT | 409 | 리소스 충돌 (예: 중복된 사용자명) |
| VALIDATION_ERROR | 422 | 유효성 검사 실패 |
| INTERNAL_ERROR | 500 | 서버 오류 |

### 에러 응답 형식

```json
{
    "status": 400,
    "data": {
        "error_code": "VALIDATION_ERROR",
        "errors": [
            {
                "field": "email",
                "message": "Invalid email format"
            }
        ]
    },
    "message": "Validation failed"
}
```

---

## 레이트 제한

- **기본값**: 1,000 요청/시간/IP
- **인증 사용자**: 5,000 요청/시간
- **응답 헤더**:
  - `X-RateLimit-Limit`: 한도
  - `X-RateLimit-Remaining`: 남은 요청 수
  - `X-RateLimit-Reset`: 리셋 시간 (Unix timestamp)

---

**API 문서 버전**: 1.0  
**마지막 업데이트**: 2026-08-26
