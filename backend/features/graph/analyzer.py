"""
토픽 분석 엔진 (순수 파이썬 구현)

외부 NLP 라이브러리(torch/transformers/nltk)에 의존하지 않고
표준 라이브러리만으로 다음을 수행합니다.

- 마크다운/HTML 정제 및 토큰화 (한글 + 영문 + 숫자)
- 한국어 조사 제거 휴리스틱
- TF-IDF 기반 키워드 추출
- 추출 요약(extractive summarization)
- 키워드 공출현(co-occurrence) 계산

무거운 모델을 쓰지 않는 대신, 어떤 실행 환경에서도 추가 설치 없이
즉시 동작하고 응답 시간이 수십 밀리초 수준으로 유지됩니다.
"""

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence, Tuple

# ============ 상수 ============

# 토큰 패턴
# - 영문/기술용어: 첫 글자는 알파벳, 이후 영숫자와 + # . _ - 허용 (예: c++, .net, gpt-4)
# - 한글: 2글자 이상 (1글자 한글은 대부분 조사/의존명사라 노이즈)
# - 숫자: 4자리 이상만 (연도 등 의미 있는 값만 남김)
TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9+#._\-]*|[가-힣]{2,}|\d{4,}")

# 문장 분리 패턴 - 종결 부호 뒤 공백 또는 줄바꿈
SENTENCE_PATTERN = re.compile(r"(?<=[.!?。？！])\s+|\n{1,}")

# 정제 대상 패턴 (순서대로 적용)
CODE_BLOCK_PATTERN = re.compile(r"```.*?```", re.DOTALL)   # 코드 펜스
INLINE_CODE_PATTERN = re.compile(r"`[^`]*`")               # 인라인 코드
MD_LINK_PATTERN = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")   # [텍스트](url) -> 텍스트
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")                  # HTML 태그
URL_PATTERN = re.compile(r"https?://\S+")                  # 원시 URL
MD_SYMBOL_PATTERN = re.compile(r"[#*_>~|`]+")              # 마크다운 기호

# 한국어 조사/어미 목록
# 형태소 분석기 없이 쓰는 휴리스틱이라, 반드시 "긴 것부터" 검사해야 합니다.
# 예를 들어 "에"를 먼저 보면 "에서는"이 "에"만 떨어져 나가 "서는"이 남습니다.
# 아래에서 길이 내림차순으로 정렬해 두므로 추가 시 순서를 신경 쓰지 않아도 됩니다.
_RAW_PARTICLES = (
    # 복합 조사
    "에서는", "으로는", "에게는", "에서도", "으로도", "이라는", "라는",
    "에서", "에게", "한테", "으로", "부터", "까지", "처럼", "보다", "마다",
    "이나", "이란", "라고", "이고", "이며",
    # 서술형 어미 - "사용한다" -> "사용" 처럼 어간만 남겨 불용어 판정이 되게 함
    "습니다", "합니다", "입니다", "됩니다",
    "하며", "하고", "한다", "했다", "된다", "됐다", "이다", "하다", "되다",
    # 단일 조사
    "은", "는", "이", "가", "을", "를", "의", "에", "와", "과", "도", "만", "로",
)

KOREAN_PARTICLES = tuple(sorted(_RAW_PARTICLES, key=len, reverse=True))

# 한국어 불용어
KOREAN_STOPWORDS = {
    "그리고", "그러나", "하지만", "또한", "때문", "위해", "통해", "대한", "대해",
    "관련", "경우", "이번", "지난", "최근", "다양", "다음", "이런", "저런", "그런",
    "이것", "그것", "저것", "여기", "거기", "저기", "우리", "저희", "당신",
    "무엇", "어떤", "어떻게", "이러한", "그러한", "가능", "필요", "중요", "생각",
    "사용", "이용", "제공", "발표", "공개", "기사", "내용", "정도", "수준",
    "있다", "없다", "한다", "된다", "됩니다", "합니다", "있습니다", "없습니다",
    "하는", "되는", "있는", "없는", "같은", "많은", "새로운", "지금", "오늘",
}

