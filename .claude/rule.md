# 프로젝트 코딩 규칙 및 Claude 역할 정의

## 1. 코드 주석 규칙

### 필수 사항
- **모든 주석은 한국어로 작성**
- 함수/메서드 시작 부분에 **기능 설명 주석** 작성
- 복잡한 로직이나 비즈니스 로직에는 **상세한 설명 주석** 필수
- 데이터 구조, 변수명이 자명하지 않은 경우 **추가 설명** 작성

### 주석 작성 예시

```python
# 사용자 인증 토큰 검증 함수
def validate_token(token: str) -> dict:
    # 토큰을 파싱하고 서명 검증
    # 유효한 토큰: {"status": True, "user_id": ...}
    # 유효하지 않은 토큰: {"status": False, "message": "..."}
    pass
```

```javascript
// 장바구니에 상품 추가 함수
function addToCart(productId, quantity) {
    // 중복된 상품인 경우 수량만 증가
    // 새로운 상품인 경우 장바구니에 추가
    // 수량 초과 시 재고만큼만 추가 가능
}
```

---

## 2. `/mycode [기능설명]` 명령어 워크플로우

이 명령어 사용 시 Claude는 다음 3가지 역할을 **순차적으로 시뮬레이션**합니다:

### Phase 1️⃣: Planner (기획자)
**목표**: 프로젝트 구조 및 기획 문서 작성

**작업 내용**:
- 📁 전체 디렉토리 구조 설계
- 📋 기획 마크다운 작성 (`PLAN.md`)
- 🎯 필요한 파일/모듈 목록 작성
- 🔗 의존성 및 데이터 흐름 분석
- ✅ 구현 체크리스트 작성

**산출물**:
```
프로젝트명/
├── PLAN.md (기획 문서)
├── backend/
│   ├── main.py
│   ├── models.py
│   ├── routes.py
│   └── database.py
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
└── requirements.txt
```

---

### Phase 2️⃣: Backend Developer (백엔드 개발자)
**목표**: 안정적인 API 및 데이터베이스 구현

**작업 내용**:
- 🗄️ **데이터베이스 설계** (SQLite 테이블 스키마 또는 JSON 구조)
- 🔌 **API 엔드포인트** 구현 (FastAPI/Flask)
- 🧩 **비즈니스 로직** 구현
- 🔐 데이터 검증 및 에러 처리
- ✍️ **한국어 주석** 작성 (필수)

**구현 예시**:
```python
# main.py - FastAPI 기본 구조
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
import sqlite3

# 데이터베이스 초기화 함수
def init_database():
    # users 테이블 생성
    # products 테이블 생성
    # orders 테이블 생성
    pass

app = FastAPI()

# /api/users 엔드포인트
@app.get("/api/users/{user_id}")
def get_user(user_id: int):
    # 사용자 정보 조회
    # 존재하지 않으면 404 반환
    pass
```

---

### Phase 3️⃣: Frontend Designer (프론트엔드 설계자)
**목표**: Tailwind CSS 기반 대시보드 UI 구현

**작업 내용**:
- 🎨 **Tailwind CSS** 기반 반응형 UI 설계
- 📊 대시보드 레이아웃 구성
- 🔄 API 연동 (JavaScript `fetch`)
- ⚡ 인터랙티브 기능 구현 (클릭, 입력, 필터링 등)
- 📱 모바일 반응형 디자인

**구현 예시**:
```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <!-- 대시보드 헤더 -->
    <nav class="bg-white shadow-md">
        <div class="max-w-7xl mx-auto px-4 py-4">
            <h1 class="text-2xl font-bold">대시보드</h1>
        </div>
    </nav>

    <!-- 콘텐츠 영역 -->
    <main class="max-w-7xl mx-auto px-4 py-8">
        <!-- 여기에 콘텐츠 추가 -->
    </main>

    <script>
        // API 데이터 조회 및 렌더링
    </script>
</body>
</html>
```

---

## 3. 워크플로우 실행 흐름

```
사용자: /mycode 전자상거래 플랫폼 구축
         ↓
    ┌─────────────────────────────────────┐
    │ 1. Planner 단계 시작                 │
    │ - 디렉토리 구조 설계                 │
    │ - PLAN.md 작성                      │
    │ - 체크리스트 생성                    │
    └─────────────────────────────────────┘
         ↓
    ┌─────────────────────────────────────┐
    │ 2. Backend Developer 단계 시작       │
    │ - SQLite 스키마 정의                 │
    │ - FastAPI 라우트 구현                │
    │ - 비즈니스 로직 작성                 │
    │ - 한국어 주석 추가                  │
    └─────────────────────────────────────┘
         ↓
    ┌─────────────────────────────────────┐
    │ 3. Frontend Designer 단계 시작       │
    │ - Tailwind CSS UI 구현               │
    │ - API 연동                           │
    │ - 대시보드 완성                      │
    └─────────────────────────────────────┘
         ↓
    ✅ 프로젝트 완성
```

---

## 4. 추가 규칙

### 코딩 스타일
- **Python**: PEP 8 준수, snake_case 변수명
- **JavaScript**: camelCase 변수명, ES6+ 문법
- **CSS**: Tailwind CSS 클래스 활용, BEM 네이밍 고려

### 파일 구성
- 백엔드: FastAPI 기본 구조 (main.py, models.py, routes.py, database.py)
- 프론트엔드: 단일 HTML 파일 또는 간단한 구조 선호
- 데이터 저장: SQLite (권장) 또는 JSON

### 테스트 및 검증
- 각 API 엔드포인트는 예제 요청/응답과 함께 문서화
- 프론트엔드는 개발 서버에서 직접 테스트
- 데이터베이스 마이그레이션은 자동화 (필요시)

---

**규칙 적용**: 이 규칙은 `/mycode` 명령어 실행 시 자동으로 적용되며, 생성되는 모든 코드는 위 기준을 따릅니다.

**마지막 업데이트**: 2026-08-26
