"""
핵심 설정 모듈
- 환경 변수 관리
- 데이터베이스 연결 정보
- 보안 설정
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # 앱 기본 설정
    APP_NAME: str = "NOTEAI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 서버 설정
    SERVER_HOST: str = "127.0.0.1"
    SERVER_PORT: int = 8000

    # 데이터베이스
    DATABASE_URL: str = "sqlite:///./noteai.db"
    # 프로덕션: postgresql://user:password@localhost/noteai

    # JWT 설정
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 24 * 60  # 24시간

    # 보안
    BCRYPT_ROUNDS: int = 12

    # CORS 설정
    CORS_ORIGINS: list = ["http://localhost:8000", "http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]

    # 파일 업로드
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB
    UPLOAD_DIR: str = "./uploads"

    # AI/NLP 설정
    AI_MODEL_NAME: str = "facebook/bart-large-cnn"  # 요약용 모델
    AI_MAX_TOKENS: int = 150

    # ============ Vault (로컬 노트 스캔) 설정 ============
    # 스캔을 허용할 루트 디렉토리 목록
    # 빈 리스트면 제한 없음(개발용). 프로덕션에서는 반드시 지정할 것
    VAULT_ALLOWED_ROOTS: list = []

    # 단일 노트 파일 최대 크기 (2MB)
    VAULT_MAX_FILE_SIZE: int = 2 * 1024 * 1024

    # ============ Trends (기술 트렌드 수집) 설정 ============
    # 외부 피드 요청 타임아웃 (초)
    TRENDS_TIMEOUT_SECONDS: float = 20.0

    # 외부 요청 시 사용할 User-Agent
    TRENDS_USER_AGENT: str = "NOTEAI/1.0 (+https://github.com/yoohanha/NOTEAI)"

    # 비활성화할 기본 소스 key 목록 (예: ["dev_to"])
    TRENDS_DISABLED_SOURCES: list = []

    # 사용자가 추가한 RSS 피드 URL 목록
    TRENDS_CUSTOM_FEEDS: list = []

    # NewsAPI 연동 (https://newsapi.org) - 키가 없으면 RSS 소스만 사용
    NEWSAPI_KEY: str = ""
    NEWSAPI_LANGUAGE: str = "en"

    class Config:
        env_file = ".env"
        case_sensitive = True


# 전역 설정 인스턴스
settings = Settings()