# 영어 불용어
ENGLISH_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "than", "that", "this",
    "these", "those", "is", "are", "was", "were", "be", "been", "being", "am",
    "do", "does", "did", "doing", "have", "has", "had", "having", "will", "would",
    "shall", "should", "can", "could", "may", "might", "must", "of", "in", "on",
    "at", "to", "for", "with", "by", "from", "up", "down", "out", "off", "over",
    "under", "again", "further", "as", "it", "its", "he", "she", "they", "them",
    "we", "you", "i", "his", "her", "their", "our", "your", "my", "me", "him",
    "us", "who", "whom", "which", "what", "when", "where", "why", "how", "all",
    "any", "both", "each", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "too", "very", "just", "also",
    "into", "about", "after", "before", "between", "during", "while", "there",
    "here", "new", "news", "said", "says", "one", "two", "get", "got", "make",
    "made", "use", "used", "using", "via", "vs", "per", "com", "www", "http",
    "https", "html", "amp", "read", "click", "post", "posts", "article",
    "now", "much", "many", "way", "ways", "thing", "things", "time", "times",
    "day", "days", "week", "year", "years", "today", "first", "last", "next",
    "back", "good", "best", "great", "like", "want", "need", "know", "see",
    "look", "going", "come", "take", "work", "works", "working", "people",
    "available", "announce", "announced", "announcing", "announcement",
    "show", "still", "even", "well", "much", "lot", "long", "big", "small",
}

# RSS/뉴스 피드 보일러플레이트
# 피드 요약문에 기계적으로 붙는 문구(예: "Comments URL", "Points: 12")와
# arXiv 분류 코드는 문헌의 내용을 설명하지 않으므로 키워드에서 제외합니다.
FEED_STOPWORDS = {
    "comments", "comment", "url", "points", "submitted", "hacker", "discuss",
    "discussion", "story", "link", "links", "feed", "rss", "subscribe",
    "newsletter", "blog", "source", "sources", "author", "published",
    # arXiv 카테고리 코드
    "cs.ai", "cs.lg", "cs.cl", "cs.cv", "cs.ne", "cs.ro", "cs.se", "cs.cr",
    "cs.db", "cs.dc", "cs.ir", "cs.hc", "stat.ml", "arxiv",
    # arXiv 초록 피드가 매 항목에 붙이는 상용구
    "abstract", "type", "v1", "v2", "v3", "v4", "v5",
}

# 순수 숫자 토큰 판별 - 논문 ID(2608...)나 버전 숫자가 키워드로 올라오는 것을 막습니다.
DIGITS_ONLY_PATTERN = re.compile(r"^\d+$")

STOPWORDS = KOREAN_STOPWORDS | ENGLISH_STOPWORDS | FEED_STOPWORDS

# 필드별 가중치 - 제목에 등장한 단어가 본문보다 중요
FIELD_WEIGHTS = {"title": 3.0, "tags": 2.0, "body": 1.0}


# ============ 데이터 구조 ============


@dataclass
class SourceDocument:
    """
    분석 대상 문헌 하나를 표현합니다.

    Attributes:
        id: 그래프 노드 id (예: "note:12", "trend:34")
        doc_type: 문헌 종류 ("note" | "trend")
        title: 제목
        body: 본문 (마크다운/HTML 가능)
        tags: 문헌에 이미 붙어 있는 태그 목록
        meta: 화면 표시용 부가 정보 (url, source, published_at 등)
    """

    id: str
    doc_type: str
    title: str
    body: str = ""
    tags: List[str] = field(default_factory=list)
    meta: Dict = field(default_factory=dict)


@dataclass
class ScoredDocument:
    """
    관련도 점수와 토큰 정보가 계산된 문헌입니다.

    Attributes:
        source: 원본 문헌
        score: 토픽 관련도 (0.0 이상, 정규화 전)
        tokens: 가중치가 반영된 토큰 카운터
        matched: 토픽 토큰 중 실제로 매칭된 단어 목록
    """

    source: SourceDocument
    score: float
    tokens: Counter
    matched: List[str] = field(default_factory=list)


