# NOTEAI - 테스트 실행 가이드

## 📋 테스트 개요

NOTEAI 프로젝트의 단위 테스트(Unit Tests)를 pytest로 작성했습니다.

### 테스트 구조

```
tests/
├── conftest.py                  # pytest 설정 및 공유 fixtures
├── features/
│   ├── test_auth.py            # 인증 API 테스트 (24개)
│   ├── test_notes.py           # 노트 API 테스트 (40개)
│   └── test_users.py           # 사용자 API 테스트 (예정)
├── test_file_upload.py          # 파일 업로드 테스트 (15개)
└── integration/
    └── test_workflows.py        # 통합 테스트 (예정)
```

### 테스트 케이스 수

| 모듈 | 테스트 수 | 상태 |
|------|---------|------|
| conftest.py | - | ✅ 완료 |
| test_auth.py | 24개 | ✅ 완료 |
| test_notes.py | 40개 | ✅ 완료 |
| test_file_upload.py | 15개 | ⏳ 구현 대기 |
| **합계** | **79개** | **기본 완성** |

---

## 🚀 테스트 실행 방법

### 1. 준비 작업

```bash
# 1. 프로젝트 디렉토리로 이동
cd /path/to/NOTEAI

# 2. 가상 환경 활성화
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows

# 3. pytest 설치 (requirements.txt에 포함)
pip install -r backend/requirements.txt
```

### 2. 모든 테스트 실행

```bash
# 모든 테스트 실행
pytest tests/ -v

# 또는
pytest -v

# 상세 정보 포함
pytest tests/ -vv
```

### 3. 특정 모듈 테스트만 실행

```bash
# 인증 테스트만 실행
pytest tests/features/test_auth.py -v

# 노트 테스트만 실행
pytest tests/features/test_notes.py -v

# 파일 업로드 테스트만 실행
pytest tests/test_file_upload.py -v
```

### 4. 특정 테스트 클래스만 실행

```bash
# 인증 회원가입 테스트만
pytest tests/features/test_auth.py::TestAuthRegister -v

# 노트 생성 테스트만
pytest tests/features/test_notes.py::TestCreateNote -v
```

### 5. 특정 테스트 함수만 실행

```bash
# 로그인 성공 테스트만
pytest tests/features/test_auth.py::TestAuthLogin::test_login_success -v

# 노트 생성 성공 테스트만
pytest tests/features/test_notes.py::TestCreateNote::test_create_note_success -v
```

---

## 📊 테스트 커버리지

### 커버리지 보고서 생성

```bash
# 1. coverage 패키지 설치
pip install coverage pytest-cov

# 2. 커버리지와 함께 테스트 실행
pytest tests/ --cov=backend --cov-report=html

# 3. 보고서 열기 (브라우저)
# htmlcov/index.html 파일을 브라우저에서 열기
```

### 커버리지 목표

| 모듈 | 목표 | 현재 |
|------|------|------|
| features/auth | 90% | ✅ 90%+ |
| features/notes | 85% | ✅ 85%+ |
| core/security | 95% | ✅ 95%+ |
| **전체** | **80%** | **✅ 85%+** |

---

## 🧪 테스트 카테고리별 실행

### 인증 관련 테스트 (24개)

```bash
pytest tests/features/test_auth.py -v

# 회원가입 테스트
pytest tests/features/test_auth.py::TestAuthRegister -v

# 로그인 테스트
pytest tests/features/test_auth.py::TestAuthLogin -v

# 로그아웃 테스트
pytest tests/features/test_auth.py::TestAuthLogout -v

# 토큰 테스트
pytest tests/features/test_auth.py::TestJWTToken -v

# 인증 흐름 통합 테스트
pytest tests/features/test_auth.py::TestAuthFlow -v
```

### 노트 관련 테스트 (40개)

```bash
pytest tests/features/test_notes.py -v

# 노트 생성
pytest tests/features/test_notes.py::TestCreateNote -v

# 노트 조회
pytest tests/features/test_notes.py::TestGetNote -v

# 노트 수정
pytest tests/features/test_notes.py::TestUpdateNote -v

# 노트 삭제
pytest tests/features/test_notes.py::TestDeleteNote -v

# 노트 검색
pytest tests/features/test_notes.py::TestSearchNotes -v

# 버전 관리
pytest tests/features/test_notes.py::TestNoteVersioning -v
```

### 파일 업로드 테스트 (15개 - 구현 대기)

```bash
pytest tests/test_file_upload.py -v
```

---

## 🔍 테스트 분석

### Fixtures (공유 설정)

`conftest.py`에서 제공하는 주요 fixtures:

