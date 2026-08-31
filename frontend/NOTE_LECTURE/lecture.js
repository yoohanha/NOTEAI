/**
 * NOTE_LECTURE 강좌 폴더 / 교안 관리
 *
 * - GET    /api/lectures
 * - POST   /api/lectures
 * - GET    /api/lectures/{id}
 * - DELETE /api/lectures/{id}
 * - POST   /api/lectures/{id}/files
 * - GET    /api/lectures/{id}/files/{fileId}
 * - DELETE /api/lectures/{id}/files/{fileId}
 */

const TOKEN_KEY = 'noteai_token';
const ALLOWED_EXT = /\.(pdf|pptx?|docx?|odp|odt|txt|md)$/i;

/** @type {{id:number, name:string, file_count:number, created_at:string}[]} */
let courses = [];

/** @type {{id:number, name:string, file_count:number}|null} */
let currentCourse = null;

/** @type {{id:number, original_name:string, extension:string, size_bytes:number, created_at:string, mime_type:string}[]} */
let files = [];
let canDelete = false;

const $ = (id) => document.getElementById(id);

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function showError(message) {
  const el = $('lectureError');
  if (!message) {
    el.classList.add('hidden');
    el.textContent = '';
    return;
  }
  el.textContent = message;
  el.classList.remove('hidden');
}

function setStatus(message) {
  $('lectureStatus').textContent = message || '';
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatTime(value) {
  if (!value) return '–';
  const normalized = /[Z+]|-\d{2}:\d{2}$/.test(value) ? value : `${value}Z`;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return '–';
  return date.toLocaleString('ko-KR');
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

  if (response.status === 204) return null;
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail;
    throw new Error(typeof detail === 'string' ? detail : payload.message || '요청 실패');
  }
  return payload.data;
}

function courseHash(courseId) {
  return courseId ? `#/course/${courseId}` : '#/';
}

