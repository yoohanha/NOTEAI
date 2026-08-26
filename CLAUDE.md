# NOTEAI 개발 가이드

**AI 기반 노트 큐레이션 및 협업 플랫폼**

---

## 📌 프로젝트 개요

NOTEAI는 연구원과 개발자를 위한 **지능형 노트 관리 시스템**입니다.

### 핵심 기능
- 📝 **구조화된 노트 작성**: 마크다운 기반 에디터
- 🤖 **AI 기반 처리**: 자동 요약, 키워드 추출, 자동 분류
- 🔗 **협업 기능**: 노트 공유, 댓글, 팀 관리
- 🔍 **강력한 검색**: 전문 검색 + 시맨틱 검색
- 📊 **대시보드**: 통계, 추천, 활동 추적

---

## ⚡ 빠른 시작

### 개발 환경 설정

```bash
# 1. 가상 환경 생성
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate  # macOS/Linux

# 2. 의존성 설치
cd backend
pip install -r requirements.txt

# 3. 데이터베이스 초기화
python database.py

# 4. 서버 실행
python main.py
```

### API 문서 확인
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 📂 프로젝트 구조 (Feature-Based Architecture)

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
│   ├── core/                    # 핵심 모듈 (공유)
│   │   ├── config.py            # 환경 설정
│   │   ├── database.py          # DB 세션
│   │   ├── security.py          # JWT, 해싱
│   │   └── constants.py         # 상수
│   │
│   ├── features/                # 기능별 모듈 (독립적)
│   │   ├── auth/
│   │   │   ├── models.py        # User 모델
│   │   │   ├── schemas.py       # 요청/응답
│   │   │   ├── routes.py        # /api/auth/*
│   │   │   ├── service.py       # 비즈니스 로직
│   │   │   └── deps.py          # get_current_user
│   │   │
│   │   ├── users/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   └── service.py
│   │   │
│   │   ├── notes/
│   │   │   ├── models.py        # Note, NoteVersion
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   └── service.py
│   │   │
│   │   ├── collaborators/
│   │   │   ├── models.py        # NoteCollaborator
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   └── service.py
│   │   │
│   │   ├── comments/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   └── service.py
│   │   │
│   │   ├── teams/
│   │   │   ├── models.py        # Team, TeamMember
│   │   │   ├── schemas.py
│   │   │   ├── routes.py
│   │   │   └── service.py
│   │   │
│   │   └── ai/
│   │       ├── schemas.py
│   │       ├── routes.py
│   │       ├── service.py
│   │       └── nlp_utils.py
│   │
│   ├── utils/                   # 공유 유틸
│   │   ├── helpers.py
│   │   ├── validators.py
│   │   └── exceptions.py
│   │
│   └── uploads/                 # 파일 저장소
│
├── frontend/
│   ├── index.html
│   ├── script.js
│   ├── style.css
│   ├── pages/
│   ├── components/
│   └── assets/
│
├── tests/
│   ├── features/
│   └── integration/
│
├── CLAUDE.md
└── README.md
```

### 🎯 Feature-Based 아키텍처의 장점

| 특징 | 설명 |
|------|------|
| **독립성** | 각 기능이 완전히 독립적으로 개발/테스트 가능 |
| **확장성** | 새 기능 추가는 `features/new_feature/` 폴더 생성만으로 완성 |
| **유지보수** | 버그 수정이 해당 기능에만 영향 |
| **협업** | 팀원들이 다른 기능을 동시에 개발 가능 |
| **테스트** | 기능별 단위 테스트 및 통합 테스트 명확 |

---

## 🛠 기술 스택

| 계층 | 기술 | 용도 |
|------|------|------|
| **Backend** | FastAPI | REST API 서버 |
| **Database** | SQLite | 개발용 데이터베이스 |
| **ORM** | SQLAlchemy | 데이터 매핑 |
| **Auth** | JWT | 토큰 기반 인증 |
| **NLP** | Hugging Face | AI 기능 (요약, 분류) |
| **Frontend** | HTML/CSS/JS | 웹 클라이언트 |
| **Styling** | Tailwind CSS | 스타일 프레임워크 |

---

## 📋 주요 API 엔드포인트

### 인증 (Authentication)
```
POST   /api/auth/register          회원가입
POST   /api/auth/login             로그인
POST   /api/auth/logout            로그아웃
GET    /api/auth/me                현재 사용자 정보
```

### 사용자 (Users)
```
GET    /api/users/{user_id}        사용자 정보
PUT    /api/users/{user_id}        프로필 수정
GET    /api/users/{user_id}/notes  사용자 노트 목록
```

### 노트 (Notes)
```
GET    /api/notes                  노트 목록
POST   /api/notes                  노트 생성
GET    /api/notes/{note_id}        노트 상세
PUT    /api/notes/{note_id}        노트 수정
DELETE /api/notes/{note_id}        노트 삭제
GET    /api/notes/search           검색
POST   /api/notes/{note_id}/share  공유
```

### AI 기능 (AI Features)
```
POST   /api/notes/{note_id}/summarize        자동 요약
POST   /api/notes/{note_id}/extract-keywords 키워드 추출
POST   /api/notes/{note_id}/classify         자동 분류
POST   /api/notes/semantic-search            시맨틱 검색
```

### 댓글 (Comments)
```
GET    /api/notes/{note_id}/comments         댓글 목록
POST   /api/notes/{note_id}/comments         댓글 작성
PUT    /api/comments/{comment_id}            댓글 수정
DELETE /api/comments/{comment_id}            댓글 삭제
```

### 팀 (Teams)
```
GET    /api/teams                  팀 목록
POST   /api/teams                  팀 생성
GET    /api/teams/{team_id}        팀 상세
POST   /api/teams/{team_id}/members 멤버 추가
```

**전체 API 문서**: `docs/api.md` 참조

---

## 🗄 데이터베이스 설계

### 주요 테이블
- **users**: 사용자 계정 정보
- **notes**: 노트 콘텐츠 및 메타데이터
- **note_collaborators**: 협업자 권한 관리
- **comments**: 노트별 댓글
- **ai_summaries**: AI 생성 요약
- **teams**: 팀 정보
- **team_members**: 팀 멤버 및 역할
- **note_versions**: 노트 변경 이력

**전체 데이터베이스 설계**: `docs/database.md` 참조

---

## 📚 주요 문서

| 문서 | 설명 |
|------|------|
| `docs/planning.md` | 전체 기획 및 아키텍처 |
| `docs/requirements.md` | 상세 요구사항 정의 |
| `docs/api.md` | API 엔드포인트 문서 |
| `docs/database.md` | 데이터베이스 스키마 |
| `CLAUDE.md` | 개발 가이드 (이 파일) |

---

## 📝 개발 단계 체크리스트

### Phase 1: 기초 구축
- [x] 프로젝트 기획 및 문서화
- [ ] 데이터베이스 스키마 구현
- [ ] FastAPI 기본 구조 설정
- [ ] 인증 시스템 구현

### Phase 2: 핵심 기능
- [ ] 노트 CRUD API
- [ ] 사용자 관리 API
- [ ] 마크다운 에디터 통합
- [ ] 기본 대시보드

### Phase 3: AI 기능
- [ ] 자동 요약
- [ ] 키워드 추출
- [ ] 자동 분류
- [ ] 시맨틱 검색

### Phase 4: 협업 기능
- [ ] 노트 공유 및 권한
- [ ] 댓글 시스템
- [ ] 팀 관리

### Phase 5: 고급 기능
- [ ] 버전 관리
- [ ] 고급 검색
- [ ] 통계 대시보드
- [ ] 추천 기능

### Phase 6: 테스트 & 배포
- [ ] 단위 테스트
- [ ] 통합 테스트
- [ ] 성능 최적화
- [ ] 배포 준비

---

## 🔧 코딩 표준

### Python (Backend)
```python
# PEP 8 준수
- 들여쓰기: 4칸
- 라인 길이: 88자 (black 형식)
- snake_case 변수명
- 한국어 주석 필수

