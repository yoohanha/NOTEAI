/**
 * NOTEAI 대시보드 - 공용 유틸 및 수집 모니터 화면
 *
 * 이 파일이 담당하는 것
 * - 인증(로그인/회원가입) 및 세션 처리
 * - 공용 유틸: apiFetch / $ / setText / formatTime / showError
 * - 상단 탭 라우팅 (📡 수집 모니터 · 📚 노트 큐레이션 · 🕸️ 토픽 지식 그래프)
 * - 📡 수집 모니터 화면 렌더링
 *
 * 큐레이션·그래프 화면 로직은 각각 curation.js / graph.js에 있으며,
 * 여기서 정의한 공용 유틸을 그대로 사용합니다.
 *
 * 사용 API
 * - /api/monitor/status : 워커 상태 + 통계 + 자가 진단 + 실행 이력 (1회 요청으로 통합 조회)
 * - /api/trends         : 최근 수집 항목
 */

// ============ 상수 ============

const API_BASE = '';                    // 같은 오리진에서 서빙되므로 상대 경로 사용
const TOKEN_KEY = 'noteai_token';       // 액세스 토큰 저장 키
const REFRESH_INTERVAL_MS = 15000;      // 자동 새로고침 주기 (15초)

// 진단 심각도별 배지 스타일
const SEVERITY_STYLES = {
  critical: 'bg-red-100 text-red-700 border-red-200',
  high: 'bg-orange-100 text-orange-700 border-orange-200',
  medium: 'bg-amber-100 text-amber-700 border-amber-200',
  low: 'bg-sky-100 text-sky-700 border-sky-200',
};

// 진단 판정별 배지 스타일
const VERDICT_STYLES = {
  healthy: 'bg-emerald-100 text-emerald-700',
  degraded: 'bg-amber-100 text-amber-700',
  unhealthy: 'bg-red-100 text-red-700',
  unknown: 'bg-cream-100 text-ink-muted',
};

const VERDICT_LABELS = {
  healthy: '정상',
  degraded: '주의',
  unhealthy: '비정상',
  unknown: '알 수 없음',
};

// 수집 결과별 배지 스타일
const RUN_STATUS_STYLES = {
  success: 'bg-emerald-100 text-emerald-700',
  partial: 'bg-amber-100 text-amber-700',
  failed: 'bg-red-100 text-red-700',
};

const RUN_STATUS_LABELS = {
  success: '성공',
  partial: '부분 성공',
  failed: '실패',
};

// 상단 탭 스타일 (활성/비활성)
const NAV_ACTIVE_CLASS =
  'nav-tab whitespace-nowrap text-sm font-medium px-3 py-3 border-b-2 transition ' +
  'border-forest-600 text-forest-700';
const NAV_INACTIVE_CLASS =
  'nav-tab whitespace-nowrap text-sm font-medium px-3 py-3 border-b-2 transition ' +
  'border-transparent text-ink-muted hover:text-ink';

// 탭 id -> {버튼, 패널} 매핑
const VIEWS = {
  monitor: { tab: 'navMonitor', panel: 'panelMonitor' },
  curation: { tab: 'navCuration', panel: 'panelCuration' },
  graph: { tab: 'navGraph', panel: 'panelGraph' },
};

// ============ 상태 ============

let refreshTimer = null;

// 현재 열려 있는 탭 - 자동 새로고침 대상 판단에 사용
let activeView = 'monitor';

// ============ 유틸 ============

/**
 * id로 엘리먼트를 조회합니다.
 * @param {string} id - 엘리먼트 id
 * @returns {HTMLElement} 엘리먼트
 */
const $ = (id) => document.getElementById(id);

/**
 * 저장된 액세스 토큰을 반환합니다.
 * @returns {string|null} 토큰
 */
const getToken = () => localStorage.getItem(TOKEN_KEY);

