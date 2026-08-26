# 🕸️ 토픽 지식 그래프 분석 기능 - 기획서

> NOTEAI 업그레이드 계획 · 작성일 2026-08-26 · Phase 1 (Planner) 산출물

---

## 📌 1. 기능 개요

사용자가 **토픽(키워드)** 을 입력하면, 시스템이 보유한 지식 자산
(내 노트 + 수집된 기술 트렌드)을 분석해 다음을 반환·시각화한다.

| 산출 | 설명 |
|------|------|
| 📝 핵심 요약 | 관련 문헌에서 추출한 대표 문장 기반 요약 |
| 🏷️ 자동 태깅 | TF-IDF 상위 키워드를 태그 후보로 제안 · 노트에 일괄 적용 |
| 🕸️ 지식 그래프 | 토픽·문헌·키워드를 Node/Edge JSON으로 반환 |

### 설계 원칙

1. **새 의존성 0개** — `requirements.txt`에 `torch`/`transformers`가 선언돼 있으나
   실제 설치 여부가 환경마다 다르다. 분석기는 **Python 표준 라이브러리만** 사용해
   어떤 환경에서도 즉시 동작하게 한다.
2. **새 테이블 0개** — 분석은 요청 시점에 계산하는 **stateless** 연산.
   마이그레이션 부담과 캐시 무효화 문제를 피한다.
3. **기존 아키텍처 준수** — `features/<name>/{models,schemas,routes,service}.py`
   Feature-Based 구조와 `{status, data, message}` 응답 규약을 그대로 따른다.

---

## 🏗️ 2. 아키텍처

### 2.1 데이터 흐름

```
[사용자] 토픽 입력 "transformer"
    │
    ▼
POST /api/graph/analyze   { topic, limit, sources, min_score }
    │
    ▼
┌─────────────────── graph/service.py ───────────────────┐
│                                                         │
│  ① 문헌 수집(collect)                                    │
│     ├─ notes        : 내 노트 + 공개 노트 (title/content/tags)│
│     └─ trend_items  : 수집된 트렌드 (title/summary/tags)     │
│                                                         │
│  ② 관련도 산출(score)  ── analyzer.score_documents()      │
│     토픽 토큰과의 매칭 가중치                              │
│     제목 3.0 · 태그 2.0 · 본문 1.0                        │
│                                                         │
│  ③ 키워드 추출(keywords) ── analyzer.extract_keywords()   │
│     TF-IDF (문서빈도 역가중) + 한/영 불용어 제거            │
│                                                         │
│  ④ 요약 생성(summary) ── analyzer.summarize()             │
│     키워드 밀도가 높은 상위 문장 추출 (extractive)          │
│                                                         │
│  ⑤ 그래프 구성(build_graph)                               │
│     Node: topic / note / trend / keyword                 │
│     Edge: relevant / tagged / co_occurs                  │
└─────────────────────────────────────────────────────────┘
    │
    ▼
{ status, data: { summary, keywords, graph{nodes,edges}, documents }, message }
    │
    ▼
[프론트] Cytoscape.js(CDN) 로 force-directed 렌더링
```

### 2.2 그래프 스키마

**Node**

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | string | `topic` / `note:12` / `trend:34` / `kw:llm` |
| `label` | string | 화면 표시 텍스트 |
| `type` | enum | `topic` \| `note` \| `trend` \| `keyword` |
| `weight` | float | 0.0~1.0 정규화 가중치 → 노드 크기 |
| `meta` | object | `url`, `source`, `category`, `published_at` 등 |

**Edge**

| 필드 | 타입 | 설명 |
|------|------|------|
| `source` / `target` | string | Node id |
| `relation` | enum | `relevant`(토픽↔문헌) \| `tagged`(문헌↔키워드) \| `co_occurs`(키워드↔키워드) |
| `weight` | float | 0.0~1.0 → 엣지 두께 |

---

## 📂 3. 파일 구조