def get_user_notes(user_id: int, limit: int = 10) -> List[Note]:
    """
    사용자의 노트 목록을 조회합니다.
    
    Args:
        user_id: 사용자 ID
        limit: 반환할 최대 아이템 수
    
    Returns:
        노트 목록
    """
    pass
```

### JavaScript (Frontend)
```javascript
// ES6+ 표준
- 들여쓰기: 2칸
- camelCase 변수명
- const/let 사용 (var 금지)
- 화살표 함수 선호

/**
 * 노트를 조회합니다.
 * @param {number} noteId - 노트 ID
 * @returns {Promise<Object>} 노트 정보
 */
async function getNote(noteId) {
  const response = await fetch(`/api/notes/${noteId}`);
  return response.json();
}
```

### API 응답 표준
```json
{
  "status": 200,
  "data": { /* 실제 데이터 */ },
  "message": "성공 메시지"
}
```

---

## 🚀 배포 가이드

### 프로덕션 체크리스트
- [ ] 환경 변수 설정 (.env)
- [ ] 데이터베이스 마이그레이션 (PostgreSQL)
- [ ] HTTPS/SSL 인증서
- [ ] CORS 설정
- [ ] 로깅 및 모니터링
- [ ] 백업 계획

### Docker 배포
```bash
docker build -t noteai .
docker run -p 8000:8000 noteai
```

---

## 📞 개발자 정보

- **Email**: o12hana@gmail.com
- **Project Manager**: Planner Team

---

**문서 버전**: 1.0  
**최종 업데이트**: 2026-08-26  
**상태**: Phase 1 완료, Phase 2 준비 중
