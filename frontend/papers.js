/**
 * 📄 학술 논문 검색 화면
 *
 * 일반 검색어로 arXiv를 조회하고, 초록 요약과 참고문헌 형식을 보여 줍니다.
 *
 * 사용 API
 * - POST /api/search-papers  { query, limit, question }
 *
 * script.js에 정의된 공용 유틸($, apiFetch, setText, showError)을 사용합니다.
 */

// 예전 접두사가 남아 있으면 괄호 안만 꺼냅니다.
const PAPERS_COMMAND_RE = /^\s*\/mycode\s*\(\s*(.+)\s*\)\s*$/i;

let lastPapersRequest = null;
let lastBibliographyText = '';

function setPapersState(state) {
  $('papersIdle').classList.toggle('hidden', state !== 'idle');
  $('papersLoading').classList.toggle('hidden', state !== 'loading');
  $('papersResult').classList.toggle('hidden', state !== 'result');
  $('papersEmpty').classList.toggle('hidden', state !== 'empty');
}

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

function showCopyHint(message) {
  const hint = $('papersCopyHint');
  if (!hint) return;
  hint.textContent = message;
  hint.classList.remove('hidden');
  window.setTimeout(() => {
    if (hint.textContent === message) hint.classList.add('hidden');
  }, 1800);
}

/**
 * 입력에서 실제 검색어만 남깁니다. 하이픈과 공백은 유지합니다.
 * @param {string} raw
 * @returns {string}
 */
function normalizePapersQuery(raw) {
  const text = (raw || '').trim();

  if (!text) {
    throw new Error('검색어를 입력하세요. 예: text-to-3d');
  }

  const match = text.match(PAPERS_COMMAND_RE);
  if (match) {
    const topic = normalizeSearchTerm(match[1]);
    if (!topic) {
      throw new Error('검색어를 입력하세요. 예: text-to-3d');
    }
    return topic;
  }

  if (text.toLowerCase().startsWith('/mycode')) {
    const rest = text.slice(7).replace(/^\s*\(|\)\s*$/g, '').trim();
    const topic = normalizeSearchTerm(rest);
    if (!topic) {
      throw new Error('검색어를 입력하세요. 예: text-to-3d');
    }
    return topic;
  }

  return normalizeSearchTerm(text);
}

function normalizeSearchTerm(raw) {
  return (raw || '').replace(/\s+/g, ' ').trim();
}

function formatAuthors(authors) {
  if (!authors || !authors.length) return '저자 미상';
  if (authors.length <= 3) return authors.join(', ');
  return `${authors.slice(0, 3).join(', ')} 외 ${authors.length - 3}명`;
}

/**
 * 클립보드에 참고문헌 텍스트를 복사합니다.
 * @param {string} text
 * @param {string} [okMessage]
 */
async function copyCitationText(text, okMessage) {
  if (!text) return;
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      const area = document.createElement('textarea');
      area.value = text;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.left = '-9999px';
      document.body.appendChild(area);
      area.select();
      document.execCommand('copy');
      document.body.removeChild(area);
    }
    showCopyHint(okMessage || '참고문헌을 복사했습니다.');
  } catch (_error) {
    showCopyHint('복사에 실패했습니다. 텍스트를 직접 선택해 주세요.');
  }
}

function createCopyButton(label, onClick) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className =
    'text-xs bg-cream-100 hover:bg-cream-200 text-ink px-3 py-1.5 rounded-xl transition';
  button.textContent = label;
  button.addEventListener('click', onClick);
  return button;
}

/**
 * 논문 카드 한 장을 만듭니다.
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

  const citationWrap = document.createElement('div');
  citationWrap.className = 'mt-4 pt-3 border-t border-cream-200';

  const citationLabel = document.createElement('p');
  citationLabel.className = 'text-[11px] text-ink-faint mb-1';
  citationLabel.textContent = '참고문헌';

  const citation = document.createElement('p');
  citation.className = 'text-xs text-ink leading-relaxed';
  citation.textContent = paper.citation || '';

  const citationActions = document.createElement('div');
  citationActions.className = 'mt-2';
  citationActions.appendChild(
    createCopyButton('인용 복사', () => {
      copyCitationText(paper.citation, '이 논문 참고문헌을 복사했습니다.');
    })
  );

  citationWrap.append(citationLabel, citation, citationActions);
  card.append(header, meta, abstract, actions, citationWrap);
  return card;
}

function renderBibliography(lines) {
  const list = $('papersBibList');
  list.replaceChildren();
  lastBibliographyText = (lines || []).filter(Boolean).join('\n');

  if (!lastBibliographyText) {
    const empty = document.createElement('li');
    empty.className = 'text-ink-faint';
    empty.textContent = '표시할 참고문헌이 없습니다.';
    list.appendChild(empty);
    return;
  }

  const fragment = document.createDocumentFragment();
  lines.forEach((line) => {
    const item = document.createElement('li');
    item.className = 'pl-1';
    item.textContent = line;
    fragment.appendChild(item);
  });
  list.appendChild(fragment);
}

function renderPapersResult(data) {
  const papers = data.papers || [];
  const insight = data.insight;
  const bibliography = data.bibliography && data.bibliography.length
    ? data.bibliography
    : papers.map((paper) => paper.citation).filter(Boolean);

  if (!papers.length) {
    setPapersState('empty');
    return;
  }

  setPapersState('result');

  const provider = insight?.provider === 'llm' ? 'LLM' : '로컬 요약';
  setText($('papersProvider'), provider);
  setText($('papersAnswer'), insight?.answer || '요약을 생성하지 못했습니다.');
  setText($('papersCount'), `'${data.query}' ${data.total}편`);
  renderBibliography(bibliography);

  const list = $('papersList');
  list.replaceChildren();
  const fragment = document.createDocumentFragment();
  papers.forEach((paper, index) => {
    fragment.appendChild(createPaperCard(paper, index + 1));
  });
  list.appendChild(fragment);
}

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

function handlePapersSubmit(event) {
  event.preventDefault();

  let query;
  try {
    query = normalizePapersQuery($('papersQuery').value);
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

function handlePapersChip(event) {
  const button = event.target.closest('[data-query]');
  if (!button) return;
  $('papersQuery').value = button.getAttribute('data-query');
  $('papersForm').requestSubmit();
}

function loadPapers() {
  if (lastPapersRequest) {
    runPapersSearch(lastPapersRequest);
  }
}

function initPapers() {
  $('papersForm').addEventListener('submit', handlePapersSubmit);
  $('papersChips').addEventListener('click', handlePapersChip);
  $('papersCopyAllBtn').addEventListener('click', () => {
    copyCitationText(lastBibliographyText, '참고문헌 전체를 복사했습니다.');
  });
}
