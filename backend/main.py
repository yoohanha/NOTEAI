"""
NOTEAI FastAPI 애플리케이션
- 핵심 기능: 노트 작성, AI 요약, 협업
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path
import uvicorn

# Core 모듈
from core.config import settings
from core.database import init_db

# Feature 라우터
from features.auth.routes import router as auth_router
from features.notes.routes import router as notes_router
from features.vault.routes import router as vault_router
from features.trends.routes import router as trends_router

# FastAPI 앱 초기화
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI 기반 학습/연구 노트 자동 큐레이션 서비스",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# 프론트엔드 정적 파일 서빙 (선택)
# frontend_path = Path(__file__).parent.parent / "frontend"
# if frontend_path.exists():
#     app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="static")


# ============ 라우터 등록 ============
app.include_router(auth_router, prefix="/api")
app.include_router(notes_router, prefix="/api")
app.include_router(vault_router, prefix="/api")    # 로컬 노트 스캔/가져오기
app.include_router(trends_router, prefix="/api")   # 기술 트렌드 수집
# 추가 라우터: users, comments, teams, ai


# ============ 헬스 체크 ============
@app.get("/api/health")
async def health_check() -> dict:
    """
    애플리케이션 헬스 체크

    Returns:
        상태 정보
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# ============ 에러 처리 ============
# 주의: 예외 핸들러는 반드시 Response 객체를 반환해야 합니다.
# dict를 그대로 반환하면 Starlette이 이를 ASGI 앱으로 호출하려다
# "'dict' object is not callable" 오류가 발생합니다.
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """HTTP 예외 처리 - 표준 응답 형식으로 변환"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "detail": exc.detail,
            "message": "Error occurred",
        },
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """예상하지 못한 예외 처리 - 500 응답"""
    return JSONResponse(
        status_code=500,
        content={
            "status": 500,
            "detail": str(exc),
            "message": "Internal server error",
        },
    )


# ============ 시작 이벤트 ============
@app.on_event("startup")
async def startup_event():
    """
    애플리케이션 시작 시 실행
    - 데이터베이스 초기화
    """
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 시작 중...")

    # 데이터베이스 초기화
    init_db()

    print("✅ 애플리케이션 준비 완료")
    print(f"📝 API 문서: http://{settings.SERVER_HOST}:{settings.SERVER_PORT}/docs")
    print(f"🔗 ReDoc: http://{settings.SERVER_HOST}:{settings.SERVER_PORT}/redoc")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    print("👋 애플리케이션 종료 중...")


# ============ 루트 경로 ============
@app.get("/")
async def root() -> dict:
    """루트 경로"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
    }


# ============ 메인 실행 ============
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
