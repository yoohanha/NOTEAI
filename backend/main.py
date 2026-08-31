"""
NOTEAI FastAPI 애플리케이션
- 핵심 기능: 노트 작성, AI 요약, 협업
"""

import sys

# Windows 한국어 환경의 콘솔은 기본 코덱이 cp949라서, 시작 로그의 이모지를
# 출력하는 순간 UnicodeEncodeError로 앱 기동 자체가 실패합니다.
# 표준 출력/에러 스트림을 UTF-8로 재설정해 어떤 로케일에서도 뜨도록 합니다.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path
from starlette.types import Scope
import uvicorn

# Core 모듈
from core.config import settings
from core.database import init_db, register_models

# 모델 간 relationship은 문자열로 참조되므로, 앱을 import하는 것만으로
# 모든 모델이 레지스트리에 등록되어 있어야 합니다. startup 이벤트에만
# 의존하면 TestClient나 스크립트가 앱을 import했을 때 매퍼 설정이
# InvalidRequestError로 실패합니다.
register_models()

# Feature 라우터
from features.auth.routes import router as auth_router
from features.notes.routes import router as notes_router
from features.vault.routes import router as vault_router
from features.trends.routes import router as trends_router
from features.monitor.routes import router as monitor_router
from features.graph.routes import router as graph_router
from features.papers.routes import router as papers_router
from features.media.routes import router as media_router

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

# 프론트엔드 정적 파일 서빙
# 주의: StaticFiles를 "/"에 마운트하면 이후 등록되는 라우트를 가리므로,
# 모든 API 라우터를 등록한 뒤 파일 맨 아래에서 마운트합니다.
FRONTEND_PATH = Path(__file__).parent.parent / "frontend"


class NoCacheStaticFiles(StaticFiles):
    """HTML/JS/CSS는 브라우저가 옛 파일을 붙잡지 않도록 캐시를 끕니다."""

    async def get_response(self, path: str, scope: Scope):
        response = await super().get_response(path, scope)
        lowered = (path or "").lower()
        if lowered.endswith((".html", ".js", ".css")) or lowered in ("", "index.html"):
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, max-age=0"
            )
            response.headers["Pragma"] = "no-cache"
        return response


# ============ 라우터 등록 ============
app.include_router(auth_router, prefix="/api")
app.include_router(notes_router, prefix="/api")
app.include_router(vault_router, prefix="/api")    # 로컬 노트 스캔/가져오기
app.include_router(trends_router, prefix="/api")   # 기술 트렌드 수집
app.include_router(monitor_router, prefix="/api")  # 백그라운드 수집 모니터링
app.include_router(graph_router, prefix="/api")    # 토픽 지식 그래프 분석
app.include_router(papers_router, prefix="/api")   # arXiv 논문 검색
app.include_router(media_router, prefix="/api")    # NOTE_3D 이미지/동영상
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

    # 단일 웹 프로세스(Render 등)에서도 대시보드가 워커를 보도록
    # 같은 이벤트 루프에서 수집 루프를 띄웁니다.
    from monitor_worker import start_embedded_worker

    await start_embedded_worker()

    print("✅ 애플리케이션 준비 완료")
    print(f"📝 API 문서: http://{settings.SERVER_HOST}:{settings.SERVER_PORT}/docs")
    print(f"🔗 ReDoc: http://{settings.SERVER_HOST}:{settings.SERVER_PORT}/redoc")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행 - 내장 수집 워커를 정리합니다."""
    from monitor_worker import stop_embedded_worker

    await stop_embedded_worker()
    print("👋 애플리케이션 종료 중...")


# ============ API 루트 경로 ============
# "/"는 프론트엔드 대시보드(frontend/index.html)가 사용하므로
# API 안내는 "/api"로 제공합니다.
@app.get("/api")
async def api_root() -> dict:
    """API 루트 - 서비스 정보 안내"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
    }


# ============ 정적 파일 마운트 ============
# 반드시 모든 API 라우트 등록 이후에 위치해야 합니다.
# "/"에 마운트하면 이 시점 이후의 경로 매칭을 StaticFiles가 가져가기 때문입니다.
if FRONTEND_PATH.exists():
    app.mount(
        "/",
        NoCacheStaticFiles(directory=str(FRONTEND_PATH), html=True),
        name="static",
    )


# ============ 메인 실행 ============
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
