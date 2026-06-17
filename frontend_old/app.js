/* ═══════════════════════════════════════════════════════════════════════════
   RentChat — app.js
   ═══════════════════════════════════════════════════════════════════════════ */

const API = 'http://localhost:8000';

// ── State ─────────────────────────────────────────────────────────────────────
let currentDocId     = null;
let currentSessionId = null;
let isSending        = false;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const $uploadZone     = document.getElementById('upload-zone');
const $fileInput      = document.getElementById('file-input');
const $uploadTrigger  = document.getElementById('upload-trigger');
const $uploadProgress = document.getElementById('upload-progress');
const $progressFill   = document.getElementById('progress-fill');
const $progressText   = document.getElementById('progress-text');
const $docList        = document.getElementById('doc-list');
const $sessList       = document.getElementById('sess-list');
const $docCount       = document.getElementById('doc-count');
const $sessCount      = document.getElementById('sess-count');
const $chatDocName    = document.getElementById('chat-doc-name');
const $chatSessionLbl = document.getElementById('chat-session-label');
const $btnNewChat     = document.getElementById('btn-new-chat');
const $btnClearChat   = document.getElementById('btn-clear-chat');
const $welcomeState   = document.getElementById('welcome-state');
const $messagesList   = document.getElementById('messages-list');
const $messagesWrapper= document.getElementById('messages-wrapper');
const $questionInput  = document.getElementById('question-input');
const $sendBtn        = document.getElementById('send-btn');

