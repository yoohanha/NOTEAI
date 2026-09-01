/**
 * 📚 노트 큐레이션 화면
 *
 * 수집된 기술 트렌드를 검색·필터링하고, 마음에 드는 항목을 내 노트로 담습니다.
 * 하단에는 지금까지 담은 내 노트 목록을 함께 보여 줍니다.
 *
 * 사용 API
 * - GET  /api/trends/sources : 소스 목록 (필터 select 채우기)
 * - GET  /api/trends         : 트렌드 목록 (검색/소스/기간 필터, 페이지네이션)
 * - POST /api/trends/refresh : 지금 수집 실행
 * - POST /api/trends/save    : 트렌드를 노트로 저장
 * - GET  /api/notes          : 내 노트 목록
 * - DELETE /api/notes/{id}   : 내 노트 삭제 (저장 취소)
 *
 * script.js에 정의된 공용 유틸($, apiFetch, setText, formatTime, showError)을 사용합니다.
 */

// ============ 상수 ============

const CURATION_PAGE_SIZE = 12;   // 트렌드 카드 한 번에 불러오는 개수
const NOTES_PAGE_SIZE = 20;      // 내 노트 목록 표시 개수

// ============ 상태 ============

// 현재 적용 중인 필터와 페이지 - "더 보기"가 같은 조건으로 이어지게 유지합니다.
let curationPage = 1;
let curationFilters = { search: '', source: '', days: '' };
let curationTotal = 0;
let sourcesLoaded = false;

// 내 노트 목록 상태 - 삭제 후 서버를 다시 기다리지 않고 화면을 바로 갱신합니다.
let myNotes = [];
let notesTotal = 0;

// ============ 유틸 ============

/**
 * 값이 있는 항목만 남겨 쿼리스트링을 만듭니다.
 * @param {Object} params - 키/값 객체
 * @returns {string} "a=1&b=2" 형태의 문자열
 */
function buildQuery(params) {
  const query = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) {
      query.set(key, value);
    }
  });

  return query.toString();
}

/**
 * 태그 배열을 작은 칩 엘리먼트로 만들어 붙입니다.
 * @param {HTMLElement} container - 칩을 담을 부모
 * @param {string[]} tags - 태그 목록
 * @param {number} max - 최대 표시 개수
 */
function appendTagChips(container, tags, max = 4) {
  (tags || []).slice(0, max).forEach((tag) => {
    const chip = document.createElement('span');
    chip.className = 'text-[11px] bg-cream-100 text-ink-muted px-2 py-0.5 rounded-full';
    chip.textContent = `#${tag}`;
    container.appendChild(chip);
  });
}

/**
 * 비어 있는 목록에 안내 문구를 표시합니다.
 * @param {HTMLElement} container - 대상 컨테이너
 * @param {string} message - 표시할 문구
 */
function renderEmptyState(container, message, emoji = '📭') {
  container.replaceChildren();

  const wrap = document.createElement('div');
  wrap.className = 'col-span-full flex flex-col items-center py-10 px-4';

  const icon = document.createElement('p');
  icon.className = 'w-14 h-14 rounded-2xl bg-cream-100 flex items-center justify-center text-2xl mb-3';
  icon.setAttribute('aria-hidden', 'true');
  icon.textContent = emoji;

  const empty = document.createElement('p');
  empty.className = 'text-sm text-ink-faint text-center';
  empty.textContent = message;

  wrap.append(icon, empty);
  container.appendChild(wrap);
}

// ============ 렌더링 ============

/**
 * 트렌드 항목 하나를 카드 엘리먼트로 만듭니다.
 *
 * 사용자 데이터가 들어가는 자리는 모두 textContent로 넣어 XSS를 막습니다.
 *
 * @param {Object} item - 트렌드 항목
 * @returns {HTMLElement} 카드 엘리먼트
 */
