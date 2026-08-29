/**
 * 🕸️ 토픽 지식 그래프 화면
 *
 * 사용자가 입력한 토픽으로 백엔드 분석을 요청하고, 그 결과를
 * 요약 카드 · 자동 태그 칩 · 인터랙티브 그래프 · 근거 문헌 목록으로 보여 줍니다.
 *
 * 사용 API
 * - GET  /api/graph/topics      : 추천 토픽 (빠른 선택 칩)
 * - POST /api/graph/analyze     : 토픽 분석 (요약 + 키워드 + Node/Edge 그래프)
 * - POST /api/graph/apply-tags  : 제안 태그를 내 노트에 적용
 *
 * 렌더링은 CDN으로 불러온 Cytoscape.js를 사용하며,
 * 라이브러리를 못 불러온 환경에서는 텍스트 인접 목록으로 자동 폴백합니다.
 *
 * script.js에 정의된 공용 유틸($, apiFetch, setText, formatTime, showError)을 사용합니다.
 */

// ============ 상수 ============

// 노드 종류별 색상 - index.html의 범례와 반드시 같은 색을 씁니다.
const NODE_COLORS = {
  topic: '#3D5C4A',    // forest-600
  note: '#6B8F71',     // sage
  trend: '#C17F4A',    // warm terracotta
  keyword: '#C4A35A',  // gold
};

// 노드 종류별 한국어 라벨 (상세 패널/폴백 표시용)
const NODE_TYPE_LABELS = {
  topic: '토픽',
  note: '내 노트',
  trend: '트렌드',
  keyword: '키워드',
};

// 간선 관계별 표시 정보
const EDGE_STYLES = {
  relevant: { color: '#C4B39A', label: '관련 문헌', dash: [] },
  tagged: { color: '#D9C9B0', label: '키워드 포함', dash: [4, 3] },
  co_occurs: { color: '#C4A35A', label: '함께 등장', dash: [1, 3] },
};

// 그래프에서 문헌 노드 라벨을 자르는 길이
const DOC_LABEL_LENGTH = 16;

// ============ 상태 ============

// Cytoscape 인스턴스 - 재분석 시 파괴하고 새로 만듭니다.
let cyInstance = null;

// 가장 최근 분석 결과 - 태그 적용/폴백 렌더링에서 재사용합니다.
let lastAnalysis = null;

// ============ 유틸 ============

/**
 * Cytoscape가 실제로 사용 가능한지 확인합니다.
 *
 * index.html의 onerror 핸들러가 CDN 실패를 window.__cytoscapeFailed로 알려주지만,
 * 스크립트가 조용히 비어서 오는 경우도 있으므로 전역 변수 존재까지 함께 봅니다.
 *
 * @returns {boolean} 사용 가능하면 true
 */
function isGraphLibraryReady() {
  return !window.__cytoscapeFailed && typeof window.cytoscape === 'function';
}

/**
 * 그래프 화면의 상태를 하나만 보이도록 전환합니다.
 * @param {'idle'|'loading'|'result'|'empty'} state - 표시할 상태
 */
function setGraphState(state) {
  $('graphIdle').classList.toggle('hidden', state !== 'idle');
  $('graphLoading').classList.toggle('hidden', state !== 'loading');
  $('graphResult').classList.toggle('hidden', state !== 'result');
  $('graphEmpty').classList.toggle('hidden', state !== 'empty');
}

/**
 * 그래프 화면 전용 오류 메시지를 표시합니다.
 * @param {string|null} message - 표시할 메시지 (null이면 숨김)
 */
function showGraphError(message) {
  const element = $('graphError');

  if (!message) {
    element.classList.add('hidden');
    return;
  }

  element.textContent = message;
  element.classList.remove('hidden');
}

// ============ 렌더링: 추천 토픽 ============

/**
 * 추천 토픽 칩을 그립니다. 클릭하면 곧바로 분석이 실행됩니다.
 * @param {Object[]} topics - [{topic, doc_count}]
 */
