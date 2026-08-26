---
name: mycode
type: command
description: Planner → Backend Developer → Frontend Designer 순서로 완전한 풀스택 프로젝트 자동 생성
usage: "/mycode [프로젝트 기능 설명]"
---

# /mycode - 풀스택 프로젝트 자동 생성 명령어

## 📖 설명

사용자가 입력한 기능 설명을 기반으로 **Planner → Backend Developer → Frontend Designer** 순서로 완전한 풀스택 프로젝트를 자동 생성합니다.

## 💡 사용 방법

```bash
/mycode [프로젝트 기능 설명]
```

## 🎯 예시

```bash
/mycode 전자상거래 플랫폼 구축
```

```bash
/mycode 사용자 일정 관리 앱
```

```bash
/mycode 비용 추적 대시보드
```

---

## 🚀 자동 실행 흐름

### Phase 1️⃣: Planner (기획자)

**역할**: 프로젝트 기획 및 구조 설계

**산출물**:
- 📁 `PLAN.md` - 전체 프로젝트 기획 문서
- 📋 디렉토리 구조 설계
- ✅ 구현 체크리스트
- 🔗 데이터 흐름 다이어그램

**작업 내용**:
1. 기능 분석 - 프로젝트 핵심 기능 및 API 엔드포인트 도출
2. 아키텍처 설계 - 백엔드(FastAPI), DB(SQLite), 프론트엔드 레이아웃
3. 파일 구조 정의 - 디렉토리 계층 구조 및 핵심 파일 목록
4. 검토 및 확인 - 구현 체크리스트 및 위험 요소 검토

---

### Phase 2️⃣: Backend Developer (백엔드 개발자)

**역할**: FastAPI 기반 백엔드 구현

**산출물**:
- 🔌 `main.py` - FastAPI 애플리케이션 진입점
- 🗄️ `models.py` - 데이터베이스 모델 및 스키마
- 🛣️ `routes.py` - REST API 엔드포인트 정의
- 🔧 `database.py` - 데이터베이스 초기화 및 헬퍼 함수
- 📦 `requirements.txt` - Python 의존성

**구현 기준**:
- ✅ 모든 주석은 **한국어로 상세하게** 작성
- ✅ SQLite 테이블 스키마 또는 JSON 구조 정의
- ✅ 각 API 엔드포인트는 요청/응답 예제와 함께 문서화
- ✅ 에러 처리 및 데이터 검증 포함
- ✅ 사용하기 쉬운 헬퍼 함수 제공

**예시**:
```python
# main.py - FastAPI 진입점
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

# 데이터베이스 초기화
def init_database():
    # 모든 테이블 생성
    pass

app = FastAPI()

# 스태틱 파일 서빙
app.mount("/", StaticFiles(directory=".", html=True), name="static")

@app.get("/api/health")
def health():
    # 애플리케이션 상태 확인
    return {"status": "healthy"}

if __name__ == "__main__":
    init_database()
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

---

### Phase 3️⃣: Frontend Designer (프론트엔드 설계자)

**역할**: Tailwind CSS 기반 UI 구현

**산출물**:
- 🎨 `index.html` - Tailwind CSS 기반 대시보드 UI
- 💄 `style.css` - 커스텀 스타일 (필요시)
- 🔄 `script.js` - API 연동 및 인터랙티브 기능

**구현 기준**:
- ✅ **Tailwind CSS** 클래스 사용으로 모던하고 반응형 UI 구현
- ✅ 모든 API 엔드포인트와 연동
- ✅ 사용자 입력 검증 및 에러 메시지 표시
- ✅ 로딩 상태 및 성공/실패 피드백 제공
- ✅ 모바일 친화적 설계 (반응형)
- ✅ 접근성 고려 (alt 텍스트, 시맨틱 HTML)

**예시**:
```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>대시보드</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <!-- 네비게이션 -->
    <nav class="bg-white shadow-md">
        <div class="max-w-7xl mx-auto px-4 py-4">
            <h1 class="text-2xl font-bold text-gray-800">대시보드</h1>
        </div>
    </nav>

    <!-- 메인 콘텐츠 -->
    <main class="max-w-7xl mx-auto px-4 py-8">
        <!-- 콘텐츠 영역 -->
    </main>

    <script>
        // API 연동 코드
        async function loadData() {
            try {
                const response = await fetch('/api/...');
                const data = await response.json();
                // 데이터 렌더링
            } catch (error) {
                console.error('데이터 로드 실패:', error);
            }
        }
        
        // 페이지 로드 시 데이터 초기화
        loadData();
    </script>
</body>
</html>
```

---

## 📁 생성되는 프로젝트 구조

```
프로젝트_이름/
├── PLAN.md                  # 기획 문서
├── backend/
│   ├── main.py              # FastAPI 진입점
│   ├── models.py            # 데이터베이스 모델
│   ├── routes.py            # API 라우트
│   ├── database.py          # DB 초기화
│   └── requirements.txt     # Python 의존성
├── frontend/
│   ├── index.html           # 대시보드 UI
│   ├── script.js            # 인터랙티브 기능
│   └── style.css            # 커스텀 스타일
└── README.md                # 프로젝트 설명
```

---

## 🛠️ 실행 방법

생성된 프로젝트 실행:

```bash
# 1. 프로젝트 디렉토리로 이동
cd 프로젝트_이름

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 애플리케이션 실행
python main.py

# 4. 브라우저에서 접속
# http://127.0.0.1:8000
```

### API 문서 확인
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## 📋 코딩 표준

### Python (Backend)
- **PEP 8** 준수
- **snake_case** 변수명
- **한국어 주석** (필수)
- SQLite ORM 또는 직접 쿼리

### JavaScript (Frontend)
- **camelCase** 변수명
- **ES6+** 문법 사용
- **fetch API**로 백엔드 연동

### CSS (Styling)
- **Tailwind CSS** 우선 사용
- **Mobile-first** 반응형 설계

### API 응답 표준
```json
{
  "status": 200,
  "data": { /* 실제 데이터 */ },
  "message": "성공 메시지"
}
```

---

## ✨ 특징

| 기능 | 설명 |
|------|------|
| **완전 자동화** | 3단계를 순차적으로 자동 실행 |
| **한국어 주석** | 모든 코드에 한국어로 상세 작성 |
| **FastAPI** | 모던하고 안전한 REST API 프레임워크 |
| **SQLite** | 경량의 데이터베이스 |
| **Tailwind CSS** | 유틸리티 우선 CSS 프레임워크 |
| **즉시 실행 가능** | 생성 후 바로 `python main.py`로 실행 |

---

**명령어 버전**: 1.0  
**마지막 업데이트**: 2026-08-26