function createTrendCard(item) {
  const card = document.createElement('article');
  card.className =
    'border border-cream-200 rounded-2xl p-5 flex flex-col gap-2 bg-cream-50/40 ' +
    'hover:border-forest-200 hover:shadow-soft transition';
  card.dataset.trendId = String(item.id);
  if (item.url) card.dataset.trendUrl = item.url;
  card.dataset.trendTitle = item.title || '';

  // ---- 출처 / 발행일 ----
  const metaRow = document.createElement('div');
  metaRow.className = 'flex items-center gap-2 text-[11px] text-ink-faint';

  const source = document.createElement('span');
  source.className = 'font-medium text-ink-muted';
  source.textContent = item.source_name || item.source_key || '알 수 없는 소스';
  metaRow.appendChild(source);

  if (item.category) {
    const category = document.createElement('span');
    category.className = 'bg-cream-100 text-ink-muted px-1.5 py-0.5 rounded-lg';
    category.textContent = item.category;
    metaRow.appendChild(category);
  }

  const published = document.createElement('span');
  published.className = 'ml-auto';
  published.textContent = formatTime(item.published_at || item.fetched_at);
  metaRow.appendChild(published);

  card.appendChild(metaRow);

  // ---- 제목 ----
  const title = document.createElement('h3');
  title.className = 'text-sm font-semibold leading-snug';
  title.textContent = item.title || '(제목 없음)';
  card.appendChild(title);

  // ---- 요약 ----
  if (item.summary) {
    const summary = document.createElement('p');
    summary.className = 'text-xs text-ink-muted leading-relaxed line-clamp-3';
    summary.textContent = item.summary;
    card.appendChild(summary);
  }

  // ---- 태그 ----
  if (item.tags && item.tags.length) {
    const tagRow = document.createElement('div');
    tagRow.className = 'flex flex-wrap gap-1.5';
    appendTagChips(tagRow, item.tags);
    card.appendChild(tagRow);
  }

  // ---- 액션 ----
  const actions = document.createElement('div');
  actions.className = 'flex items-center gap-2 mt-auto pt-2';

  const openLink = document.createElement('a');
  openLink.href = item.url;
  openLink.target = '_blank';
  openLink.rel = 'noopener noreferrer';   // 원문 탭이 이 페이지를 조작하지 못하게 차단
  openLink.className = 'text-xs text-forest-600 hover:underline';
  openLink.textContent = '🔗 원문 열기';
  actions.appendChild(openLink);

  const saveBtn = document.createElement('button');
  saveBtn.type = 'button';
  saveBtn.dataset.role = 'save-note';
  saveBtn.className =
    'ml-auto text-xs bg-cream-100 hover:bg-cream-200 disabled:bg-forest-50 ' +
    'disabled:text-forest-700 px-3 py-1.5 rounded-xl transition';
  saveBtn.addEventListener('click', () => handleSaveTrend(item, saveBtn));

  if (item.is_saved) {
    saveBtn.textContent = '✅ 저장됨';
    saveBtn.disabled = true;
  } else {
    saveBtn.textContent = '📌 노트로 저장';
  }

  actions.appendChild(saveBtn);
  card.appendChild(actions);

  return card;
}

/**
 * 트렌드 카드 목록을 그립니다.
 * @param {Object[]} items - 트렌드 항목 배열
 * @param {boolean} append - true면 기존 목록 뒤에 덧붙임 ("더 보기")
 */
function renderCurationTrends(items, append = false) {
  const container = $('curationTrends');

  if (!append) container.replaceChildren();

  if (!items.length && !append) {
    renderEmptyState(
      container,
      '조건에 맞는 트렌드가 없습니다. 🛰️ 지금 수집을 눌러 보세요.',
      '🛰️'
    );
    return;
  }

  const fragment = document.createDocumentFragment();
  items.forEach((item) => fragment.appendChild(createTrendCard(item)));
  container.appendChild(fragment);
}

