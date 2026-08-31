/**
 * NOTE_3D 미디어 라이브러리
 *
 * - GET    /api/media
 * - POST   /api/media          multipart file
 * - GET    /api/media/{id}/file
 * - DELETE /api/media/{id}
 */

const TOKEN_KEY = 'noteai_token';
const ALLOWED_EXT = /\.(png|jpe?g|webp|gif|mp4|webm|mov)$/i;

/** @type {{id:number, original_name:string, mime_type:string, kind:string, size_bytes:number, created_at:string, previewUrl?:string}[]} */
let mediaItems = [];

const $ = (id) => document.getElementById(id);

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function showError(message) {
  const el = $('mediaError');
  if (!message) {
    el.classList.add('hidden');
    el.textContent = '';
    return;
  }
  el.textContent = message;
  el.classList.remove('hidden');
}

function setStatus(message) {
  $('mediaStatus').textContent = message || '';
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

async function loadPreviewUrl(item) {
  if (item.previewUrl) return item.previewUrl;
  const token = getToken();
  const response = await fetch(`/api/media/${item.id}/file`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) throw new Error('미리보기를 불러오지 못했습니다.');
  const blob = await response.blob();
  item.previewUrl = URL.createObjectURL(blob);
  return item.previewUrl;
}

function revokePreviews() {
  mediaItems.forEach((item) => {
    if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
  });
}

function renderTable() {
  const body = $('mediaTableBody');
  const empty = $('mediaEmpty');
  body.replaceChildren();
  $('mediaCount').textContent = mediaItems.length ? `${mediaItems.length}건` : '';

  if (!mediaItems.length) {
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  const fragment = document.createDocumentFragment();
  mediaItems.forEach((item) => {
    const row = document.createElement('tr');
    row.className = 'align-middle';

    const previewCell = document.createElement('td');
    previewCell.className = 'px-4 py-3';
    const thumb = document.createElement('button');
    thumb.type = 'button';
    thumb.className = 'media-thumb';
    thumb.setAttribute('aria-label', `${item.original_name} 확대 보기`);

    if (item.kind === 'video') {
      const video = document.createElement('video');
      video.muted = true;
      video.loop = true;
      video.playsInline = true;
      video.preload = 'metadata';
      if (item.previewUrl) video.src = item.previewUrl;
      thumb.appendChild(video);
      thumb.addEventListener('mouseenter', () => {
        video.play().catch(() => {});
      });
      thumb.addEventListener('mouseleave', () => {
        video.pause();
        video.currentTime = 0;
      });
    } else {
      const img = document.createElement('img');
      img.alt = item.original_name;
      if (item.previewUrl) img.src = item.previewUrl;
      thumb.appendChild(img);
    }

    thumb.addEventListener('click', () => openModal(item));
    previewCell.appendChild(thumb);

    const name = document.createElement('td');
    name.className = 'px-4 py-3 font-medium break-all';
    name.textContent = item.original_name;

    const kind = document.createElement('td');
    kind.className = 'px-4 py-3 text-ink-muted';
    kind.textContent = item.kind === 'video' ? '동영상' : '이미지';

    const size = document.createElement('td');
    size.className = 'px-4 py-3 text-ink-muted whitespace-nowrap';
    size.textContent = formatBytes(item.size_bytes);

    const date = document.createElement('td');
    date.className = 'px-4 py-3 text-ink-muted whitespace-nowrap';
    date.textContent = formatTime(item.created_at);

    const actions = document.createElement('td');
    actions.className = 'px-4 py-3 text-right';
    const del = document.createElement('button');
    del.type = 'button';
    del.className =
      'text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 border border-red-200 px-2.5 py-1 rounded-lg';
    del.textContent = '삭제';
    del.addEventListener('click', () => handleDelete(item, del));
    actions.appendChild(del);

    row.append(previewCell, name, kind, size, date, actions);
    fragment.appendChild(row);
  });
  body.appendChild(fragment);
}

function openModal(item) {
  const modal = $('mediaModal');
  const box = $('mediaModalBody');
  box.replaceChildren();

  if (item.kind === 'video') {
    const video = document.createElement('video');
    video.controls = true;
    video.autoplay = true;
    video.src = item.previewUrl;
    box.appendChild(video);
  } else {
    const img = document.createElement('img');
    img.alt = item.original_name;
    img.src = item.previewUrl;
    box.appendChild(img);
  }

  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  $('mediaModal').classList.add('hidden');
  $('mediaModalBody').replaceChildren();
  document.body.style.overflow = '';
}

async function refreshList() {
  const data = await apiJson('/api/media');
  revokePreviews();
  mediaItems = data.items || [];
  await Promise.all(
    mediaItems.map(async (item) => {
      try {
        await loadPreviewUrl(item);
      } catch (_error) {
        /* 미리보기 실패해도 행은 남깁니다 */
      }
    })
  );
  renderTable();
}

async function uploadFiles(fileList) {
  const files = [...fileList].filter((file) => ALLOWED_EXT.test(file.name));
  if (!files.length) {
    showError('이미지 또는 동영상 파일만 올릴 수 있습니다.');
    return;
  }

  showError(null);
  setStatus(`${files.length}개 올리는 중…`);

  for (const file of files) {
    const form = new FormData();
    form.append('file', file);
    try {
      const created = await apiJson('/api/media', { method: 'POST', body: form });
      await loadPreviewUrl(created);
      mediaItems.unshift(created);
    } catch (error) {
      showError(`${file.name}: ${error.message}`);
    }
  }

  renderTable();
  setStatus('업로드가 반영되었습니다.');
}

async function handleDelete(item, button) {
  if (!window.confirm(`「${item.original_name}」을(를) 삭제할까요?`)) return;
  button.disabled = true;
  try {
    await apiJson(`/api/media/${item.id}`, { method: 'DELETE' });
    if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
    mediaItems = mediaItems.filter((row) => row.id !== item.id);
    renderTable();
    setStatus('파일을 삭제했습니다.');
  } catch (error) {
    button.disabled = false;
    showError(error.message);
  }
}

function bindDropZone() {
  const zone = $('dropZone');
  const input = $('mediaFileInput');

  ['dragenter', 'dragover'].forEach((type) => {
    zone.addEventListener(type, (event) => {
      event.preventDefault();
      zone.classList.add('media-drop-active');
    });
  });

  ['dragleave', 'drop'].forEach((type) => {
    zone.addEventListener(type, (event) => {
      event.preventDefault();
      zone.classList.remove('media-drop-active');
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

async function initMediaPage() {
  if (!getToken()) {
    window.location.href = '/';
    return;
  }

  bindDropZone();
  $('mediaModalClose').addEventListener('click', closeModal);
  $('mediaModal').addEventListener('click', (event) => {
    if (event.target === $('mediaModal')) closeModal();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeModal();
  });

  try {
    await refreshList();
  } catch (error) {
    showError(error.message);
  }
}

initMediaPage();