```
backend/features/graph/          ← 🆕 신규 feature
├── __init__.py
├── analyzer.py                  # 순수 파이썬 NLP 엔진 (토큰화/TF-IDF/요약/공출현)
├── schemas.py                   # Pydantic 요청·응답 모델
├── service.py                   # 문헌 수집 → 분석 → 그래프 조립
└── routes.py                    # /api/graph/*

backend/main.py                  # ✏️ graph_router 등록

frontend/
├── index.html                   # ✏️ 상단 탭 3종 + 큐레이션/그래프 화면 추가
├── script.js                    # ✏️ 뷰 라우팅 + 큐레이션/그래프 로직
└── style.css                    # ✏️ 그래프 캔버스 스타일

tests/features/test_graph.py     # 🆕 분석기·엔드포인트 테스트
```

---

## 🛣️ 4. API 설계

### `POST /api/graph/analyze` — 토픽 분석 (인증 필요)

**요청**
```json
{
  "topic": "transformer",
  "limit": 30,
  "sources": ["notes", "trends"],
  "max_keywords": 15
}
```

**응답**
```json
{
  "status": 200,
  "data": {
    "topic": "transformer",
    "summary": "트랜스포머 아키텍처는 ...",
    "document_count": 12,
    "keywords": [{ "word": "attention", "score": 0.91, "doc_count": 7 }],
    "suggested_tags": ["attention", "llm", "nlp"],
    "documents": [
      { "id": "trend:34", "type": "trend", "title": "...", "score": 0.83, "url": "..." }
    ],
    "graph": { "nodes": [], "edges": [] },
    "analyzed_at": "2026-08-26T15:40:00"
  },
  "message": "12건의 문헌에서 15개 키워드를 추출했습니다"
}
```

### `GET /api/graph/topics` — 추천 토픽 (인증 필요)
보유 데이터에서 빈도가 높은 키워드를 토픽 후보로 제안 (입력창 자동완성용).

### `POST /api/graph/apply-tags` — 자동 태깅 적용 (인증 필요)
분석에서 나온 `suggested_tags`를 **본인 소유 노트에만** 병합 저장.

---

## ✅ 5. 구현 체크리스트

### Phase 2 — Backend
- [ ] `analyzer.py` : 토큰화(한글/영문/숫자), 한·영 불용어, TF-IDF, 추출 요약, 공출현 행렬
- [ ] `schemas.py` : `AnalyzeRequest`(topic 1~100자 검증) / `GraphNode` / `GraphEdge` / `AnalyzeResponse`
- [ ] `service.py` : 노트·트렌드 수집, 관련도 점수, 그래프 조립
- [ ] `routes.py` : analyze / topics / apply-tags
- [ ] `main.py` : 라우터 등록
- [ ] 모든 주석 한국어 + docstring

### Phase 3 — Frontend
- [ ] 상단 탭 네비게이션 (📡 수집 모니터 · 📚 노트 큐레이션 · 🕸️ 토픽 지식 그래프)
- [ ] 탭별 폴링 제어 — 모니터 탭에서만 자동 새로고침 동작
- [ ] 큐레이션 화면: 트렌드 검색·필터·노트 저장, 내 노트 목록
- [ ] 그래프 화면: 토픽 입력 → 요약 카드 · 키워드 칩 · Cytoscape 캔버스 · 문헌 목록
- [ ] CDN 로드 실패 시 텍스트 폴백 렌더링
- [ ] 로딩/빈 상태/에러 피드백, 반응형, 이모지 활용

### 검증
- [ ] `pytest` 전체 통과
- [ ] 실제 서버 기동 후 엔드포인트 200 확인

---

## ⚠️ 6. 위험 요소 및 대응

| 위험 | 영향 | 대응 |
|------|------|------|
| CDN(Cytoscape) 로드 실패 | 그래프 영역 공백 | 로드 실패 감지 → 인접 리스트 텍스트 폴백 |
| 노드 과다로 렌더링 지연 | 브라우저 멈춤 | 문헌 `limit` 상한 50, 키워드 상한 30, 엣지 가중치 하한 컷 |
| 한글 형태소 분석기 부재 | 조사 포함 토큰 | 어미·조사 접미 제거 휴리스틱 + 불용어 사전으로 완화 |
| 데이터 부족(노트 0건) | 빈 그래프 | 트렌드 80건을 기본 소스로 사용, 빈 결과 시 안내 문구 |
| `apply-tags` 오적용 | 남의 노트 오염 | `user_id == current_user.id` 조건 강제, 태그 병합(덮어쓰기 금지) |

---

**문서 버전**: 1.0
**연관 문서**: `PLAN.md`, `CLAUDE.md`, `docs/api.md`