function renderTopicSuggestions(topics) {
  const container = $('graphSuggestions');
  container.replaceChildren();

  if (!topics.length) {
    const empty = document.createElement('span');
    empty.className = 'text-xs text-ink-faint';
    empty.textContent = '아직 분석할 데이터가 없습니다. 큐레이션 탭에서 트렌드를 수집해 보세요.';
    container.appendChild(empty);
    return;
  }

  const fragment = document.createDocumentFragment();

  topics.forEach((item) => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className =
      'text-xs bg-cream-100 hover:bg-forest-50 hover:text-forest-700 ' +
      'px-2.5 py-1 rounded-full transition';
    chip.textContent = `${item.topic} (${item.doc_count})`;

    chip.addEventListener('click', () => {
      $('graphTopic').value = item.topic;
      runAnalysis();
    });

    fragment.appendChild(chip);
  });

  container.appendChild(fragment);
}

// ============ 렌더링: 분석 결과 ============

/**
 * 키워드 칩을 그립니다. 점수가 높을수록 진한 배경을 씁니다.
 * @param {Object[]} keywords - [{word, score, doc_count}]
 */
function renderKeywords(keywords) {
  const container = $('graphKeywords');
  container.replaceChildren();

  if (!keywords.length) {
    const empty = document.createElement('span');
    empty.className = 'text-xs text-ink-faint';
    empty.textContent = '추출된 키워드가 없습니다.';
    container.appendChild(empty);
    return;
  }

  const fragment = document.createDocumentFragment();

  keywords.forEach((keyword) => {
    // 상위 키워드는 강조, 나머지는 옅게 - 중요도를 한눈에 보이게 합니다.
    const emphasis = keyword.score >= 0.6
      ? 'bg-amber-50 text-amber-800 border-amber-200'
      : 'bg-cream-50 text-ink-muted border-cream-200';

    const chip = document.createElement('span');
    chip.className = `text-xs border px-2.5 py-1 rounded-full ${emphasis}`;
    chip.title = `${keyword.doc_count}개 문헌에 등장 · 점수 ${keyword.score}`;
    chip.textContent = `#${keyword.word}`;

    fragment.appendChild(chip);
  });

  container.appendChild(fragment);
}

/**
 * 근거 문헌 목록을 그립니다.
 * @param {Object[]} documents - 분석에 사용된 문헌 목록
 */
function renderGraphDocuments(documents) {
  const list = $('graphDocuments');
  list.replaceChildren();

  const fragment = document.createDocumentFragment();

  documents.forEach((doc) => {
    const row = document.createElement('li');
    row.className = 'px-5 py-4 hover:bg-cream-50/80';

    const header = document.createElement('div');
    header.className = 'flex items-start gap-2';

    // 문헌 종류 배지
    const badge = document.createElement('span');
    const isNote = doc.type === 'note';
    badge.className = isNote
      ? 'text-[11px] bg-forest-50 text-forest-700 px-1.5 py-0.5 rounded-lg whitespace-nowrap'
      : 'text-[11px] bg-cream-100 text-ink-muted px-1.5 py-0.5 rounded-lg whitespace-nowrap';
    badge.textContent = isNote ? '📝 노트' : '📰 트렌드';
    header.appendChild(badge);

    // 제목 - 원문 링크가 있으면 링크로
    if (doc.url) {
      const link = document.createElement('a');
      link.href = doc.url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.className = 'text-sm font-medium hover:text-forest-600 hover:underline';
      link.textContent = doc.title;
      header.appendChild(link);
    } else {
      const title = document.createElement('span');
      title.className = 'text-sm font-medium';
      title.textContent = doc.title;
      header.appendChild(title);
    }

    // 관련도 점수
    const score = document.createElement('span');
    score.className = 'ml-auto text-[11px] text-ink-faint whitespace-nowrap';
    score.textContent = `관련도 ${Math.round(doc.score * 100)}%`;
    header.appendChild(score);

    row.appendChild(header);

    if (doc.snippet) {
      const snippet = document.createElement('p');
      snippet.className = 'text-xs text-ink-muted mt-1 line-clamp-2';
      snippet.textContent = doc.snippet;
      row.appendChild(snippet);
    }

    const meta = document.createElement('p');
    meta.className = 'text-[11px] text-ink-faint mt-1';
    meta.textContent = [doc.source_name, formatTime(doc.published_at)]
      .filter(Boolean)
      .join(' · ');
    row.appendChild(meta);

    fragment.appendChild(row);
  });

  list.appendChild(fragment);
}

