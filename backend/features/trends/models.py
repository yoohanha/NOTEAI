"""
트렌드 관련 데이터 모델
- TrendItem: 외부 소스에서 수집한 기술 트렌드 항목
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
)

from core.database import Base


class TrendItem(Base):
    """수집된 기술 트렌드 항목"""

    __tablename__ = "trend_items"

    # 기본 정보
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text)

    # 원문 링크 (같은 기사를 중복 저장하지 않도록 unique)
    url = Column(String(1000), nullable=False, unique=True, index=True)

    # URL의 SHA-256 해시 - 긴 URL도 인덱스 길이 제한 없이 조회 가능
    url_hash = Column(String(64), nullable=False, unique=True, index=True)

    # 출처
    source_key = Column(String(50), nullable=False, index=True)
    source_name = Column(String(150))
    category = Column(String(50), index=True)
    author = Column(String(100))
    image_url = Column(String(1000))

    # 분류 태그 (피드가 제공한 category 목록)
    tags = Column(JSON, default=[])

    # 노트로 저장했는지 여부 (대시보드 필터용)
    is_saved = Column(Boolean, default=False, index=True)

    # 타임스탬프
    published_at = Column(DateTime, index=True)  # 원문 발행 시각
    fetched_at = Column(DateTime, default=datetime.utcnow, index=True)  # 수집 시각

    def __repr__(self):
        return f"<TrendItem(id={self.id}, source={self.source_key}, title={self.title[:30]})>"