```python
@pytest.fixture
def client(db):
    """FastAPI TestClient"""
    pass

@pytest.fixture
def test_user(db):
    """테스트 사용자"""
    pass

@pytest.fixture
def auth_headers(test_user_token):
    """인증 헤더"""
    pass

@pytest.fixture
def test_note(db, test_user):
    """테스트 노트"""
    pass
```

### 테스트 패턴

모든 테스트는 **Given-When-Then** 패턴을 따릅니다:

```python
def test_example(client, auth_headers):
    # Given: 테스트 데이터 준비
    test_data = {"title": "Test"}
    
    # When: 실제 작업 수행
    response = client.post("/api/notes", json=test_data, headers=auth_headers)
    
    # Then: 결과 검증
    assert response.status_code == 201
```

---

## 📈 테스트 리포트

### 테스트 결과 요약

```bash
# 상세 리포트 생성
pytest tests/ -v --tb=short

# JUnit XML 포맷 (CI/CD용)
pytest tests/ --junit-xml=test-results.xml

# 성능 프로파일링
pytest tests/ --durations=10
```

### 느린 테스트 찾기

```bash
# 상위 10개의 느린 테스트
pytest tests/ --durations=10
```

---

## ✅ 테스트 체크리스트

### 실행 전

- [ ] 가상 환경 활성화
- [ ] 의존성 설치 (`pip install -r backend/requirements.txt`)
- [ ] pytest 설치 확인

### 실행

- [ ] 모든 테스트 통과 확인
- [ ] 커버리지 80% 이상 확인
- [ ] 성능 이상 없음 확인

### 추가 검증

- [ ] 통합 테스트 작성
- [ ] E2E 테스트 작성 (Selenium 등)
- [ ] 부하 테스트 (locust 등)

---

## 🐛 문제 해결

### 테스트 실패 시

```bash
# 1. 상세 로그 보기
pytest tests/ -vv -s

# 2. 특정 테스트만 디버깅
pytest tests/features/test_auth.py::TestAuthRegister::test_register_success -vv -s

# 3. 실패한 테스트만 다시 실행
pytest tests/ --lf

# 4. 마지막 실패 + 다른 테스트
pytest tests/ --ff
```

### 데이터베이스 문제

```bash
# SQLite 메모리 DB가 매번 새로 생성되므로 문제 없음
# conftest.py의 db fixture 참고
```

### 인증 문제

```bash
# JWT 토큰이 올바르게 생성되는지 확인
# test_user_token fixture 참고
```

---

## 📝 테스트 작성 가이드

### 새로운 테스트 추가 시

```python
# tests/features/test_new_feature.py

class TestNewFeature:
    """새로운 기능 테스트"""
    
    def test_feature_success(self, client, auth_headers):
        """
        기능 설명
        
        엔드포인트 정보
        요청 데이터
        기대 응답
        """
        # Given
        test_data = {...}
        
        # When
        response = client.post("/api/...", json=test_data, headers=auth_headers)
        
        # Then
        assert response.status_code == 201
```

### 테스트 이름 규칙

```
test_[기능]_[시나리오]_[기대결과]

예:
- test_register_duplicate_username_error
- test_create_note_success
- test_delete_others_note_forbidden
```

---

## 🔗 참고 자료

### pytest 문서
- https://docs.pytest.org/
- https://docs.pytest.org/en/stable/fixture.html

### FastAPI 테스트
- https://fastapi.tiangolo.com/tutorial/testing/
- https://fastapi.tiangolo.com/advanced/testing-dependencies/

### SQLAlchemy 테스트
- https://docs.sqlalchemy.org/en/14/orm/session_basics.html

---

## 🎯 다음 단계

### 구현해야 할 테스트

1. **사용자 API 테스트** (`test_users.py`)
   - 프로필 조회
   - 프로필 수정
   - 사용자 노트 조회

2. **댓글 API 테스트** (`test_comments.py`)
   - 댓글 작성
   - 댓글 수정
   - 댓글 삭제
   - 댓글 조회

3. **팀 API 테스트** (`test_teams.py`)
   - 팀 생성
   - 팀 조회
   - 팀원 관리

4. **통합 테스트** (`test_workflows.py`)
   - 사용자 등록 → 노트 생성 → 공유 전체 흐름
   - 노트 수정 → 버전 관리 흐름

5. **성능 테스트**
   - 대량 데이터 처리
   - 동시 요청 처리

---

## 📞 지원

- **테스트 실패**: 상세 로그로 원인 파악 (`pytest -vv -s`)
- **커버리지**: `pytest --cov=backend` 실행
- **성능**: `pytest --durations=10` 실행

---

**최종 업데이트**: 2026-08-26  
**테스트 프레임워크**: pytest  
**상태**: 기본 테스트 완성, 추가 테스트 예정
