"""
Graph API 엔드포인트

- POST /api/graph/analyze     토픽 분석 (요약 + 자동 태깅 + 지식 그래프)
- GET  /api/graph/topics      추천 토픽 목록
- POST /api/graph/apply-tags  제안 태그를 내 노트에 적용
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from features.auth.deps import get_current_user
from features.auth.models import User
from features.graph.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ApplyTagsRequest,
    ApplyTagsResponse,
    TopicSuggestion,
)
from features.graph.service import graph_service

# 라우터 생성
router = APIRouter(prefix="/graph", tags=["graph"])


@router.post("/analyze", response_model=dict)
async def analyze_topic(
    request: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    토픽을 분석해 지식 그래프를 생성합니다.

    내 노트와 수집된 기술 트렌드에서 토픽 관련 문헌을 찾아
    핵심 요약, 자동 태그 후보, Node/Edge 그래프를 반환합니다.

    요청 예시:
        {
            "topic": "transformer",
            "limit": 30,
            "sources": ["notes", "trends"],
            "max_keywords": 15
        }

    응답 예시:
        {
            "status": 200,
            "data": {
                "topic": "transformer",
                "summary": "트랜스포머는 attention 메커니즘을 ...",
                "document_count": 12,
                "keywords": [{"word": "attention", "score": 0.91, "doc_count": 7}],
                "suggested_tags": ["attention", "llm"],
                "documents": [...],
                "graph": {"nodes": [...], "edges": [...]},
                "analyzed_at": "2026-08-26T15:40:00"
            },
            "message": "12건의 문헌에서 15개 키워드를 추출했습니다"
        }

    Args:
        request: 분석 옵션 (토픽/문헌 상한/소스/키워드 상한)
        current_user: 현재 사용자 (노트 접근 범위 판단에 사용)
        db: 데이터베이스 세션

    Returns:
        분석 결과. 관련 문헌이 없으면 document_count가 0인 빈 결과.

    Raises:
        HTTPException: 분석 중 오류가 발생하면 500
    """
    try:
        result = graph_service.analyze(
            db,
            topic=request.topic,
            user=current_user,
            limit=request.limit,
            sources=request.sources,
            max_keywords=request.max_keywords,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"토픽 분석 실패: {exc}",
        )

    # 문헌을 못 찾은 경우에도 200으로 응답하고 안내 문구만 다르게 전달합니다.
    # (검색 결과 없음은 오류가 아니라 정상적인 결과이기 때문)
    if result["document_count"] == 0:
        message = f"'{request.topic}' 과(와) 관련된 문헌을 찾지 못했습니다"
    else:
        message = (
            f"{result['document_count']}건의 문헌에서 "
            f"{len(result['keywords'])}개 키워드를 추출했습니다"
        )

    return {
        "status": 200,
        "data": AnalyzeResponse(**result).model_dump(mode="json"),
        "message": message,
    }


@router.get("/topics", response_model=dict)
async def suggest_topics(
    limit: int = Query(12, ge=1, le=30, description="추천 토픽 개수"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    보유 데이터에서 자주 등장하는 단어를 토픽 후보로 제안합니다.

    분석 화면의 빠른 선택 칩(chip) UI에 사용합니다.

    응답 예시:
        {
            "status": 200,
            "data": {"topics": [{"topic": "llm", "doc_count": 14}], "total": 12},
            "message": "12개 추천 토픽"
        }

    Args:
        limit: 반환할 토픽 개수
        current_user: 현재 사용자
        db: 데이터베이스 세션

    Returns:
        추천 토픽 목록
    """
    topics = graph_service.suggest_topics(db, current_user, limit=limit)

    return {
        "status": 200,
        "data": {
            "topics": [TopicSuggestion(**topic).model_dump() for topic in topics],
            "total": len(topics),
        },
        "message": f"{len(topics)}개 추천 토픽",
    }


@router.post("/apply-tags", response_model=dict)
async def apply_tags(
    request: ApplyTagsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    분석에서 제안된 태그를 내 노트에 병합 적용합니다.

    기존 태그는 유지하고 새 태그만 추가합니다.
    본인 소유가 아닌 노트는 건너뛰고 skipped_note_ids로 알려줍니다.

    요청 예시:
        {"note_ids": [3, 7], "tags": ["attention", "llm"]}

    응답 예시:
        {
            "status": 200,
            "data": {
                "updated_note_ids": [3],
                "skipped_note_ids": [7],
                "applied_tags": ["attention", "llm"]
            },
            "message": "1개 노트에 태그를 적용했습니다"
        }

    Args:
        request: 대상 노트 ID와 적용할 태그
        current_user: 현재 사용자 (소유자 검증)
        db: 데이터베이스 세션

    Returns:
        적용 결과

    Raises:
        HTTPException: 저장 실패 시 500
    """
    try:
        result = graph_service.apply_tags(
            db,
            user=current_user,
            note_ids=request.note_ids,
            tags=request.tags,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"태그 적용 실패: {exc}",
        )

    updated_count = len(result["updated_note_ids"])
    skipped_count = len(result["skipped_note_ids"])

    message = f"{updated_count}개 노트에 태그를 적용했습니다"
    if skipped_count:
        message += f" ({skipped_count}개는 접근 권한이 없어 건너뜀)"

    return {
        "status": 200,
        "data": ApplyTagsResponse(**result).model_dump(),
        "message": message,
    }
