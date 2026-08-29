/**
 * 📄 학술 논문 검색 화면
 *
 * 사용자가 `/mycode (검색어)` 형식으로 명령을 내면 arXiv API로
 * 논문을 실시간 검색하고, 초록을 LLM 컨텍스트에 넣어 요약·추천을 보여 줍니다.
 *
 * 사용 API
 * - GET  /api/search-papers?q=...
 * - POST /api/search-papers  { query, limit, question }
 *
 * script.js에 정의된 공용 유틸($, apiFetch, setText, showError)을 사용합니다.
 */

// 예: /mycode (Text-to-3D)
const PAPERS_COMMAND_RE = /^\s*\/mycode\s*\(\s*(.+?)\s*\)\s*$/i;

// 마지막 검색 — 새로고침 버튼에서 재실행
let lastPapersRequest = null;

/**
 * 화면 상태를 idle / loading / result / empty 중 하나만 보이게 합니다.
 * @param {'idle'|'loading'|'result'|'empty'} state
 */
function setPapersState(state) {
  $('papersIdle').classList.toggle('hidden', state !== 'idle');
  $('papersLoading').classList.toggle('hidden', state !== 'loading');
  $('papersResult').classList.toggle('hidden', state !== 'result');
  $('papersEmpty').classList.toggle('hidden', state !== 'empty');
}

/**
 * 논문 검색 전용 오류 메시지를 표시합니다.
 * @param {string|null} message
 */
function showPapersError(message) {
  const el = $('papersError');
  if (!el) return;
  if (!message) {
    el.classList.add('hidden');
    el.textContent = '';
    return;
  }
  el.classList.remove('hidden');
  el.textContent = message;
}

/**
 * 입력을 `/mycode (검색어)` 정규 형식으로 맞춥니다.
 *
 * - 이미 올바른 명령이면 공백만 정리합니다.
 * - `/mycode`로 시작했지만 괄호가 없으면 오류입니다.
 * - 일반 검색어만 있으면 자동으로 감쌉니다.
 *
 * @param {string} raw
 * @returns {string}
 */
function normalizePapersCommand(raw) {
  const text = (raw || '').trim();

  if (!text) {
    throw new Error('검색어를 입력하세요. 예: /mycode (Text-to-3D)');
  }

  const match = text.match(PAPERS_COMMAND_RE);
  if (match) {
    const topic = match[1].replace(/\s+/g, ' ').trim();
    if (!topic) {
      throw new Error('괄호 안에 검색어가 없습니다. 예: /mycode (Text-to-3D)');
    }
    return `/mycode (${topic})`;
  }

  if (text.toLowerCase().startsWith('/mycode')) {
    throw new Error('명령 형식이 올바르지 않습니다. /mycode (검색어) 형태로 입력하세요.');
  }

  return `/mycode (${text.replace(/\s+/g, ' ')})`;
}

/**
 * 저자 목록을 짧게 표시합니다.
 * @param {string[]} authors
 * @returns {string}
 */
function formatAuthors(authors) {
  if (!authors || !authors.length) return '저자 미상';
  if (authors.length <= 3) return authors.join(', ');
  return `${authors.slice(0, 3).join(', ')} 외 ${authors.length - 3}명`;
}

/**
 * 논문 카드 한 장을 만듭니다. 제목·초록은 textContent만 사용합니다.
 * @param {Object} paper
 * @param {number} index
 * @returns {HTMLElement}
 */