# ============ 텍스트 정제 및 토큰화 ============


def clean_text(text: str) -> str:
    """
    마크다운/HTML 잡음을 제거해 순수 문장만 남깁니다.

    Args:
        text: 원본 텍스트

    Returns:
        정제된 텍스트
    """
    if not text:
        return ""

    cleaned = CODE_BLOCK_PATTERN.sub(" ", text)
    cleaned = INLINE_CODE_PATTERN.sub(" ", cleaned)
    cleaned = MD_LINK_PATTERN.sub(r"\1", cleaned)   # 링크는 표시 텍스트만 남김
    cleaned = HTML_TAG_PATTERN.sub(" ", cleaned)
    cleaned = URL_PATTERN.sub(" ", cleaned)
    cleaned = MD_SYMBOL_PATTERN.sub(" ", cleaned)

    # 연속 공백 축약
    return re.sub(r"\s+", " ", cleaned).strip()


def strip_particle(token: str) -> str:
    """
    한글 토큰 끝의 조사를 제거합니다.

    형태소 분석기 없이 쓰는 휴리스틱이므로, 제거 후 2글자 미만이 되면
    과도한 절삭으로 보고 원본을 그대로 둡니다.

    Args:
        token: 한글 토큰

    Returns:
        조사가 제거된 토큰 (예: "모델에서는" -> "모델")
    """
    for particle in KOREAN_PARTICLES:
        if token.endswith(particle):
            stripped = token[: -len(particle)]

            # 2글자 이상 남을 때만 조사로 인정
            if len(stripped) >= 2:
                return stripped

    return token


def normalize_token(token: str) -> str:
    """
    토큰을 비교 가능한 형태로 정규화합니다.

    Args:
        token: 원시 토큰

    Returns:
        정규화된 토큰 (불용어/짧은 토큰이면 빈 문자열)
    """
    # 영문은 소문자로 통일.
    # 오른쪽 구두점은 "._-"만 떼어냅니다. "+"와 "#"은 c++, c#, f# 처럼
    # 언어 이름의 일부라서 함께 지우면 토큰이 "c" 하나로 뭉개집니다.
    normalized = token.lower().lstrip("._-+#").rstrip("._-")

    if not normalized:
        return ""

    # 조사를 떼기 전에 먼저 불용어인지 확인합니다.
    # "하지만"은 조사 "만"을 먼저 떼면 "하지"가 되어 불용어 판정을 빠져나갑니다.
    if normalized in STOPWORDS:
        return ""

    # 한글이면 조사 제거
    if re.fullmatch(r"[가-힣]+", normalized):
        normalized = strip_particle(normalized)

    # 1글자 토큰과 (조사를 뗀 뒤의) 불용어는 제외
    if len(normalized) < 2 or normalized in STOPWORDS:
        return ""

    return normalized


def tokenize(text: str) -> List[str]:
    """
    텍스트를 정제·토큰화·정규화해 의미 있는 단어 목록을 만듭니다.

    Args:
        text: 원본 텍스트

    Returns:
        정규화된 토큰 목록
        (예: "Transformer 모델은 Attention을 쓴다" -> ['transformer', '모델', 'attention'])
    """
    cleaned = clean_text(text)
    tokens = []

    for raw in TOKEN_PATTERN.findall(cleaned):
        normalized = normalize_token(raw)

        if normalized:
            tokens.append(normalized)

    return tokens


def build_weighted_tokens(document: SourceDocument) -> Counter:
    """
    문헌의 제목/태그/본문을 각기 다른 가중치로 합산한 토큰 카운터를 만듭니다.

    제목과 태그는 작성자가 의도적으로 고른 단어이므로 본문보다 높게 칩니다.

    Args:
        document: 원본 문헌

    Returns:
        토큰 -> 가중 빈도 Counter
    """
    weighted: Counter = Counter()

    for token in tokenize(document.title):
        weighted[token] += FIELD_WEIGHTS["title"]

    for tag in document.tags or []:
        for token in tokenize(str(tag)):
            weighted[token] += FIELD_WEIGHTS["tags"]

    for token in tokenize(document.body):
        weighted[token] += FIELD_WEIGHTS["body"]

    return weighted