/**
 * 내 노트 한 줄을 만듭니다.
 * @param {Object} note - 노트
 * @returns {HTMLElement} 리스트 아이템
 */
function createNoteRow(note) {
  const row = document.createElement('li');
  row.className = 'px-5 py-4 hover:bg-cream-50/80';
  row.dataset.noteId = String(note.id);

  const header = document.createElement('div');
  header.className = 'flex items-start gap-3';

  const textCol = document.createElement('div');
  textCol.className = 'min-w-0 flex-1';

  const title = document.createElement('p');
  title.className = 'text-sm font-medium leading-snug break-words';
  title.textContent = note.title || '(제목 없음)';
  textCol.appendChild(title);

  const date = document.createElement('span');
  date.className = 'block text-[11px] text-ink-faint mt-1';
  date.textContent = formatTime(note.updated_at || note.created_at);
  textCol.appendChild(date);

  header.appendChild(textCol);

  if (typeof canDeleteContent === 'function' && canDeleteContent()) {
    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.dataset.role = 'delete-note';
    deleteBtn.className =
      'shrink-0 self-start text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 ' +
      'border border-red-200 px-2.5 py-1 rounded-lg transition';
    deleteBtn.setAttribute('aria-label', '노트 삭제');
    deleteBtn.title = '이 노트를 삭제합니다';
    deleteBtn.textContent = '삭제';
    header.appendChild(deleteBtn);
  }

  row.appendChild(header);

  if (note.content) {
    const preview = document.createElement('p');
    preview.className = 'text-xs text-ink-muted mt-1 line-clamp-2';
    preview.textContent = note.content.slice(0, 200);
    row.appendChild(preview);
  }

  if ((note.tags && note.tags.length) || note.category) {
    const tagRow = document.createElement('div');
    tagRow.className = 'flex flex-wrap gap-1.5 mt-2';

    if (note.category) {
      const category = document.createElement('span');
      category.className = 'text-[11px] bg-forest-50 text-forest-700 px-2 py-0.5 rounded-full';
      category.textContent = note.category;
      tagRow.appendChild(category);
    }

    appendTagChips(tagRow, note.tags, 6);
    row.appendChild(tagRow);
  }

  return row;
}

/**
 * 내 노트 목록을 그립니다.
 * @param {Object[]} notes - 노트 배열
 */
function renderNotes(notes) {
  myNotes = notes;
  const list = $('notesList');
  list.replaceChildren();

  if (!notes.length) {
    const empty = document.createElement('li');
    empty.className = 'px-5 py-10 text-center';
    const wrap = document.createElement('div');
    wrap.className = 'flex flex-col items-center gap-2';
    const icon = document.createElement('span');
    icon.className = 'w-12 h-12 rounded-2xl bg-cream-100 flex items-center justify-center text-xl';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = '📌';
    const text = document.createElement('span');
    text.className = 'text-sm text-ink-faint';
    text.textContent = '아직 담은 노트가 없습니다. 위 트렌드에서 📌 버튼을 눌러 보세요.';
    wrap.append(icon, text);
    empty.append(wrap);
    list.appendChild(empty);
    return;
  }

  const fragment = document.createDocumentFragment();
  notes.forEach((note) => fragment.appendChild(createNoteRow(note)));
  list.appendChild(fragment);
}

/**
 * 소스 필터 select를 채웁니다. (최초 1회만 호출)
 * @param {Object[]} sources - 소스 목록
 */
function renderSourceOptions(sources) {
  const select = $('curationSource');

  sources.forEach((source) => {
    const option = document.createElement('option');
    option.value = source.key;
    option.textContent = source.name || source.key;
    select.appendChild(option);
  });
}

// ============ 데이터 로딩 ============

/**
 * 큐레이션 화면 전체를 불러옵니다.
 * 트렌드/노트/소스 요청은 서로 독립적이므로 병렬로 보냅니다.
 */
