// ── State ──────────────────────────────────────────────────────────────────
let allEvents = [];
let resultMeta = null; // final claude result line if present
let activeTools = new Set();

// ── DOM refs ───────────────────────────────────────────────────────────────
const fileInput = document.getElementById('file-input');
const fileName = document.getElementById('file-name');
const timeline = document.getElementById('timeline');
const emptyState = document.getElementById('empty-state');
const summaryBar = document.getElementById('summary-bar');
const toolFilters = document.getElementById('tool-filters');
const showResponses = document.getElementById('show-responses');
const errorsOnly = document.getElementById('errors-only');
const modal = document.getElementById('detail-modal');
const modalTitle = document.getElementById('modal-title');
const modalBody = document.getElementById('modal-body');

// ── File loading ───────────────────────────────────────────────────────────
fileInput.addEventListener('change', (e) => {
  if (e.target.files[0]) loadFile(e.target.files[0]);
});

// Drag & drop
document.body.addEventListener('dragover', (e) => {
  e.preventDefault();
  document.body.classList.add('drag-over');
});
document.body.addEventListener('dragleave', () => {
  document.body.classList.remove('drag-over');
});
document.body.addEventListener('drop', (e) => {
  e.preventDefault();
  document.body.classList.remove('drag-over');
  if (e.dataTransfer.files[0]) loadFile(e.dataTransfer.files[0]);
});

function loadFile(file) {
  fileName.textContent = file.name;
  const reader = new FileReader();
  reader.onload = (e) => parseTrace(e.target.result);
  reader.readAsText(file);
}

// ── Parsing ────────────────────────────────────────────────────────────────
function parseTrace(text) {
  allEvents = [];
  resultMeta = null;

  for (const line of text.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      const obj = JSON.parse(trimmed);
      // Detect the claude final result line (has type:"result")
      if (obj.type === 'result') {
        resultMeta = obj;
        continue;
      }
      // Skip lines that aren't trace events (no event or tool field)
      if (obj.event || obj.tool) {
        allEvents.push(obj);
      }
    } catch {
      // skip unparseable lines
    }
  }

  buildFilters();
  updateSummary();
  render();

  emptyState.classList.add('hidden');
  timeline.classList.remove('hidden');
  summaryBar.classList.remove('hidden');
}

// ── Filters ────────────────────────────────────────────────────────────────
function buildFilters() {
  const tools = [...new Set(allEvents.map(e => e.tool).filter(Boolean))].sort();
  activeTools = new Set(tools);
  toolFilters.innerHTML = '';

  for (const tool of tools) {
    const btn = document.createElement('button');
    btn.className = 'tool-btn active';
    btn.textContent = tool;
    btn.dataset.tool = tool;
    btn.addEventListener('click', () => {
      btn.classList.toggle('active');
      if (btn.classList.contains('active')) {
        activeTools.add(tool);
      } else {
        activeTools.delete(tool);
      }
      render();
    });
    toolFilters.appendChild(btn);
  }
}

showResponses.addEventListener('change', render);
errorsOnly.addEventListener('change', render);

// ── Summary ────────────────────────────────────────────────────────────────
function updateSummary() {
  const toolEvents = allEvents.filter(e => e.tool);
  const errors = allEvents.filter(e => e.event === 'PostToolUseFailure' || e.error);

  document.getElementById('stat-total').textContent = allEvents.length;
  document.getElementById('stat-tools').textContent = toolEvents.length;

  const errEl = document.getElementById('stat-errors');
  errEl.textContent = errors.length;
  errEl.style.color = errors.length > 0 ? 'var(--red)' : 'var(--green)';

  // Duration from first to last event
  if (allEvents.length >= 2) {
    const first = new Date(allEvents[0].timestamp);
    const last = new Date(allEvents[allEvents.length - 1].timestamp);
    const secs = (last - first) / 1000;
    document.getElementById('stat-duration').textContent =
      secs >= 60 ? `${Math.floor(secs / 60)}m ${Math.round(secs % 60)}s` : `${Math.round(secs)}s`;
  }

  // Cost from result meta
  if (resultMeta && resultMeta.total_cost_usd) {
    document.getElementById('stat-cost').textContent = `$${resultMeta.total_cost_usd.toFixed(2)}`;
  }
}