/**
 * XSS를 막기 위해 텍스트로만 삽입합니다.
 * @param {HTMLElement} el - 대상 엘리먼트
 * @param {string} text - 삽입할 텍스트
 */
const setText = (el, text) => { el.textContent = text ?? '–'; };

/**
 * 인증 헤더를 붙여 API를 호출합니다.
 * @param {string} path - API 경로
 * @param {Object} options - fetch 옵션
 * @returns {Promise<Object>} 응답 JSON의 data 필드
 * @throws {Error} 요청 실패 시
 */
async function apiFetch(path, options = {}) {
  const token = getToken();

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  // 토큰이 만료되면 로그인 화면으로 되돌림
  if (response.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    showLogin();
    throw new Error('세션이 만료되었습니다. 다시 로그인하세요.');
  }

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(extractErrorMessage(payload, response.status));
  }

  return payload.data;
}

/**
 * 서버 오류 응답에서 사람이 읽을 메시지를 뽑아냅니다.
 *
 * FastAPI는 검증 실패(422) 시 detail을 객체 배열로 돌려주므로,
 * 그대로 표시하면 "[object Object]"가 됩니다. 필드명과 사유를
 * 한국어로 풀어서 보여줍니다.
 *
 * @param {Object} payload - 응답 JSON
 * @param {number} httpStatus - HTTP 상태 코드
 * @returns {string} 표시할 오류 메시지
 */
function extractErrorMessage(payload, httpStatus) {
  const detail = payload?.detail;

  // 400 등 단순 문자열 detail
  if (typeof detail === 'string') return detail;

  // 422 검증 오류 - [{loc: ["body","email"], msg: "..."}]
  if (Array.isArray(detail) && detail.length > 0) {
    const fieldLabels = {
      username: '사용자명',
      email: '이메일',
      password: '비밀번호',
      full_name: '이름',
    };

    return detail
      .map((item) => {
        const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : '';
        const label = fieldLabels[field] || field;
        return label ? `${label}: ${item.msg}` : item.msg;
      })
      .join('\n');
  }

  return payload?.message || `요청 실패 (HTTP ${httpStatus})`;
}

/**
 * UTC 기준 시각 문자열을 로컬 시각으로 표시합니다.
 * 서버는 naive UTC를 반환하므로 Z를 붙여 UTC임을 명시합니다.
 * @param {string|null} value - ISO 시각 문자열
 * @returns {string} 표시용 문자열
 */