// ============ 렌더링: 그래프 ============

/**
 * 백엔드 Node/Edge JSON을 Cytoscape 엘리먼트 배열로 변환합니다.
 * @param {Object} graph - {nodes, edges}
 * @returns {Object[]} Cytoscape elements
 */
function toCytoscapeElements(graph) {
  const nodes = graph.nodes.map((node) => ({
    data: {
      id: node.id,
      // 문헌 제목은 길어서 그래프에서는 잘라 쓰고, 전체는 상세 패널에서 보여 줍니다.
      label: node.type === 'note' || node.type === 'trend'
        ? `${node.label.slice(0, DOC_LABEL_LENGTH)}${node.label.length > DOC_LABEL_LENGTH ? '…' : ''}`
        : node.label,
      fullLabel: node.label,
      type: node.type,
      weight: node.weight,
      meta: node.meta || {},
    },
  }));

  const edges = graph.edges.map((edge, index) => ({
    data: {
      id: `e${index}`,
      source: edge.source,
      target: edge.target,
      relation: edge.relation,
      weight: edge.weight,
    },
  }));

  return [...nodes, ...edges];
}

/**
 * Cytoscape 스타일 정의를 만듭니다.
 * @returns {Object[]} 스타일 배열
 */
function buildGraphStyles() {
  const styles = [
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'font-size': '9px',
        'font-family': 'Pretendard, Inter, system-ui, sans-serif',
        'color': '#2C2925',
        'text-valign': 'bottom',
        'text-margin-y': 4,
        'text-wrap': 'none',
        'border-width': 2,
        'border-color': '#FFFEFB',
        // 가중치를 노드 크기로 매핑 - 중요할수록 크게 보입니다.
        'width': 'mapData(weight, 0, 1, 16, 52)',
        'height': 'mapData(weight, 0, 1, 16, 52)',
      },
    },
    {
      selector: 'node:selected',
      style: {
        'border-width': 3,
        'border-color': '#2C2925',
      },
    },
    {
      selector: 'edge',
      style: {
        'curve-style': 'bezier',
        'width': 'mapData(weight, 0, 1, 0.5, 3)',
        'opacity': 0.65,
      },
    },
  ];

  // 노드 종류별 색상
  Object.entries(NODE_COLORS).forEach(([type, color]) => {
    styles.push({
      selector: `node[type="${type}"]`,
      style: { 'background-color': color },
    });
  });

  // 토픽 노드는 중심이므로 라벨을 더 크게
  styles.push({
    selector: 'node[type="topic"]',
    style: { 'font-size': '13px', 'font-weight': 'bold', 'color': '#2F4A3C' },
  });

  // 간선 관계별 색상/점선
  Object.entries(EDGE_STYLES).forEach(([relation, config]) => {
    styles.push({
      selector: `edge[relation="${relation}"]`,
      style: {
        'line-color': config.color,
        'line-style': config.dash.length ? 'dashed' : 'solid',
        'line-dash-pattern': config.dash.length ? config.dash : undefined,
      },
    });
  });

  return styles;
}

/**
 * 노드를 클릭했을 때 하단 상세 패널을 채웁니다.
 * @param {Object} nodeData - Cytoscape 노드의 data 객체
 */