// ── Render ──────────────────────────────────────────────────────────────────
function render() {
  const wantResponses = showResponses.checked;
  const onlyErrors = errorsOnly.checked;

  let filtered = allEvents.filter(e => {
    if (e.tool && !activeTools.has(e.tool)) return false;
    if (onlyErrors && e.event !== 'PostToolUseFailure' && !e.error) return false;
    return true;
  });

  timeline.innerHTML = '';

  let prevTime = null;
  for (let i = 0; i < filtered.length; i++) {
    const ev = filtered[i];
    const el = renderEvent(ev, prevTime, wantResponses);
    timeline.appendChild(el);
    prevTime = ev.timestamp ? new Date(ev.timestamp) : null;
  }
}

function renderEvent(ev, prevTime, wantResponses) {
  const isError = ev.event === 'PostToolUseFailure' || !!ev.error;
  const tool = ev.tool || ev.event || 'unknown';

  const div = document.createElement('div');
  div.className = 'event' + (isError ? ' error' : '');

  // Time column
  const timeEl = document.createElement('div');
  timeEl.className = 'event-time';
  if (ev.timestamp) {
    const d = new Date(ev.timestamp);
    timeEl.textContent = d.toLocaleTimeString('en-US', { hour12: false });
    if (prevTime) {
      const delta = (d - prevTime) / 1000;
      if (delta > 0) {
        const deltaEl = document.createElement('span');
        deltaEl.className = 'event-delta';
        deltaEl.textContent = delta >= 60
          ? `+${Math.floor(delta / 60)}m${Math.round(delta % 60)}s`
          : `+${delta.toFixed(1)}s`;
        timeEl.appendChild(deltaEl);
      }
    }
  }
  div.appendChild(timeEl);

  // Icon
  const iconEl = document.createElement('div');
  const toolLower = tool.toLowerCase();
  const iconClass = isError ? 'error'
    : ['bash'].includes(toolLower) ? 'bash'
    : ['read'].includes(toolLower) ? 'read'
    : ['write'].includes(toolLower) ? 'write'
    : ['edit'].includes(toolLower) ? 'edit'
    : ['glob'].includes(toolLower) ? 'glob'
    : ['grep'].includes(toolLower) ? 'grep'
    : 'other';
  iconEl.className = `event-icon ${iconClass}`;
  iconEl.textContent = iconMap(tool, isError);
  div.appendChild(iconEl);

  // Body
  const bodyEl = document.createElement('div');
  bodyEl.className = 'event-body';

  // Header line
  const headerEl = document.createElement('div');
  headerEl.className = 'event-header';
  const toolEl = document.createElement('span');
  toolEl.className = 'event-tool';
  toolEl.textContent = tool;
  headerEl.appendChild(toolEl);

  const statusEl = document.createElement('span');
  statusEl.className = 'event-status ' + (isError ? 'failure' : 'success');
  statusEl.textContent = isError ? 'FAIL' : 'OK';
  headerEl.appendChild(statusEl);

  // Show file path for Read/Write/Edit
  if (ev.tool_input) {
    const filePath = ev.tool_input.file_path;
    if (filePath) {
      const fileEl = document.createElement('span');
      fileEl.className = 'event-file';
      fileEl.textContent = shortenPath(filePath);
      headerEl.appendChild(fileEl);
    }
  }

  bodyEl.appendChild(headerEl);

  // Input
  if (ev.tool_input) {
    const inputEl = document.createElement('div');
    inputEl.className = 'event-input';
    inputEl.textContent = formatInput(ev.tool, ev.tool_input);
    if (inputEl.textContent.length > 300) {
      inputEl.classList.add('expandable');
    }
    bodyEl.appendChild(inputEl);
  }

  // Error message
  if (ev.error) {
    const errEl = document.createElement('div');
    errEl.className = 'event-response error-response';
    errEl.textContent = typeof ev.error === 'string' ? ev.error : JSON.stringify(ev.error, null, 2);
    bodyEl.appendChild(errEl);
  }

  // Response
  if (wantResponses && ev.tool_response && !isError) {
    const respEl = document.createElement('div');
    respEl.className = 'event-response';
    respEl.textContent = formatResponse(ev.tool_response);
    bodyEl.appendChild(respEl);
  }

  div.appendChild(bodyEl);

  // Click to open full detail
  div.addEventListener('click', () => openModal(ev));

  return div;
}

