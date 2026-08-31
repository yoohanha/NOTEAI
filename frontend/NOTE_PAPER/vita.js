/**
 * NOTE_PAPER 학술·전문 이력
 *
 * - GET    /api/vita
 * - POST   /api/vita/publications|certificates|teachings
 * - DELETE /api/vita/{type}/{id}
 */

const TOKEN_KEY = 'noteai_token';

const state = {
  publications: [],
  certificates: [],
  teachings: [],
};

let activeForm = 'publication';

const FORMS = {
  publication: {
    title: '논문 추가',
    path: '/api/vita/publications',
    key: 'publications',
    fields: [
      { name: 'title', label: '논문 제목', required: true, placeholder: '예: Efficient Note Graphs' },
      { name: 'venue', label: '학술지/학회', placeholder: '예: ACL 2025' },
      { name: 'year', label: '발표 연도', placeholder: '2025' },
      { name: 'role', label: '역할', placeholder: '예: 제1저자' },
      { name: 'link_or_status', label: '링크 또는 상태', placeholder: 'https://... 또는 게재 확정' },
    ],
  },
  certificate: {
    title: '자격증 추가',
    path: '/api/vita/certificates',
    key: 'certificates',
    fields: [
      { name: 'name', label: '자격증명', required: true, placeholder: '예: 정보처리기사' },
      { name: 'organization', label: '발행 기관', placeholder: '예: 한국산업인력공단' },
      { name: 'acquired_on', label: '취득일', type: 'date' },
    ],
  },
  teaching: {
    title: '교육 경력 추가',
    path: '/api/vita/teachings',
    key: 'teachings',
    fields: [
      { name: 'institution', label: '기관/학교명', required: true, placeholder: '예: NoteAI University' },
      { name: 'course', label: '과목/강의명', placeholder: '예: 딥러닝 입문' },
      { name: 'period', label: '기간', placeholder: '예: 2024.03 – 2025.02' },
      { name: 'role', label: '역할', placeholder: '예: 시간강사' },
    ],
  },
};

const $ = (id) => document.getElementById(id);

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function showError(message) {
  const el = $('vitaError');
  if (!message) {
    el.classList.add('hidden');
    el.textContent = '';
    return;
  }
  el.textContent = message;
  el.classList.remove('hidden');
}

function setStatus(message) {
  $('vitaStatus').textContent = message || '';
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function isUrl(value) {
  return /^https?:\/\//i.test(value || '');
}

async function apiJson(path, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) {
    window.location.href = '/';
    throw new Error('세션이 만료되었습니다. 다시 로그인하세요.');
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail;
    throw new Error(typeof detail === 'string' ? detail : payload.message || '요청 실패');
  }
  return payload.data;
}

function deleteButton(kind, id) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className =
    'text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 px-3 py-1.5 rounded-xl';
  button.textContent = '삭제';
  button.addEventListener('click', () => handleDelete(kind, id, button));
  return button;
}