# ============ 관련도 점수 ============


def score_documents(
    topic: str,
    documents: Sequence[SourceDocument],
) -> List[ScoredDocument]:
    """
    토픽과의 관련도를 기준으로 문헌에 점수를 매깁니다.

    토픽 토큰이 하나도 등장하지 않는 문헌은 결과에서 제외합니다.
    토픽이 여러 단어면, 더 많은 단어가 겹칠수록 가산점을 줍니다.

    Args:
        topic: 사용자가 입력한 토픽 문자열
        documents: 후보 문헌 목록

    Returns:
        점수 내림차순으로 정렬된 ScoredDocument 목록
    """
    topic_tokens = tokenize(topic)

    # 토픽이 전부 불용어라면 원문 소문자 자체를 토큰으로 사용
    if not topic_tokens:
        fallback = topic.strip().lower()
        topic_tokens = [fallback] if fallback else []

    if not topic_tokens:
        return []

    unique_topic_tokens = set(topic_tokens)
    scored: List[ScoredDocument] = []

    for document in documents:
        tokens = build_weighted_tokens(document)

        matched = [t for t in unique_topic_tokens if tokens.get(t)]

        # 완전 일치 토큰이 없으면 부분 문자열 매칭으로 한 번 더 시도
        # (예: 토픽 "llm" ↔ 문서 토큰 "llms")
        partial_score = 0.0
        if not matched:
            for topic_token in unique_topic_tokens:
                for token, weight in tokens.items():
                    if topic_token in token or token in topic_token:
                        partial_score += weight * 0.5
                        matched.append(topic_token)
                        break

        if not matched:
            continue

        base = sum(tokens.get(t, 0.0) for t in unique_topic_tokens) + partial_score

        # 토픽 단어 커버리지 보너스 - 여러 단어가 모두 등장하면 더 관련성 높음
        coverage = len(set(matched)) / len(unique_topic_tokens)
        score = base * (0.5 + 0.5 * coverage)

        scored.append(
            ScoredDocument(
                source=document,
                score=round(score, 4),
                tokens=tokens,
                matched=sorted(set(matched)),
            )
        )

    scored.sort(key=lambda d: d.score, reverse=True)

    return scored


# ============ 키워드 추출 (TF-IDF) ============