function formatTime(value) {
  if (!value) return '–';

  const normalized = /[Z+]|-\d{2}:\d{2}$/.test(value) ? value : `${value}Z`;
  const date = new Date(normalized);

  if (Number.isNaN(date.getTime())) return '–';

  return date.toLocaleString('ko-KR', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

/**
 * 기준 시각까지 남은 시간을 사람이 읽는 형태로 변환합니다.
 * @param {string|null} value - ISO 시각 문자열
 * @returns {string} 예: "12분 후", "지연됨"
 */
function formatCountdown(value) {
  if (!value) return '–';

  const normalized = /[Z+]|-\d{2}:\d{2}$/.test(value) ? value : `${value}Z`;
  const diffMs = new Date(normalized).getTime() - Date.now();

  if (Number.isNaN(diffMs)) return '–';
  if (diffMs <= 0) return '지연됨';

  const minutes = Math.floor(diffMs / 60000);

  if (minutes < 1) return '곧';
  if (minutes < 60) return `${minutes}분 후`;

  return `${Math.floor(minutes / 60)}시간 ${minutes % 60}분 후`;
}

/**
 * 전역 오류 배너를 표시하거나 숨깁니다.
 * @param {string|null} message - 표시할 메시지 (null이면 숨김)
 */
function showError(message) {
  const banner = $('errorBanner');

  if (!message) {
    banner.classList.add('hidden');
    return;
  }

  setText(banner, message);
  banner.classList.remove('hidden');
}

// ============ 화면 전환 ============

/** 인증 화면(로그인 탭)을 표시합니다. */
function showLogin() {
  stopAutoRefresh();
  $('dashboardView').classList.add('hidden');
  $('loginView').classList.remove('hidden');
  $('loginView').classList.add('flex');
  switchAuthTab('login');
}

/**
 * 로그인/회원가입 탭을 전환합니다.
 * @param {'login'|'signup'} tab - 표시할 탭
 */
function switchAuthTab(tab) {
  const isLogin = tab === 'login';

  // 폼 전환
  $('loginForm').classList.toggle('hidden', !isLogin);
  $('signupForm').classList.toggle('hidden', isLogin);

  // 탭 버튼 활성화 스타일
  const activeClass = 'flex-1 text-sm font-medium py-1.5 rounded-lg transition ' +
                      'bg-paper text-ink shadow-soft';
  const inactiveClass = 'flex-1 text-sm font-medium py-1.5 rounded-lg transition ' +
                        'text-ink-muted hover:text-ink';

  $('tabLogin').className = isLogin ? activeClass : inactiveClass;
  $('tabSignup').className = isLogin ? inactiveClass : activeClass;
  $('tabLogin').setAttribute('aria-selected', String(isLogin));
  $('tabSignup').setAttribute('aria-selected', String(!isLogin));

  setText(
    $('authSubtitle'),
    isLogin ? '대시보드를 보려면 로그인하세요.' : '계정을 만들면 바로 대시보드로 이동합니다.'
  );

  // 탭을 옮기면 이전 오류 메시지는 더 이상 유효하지 않음
  $('loginError').classList.add('hidden');
  $('signupError').classList.add('hidden');
}

/** 대시보드를 표시하고 데이터를 불러옵니다. */
function showDashboard() {
  $('loginView').classList.add('hidden');
  $('loginView').classList.remove('flex');
  $('dashboardView').classList.remove('hidden');

  // 모니터 탭을 기본 화면으로 열면서 데이터 로딩까지 함께 처리
  switchView('monitor');
}

/**
 * 상단 탭을 전환하고 해당 화면의 데이터를 불러옵니다.
 *
 * 자동 새로고침은 실시간성이 필요한 모니터 탭에서만 동작시켜
 * 다른 탭을 보는 동안 불필요한 폴링이 쌓이지 않게 합니다.
 *
 * @param {'monitor'|'curation'|'graph'} view - 표시할 화면
 */
function switchView(view) {
  if (!VIEWS[view]) return;

  activeView = view;

  // 탭 버튼과 패널의 표시 상태를 한 번에 갱신
  Object.entries(VIEWS).forEach(([name, ids]) => {
    const isActive = name === view;

    $(ids.tab).className = isActive ? NAV_ACTIVE_CLASS : NAV_INACTIVE_CLASS;
    $(ids.tab).setAttribute('aria-selected', String(isActive));
    $(ids.panel).classList.toggle('hidden', !isActive);
  });

  // 탭을 옮기면 이전 화면의 오류 메시지는 더 이상 유효하지 않음
  showError(null);

  // 자동 새로고침 체크박스는 모니터 탭에서만 의미가 있음
  $('autoRefreshLabel').classList.toggle('hidden', view !== 'monitor');

  if (view === 'monitor') {
    loadAll();
    if ($('autoRefresh').checked) startAutoRefresh();
  } else {
    stopAutoRefresh();
    refreshActiveView();
  }
}

/**
 * 현재 열려 있는 탭의 데이터를 다시 불러옵니다.
 * 새로고침 버튼이 탭마다 다르게 동작하도록 하는 진입점입니다.
 */
function refreshActiveView() {
  if (activeView === 'monitor') {
    loadAll();
  } else if (activeView === 'curation') {
    loadCuration();
  } else if (activeView === 'graph') {
    loadTopicSuggestions();
  }
}

// ============ 렌더링 ============

/**
 * 워커 상태 배지를 갱신합니다.
 * @param {Object} worker - 워커 상태
 */
function renderWorker(worker) {
  const dot = $('workerDot');
  const badge = $('workerBadge');

  let label;
  let dotColor;
  let badgeColor;

  if (!worker.running) {
    label = '워커 중지됨';
    dotColor = 'bg-red-500';
    badgeColor = 'bg-red-50 text-red-700';
  } else if (worker.stale) {
    // 프로세스는 살아 있으나 주기를 놓친 상태 - 멈춘 것과 구분해서 알림
    label = '워커 정체';
    dotColor = 'bg-amber-500';
    badgeColor = 'bg-amber-50 text-amber-700';
  } else {
    label = `워커 실행 중 (PID ${worker.pid})`;
    dotColor = 'bg-emerald-500 animate-pulse';
    badgeColor = 'bg-emerald-50 text-emerald-700';
  }

  setText($('workerText'), label);
  dot.className = `w-1.5 h-1.5 rounded-full ${dotColor}`;
  badge.className =
    `inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${badgeColor}`;
}

/**
 * 상단 지표 카드를 갱신합니다.
 * @param {Object} data - /api/monitor/status 응답 data
 */
function renderMetrics(data) {
  const { stats, worker } = data;

  setText($('mSuccessRate'), `${(stats.success_rate * 100).toFixed(0)}%`);
  setText(
    $('mRunCount'),
    `${stats.total_runs}회 실행 · 실패 ${stats.failed_runs}회`
  );

  setText($('mSaved'), stats.total_saved.toLocaleString('ko-KR'));
  setText($('mFetched'), `시도 ${stats.total_fetched.toLocaleString('ko-KR')}건`);

  setText($('mTotal'), (data.total_trends || 0).toLocaleString('ko-KR'));
  setText($('mAvgDuration'), `평균 ${stats.avg_duration_seconds.toFixed(1)}초`);

  setText($('mNextRun'), formatCountdown(worker.next_run_estimate));
  setText($('mLastRun'), `직전 ${formatTime(worker.last_run_at)}`);
}

/**
 * 자가 진단 결과를 렌더링합니다.
 * @param {Object} diagnosis - 진단 결과
 */
function renderDiagnosis(diagnosis) {
  const badge = $('verdictBadge');
  const verdict = diagnosis.verdict || 'unknown';

  setText(badge, VERDICT_LABELS[verdict] || verdict);
  badge.className =
    `text-xs font-medium px-2 py-0.5 rounded-full ${VERDICT_STYLES[verdict] || VERDICT_STYLES.unknown}`;

  setText($('diagSummary'), diagnosis.summary);

  const container = $('diagFindings');
  container.replaceChildren();

  if (!diagnosis.findings || diagnosis.findings.length === 0) {
    return;
  }

  diagnosis.findings.forEach((finding) => {
    const card = document.createElement('div');
    card.className =
      `rounded-lg border px-3 py-2.5 ${SEVERITY_STYLES[finding.severity] || SEVERITY_STYLES.low}`;

    // 제목 줄: 심각도 · 증상명 · 건수
    const head = document.createElement('div');
    head.className = 'flex items-center gap-2 flex-wrap';

    const sev = document.createElement('span');
    sev.className = 'text-xs font-bold uppercase';
    sev.textContent = finding.severity;

    const label = document.createElement('span');
    label.className = 'text-sm font-medium';
    label.textContent = finding.label;

    const count = document.createElement('span');
    count.className = 'text-xs opacity-70';
    count.textContent = `${finding.count}건`;

    head.append(sev, label, count);

    if (finding.transient) {
      const tag = document.createElement('span');
      tag.className = 'text-xs px-1.5 py-0.5 rounded bg-white/60';
      tag.textContent = '일시적';
      head.append(tag);
    }

    // 원인과 조치
    const cause = document.createElement('p');
    cause.className = 'text-xs mt-1.5 opacity-90';
    cause.textContent = `원인: ${finding.cause}`;

    const action = document.createElement('p');
    action.className = 'text-xs mt-1 opacity-90';
    action.textContent = `조치: ${finding.action}`;

    card.append(head, cause, action);
    container.append(card);
  });
}

/**
 * 실행 이력 표를 렌더링합니다.
 * @param {Array<Object>} runs - 실행 기록 목록
 */
function renderRuns(runs) {
  const body = $('runsBody');
  body.replaceChildren();

  if (!runs || runs.length === 0) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 7;
    cell.className = 'px-5 py-10 text-center text-sm text-ink-faint';
    const emptyWrap = document.createElement('div');
    emptyWrap.className = 'flex flex-col items-center gap-2';
    const emptyIcon = document.createElement('span');
    emptyIcon.className = 'w-12 h-12 rounded-2xl bg-cream-100 flex items-center justify-center text-xl';
    emptyIcon.setAttribute('aria-hidden', 'true');
    emptyIcon.textContent = '📭';
    const emptyText = document.createElement('span');
    emptyText.textContent = '아직 수집 이력이 없습니다. 워커를 실행하세요.';
    emptyWrap.append(emptyIcon, emptyText);
    cell.append(emptyWrap);
    row.append(cell);
    body.append(row);
    return;
  }

  runs.forEach((run) => {
    const row = document.createElement('tr');
    row.className = 'hover:bg-cream-50';

    // 시작 시각
    const time = document.createElement('td');
    time.className = 'px-5 py-2.5 whitespace-nowrap text-ink-muted';
    time.textContent = formatTime(run.started_at);

    // 결과 배지
    const statusCell = document.createElement('td');
    statusCell.className = 'px-5 py-2.5 whitespace-nowrap';

    const statusBadge = document.createElement('span');
    statusBadge.className =
      `text-xs font-medium px-2 py-0.5 rounded-full ${RUN_STATUS_STYLES[run.status] || ''}`;
    statusBadge.textContent = RUN_STATUS_LABELS[run.status] || run.status;
    statusCell.append(statusBadge);

    // 숫자 열
    const makeNum = (value) => {
      const cell = document.createElement('td');
      cell.className = 'px-5 py-2.5 text-right tabular-nums text-ink-muted';
      cell.textContent = value;
      return cell;
    };

    const fetched = makeNum((run.fetched || 0).toLocaleString('ko-KR'));
    const saved = makeNum((run.saved || 0).toLocaleString('ko-KR'));
    const duplicates = makeNum((run.duplicates || 0).toLocaleString('ko-KR'));
    const duration = makeNum(`${(run.duration_seconds || 0).toFixed(1)}초`);

    // 비고: 사이클 실패 메시지 우선, 없으면 소스별 실패 요약
    const note = document.createElement('td');
    note.className = 'px-5 py-2.5 text-xs text-ink-muted max-w-xs truncate';

    if (run.error_message) {
      note.textContent = run.error_message;
      note.title = run.error_message;
      note.classList.add('text-red-600');
    } else if (run.errors && run.errors.length > 0) {
      const text = run.errors.join(' / ');
      note.textContent = `${run.errors.length}개 소스 실패`;
      note.title = text;
    } else {
      note.textContent = '–';
    }

    row.append(time, statusCell, fetched, saved, duplicates, duration, note);
    body.append(row);
  });
}

/**
 * 최신 수집 항목 목록을 렌더링합니다.
 * @param {Array<Object>} items - 트렌드 항목
 */
function renderTrends(items) {
  const list = $('trendsList');
  list.replaceChildren();

  if (!items || items.length === 0) {
    const empty = document.createElement('li');
    empty.className = 'px-5 py-10 text-center text-sm text-ink-faint';
    const emptyWrap = document.createElement('div');
    emptyWrap.className = 'flex flex-col items-center gap-2';
    const emptyIcon = document.createElement('span');
    emptyIcon.className = 'w-12 h-12 rounded-2xl bg-cream-100 flex items-center justify-center text-xl';
    emptyIcon.setAttribute('aria-hidden', 'true');
    emptyIcon.textContent = '📭';
    const emptyText = document.createElement('span');
    emptyText.textContent = '수집된 항목이 없습니다.';
    emptyWrap.append(emptyIcon, emptyText);
    empty.append(emptyWrap);
    list.append(empty);
    return;
  }

  items.forEach((item) => {
    const li = document.createElement('li');
    li.className = 'px-5 py-3.5 hover:bg-cream-50';

    const link = document.createElement('a');
    link.href = item.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.className = 'text-sm font-medium text-forest-700 hover:underline';
    link.textContent = item.title;

    const meta = document.createElement('p');
    meta.className = 'text-xs text-ink-faint mt-0.5';
    meta.textContent =
      `${item.source_name || item.source_key} · ${formatTime(item.published_at)}`;

    li.append(link, meta);
    list.append(li);
  });
}

// ============ 데이터 로딩 ============

/**
 * 대시보드 전체 데이터를 새로 불러옵니다.
 * 두 요청은 서로 독립적이므로 병렬로 보내고, 한쪽이 실패해도
 * 다른 쪽 결과는 화면에 반영합니다.
 */
async function loadAll() {
  showError(null);

  const [statusResult, trendsResult] = await Promise.allSettled([
    apiFetch('/api/monitor/status?hours=24&recent_limit=10'),
    apiFetch('/api/trends?page=1&limit=8'),
  ]);

  if (statusResult.status === 'fulfilled') {
    const data = statusResult.value;
    renderWorker(data.worker);
    renderMetrics(data);
    renderDiagnosis(data.diagnosis);
    renderRuns(data.recent_runs);
  } else {
    showError(`상태 조회 실패: ${statusResult.reason.message}`);
  }

  if (trendsResult.status === 'fulfilled') {
    renderTrends(trendsResult.value.items);
  }

  setText($('lastUpdated'), `업데이트 ${new Date().toLocaleTimeString('ko-KR')}`);
}

/** 자동 새로고침을 시작합니다. */
function startAutoRefresh() {
  stopAutoRefresh();
  refreshTimer = setInterval(loadAll, REFRESH_INTERVAL_MS);
}

/** 자동 새로고침을 중지합니다. */
function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

// ============ 이벤트 바인딩 ============

/**
 * 로그인 폼 제출을 처리합니다.
 * @param {Event} event - submit 이벤트
 */
async function handleLogin(event) {
  event.preventDefault();

  const username = $('username').value.trim();
  const password = $('password').value;
  const errorEl = $('loginError');
  const button = $('loginBtn');

  errorEl.classList.add('hidden');

  // 클라이언트 측 입력 검증
  if (!username || !password) {
    setText(errorEl, '사용자명과 비밀번호를 모두 입력하세요.');
    errorEl.classList.remove('hidden');
    return;
  }

  button.disabled = true;
  setText(button, '로그인 중…');

  try {
    const data = await apiFetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });

    localStorage.setItem(TOKEN_KEY, data.access_token);
    $('password').value = '';
    showDashboard();
  } catch (error) {
    setText(errorEl, error.message);
    errorEl.classList.remove('hidden');
  } finally {
    button.disabled = false;
    setText(button, '로그인');
  }
}