// ── Formatting helpers ─────────────────────────────────────────────────────
function iconMap(tool, isError) {
  if (isError) return '✗';
  const map = {
    Bash: '$', Read: '◀', Write: '▶', Edit: '✎',
    Glob: '⊕', Grep: '⌕', Agent: '◈',
  };
  return map[tool] || '•';
}

function shortenPath(p) {
  // Show only last 2 path segments
  const parts = p.split('/');
  if (parts.length <= 3) return p;
  return '…/' + parts.slice(-2).join('/');
}

function formatInput(tool, input) {
  if (!input) return '';
  if (tool === 'Bash') {
    return input.command || JSON.stringify(input, null, 2);
  }
  if (tool === 'Write') {
    const content = input.content || '';
    const lines = content.split('\n').length;
    const preview = content.length > 500
      ? content.slice(0, 500) + `\n… (${lines} lines total)`
      : content;
    return preview;
  }
  if (tool === 'Read') {
    return input.file_path || JSON.stringify(input, null, 2);
  }
  if (tool === 'Edit') {
    let s = '';
    if (input.old_string) s += `- ${input.old_string.slice(0, 200)}\n`;
    if (input.new_string) s += `+ ${input.new_string.slice(0, 200)}`;
    return s || JSON.stringify(input, null, 2);
  }
  if (tool === 'Grep') {
    return `pattern: ${input.pattern || ''}  path: ${input.path || '.'}`;
  }
  if (tool === 'Glob') {
    return `pattern: ${input.pattern || ''}`;
  }
  return JSON.stringify(input, null, 2);
}

function formatResponse(resp) {
  if (!resp) return '';
  if (typeof resp === 'string') {
    // Try to parse as JSON for pretty printing
    try {
      const obj = JSON.parse(resp);
      // For Bash responses, show stdout
      if (obj.stdout !== undefined) {
        let s = obj.stdout || '';
        if (obj.stderr) s += '\nSTDERR: ' + obj.stderr;
        return s.slice(0, 800);
      }
      // For Read responses, show a summary
      if (obj.file && obj.file.content) {
        const lines = obj.file.content.split('\n').length;
        return `${lines} lines read from ${obj.file.filePath || 'file'}`;
      }
      // For Write responses
      if (obj.type === 'create' || obj.type === 'update') {
        return `${obj.type}: ${obj.filePath || ''}`;
      }
      return JSON.stringify(obj, null, 2).slice(0, 800);
    } catch {
      return resp.slice(0, 800);
    }
  }
  return JSON.stringify(resp, null, 2).slice(0, 800);
}

// ── Modal ──────────────────────────────────────────────────────────────────
function openModal(ev) {
  modalTitle.textContent = `${ev.tool || ev.event} — ${ev.timestamp || ''}`;
  modalBody.textContent = JSON.stringify(ev, null, 2);
  modal.classList.remove('hidden');
}

modal.querySelector('.modal-backdrop').addEventListener('click', closeModal);
modal.querySelector('.modal-close').addEventListener('click', closeModal);
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
});

function closeModal() {
  modal.classList.add('hidden');
}