async function loadCuration() {
  curationPage = 1;

  const requests = [loadCurationTrends(false), loadNotes()];

  // 소스 목록은 바뀌지 않으므로 최초 1회만 요청합니다.
  if (!sourcesLoaded) requests.push(loadSources());

  await Promise.allSettled(requests);

  setText($('lastUpdated'), `업데이트 ${new Date().toLocaleTimeString('ko-KR')}`);
}

/**
 * 현재 필터 조건으로 트렌드 목록을 불러옵니다.
 * @param {boolean} append - true면 다음 페이지를 이어 붙임
 */
async function loadCurationTrends(append = false) {
  const query = buildQuery({
    page: curationPage,
    limit: CURATION_PAGE_SIZE,
    search: curationFilters.search,
    source: curationFilters.source,
    days: curationFilters.days,
  });

  try {
    const data = await apiFetch(`/api/trends?${query}`);

    curationTotal = data.total;

    renderCurationTrends(data.items, append);

    setText($('curationCount'), `${data.total}건 중 ${curationPage * CURATION_PAGE_SIZE >= data.total
      ? data.total
      : curationPage * CURATION_PAGE_SIZE}건 표시`);

    // 아직 남은 항목이 있을 때만 "더 보기" 노출
    const hasMore = curationPage * CURATION_PAGE_SIZE < data.total;
    $('curationMoreBtn').classList.toggle('hidden', !hasMore);
  } catch (error) {
    showError(`트렌드 조회 실패: ${error.message}`);
  }
}

/** 내 노트 목록을 불러옵니다. */
async function loadNotes() {
  try {
    const data = await apiFetch(`/api/notes?page=1&limit=${NOTES_PAGE_SIZE}`);

    notesTotal = data.pagination.total;
    renderNotes(data.notes);
    setText($('notesCount'), `${notesTotal}건`);
  } catch (error) {
    showError(`노트 조회 실패: ${error.message}`);
  }
}

/** 소스 목록을 불러와 필터 select를 채웁니다. */
async function loadSources() {
  try {
    const data = await apiFetch('/api/trends/sources');

    renderSourceOptions(data.sources);
    sourcesLoaded = true;
  } catch (error) {
    // 필터가 비어 있어도 화면은 동작하므로 배너까지 띄우지 않습니다.
    console.error('소스 목록 조회 실패:', error);
  }
}

// ============ 이벤트 핸들러 ============

/**
 * 필터 폼 제출 - 첫 페이지부터 다시 조회합니다.
 * @param {Event} event - submit 이벤트
 */
function handleCurationFilter(event) {
  event.preventDefault();

  curationFilters = {
    search: $('curationSearch').value.trim(),
    source: $('curationSource').value,
    days: $('curationDays').value,
  };
  curationPage = 1;

  showError(null);
  loadCurationTrends(false);
}

/** "더 보기" - 다음 페이지를 이어서 불러옵니다. */
function handleCurationMore() {
  curationPage += 1;
  loadCurationTrends(true);
}

/**
 * 트렌드를 노트로 저장합니다.
 * @param {Object} item - 트렌드 항목
 * @param {HTMLButtonElement} button - 클릭된 버튼 (진행 상태 표시용)
 */
async function handleSaveTrend(item, button) {
  button.disabled = true;
  button.textContent = '저장 중…';

  try {
    await apiFetch('/api/trends/save', {
      method: 'POST',
      body: JSON.stringify({ trend_id: item.id }),
    });

    button.textContent = '✅ 저장됨';
    button.disabled = true;

    // 새로 담은 노트가 바로 보이도록 목록만 갱신
    loadNotes();
  } catch (error) {
    button.disabled = false;
    button.textContent = '📌 노트로 저장';
    showError(`노트 저장 실패: ${error.message}`);
  }
}

/**
 * 내 노트를 삭제합니다. 성공하면 목록에서 바로 제거합니다.
 * @param {Object} note - 삭제할 노트
 * @param {HTMLButtonElement} button - 클릭된 삭제 버튼
 */