/**
 * 회원가입 폼 제출을 처리합니다.
 *
 * 서버가 가입과 동시에 토큰을 발급하므로, 별도 로그인 없이
 * 곧바로 대시보드로 이동합니다.
 *
 * @param {Event} event - submit 이벤트
 */
async function handleSignup(event) {
  event.preventDefault();

  const username = $('signupUsername').value.trim();
  const email = $('signupEmail').value.trim();
  const fullName = $('signupFullName').value.trim();
  const password = $('signupPassword').value;
  const passwordConfirm = $('signupPasswordConfirm').value;

  const errorEl = $('signupError');
  const button = $('signupBtn');

  errorEl.classList.add('hidden');

  // 서버에 보내기 전 클라이언트에서 먼저 검증해 왕복을 줄임
  // (규칙은 backend/features/auth/schemas.py의 UserCreate와 일치)
  const validationError = validateSignup({
    username, email, password, passwordConfirm,
  });

  if (validationError) {
    setText(errorEl, validationError);
    errorEl.classList.remove('hidden');
    return;
  }

  button.disabled = true;
  setText(button, '가입 중…');

  try {
    // full_name은 선택 항목이므로 값이 있을 때만 전송
    const payload = { username, email, password };
    if (fullName) payload.full_name = fullName;

    const data = await apiFetch('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    localStorage.setItem(TOKEN_KEY, data.access_token);

    // 비밀번호가 DOM에 남지 않도록 폼 초기화
    $('signupForm').reset();
    showDashboard();
  } catch (error) {
    setText(errorEl, error.message);
    errorEl.classList.remove('hidden');
  } finally {
    button.disabled = false;
    setText(button, '가입하고 시작하기');
  }
}

/**
 * 회원가입 입력값을 검증합니다.
 *
 * @param {Object} values - 입력값
 * @param {string} values.username - 사용자명
 * @param {string} values.email - 이메일
 * @param {string} values.password - 비밀번호
 * @param {string} values.passwordConfirm - 비밀번호 확인
 * @returns {string|null} 오류 메시지, 문제가 없으면 null
 */
function validateSignup({ username, email, password, passwordConfirm }) {
  if (!username || !email || !password) {
    return '필수 항목(*)을 모두 입력하세요.';
  }

  if (username.length < 3 || username.length > 50) {
    return '사용자명은 3자 이상 50자 이하여야 합니다.';
  }

  // 서버의 EmailStr 검증에 걸리기 전에 형태만 간단히 확인
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return '올바른 이메일 주소를 입력하세요.';
  }

  if (password.length < 8) {
    return '비밀번호는 8자 이상이어야 합니다.';
  }

  if (password !== passwordConfirm) {
    return '비밀번호가 일치하지 않습니다.';
  }

  return null;
}