function renderNodeDetail(nodeData) {
  const panel = $('graphNodeDetail');
  panel.replaceChildren();
  panel.classList.remove('hidden');

  const header = document.createElement('div');
  header.className = 'flex items-center gap-2 mb-1';

  const dot = document.createElement('span');
  dot.className = 'w-2.5 h-2.5 rounded-full';
  dot.style.backgroundColor = NODE_COLORS[nodeData.type] || '#94a3b8';
  header.appendChild(dot);

  const type = document.createElement('span');
  type.className = 'text-xs text-ink-muted';
  type.textContent = NODE_TYPE_LABELS[nodeData.type] || nodeData.type;
  header.appendChild(type);

  panel.appendChild(header);

  const title = document.createElement('p');
  title.className = 'font-medium';
  title.textContent = nodeData.fullLabel;
  panel.appendChild(title);

  const meta = nodeData.meta || {};
  const details = [];

  if (meta.source_name) details.push(`출처: ${meta.source_name}`);
  if (meta.category) details.push(`분류: ${meta.category}`);
  if (meta.doc_count !== undefined) details.push(`${meta.doc_count}개 문헌에 등장`);
  if (meta.document_count !== undefined) details.push(`관련 문헌 ${meta.document_count}건`);
  if (meta.matched && meta.matched.length) details.push(`매칭: ${meta.matched.join(', ')}`);

  if (details.length) {
    const info = document.createElement('p');
    info.className = 'text-xs text-ink-muted mt-1';
    info.textContent = details.join(' · ');
    panel.appendChild(info);
  }

  if (meta.url) {
    const link = document.createElement('a');
    link.href = meta.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.className = 'inline-block mt-2 text-xs text-forest-600 hover:underline';
    link.textContent = '🔗 원문 열기';
    panel.appendChild(link);
  }
}

/**
 * 지식 그래프를 그립니다.
 *
 * 라이브러리를 못 불러온 경우에는 캔버스를 숨기고
 * 텍스트 인접 목록(폴백)을 대신 보여 줍니다.
 *
 * @param {Object} graph - {nodes, edges}
 */
function renderGraph(graph) {
  const canvas = $('graphCanvas');
  const fallback = $('graphFallback');

  $('graphNodeDetail').classList.add('hidden');

  if (!isGraphLibraryReady()) {
    canvas.classList.add('hidden');
    fallback.classList.remove('hidden');
    renderGraphFallback(graph);
    return;
  }

  canvas.classList.remove('hidden');
  fallback.classList.add('hidden');

  // 이전 인스턴스를 정리하지 않으면 캔버스가 겹쳐 그려집니다.
  if (cyInstance) {
    cyInstance.destroy();
    cyInstance = null;
  }

  cyInstance = window.cytoscape({
    container: canvas,
    elements: toCytoscapeElements(graph),
    style: buildGraphStyles(),
    // 물리 시뮬레이션 기반 배치 - 연결이 많은 노드가 자연스럽게 중앙에 모입니다.
    layout: {
      name: 'cose',
      animate: false,        // 노드가 많을 때 애니메이션은 체감 지연만 키움
      nodeDimensionsIncludeLabels: true,
      idealEdgeLength: 90,
      nodeRepulsion: 9000,
      padding: 24,
    },
    // 과도한 확대/축소로 그래프를 잃어버리지 않도록 제한
    minZoom: 0.2,
    maxZoom: 2.5,
    wheelSensitivity: 0.2,
  });

  // 노드 클릭 시 상세 표시
  cyInstance.on('tap', 'node', (event) => {
    renderNodeDetail(event.target.data());
  });

  // 빈 곳을 누르면 상세를 닫음
  cyInstance.on('tap', (event) => {
    if (event.target === cyInstance) {
      $('graphNodeDetail').classList.add('hidden');
    }
  });
}

/**
 * 그래프 라이브러리를 쓸 수 없을 때의 텍스트 폴백을 그립니다.
 * 토픽에 직접 연결된 문헌과, 문헌별 키워드를 목록으로 보여 줍니다.
 *
 * @param {Object} graph - {nodes, edges}
 */