def extract_keywords(
    scored_documents: Sequence[ScoredDocument],
    top_n: int = 15,
    exclude: Iterable[str] = (),
) -> List[Dict]:
    """
    TF-IDF로 문헌 집합의 핵심 키워드를 추출합니다.

    - TF: 문헌 내 가중 빈도를 최대 빈도로 나눈 정규화 값 (긴 문서 편향 제거)
    - IDF: log(N / (1 + df)) + 1 (모든 문서에 나오는 흔한 단어를 감점)

    Args:
        scored_documents: 점수가 매겨진 문헌 목록
        top_n: 반환할 키워드 개수
        exclude: 결과에서 제외할 단어 (보통 토픽 자신)

    Returns:
        [{"word", "score", "doc_count"}] 형태의 목록 (score는 0~1 정규화)
    """
    if not scored_documents:
        return []

    total_docs = len(scored_documents)
    excluded = {str(e).lower() for e in exclude}

    # 문서 빈도(df) 집계
    doc_frequency: Counter = Counter()
    for doc in scored_documents:
        for token in doc.tokens:
            doc_frequency[token] += 1

    # TF-IDF 누적
    accumulated: Dict[str, float] = defaultdict(float)

    for doc in scored_documents:
        if not doc.tokens:
            continue

        max_freq = max(doc.tokens.values())

        for token, freq in doc.tokens.items():
            # 토픽 자신과 순수 숫자는 키워드로서 정보량이 없음
            # (검색 매칭에는 여전히 쓰이므로 토큰 자체는 제거하지 않습니다)
            if token in excluded or DIGITS_ONLY_PATTERN.match(token):
                continue

            tf = freq / max_freq
            idf = math.log(total_docs / (1 + doc_frequency[token])) + 1.0
            accumulated[token] += tf * idf

    if not accumulated:
        return []

    ranked = sorted(accumulated.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    max_score = ranked[0][1] or 1.0

    return [
        {
            "word": word,
            "score": round(score / max_score, 4),
            "doc_count": doc_frequency[word],
        }
        for word, score in ranked
    ]


# ============ 추출 요약 ============


def summarize(
    scored_documents: Sequence[ScoredDocument],
    keywords: Sequence[Dict],
    max_sentences: int = 3,
) -> str:
    """
    상위 문헌에서 키워드 밀도가 높은 문장을 골라 요약문을 만듭니다.

    생성 요약(abstractive)이 아니라 원문 문장을 그대로 뽑는 추출 요약이므로,
    사실 왜곡 없이 근거 문장을 보여줄 수 있습니다.

    Args:
        scored_documents: 점수가 매겨진 문헌 목록 (상위 문헌만 사용)
        keywords: extract_keywords 결과
        max_sentences: 요약에 포함할 문장 수

    Returns:
        요약 문자열 (문장을 공백으로 이어붙임)
    """
    if not scored_documents:
        return ""

    keyword_weights = {kw["word"]: kw["score"] for kw in keywords}

    candidates: List[Tuple[float, str]] = []

    # 상위 8개 문헌까지만 훑어도 대표 문장은 충분히 확보됨
    for doc in scored_documents[:8]:
        text = clean_text(f"{doc.source.title}. {doc.source.body}")

        for sentence in SENTENCE_PATTERN.split(text):
            sentence = sentence.strip()

            # 너무 짧거나 지나치게 긴 문장은 요약문으로 부적합
            if not (20 <= len(sentence) <= 300):
                continue

            tokens = tokenize(sentence)

            if not tokens:
                continue

            # 키워드 밀도 = 문장 내 키워드 가중치 합 / 토큰 수
            density = sum(keyword_weights.get(t, 0.0) for t in tokens) / len(tokens)

            # 문헌 관련도를 곱해 상위 문헌 문장을 우대
            candidates.append((density * (1.0 + doc.score / 100.0), sentence))

    if not candidates:
        return ""

    candidates.sort(key=lambda c: c[0], reverse=True)

    selected: List[str] = []
    for _, sentence in candidates:
        # 거의 같은 문장이 중복 선택되지 않도록 방어
        if any(sentence[:40] == chosen[:40] for chosen in selected):
            continue

        selected.append(sentence)

        if len(selected) >= max_sentences:
            break

    return " ".join(selected)


# ============ 키워드 공출현 ============


def co_occurrences(
    scored_documents: Sequence[ScoredDocument],
    keywords: Sequence[Dict],
    per_document: int = 6,
    min_count: int = 2,
) -> List[Tuple[str, str, int]]:
    """
    같은 문헌에 함께 등장한 키워드 쌍을 세어 연결 관계를 만듭니다.

    Args:
        scored_documents: 점수가 매겨진 문헌 목록
        keywords: extract_keywords 결과 (이 목록에 있는 단어만 대상)
        per_document: 문헌당 고려할 상위 키워드 수
        min_count: 엣지로 인정할 최소 공출현 횟수

    Returns:
        [(단어A, 단어B, 공출현횟수)] - 횟수 내림차순
    """
    keyword_set = {kw["word"] for kw in keywords}

    if len(keyword_set) < 2:
        return []

    pair_counts: Counter = Counter()

    for doc in scored_documents:
        # 이 문헌에 등장한 키워드를 빈도순으로 상위 N개만 사용
        present = [
            (token, freq)
            for token, freq in doc.tokens.items()
            if token in keyword_set
        ]
        present.sort(key=lambda kv: kv[1], reverse=True)

        words = sorted(token for token, _ in present[:per_document])

        for i in range(len(words)):
            for j in range(i + 1, len(words)):
                pair_counts[(words[i], words[j])] += 1

    pairs = [
        (a, b, count)
        for (a, b), count in pair_counts.items()
        if count >= min_count
    ]
    pairs.sort(key=lambda p: p[2], reverse=True)

    return pairs