function fillTable(bodyId, emptyId, rows, renderRow) {
  const body = $(bodyId);
  const empty = $(emptyId);
  body.replaceChildren();
  if (!rows.length) {
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');
  const fragment = document.createDocumentFragment();
  rows.forEach((item) => fragment.appendChild(renderRow(item)));
  body.appendChild(fragment);
}

function renderAll() {
  fillTable('publicationBody', 'publicationEmpty', state.publications, (item) => {
    const row = document.createElement('tr');
    const link = item.link_or_status || '–';
    const linkHtml = isUrl(item.link_or_status)
      ? `<a class="text-forest-600 hover:underline break-all" href="${escapeHtml(item.link_or_status)}" target="_blank" rel="noopener">링크</a>`
      : escapeHtml(link);
    row.innerHTML = `
      <td class="px-4 py-4 font-medium">${escapeHtml(item.title)}</td>
      <td class="px-4 py-4 text-ink-muted">${escapeHtml(item.venue || '–')}</td>
      <td class="px-4 py-4 text-ink-muted whitespace-nowrap">${escapeHtml(item.year || '–')}</td>
      <td class="px-4 py-4 text-ink-muted">${escapeHtml(item.role || '–')}</td>
      <td class="px-4 py-4 text-ink-muted">${linkHtml}</td>
      <td class="px-4 py-4 text-right"></td>
    `;
    row.lastElementChild.appendChild(deleteButton('publications', item.id));
    return row;
  });

  fillTable('certificateBody', 'certificateEmpty', state.certificates, (item) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td class="px-4 py-4 font-medium">${escapeHtml(item.name)}</td>
      <td class="px-4 py-4 text-ink-muted">${escapeHtml(item.organization || '–')}</td>
      <td class="px-4 py-4 text-ink-muted whitespace-nowrap">${escapeHtml(item.acquired_on || '–')}</td>
      <td class="px-4 py-4 text-right"></td>
    `;
    row.lastElementChild.appendChild(deleteButton('certificates', item.id));
    return row;
  });

  fillTable('teachingBody', 'teachingEmpty', state.teachings, (item) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td class="px-4 py-4 font-medium">${escapeHtml(item.institution)}</td>
      <td class="px-4 py-4 text-ink-muted">${escapeHtml(item.course || '–')}</td>
      <td class="px-4 py-4 text-ink-muted whitespace-nowrap">${escapeHtml(item.period || '–')}</td>
      <td class="px-4 py-4 text-ink-muted">${escapeHtml(item.role || '–')}</td>
      <td class="px-4 py-4 text-right"></td>
    `;
    row.lastElementChild.appendChild(deleteButton('teachings', item.id));
    return row;
  });
}

function openModal(kind) {
  activeForm = kind;
  const spec = FORMS[kind];
  $('vitaModalTitle').textContent = spec.title;
  const form = $('vitaForm');
  form.replaceChildren();
  spec.fields.forEach((field) => {
    const wrap = document.createElement('label');
    wrap.className = 'block';
    wrap.innerHTML = `
      <span class="block text-xs font-medium text-ink-muted mb-1">${escapeHtml(field.label)}</span>
      <input name="${field.name}" ${field.required ? 'required' : ''}
             type="${field.type || 'text'}" maxlength="400" autocomplete="off"
             placeholder="${escapeHtml(field.placeholder || '')}"
             class="w-full rounded-xl border border-cream-200 bg-cream-50 px-3 py-2.5 text-sm">
    `;
    form.appendChild(wrap);
  });
  $('vitaModal').classList.remove('hidden');
  const first = form.querySelector('input');
  if (first) first.focus();
}

function closeModal() {
  $('vitaModal').classList.add('hidden');
}

async function handleSubmit(event) {
  event.preventDefault();
  const spec = FORMS[activeForm];
  const form = new FormData(event.target);
  const payload = {};
  spec.fields.forEach((field) => {
    payload[field.name] = String(form.get(field.name) || '').trim();
  });

  showError(null);
  try {
    const created = await apiJson(spec.path, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    state[spec.key].unshift(created);
    closeModal();
    renderAll();
    setStatus('항목을 추가했습니다.');
  } catch (error) {
    showError(error.message);
  }
}

async function handleDelete(kind, id, button) {
  if (!window.confirm('이 항목을 삭제할까요?')) return;
  button.disabled = true;
  try {
    await apiJson(`/api/vita/${kind}/${id}`, { method: 'DELETE' });
    state[kind] = state[kind].filter((row) => row.id !== id);
    renderAll();
    setStatus('항목을 삭제했습니다.');
  } catch (error) {
    button.disabled = false;
    showError(error.message);
  }
}

async function initVitaPage() {
  if (!getToken()) {
    window.location.href = '/';
    return;
  }

  document.querySelectorAll('[data-open-form]').forEach((button) => {
    button.addEventListener('click', () => openModal(button.getAttribute('data-open-form')));
  });
  $('vitaModalCancel').addEventListener('click', closeModal);
  $('vitaModal').addEventListener('click', (event) => {
    if (event.target === $('vitaModal')) closeModal();
  });
  $('vitaForm').addEventListener('submit', handleSubmit);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeModal();
  });

  try {
    const data = await apiJson('/api/vita');
    state.publications = data.publications || [];
    state.certificates = data.certificates || [];
    state.teachings = data.teachings || [];
    renderAll();
  } catch (error) {
    showError(error.message);
    renderAll();
  }
}

initVitaPage();
