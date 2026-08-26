"""
모니터링 관련 데이터 모델
- CollectionRun: 수집 워커의 사이클별 실행 이력
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text

from core.database import Base


class CollectionRun(Base):
    """
    백그라운드 수집 워커의 1회 실행(사이클) 기록

    대시보드가 이 테이블을 읽어 수집기 건강 상태를 표시하고,
    자가 진단 루틴이 실패 패턴을 분석하는 근거로 사용합니다.
    """

    __tablename__ = "collection_runs"

    id = Column(Integer, primary_key=True, index=True)

    # 실행 결과: success | partial | failed
    # partial = 일부 소스만 실패했으나 수집 자체는 성공한 경우
    status = Column(String(20), nullable=False, index=True)

    # 수집 통계
    fetched = Column(Integer, default=0)      # 외부에서 가져온 총 항목 수
    saved = Column(Integer, default=0)        # 신규 저장 수
    duplicates = Column(Integer, default=0)   # 중복으로 건너뛴 수

    # 사용한 소스와 실패한 소스
    sources_used = Column(JSON, default=[])
    errors = Column(JSON, default=[])

    # 실패 시 예외 메시지 (사이클 전체가 실패한 경우)
    error_message = Column(Text)

    # 소요 시간 (초)
    duration_seconds = Column(Float, default=0.0)

    # 이 사이클 시점의 연속 실패 횟수 (백오프 판단 근거)
    consecutive_failures = Column(Integer, default=0)

    # 실행 시각
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    finished_at = Column(DateTime)

    def __repr__(self):
        return (
            f"<CollectionRun(id={self.id}, status={self.status}, "
            f"saved={self.saved}, started_at={self.started_at})>"
        )