function renderGraphFallback(graph) {
  const container = $('graphFallbackList');
  container.replaceChildren();

  // id -> 노드 조회용 맵
  const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));

  // 문헌별로 연결된 키워드를 모읍니다.
  const keywordsByDoc = new Map();

  graph.edges
    .filter((edge) => edge.relation === 'tagged')
    .forEach((edge) => {
      const list = keywordsByDoc.get(edge.source) || [];
      const keywordNode = nodeById.get(edge.target);

      if (keywordNode) list.push(keywordNode.label);

      keywordsByDoc.set(edge.source, list);
    });

  const documentNodes = graph.nodes.filter(
    (node) => node.type === 'note' || node.type === 'trend'
  );

  const fragment = document.createDocumentFragment();

  documentNodes.forEach((node) => {
    const row = document.createElement('div');
    row.className = 'border border-cream-200 rounded-xl px-3 py-2 bg-cream-50/50';

    const title = document.createElement('p');
    title.className = 'font-medium text-sm';
    title.textContent = `${node.type === 'note' ? '📝' : '📰'} ${node.label}`;
    row.appendChild(title);

    const keywords = keywordsByDoc.get(node.id) || [];

    const linked = document.createElement('p');
    linked.className = 'text-xs text-ink-muted mt-0.5';
    linked.textContent = keywords.length
      ? `연결 키워드: ${keywords.join(', ')}`
      : '연결된 키워드 없음';
    row.appendChild(linked);

    fragment.appendChild(row);
  });

  container.appendChild(fragment);
}

// ============ 데이터 로딩 ============

/** 추천 토픽을 불러옵니다. */
async function loadTopicSuggestions() {
  try {
    const data = await apiFetch('/api/graph/topics?limit=12');

    renderTopicSuggestions(data.topics);
  } catch (error) {
    // 추천 토픽은 부가 기능이므로 실패해도 화면 전체를 막지 않습니다.
    console.error('추천 토픽 조회 실패:', error);

    const container = $('graphSuggestions');
    container.replaceChildren();

    const message = document.createElement('span');
    message.className = 'text-xs text-ink-faint';
    message.textContent = '추천 토픽을 불러오지 못했습니다.';
    container.appendChild(message);
  }
}

/**
 * 입력된 토픽으로 분석을 실행하고 결과를 그립니다.
 */
async function runAnalysis() {
  const topic = $('graphTopic').value.replace(/\s+/g, ' ').trim();

  // ---- 클라이언트 입력 검증 ----
  if (!topic) {
    showGraphError('분석할 토픽을 입력해 주세요.');
    $('graphTopic').focus();
    return;
  }

  const sources = [];
  if ($('graphSourceNotes').checked) sources.push('notes');
  if ($('graphSourceTrends').checked) sources.push('trends');

  if (!sources.length) {
    showGraphError('데이터 소스를 최소 하나 선택해 주세요.');
    return;
  }

  showGraphError(null);
  showError(null);
  setGraphState('loading');

  const button = $('graphAnalyzeBtn');
  button.disabled = true;

  try {
    const data = await apiFetch('/api/graph/analyze', {
      method: 'POST',
      body: JSON.stringify({
        topic,
        sources,
        limit: Number($('graphLimit').value),
        max_keywords: 15,
      }),
    });

    lastAnalysis = data;

    if (data.document_count === 0) {
      setText($('graphEmptyText'), `'${topic}' 과(와) 관련된 문헌을 찾지 못했습니다`);
      setGraphState('empty');
      return;
    }

    renderAnalysis(data);
    setGraphState('result');
  } catch (error) {
    showGraphError(`분석 실패: ${error.message}`);
    setGraphState('idle');
  } finally {
    button.disabled = false;
  }
}

/**
 * 분석 결과 전체를 화면에 반영합니다.
 * @param {Object} data - /api/graph/analyze 응답의 data
 */
function renderAnalysis(data) {
  setText($('graphTopicBadge'), data.topic);
  setText($('graphDocCount'), `문헌 ${data.document_count}건 · 키워드 ${data.keywords.length}개`);
  setText(
    $('graphSummary'),
    data.summary || '요약할 만한 문장을 찾지 못했습니다. 문헌 수가 적을 수 있습니다.'
  );

  renderKeywords(data.keywords);
  renderGraph(data.graph);
  renderGraphDocuments(data.documents);

  // 이전 분석의 태그 적용 결과 메시지는 지웁니다.
  $('applyTagsResult').classList.add('hidden');
}