async function handleDeleteNote(note, button) {
  // 권한 판정을 못 하면 삭제하지 않습니다(fail-closed).
  // script.js가 아직 로드되지 않았거나 세션 복원 전이면 관리자로 볼 수 없습니다.
  if (typeof canDeleteContent !== 'function' || !canDeleteContent()) {
    return;
  }
  const title = note.title || '이 노트';
  if (!window.confirm(`「${title}」을(를) 삭제할까요?`)) {
    return;
  }

  button.disabled = true;
  showError(null);

  try {
    await apiFetch(`/api/notes/${note.id}`, { method: 'DELETE' });

    myNotes = myNotes.filter((item) => item.id !== note.id);
    notesTotal = Math.max(0, notesTotal - 1);
    renderNotes(myNotes);
    setText($('notesCount'), `${notesTotal}건`);

    // 같은 트렌드를 다시 저장할 수 있도록 카드 버튼을 되돌립니다.
    unlockTrendSaveButton(note);
  } catch (error) {
    button.disabled = false;
    showError(`노트 삭제 실패: ${error.message}`);
  }
}

/**
 * 삭제한 노트와 연결된 트렌드 카드의 '저장됨'을 다시 저장 가능하게 바꿉니다.
 * @param {Object} note - 방금 삭제한 노트
 */
function unlockTrendSaveButton(note) {
  const content = note.content || '';
  const urlMatch = content.match(/https?:\/\/[^\s)]+/);
  const noteUrl = urlMatch ? urlMatch[0] : '';

  document.querySelectorAll('#curationTrends article').forEach((card) => {
    const trendUrl = card.dataset.trendUrl || '';
    const trendTitle = card.dataset.trendTitle || '';
    const matchesUrl = noteUrl && trendUrl && trendUrl === noteUrl;
    const matchesTitle = !noteUrl && trendTitle && trendTitle === (note.title || '');

    if (!matchesUrl && !matchesTitle) return;

    const saveBtn = card.querySelector('[data-role="save-note"]');
    if (!saveBtn) return;

    saveBtn.disabled = false;
    saveBtn.textContent = '📌 노트로 저장';
  });
}

/** "지금 수집" - 외부 소스에서 최신 트렌드를 즉시 수집합니다. */
async function handleCollectNow() {
  const button = $('collectBtn');

  button.disabled = true;
  button.textContent = '수집 중…';
  showError(null);

  try {
    const data = await apiFetch('/api/trends/refresh', {
      method: 'POST',
      body: JSON.stringify({ limit_per_source: 20 }),
    });

    setText($('curationCount'), `방금 ${data.saved}건 신규 저장 (${data.duplicates}건 중복)`);

    curationPage = 1;
    await loadCurationTrends(false);
  } catch (error) {
    showError(`수집 실패: ${error.message}`);
  } finally {
    button.disabled = false;
    button.textContent = '🛰️ 지금 수집';
  }
}

// ============ 초기화 ============

/** 큐레이션 화면의 이벤트를 바인딩합니다. (script.js의 init에서 호출) */
function initCuration() {
  $('curationFilterForm').addEventListener('submit', handleCurationFilter);
  $('curationMoreBtn').addEventListener('click', handleCurationMore);
  $('collectBtn').addEventListener('click', handleCollectNow);

  // 삭제 버튼은 목록을 다시 그릴 때마다 생기므로, 부모에서 한 번만 받습니다.
  $('notesList').addEventListener('click', (event) => {
    const button = event.target.closest('[data-role="delete-note"]');
    if (!button) return;

    const row = button.closest('li[data-note-id]');
    const noteId = Number(row && row.dataset.noteId);
    const note = myNotes.find((item) => Number(item.id) === noteId);
    if (!note) {
      showError('삭제할 노트를 찾지 못했습니다. 목록을 새로고침해 주세요.');
      return;
    }

    handleDeleteNote(note, button);
  });
}