function parseHash() {
  const match = (window.location.hash || '').match(/^#\/course\/(\d+)$/);
  return match ? Number(match[1]) : null;
}

function showCourseList() {
  currentCourse = null;
  files = [];
  $('courseView').classList.remove('hidden');
  $('folderView').classList.add('hidden');
  $('addCourseBtn').classList.remove('hidden');
  renderCourses();
}

function showFolderView() {
  $('courseView').classList.add('hidden');
  $('folderView').classList.remove('hidden');
  $('addCourseBtn').classList.add('hidden');
}

function renderCourses() {
  const grid = $('courseGrid');
  const empty = $('courseEmpty');
  grid.replaceChildren();
  $('lectureMeta').textContent = courses.length ? `${courses.length}개 강좌` : '';

  if (!courses.length) {
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  const fragment = document.createDocumentFragment();
  courses.forEach((course) => {
    const card = document.createElement('article');
    card.className = 'lecture-folder-card';
    card.setAttribute('role', 'listitem');

    const open = document.createElement('button');
    open.type = 'button';
    open.className = 'lecture-folder-open';
    open.innerHTML = `
      <span class="lecture-folder-icon" aria-hidden="true">
        <svg viewBox="0 0 48 48" fill="none">
          <path d="M8 16h12l4 4h16v18H8V16z" fill="#E8DCC8"/>
          <path d="M8 20h32v18H8V20z" fill="#FFFBF5"/>
          <path d="M8 16h12l4 4H8V16z" fill="#D9C9B0"/>
        </svg>
      </span>
      <span class="block text-sm font-semibold tracking-tight truncate">${escapeHtml(course.name)}</span>
      <span class="block text-xs text-ink-faint mt-1">${course.file_count || 0}개 파일</span>
    `;
    open.addEventListener('click', () => {
      window.location.hash = courseHash(course.id);
    });

    card.append(open);
    if (canDelete) {
      const del = document.createElement('button');
      del.type = 'button';
      del.className = 'lecture-folder-delete';
      del.textContent = '삭제';
      del.addEventListener('click', (event) => {
        event.stopPropagation();
        handleDeleteCourse(course, del);
      });
      card.appendChild(del);
    }
    fragment.appendChild(card);
  });
  grid.appendChild(fragment);
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function renderFiles() {
  const body = $('fileTableBody');
  const empty = $('fileEmpty');
  body.replaceChildren();
  $('folderTitle').textContent = currentCourse ? currentCourse.name : '';
  $('lectureMeta').textContent = currentCourse
    ? `${files.length}개 교안`
    : '';

  if (!files.length) {
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  const fragment = document.createDocumentFragment();
  files.forEach((item) => {
    const row = document.createElement('tr');

    const name = document.createElement('td');
    name.className = 'px-4 py-4';
    const open = document.createElement('button');
    open.type = 'button';
    open.className = 'text-left font-medium hover:underline';
    open.textContent = item.original_name;
    open.addEventListener('click', () => openFile(item));
    name.appendChild(open);

    const ext = document.createElement('td');
    ext.className = 'px-4 py-4 text-ink-muted uppercase';
    ext.textContent = item.extension || '–';

    const size = document.createElement('td');
    size.className = 'px-4 py-4 text-ink-muted whitespace-nowrap';
    size.textContent = formatBytes(item.size_bytes);

    const date = document.createElement('td');
    date.className = 'px-4 py-4 text-ink-muted whitespace-nowrap';
    date.textContent = formatTime(item.created_at);

    const actions = document.createElement('td');
    actions.className = 'px-4 py-4 text-right whitespace-nowrap';

    const preview = document.createElement('button');
    preview.type = 'button';
    preview.className =
      'text-xs font-medium text-forest-600 bg-forest-50 hover:bg-forest-100 px-3 py-1.5 rounded-xl mr-1';
    preview.textContent = item.extension === 'pdf' ? '미리보기' : '열기';
    preview.addEventListener('click', () => openFile(item));

    actions.append(preview);
    if (canDelete) {
      const del = document.createElement('button');
      del.type = 'button';
      del.className =
        'text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 px-3 py-1.5 rounded-xl';
      del.textContent = '삭제';
      del.addEventListener('click', () => handleDeleteFile(item, del));
      actions.appendChild(del);
    }
    row.append(name, ext, size, date, actions);
    fragment.appendChild(row);
  });
  body.appendChild(fragment);
}

async function loadCourses() {
  const data = await apiJson('/api/lectures');
  courses = data.items || [];
  renderCourses();
}

async function openCourse(courseId) {
  const data = await apiJson(`/api/lectures/${courseId}`);
  currentCourse = data.course;
  files = data.files || [];
  showFolderView();
  renderFiles();
}

async function handleRoute() {
  showError(null);
  const courseId = parseHash();
  if (!courseId) {
    showCourseList();
    await loadCourses();
    return;
  }
  try {
    await openCourse(courseId);
  } catch (error) {
    showError(error.message);
    window.location.hash = '#/';
  }
}

function openNameModal() {
  $('nameModal').classList.remove('hidden');
  $('courseNameInput').value = '';
  $('courseNameInput').focus();
}

function closeNameModal() {
  $('nameModal').classList.add('hidden');
}

async function handleCreateCourse(event) {
  event.preventDefault();
  const name = $('courseNameInput').value.trim();
  if (!name) {
    showError('강좌 이름을 입력하세요.');
    return;
  }

  showError(null);
  try {
    const created = await apiJson('/api/lectures', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
    courses.unshift(created);
    closeNameModal();
    renderCourses();
    setStatus(`「${created.name}」 강좌를 만들었습니다.`);
  } catch (error) {
    showError(error.message);
  }
}

async function handleDeleteCourse(course, button) {
  if (!canDelete) return;
  if (!window.confirm(`「${course.name}」 강좌와 안의 교안을 모두 삭제할까요?`)) return;
  button.disabled = true;
  try {
    await apiJson(`/api/lectures/${course.id}`, { method: 'DELETE' });
    courses = courses.filter((row) => row.id !== course.id);
    if (currentCourse && currentCourse.id === course.id) {
      window.location.hash = '#/';
    } else {
      renderCourses();
    }
    setStatus('강좌 폴더를 삭제했습니다.');
  } catch (error) {
    button.disabled = false;
    showError(error.message);
  }
}

async function uploadFiles(fileList) {
  if (!currentCourse) return;
  const selected = [...fileList].filter((file) => ALLOWED_EXT.test(file.name));
  if (!selected.length) {
    showError('PDF, PPT, DOC 등 교안 파일만 올릴 수 있습니다.');
    return;
  }

  showError(null);
  setStatus(`${selected.length}개 올리는 중…`);

  for (const file of selected) {
    const form = new FormData();
    form.append('file', file);
    try {
      const created = await apiJson(`/api/lectures/${currentCourse.id}/files`, {
        method: 'POST',
        body: form,
      });
      files.unshift(created);
      const card = courses.find((row) => row.id === currentCourse.id);
      if (card) card.file_count = (card.file_count || 0) + 1;
    } catch (error) {
      showError(`${file.name}: ${error.message}`);
    }
  }

  renderFiles();
  setStatus('업로드가 반영되었습니다.');
}

async function handleDeleteFile(item, button) {
  if (!canDelete || !currentCourse) return;
  if (!window.confirm(`「${item.original_name}」을(를) 삭제할까요?`)) return;
  button.disabled = true;
  try {
    await apiJson(`/api/lectures/${currentCourse.id}/files/${item.id}`, { method: 'DELETE' });
    files = files.filter((row) => row.id !== item.id);
    const card = courses.find((row) => row.id === currentCourse.id);
    if (card) card.file_count = Math.max(0, (card.file_count || 1) - 1);
    renderFiles();
    setStatus('교안을 삭제했습니다.');
  } catch (error) {
    button.disabled = false;
    showError(error.message);
  }
}

async function openFile(item) {
  if (!currentCourse) return;

  if (item.public_url) {
    if (item.extension === 'pdf') {
      const modal = $('previewModal');
      const box = $('previewModalBody');
      box.replaceChildren();
      const frame = document.createElement('iframe');
      frame.src = item.public_url;
      frame.title = item.original_name;
      frame.className = 'lecture-preview-frame';
      box.appendChild(frame);
      modal.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
      return;
    }
    window.open(item.public_url, '_blank', 'noopener');
    return;
  }

  const token = getToken();
  const response = await fetch(
    `/api/lectures/${currentCourse.id}/files/${item.id}`,
    { headers: token ? { Authorization: `Bearer ${token}` } : {} }
  );
  if (!response.ok) {
    showError('파일을 열 수 없습니다.');
    return;
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);

  if (item.extension === 'pdf') {
    const modal = $('previewModal');
    const box = $('previewModalBody');
    box.replaceChildren();
    const frame = document.createElement('iframe');
    frame.src = url;
    frame.title = item.original_name;
    frame.className = 'lecture-preview-frame';
    box.appendChild(frame);
    modal.dataset.blobUrl = url;
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    return;
  }

  const link = document.createElement('a');
  link.href = url;
  link.download = item.original_name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

function closePreview() {
  const modal = $('previewModal');
  const url = modal.dataset.blobUrl;
  if (url) URL.revokeObjectURL(url);
  delete modal.dataset.blobUrl;
  modal.classList.add('hidden');
  $('previewModalBody').replaceChildren();
  document.body.style.overflow = '';
}

function bindDropZone() {
  const zone = $('dropZone');
  const input = $('lectureFileInput');

  ['dragenter', 'dragover'].forEach((type) => {
    zone.addEventListener(type, (event) => {
      event.preventDefault();
      zone.classList.add('lecture-drop-active');
    });
  });

  ['dragleave', 'drop'].forEach((type) => {
    zone.addEventListener(type, (event) => {
      event.preventDefault();
      zone.classList.remove('lecture-drop-active');
    });
  });

  zone.addEventListener('drop', (event) => {
    if (event.dataTransfer && event.dataTransfer.files.length) {
      uploadFiles(event.dataTransfer.files);
    }
  });

  input.addEventListener('change', () => {
    if (input.files && input.files.length) {
      uploadFiles(input.files);
      input.value = '';
    }
  });
}

function applyDeleteVisibility() {
  const btn = $('deleteCourseBtn');
  if (!btn) return;
  btn.classList.toggle('hidden', !canDelete);
  btn.disabled = !canDelete;
}

async function initLecturePage() {
  if (!getToken()) {
    window.location.href = '/';
    return;
  }

  $('addCourseBtn').addEventListener('click', openNameModal);
  $('nameModalCancel').addEventListener('click', closeNameModal);
  $('nameModal').addEventListener('click', (event) => {
    if (event.target === $('nameModal')) closeNameModal();
  });
  $('nameForm').addEventListener('submit', handleCreateCourse);
  $('backToCoursesBtn').addEventListener('click', () => {
    window.location.hash = '#/';
  });
  $('deleteCourseBtn').addEventListener('click', () => {
    if (currentCourse) handleDeleteCourse(currentCourse, $('deleteCourseBtn'));
  });
  $('previewModalClose').addEventListener('click', closePreview);
  $('previewModal').addEventListener('click', (event) => {
    if (event.target === $('previewModal')) closePreview();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    closeNameModal();
    closePreview();
  });
  window.addEventListener('hashchange', () => {
    handleRoute().catch((error) => showError(error.message));
  });

  bindDropZone();

  try {
    const me = await apiJson('/api/auth/me');
    canDelete = Boolean(me && me.is_admin);
    applyDeleteVisibility();
    await handleRoute();
  } catch (error) {
    showError(error.message);
  }
}

initLecturePage();