/** 자가 진단을 다시 실행합니다. */
async function handleDiagnose() {
  const button = $('diagnoseBtn');
  button.disabled = true;
  setText(button, '진단 중…');

  try {
    const data = await apiFetch('/api/monitor/diagnose?hours=24');
    renderDiagnosis(data);
  } catch (error) {
    showError(`진단 실패: ${error.message}`);
  } finally {
    button.disabled = false;
    setText(button, '다시 진단');
  }
}

/** 페이지 초기화 - 토큰이 있으면 바로 대시보드를 엽니다. */
function init() {
  $('loginForm').addEventListener('submit', handleLogin);
  $('signupForm').addEventListener('submit', handleSignup);
  $('refreshBtn').addEventListener('click', refreshActiveView);
  $('diagnoseBtn').addEventListener('click', handleDiagnose);

  // 상단 화면 전환 탭 - data-view 속성으로 대상 화면을 지정
  document.querySelectorAll('.nav-tab').forEach((button) => {
    button.addEventListener('click', () => switchView(button.dataset.view));
  });

  // 탭 버튼과 폼 하단 링크 모두에서 전환 가능
  $('tabLogin').addEventListener('click', () => switchAuthTab('login'));
  $('tabSignup').addEventListener('click', () => switchAuthTab('signup'));
  $('goSignup').addEventListener('click', () => switchAuthTab('signup'));
  $('goLogin').addEventListener('click', () => switchAuthTab('login'));

  $('logoutBtn').addEventListener('click', () => {
    localStorage.removeItem(TOKEN_KEY);
    showLogin();
  });

  $('autoRefresh').addEventListener('change', (event) => {
    // 모니터 탭에서만 폴링을 켭니다.
    if (event.target.checked && activeView === 'monitor') startAutoRefresh();
    else stopAutoRefresh();
  });

  // 브라우저 탭이 백그라운드일 때는 폴링을 멈춰 불필요한 요청을 줄임
  document.addEventListener('visibilitychange', () => {
    const dashboardOpen = !$('dashboardView').classList.contains('hidden');

    if (document.hidden) {
      stopAutoRefresh();
    } else if (dashboardOpen && activeView === 'monitor' && $('autoRefresh').checked) {
      loadAll();
      startAutoRefresh();
    }
  });

  // 화면별 모듈 초기화 (curation.js / graph.js에서 정의)
  initCuration();
  initGraph();

  if (getToken()) showDashboard();
  else showLogin();
}