// ══════════════════════════════════════════════════════════════════════════════
// TOAST
// ══════════════════════════════════════════════════════════════════════════════
function showToast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast toast--${type}`;
  el.textContent = msg;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => {
    el.classList.add('fade-out');
    setTimeout(() => el.remove(), 350);
  }, 3500);
}

// ══════════════════════════════════════════════════════════════════════════════
// API HELPERS
// ══════════════════════════════════════════════════════════════════════════════
async function apiFetch(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ══════════════════════════════════════════════════════════════════════════════
// UPLOAD
// ══════════════════════════════════════════════════════════════════════════════
async function uploadFile(file) {
  if (!file || file.type !== 'application/pdf') {
    showToast('Please select a valid PDF file.', 'error');
    return;
  }

  // Show progress
  $uploadProgress.classList.remove('hidden');
  $progressFill.style.width = '15%';
  $progressText.textContent = 'Uploading…';

  const formData = new FormData();
  formData.append('file', file);

  try {
    $progressFill.style.width = '40%';
    $progressText.textContent = 'Parsing PDF…';

    const doc = await fetch(`${API}/upload`, { method: 'POST', body: formData })
      .then(async r => {
        if (!r.ok) { const e = await r.json(); throw new Error(e.detail); }
        return r.json();
      });

    $progressFill.style.width = '80%';
    $progressText.textContent = 'Indexing to Pinecone…';

    await new Promise(r => setTimeout(r, 600));   // brief visual pause

    $progressFill.style.width = '100%';
    $progressText.textContent = 'Done!';

    // Only add to sidebar if not already shown
    const alreadyInSidebar = document.querySelector(`.doc-item[data-doc-id="${doc.doc_id}"]`);
    if (!alreadyInSidebar) {
      addDocToSidebar(doc);
      $docCount.textContent = document.querySelectorAll('.doc-item').length;
    }

    if (doc.already_existed) {
      showToast(`ℹ️ "${doc.filename}" already indexed — reusing existing data`, 'info');
    } else {
      showToast(`✓ "${doc.filename}" indexed — ${doc.chunk_count} chunks`, 'success');
    }

    // Auto-create a session for the newly uploaded document
    await createSession(doc.doc_id);

  } catch (err) {
    showToast(`Upload failed: ${err.message}`, 'error');
  } finally {
    setTimeout(() => {
      $uploadProgress.classList.add('hidden');
      $progressFill.style.width = '0%';
    }, 800);
  }
}

// ── Drag & Drop ───────────────────────────────────────────────────────────────
$uploadZone.addEventListener('dragover', e => {
  e.preventDefault();
  $uploadZone.classList.add('drag-over');
});
$uploadZone.addEventListener('dragleave', () => $uploadZone.classList.remove('drag-over'));
$uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  $uploadZone.classList.remove('drag-over');
  uploadFile(e.dataTransfer.files[0]);
});
$uploadZone.addEventListener('click', () => $fileInput.click());
$uploadTrigger.addEventListener('click', e => { e.stopPropagation(); $fileInput.click(); });
$fileInput.addEventListener('change', () => {
  if ($fileInput.files[0]) uploadFile($fileInput.files[0]);
  $fileInput.value = '';   // reset so same file can be re-uploaded
});

// ══════════════════════════════════════════════════════════════════════════════
// DOCUMENTS
// ══════════════════════════════════════════════════════════════════════════════
function addDocToSidebar(doc) {
  // Remove empty hint
  const hint = $docList.querySelector('.empty-hint');
  if (hint) hint.remove();

  const el = document.createElement('div');
  el.className = 'doc-item';
  el.dataset.docId = doc.doc_id;
  el.innerHTML = `
    <div class="doc-item-icon">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
    </div>
    <div class="doc-item-info">
      <div class="doc-item-name" title="${doc.filename}">${doc.filename}</div>
      <div class="doc-item-meta">${doc.page_count} pages · ${doc.chunk_count} chunks</div>
    </div>
    <button class="doc-item-del" title="Delete document" data-doc-id="${doc.doc_id}">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/>
      </svg>
    </button>`;

  el.querySelector('.doc-item-del').addEventListener('click', async e => {
    e.stopPropagation();
    if (!confirm(`Delete "${doc.filename}" and all its data?`)) return;
    try {
      await apiFetch(`/documents/${doc.doc_id}`, { method: 'DELETE' });
      el.remove();
      $docCount.textContent = document.querySelectorAll('.doc-item').length;
      if (!$docList.children.length) $docList.innerHTML = '<p class="empty-hint">No documents yet</p>';
      if (currentDocId === doc.doc_id) clearChatArea();
      showToast('Document deleted.', 'info');
    } catch (err) { showToast(err.message, 'error'); }
  });

  el.addEventListener('click', () => selectDoc(doc.doc_id, doc.filename));
  $docList.appendChild(el);
}

function selectDoc(docId, filename) {
  document.querySelectorAll('.doc-item').forEach(el =>
    el.classList.toggle('active', el.dataset.docId === docId));
  currentDocId = docId;
  $chatDocName.textContent = filename;
  $btnNewChat.disabled = false;
}

// ══════════════════════════════════════════════════════════════════════════════
// SESSIONS
// ══════════════════════════════════════════════════════════════════════════════
async function createSession(docId) {
  try {
    const sess = await apiFetch('/sessions', {
      method: 'POST',
      body: JSON.stringify({ doc_id: docId }),
    });
    addSessToSidebar(sess);
    $sessCount.textContent = document.querySelectorAll('.sess-item').length;
    await loadSession(sess.session_id, sess.filename);
    showToast('New conversation started.', 'info');
  } catch (err) { showToast(err.message, 'error'); }
}

function addSessToSidebar(sess) {
  const hint = $sessList.querySelector('.empty-hint');
  if (hint) hint.remove();

  const el = document.createElement('div');
  el.className = 'sess-item';
  el.dataset.sessId = sess.session_id;

  const shortName = sess.filename.replace('.pdf', '');
  const label = `Chat — ${shortName.length > 20 ? shortName.slice(0,20)+'…' : shortName}`;

  el.innerHTML = `
    <div class="sess-item-dot"></div>
    <div class="sess-item-info">
      <div class="sess-item-name" title="${sess.filename}">${label}</div>
      <div class="sess-item-meta">${sess.session_id} · ${sess.message_count ?? 0} msgs</div>
    </div>
    <button class="sess-item-del" title="Delete conversation" data-sess-id="${sess.session_id}">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/>
      </svg>
    </button>`;

  el.querySelector('.sess-item-del').addEventListener('click', async e => {
    e.stopPropagation();
    try {
      await apiFetch(`/sessions/${sess.session_id}`, { method: 'DELETE' });
      el.remove();
      $sessCount.textContent = document.querySelectorAll('.sess-item').length;
      if (!$sessList.children.length) $sessList.innerHTML = '<p class="empty-hint">No conversations yet</p>';
      if (currentSessionId === sess.session_id) clearChatArea();
      showToast('Conversation deleted.', 'info');
    } catch (err) { showToast(err.message, 'error'); }
  });

  el.addEventListener('click', () => loadSession(sess.session_id, sess.filename));
  $sessList.prepend(el);   // newest first
}

async function loadSession(sessionId, filename) {
  try {
    const data = await apiFetch(`/sessions/${sessionId}/history`);
    currentSessionId = sessionId;
    currentDocId = data.doc_id;

    // Update header
    $chatDocName.textContent = filename || data.filename;
    $chatSessionLbl.textContent = `Session ${sessionId} · ${data.messages.length} messages`;
    $btnNewChat.disabled = false;
    $btnClearChat.disabled = false;
    enableInput(true);

    // Highlight active session
    document.querySelectorAll('.sess-item').forEach(el =>
      el.classList.toggle('active', el.dataset.sessId === sessionId));
    // Highlight active doc
    document.querySelectorAll('.doc-item').forEach(el =>
      el.classList.toggle('active', el.dataset.docId === data.doc_id));

    // Render messages
    $welcomeState.classList.add('hidden');
    $messagesList.innerHTML = '';
    data.messages.forEach(msg => renderMessage(msg.role, msg.content, [], msg.timestamp));
    scrollToBottom();

  } catch (err) { showToast(err.message, 'error'); }
}

// ══════════════════════════════════════════════════════════════════════════════
// CHAT
// ══════════════════════════════════════════════════════════════════════════════
async function sendMessage() {
  const question = $questionInput.value.trim();
  if (!question || isSending || !currentSessionId) return;

  isSending = true;
  enableInput(false);
  $questionInput.value = '';
  autoResize();

  // Immediately show user bubble
  renderMessage('human', question, [], new Date().toISOString());
  $welcomeState.classList.add('hidden');

  // Typing indicator
  const typingEl = showTyping();
  scrollToBottom();

  try {
    const res = await apiFetch('/chat', {
      method: 'POST',
      body: JSON.stringify({ session_id: currentSessionId, question }),
    });

    hideTyping(typingEl);
    renderMessage('ai', res.answer, res.sources, new Date().toISOString());

    // Update session label
    $chatSessionLbl.textContent =
      `Session ${currentSessionId} · turn ${res.turn}`;

    // Update message count in sidebar item
    const sessEl = document.querySelector(`.sess-item[data-sess-id="${currentSessionId}"] .sess-item-meta`);
    if (sessEl) {
      const parts = sessEl.textContent.split('·');
      sessEl.textContent = `${parts[0].trim()} · ${res.turn * 2} msgs`;
    }

    scrollToBottom();

  } catch (err) {
    hideTyping(typingEl);
    renderMessage('ai', `⚠️ Error: ${err.message}`, [], new Date().toISOString());
    showToast(err.message, 'error');
  } finally {
    isSending = false;
    enableInput(true);
    $questionInput.focus();
  }
}

// ── Header buttons ────────────────────────────────────────────────────────────
$btnNewChat.addEventListener('click', () => {
  if (currentDocId) createSession(currentDocId);
});

$btnClearChat.addEventListener('click', async () => {
  if (!currentSessionId) return;
  if (!confirm('Delete this entire conversation?')) return;
  try {
    await apiFetch(`/sessions/${currentSessionId}`, { method: 'DELETE' });
    const el = document.querySelector(`.sess-item[data-sess-id="${currentSessionId}"]`);
    if (el) el.remove();
    $sessCount.textContent = document.querySelectorAll('.sess-item').length;
    if (!$sessList.children.length) $sessList.innerHTML = '<p class="empty-hint">No conversations yet</p>';
    clearChatArea();
    showToast('Conversation cleared.', 'info');
  } catch (err) { showToast(err.message, 'error'); }
});

// ══════════════════════════════════════════════════════════════════════════════
// RENDER HELPERS
// ══════════════════════════════════════════════════════════════════════════════
function renderMessage(role, content, sources = [], timestamp) {
  const isHuman = role === 'human';
  const time = timestamp ? formatTime(timestamp) : '';

  const msg = document.createElement('div');
  msg.className = `message message--${isHuman ? 'human' : 'ai'}`;

  const avatar = isHuman ? 'You' : '🤖';
  const initials = isHuman ? 'U' : '';

  msg.innerHTML = `
    <div class="message-meta">
      <div class="message-avatar">${isHuman ? initials : '🤖'}</div>
      <span class="message-time">${time}</span>
    </div>
    <div class="message-bubble">${formatContent(content, isHuman)}</div>
    ${(!isHuman && sources && sources.length) ? renderSources(sources) : ''}
  `;

  // Wire up source toggle
  const toggle = msg.querySelector('.sources-toggle');
  if (toggle) {
    toggle.addEventListener('click', () => {
      const list = toggle.nextElementSibling;
      const isOpen = toggle.classList.toggle('open');
      list.classList.toggle('visible', isOpen);
    });
  }

  $messagesList.appendChild(msg);
}

function formatContent(text, isHuman) {
  if (isHuman) return escHtml(text);
  // Simple markdown-ish: bold, line breaks, bullets
  return escHtml(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^•\s(.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/gs, m => `<ul>${m}</ul>`)
    .replace(/\n/g, '<br>');
}

function renderSources(sources) {
  const chips = sources.map((s, i) => `
    <div class="source-chip">
      <div class="source-chip-header">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        Page ${s.page}
      </div>
      <div class="source-chip-text">${escHtml(s.snippet)}…</div>
    </div>`).join('');

  return `
    <div class="message-sources">
      <div class="sources-toggle">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
        ${sources.length} source${sources.length > 1 ? 's' : ''}
      </div>
      <div class="sources-list">${chips}</div>
    </div>`;
}

function showTyping() {
  const el = document.createElement('div');
  el.className = 'typing-indicator';
  el.innerHTML = `
    <div class="message-avatar" style="width:26px;height:26px;border-radius:50%;background:var(--bg-card);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;">🤖</div>
    <div class="typing-bubble">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>`;
  $messagesList.appendChild(el);
  return el;
}
function hideTyping(el) { if (el && el.parentNode) el.remove(); }

function clearChatArea() {
  currentSessionId = null;
  currentDocId = null;
  $chatDocName.textContent = 'Select a document to begin';
  $chatSessionLbl.textContent = 'No active session';
  $btnNewChat.disabled = true;
  $btnClearChat.disabled = true;
  $messagesList.innerHTML = '';
  $welcomeState.classList.remove('hidden');
  enableInput(false);
  document.querySelectorAll('.sess-item').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.doc-item').forEach(el => el.classList.remove('active'));
}

// ══════════════════════════════════════════════════════════════════════════════
// INPUT
// ══════════════════════════════════════════════════════════════════════════════
function enableInput(on) {
  $questionInput.disabled = !on;
  $sendBtn.disabled = !on;
}

function autoResize() {
  $questionInput.style.height = 'auto';
  $questionInput.style.height = `${Math.min($questionInput.scrollHeight, 160)}px`;
}

$questionInput.addEventListener('input', autoResize);
$questionInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
$sendBtn.addEventListener('click', sendMessage);

// ══════════════════════════════════════════════════════════════════════════════
// UTILS
// ══════════════════════════════════════════════════════════════════════════════
function scrollToBottom() {
  requestAnimationFrame(() => {
    $messagesWrapper.scrollTop = $messagesWrapper.scrollHeight;
  });
}

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch { return ''; }
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ══════════════════════════════════════════════════════════════════════════════
// INIT — Load existing docs & sessions on page load
// ══════════════════════════════════════════════════════════════════════════════
async function init() {
  try {
    const [docs, sessions] = await Promise.all([
      apiFetch('/documents'),
      apiFetch('/sessions'),
    ]);

    docs.forEach(doc => addDocToSidebar(doc));
    $docCount.textContent = docs.length;

    // Sessions newest first
    [...sessions].reverse().forEach(sess => addSessToSidebar(sess));
    $sessCount.textContent = sessions.length;

    // Restore last session if available
    if (sessions.length) {
      const last = sessions[sessions.length - 1];
      const doc = docs.find(d => d.doc_id === last.doc_id);
      await loadSession(last.session_id, doc?.filename || last.filename);
    }
  } catch (err) {
    // Backend may not be running yet — silently ignore on init
    console.warn('Init: could not reach backend.', err.message);
  }
}

init();