/**
 * 태그를 붙일 내 노트 ID를 모읍니다.
 * 이번 분석에 노트가 있으면 그것을 쓰고, 없으면 계정에 있는 내 노트를 씁니다.
 * @param {Object} analysis - /api/graph/analyze 응답 data
 * @returns {Promise<number[]>}
 */
async function resolveNoteIdsForTags(analysis) {
  const fromAnalysis = (analysis.documents || [])
    .filter((doc) => doc.type === 'note' && Number(doc.ref_id) > 0)
    .map((doc) => Number(doc.ref_id));

  if (fromAnalysis.length) {
    return [...new Set(fromAnalysis)];
  }

  const fromAccount = (analysis.my_note_ids || [])
    .map((id) => Number(id))
    .filter((id) => id > 0);

  if (fromAccount.length) {
    return [...new Set(fromAccount)];
  }

  // 분석 응답에 ID가 없으면 노트 목록 API로 한 번 더 확인합니다.
  try {
    const data = await apiFetch('/api/notes?page=1&limit=50');
    return (data.notes || [])
      .map((note) => Number(note.id))
      .filter((id) => id > 0);
  } catch (error) {
    console.error('내 노트 조회 실패:', error);
    return [];
  }
}

/**
 * 제안된 태그를 내 노트에 적용합니다.
 */
async function handleApplyTags() {
  if (!lastAnalysis) return;

  const resultElement = $('applyTagsResult');
  const tags = lastAnalysis.suggested_tags || [];

  if (!tags.length) {
    resultElement.className = 'mt-3 text-xs text-amber-700';
    resultElement.textContent = '적용할 태그 후보가 없습니다. 먼저 토픽 분석을 실행해 주세요.';
    resultElement.classList.remove('hidden');
    return;
  }

  const noteIds = await resolveNoteIdsForTags(lastAnalysis);

  if (!noteIds.length) {
    resultElement.className = 'mt-3 text-xs text-amber-700';
    resultElement.textContent =
      '적용할 내 노트가 없습니다. 큐레이션 탭에서 트렌드를 노트로 담아 보세요.';
    resultElement.classList.remove('hidden');
    return;
  }

  const button = $('applyTagsBtn');
  button.disabled = true;
  button.textContent = '적용 중…';

  try {
    const data = await apiFetch('/api/graph/apply-tags', {
      method: 'POST',
      body: JSON.stringify({
        note_ids: noteIds,
        tags,
      }),
    });

    resultElement.className = 'mt-3 text-xs text-emerald-700';
    resultElement.textContent =
      `✅ ${data.updated_note_ids.length}개 노트에 ${data.applied_tags.length}개 태그를 적용했습니다.`;
    resultElement.classList.remove('hidden');
  } catch (error) {
    resultElement.className = 'mt-3 text-xs text-red-600';
    resultElement.textContent = `태그 적용 실패: ${error.message}`;
    resultElement.classList.remove('hidden');
  } finally {
    button.disabled = false;
    button.textContent = '내 노트에 태그 적용';
  }
}

/** 그래프 레이아웃을 다시 계산합니다. (노드가 겹쳤을 때 사용) */
function handleRelayout() {
  if (!cyInstance) return;

  cyInstance.layout({
    name: 'cose',
    animate: false,
    nodeDimensionsIncludeLabels: true,
    idealEdgeLength: 90,
    nodeRepulsion: 9000,
    padding: 24,
  }).run();
}

// ============ 초기화 ============

/** 그래프 화면의 이벤트를 바인딩합니다. (script.js의 init에서 호출) */
function initGraph() {
  $('graphForm').addEventListener('submit', (event) => {
    event.preventDefault();
    runAnalysis();
  });

  $('applyTagsBtn').addEventListener('click', handleApplyTags);
  $('graphRelayoutBtn').addEventListener('click', handleRelayout);
}