// ============ 화면 조각(partial) 로딩 ============

/**
 * 탭별 화면 HTML을 pages/*.html에서 불러와 각 컨테이너에 주입합니다.
 *
 * index.html에는 껍데기(헤더 + 탭 + 빈 컨테이너)만 두고 실제 화면은
 * 파일로 분리해 두었습니다. 화면 하나를 고칠 때 다른 화면의 마크업을
 * 건드릴 위험이 없어지고, 파일당 길이도 크게 줄어듭니다.
 *
 * 세 조각을 병렬로 받아 한 번에 주입한 뒤 init()을 실행합니다.
 * (initCuration/initGraph가 조각 안의 엘리먼트에 이벤트를 걸기 때문에,
 *  주입이 끝나기 전에 init()을 호출하면 바인딩이 전부 실패합니다.)
 *
 * @returns {Promise<void>} 모든 조각의 주입이 끝나면 resolve
 * @throws {Error} 조각을 하나라도 불러오지 못하면 예외
 */
async function loadPanels() {
  // 컨테이너 id -> 조각 파일 경로
  const PANEL_SOURCES = {
    panelMonitor: 'pages/monitor.html',
    panelCuration: 'pages/curation.html',
    panelGraph: 'pages/graph.html',
  };

  const entries = Object.entries(PANEL_SOURCES);

  // 세 파일을 동시에 요청 - 순차 요청 대비 왕복 시간을 1/3로 줄입니다.
  const htmlList = await Promise.all(
    entries.map(async ([, path]) => {
      const response = await fetch(path, { cache: 'no-cache' });

      if (!response.ok) {
        throw new Error(`${path} 로드 실패 (HTTP ${response.status})`);
      }

      return response.text();
    })
  );

  entries.forEach(([containerId], index) => {
    const container = document.getElementById(containerId);

    // 조각은 우리가 작성한 정적 파일이므로 innerHTML 주입이 안전합니다.
    // (사용자 입력이 섞이는 경로가 아니며, 동적 데이터는 여전히
    //  textContent로만 렌더링합니다.)
    if (container) container.innerHTML = htmlList[index];
  });
}

/**
 * 페이지 진입점 - 조각을 먼저 주입한 뒤 기존 초기화를 실행합니다.
 */
async function bootstrap() {
  try {
    await loadPanels();
  } catch (error) {
    // 조각을 못 불러오면 화면이 텅 비므로, 원인을 눈에 보이게 알립니다.
    document.body.insertAdjacentHTML(
      'afterbegin',
      '<div class="m-4 rounded-2xl bg-red-50 border border-red-200 px-4 py-3 ' +
        'text-sm text-red-700" role="alert"></div>'
    );
    document.body.firstElementChild.textContent =
      `화면을 불러오지 못했습니다: ${error.message}`;
    return;
  }

  init();
}

document.addEventListener('DOMContentLoaded', bootstrap);