function createPaperCard(paper, index) {
  const card = document.createElement('article');
  card.className = 'bg-paper rounded-2xl border border-cream-200 shadow-soft p-5';

  const header = document.createElement('div');
  header.className = 'flex items-start gap-3 mb-2';

  const indexBadge = document.createElement('span');
  indexBadge.className =
    'shrink-0 w-6 h-6 rounded-lg bg-forest-50 text-forest-700 text-xs font-medium ' +
    'flex items-center justify-center';
  indexBadge.textContent = String(index);

  const title = document.createElement('h3');
  title.className = 'text-sm font-semibold leading-snug';
  title.textContent = paper.title || '(제목 없음)';

  header.append(indexBadge, title);

  const meta = document.createElement('p');
  meta.className = 'text-xs text-ink-muted mb-2';
  const parts = [formatAuthors(paper.authors)];
  if (paper.published_at) {
    parts.push(String(paper.published_at).slice(0, 10));
  }
  if (paper.arxiv_id) {
    parts.push(paper.arxiv_id);
  }
  meta.textContent = parts.join(' · ');

  const abstract = document.createElement('p');
  abstract.className = 'text-xs text-ink-muted leading-relaxed line-clamp-4';
  abstract.textContent = paper.abstract || '초록 없음';

  const actions = document.createElement('div');
  actions.className = 'flex flex-wrap gap-2 mt-3';

  if (paper.pdf_url) {
    const pdf = document.createElement('a');
    pdf.href = paper.pdf_url;
    pdf.target = '_blank';
    pdf.rel = 'noopener noreferrer';
    pdf.className =
      'text-xs bg-forest-600 hover:bg-forest-700 text-cream-50 px-3 py-1.5 rounded-xl transition';
    pdf.textContent = 'PDF 열기';
    actions.appendChild(pdf);
  }

  if (paper.abs_url) {
    const abs = document.createElement('a');
    abs.href = paper.abs_url;
    abs.target = '_blank';
    abs.rel = 'noopener noreferrer';
    abs.className =
      'text-xs bg-cream-100 hover:bg-cream-200 text-ink px-3 py-1.5 rounded-xl transition';
    abs.textContent = '초록 페이지';
    actions.appendChild(abs);
  }

  card.append(header, meta, abstract, actions);
  return card;
}

/**
 * 검색 결과를 화면에 그립니다.
 * @param {Object} data - SearchPapersResponse
 */
function renderPapersResult(data) {
  const papers = data.papers || [];
  const insight = data.insight;

  if (!papers.length) {
    setPapersState('empty');
    return;
  }

  setPapersState('result');

  const provider = insight?.provider === 'llm' ? 'LLM' : '로컬 요약';
  setText($('papersProvider'), provider);
  setText($('papersAnswer'), insight?.answer || '요약을 생성하지 못했습니다.');
  setText($('papersCount'), `'${data.query}' ${data.total}편`);

  const list = $('papersList');
  list.replaceChildren();
  const fragment = document.createDocumentFragment();
  papers.forEach((paper, index) => {
    fragment.appendChild(createPaperCard(paper, index + 1));
  });
  list.appendChild(fragment);
}

/**
 * POST /api/search-papers 를 호출합니다.
 * @param {{query: string, limit: number, question?: string}} payload
 */
async function runPapersSearch(payload) {
  showPapersError(null);
  showError(null);
  setPapersState('loading');

  const btn = $('papersSearchBtn');
  if (btn) btn.disabled = true;

  try {
    lastPapersRequest = payload;
    const data = await apiFetch('/api/search-papers', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    renderPapersResult(data);
  } catch (error) {
    setPapersState(lastPapersRequest && $('papersList').childElementCount ? 'result' : 'idle');
    showPapersError(error.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

/**
 * 폼 제출을 처리합니다.
 * @param {Event} event
 */
function handlePapersSubmit(event) {
  event.preventDefault();

  let query;
  try {
    query = normalizePapersCommand($('papersQuery').value);
  } catch (error) {
    showPapersError(error.message);
    return;
  }

  $('papersQuery').value = query;

  const question = $('papersQuestion').value.trim();
  const limit = Number($('papersLimit').value) || 8;

  runPapersSearch({
    query,
    limit,
    question: question || null,
  });
}

/**
 * 빠른 검색 칩을 누르면 입력을 채우고 바로 검색합니다.
 * @param {Event} event
 */
function handlePapersChip(event) {
  const button = event.target.closest('[data-query]');
  if (!button) return;
  $('papersQuery').value = button.getAttribute('data-query');
  $('papersForm').requestSubmit();
}

/**
 * 새로고침 버튼에서 마지막 검색을 다시 실행합니다.
 */
function loadPapers() {
  if (lastPapersRequest) {
    runPapersSearch(lastPapersRequest);
  }
}

/**
 * 논문 검색 화면의 이벤트를 바인딩합니다. (script.js의 init에서 호출)
 */
function initPapers() {
  $('papersForm').addEventListener('submit', handlePapersSubmit);
  $('papersChips').addEventListener('click', handlePapersChip);
}
