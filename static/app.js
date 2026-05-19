let currentEntity = 'users';
let currentFmt    = 'json';
let lastRaw       = '';

// ── Entity buttons ────────────────────────────────────────────────────────
document.getElementById('entity-grid').addEventListener('click', e => {
  const btn = e.target.closest('.entity-btn');
  if (!btn) return;
  document.querySelectorAll('.entity-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentEntity = btn.dataset.entity;
  updateUrlBar();
});

document.getElementById('fmt-row').addEventListener('click', e => {
  const btn = e.target.closest('.fmt-btn');
  if (!btn) return;
  document.querySelectorAll('.fmt-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentFmt = btn.dataset.fmt;
  updateUrlBar();
});

['count', 'locale'].forEach(id =>
  document.getElementById(id).addEventListener('input', updateUrlBar)
);

function updateUrlBar() {
  const count  = document.getElementById('count').value;
  const locale = document.getElementById('locale').value;
  document.getElementById('url-text').textContent =
    `/api/${currentEntity}?count=${count}&locale=${locale}&format=${currentFmt}`;
  document.getElementById('url-display').querySelector('.method').textContent = 'GET';
}

// ── Generate ──────────────────────────────────────────────────────────────
async function generateData() {
  const count  = document.getElementById('count').value;
  const locale = document.getElementById('locale').value;
  const url    = `/api/${currentEntity}?count=${count}&locale=${locale}&format=${currentFmt}`;

  setStatus('loading', 'Генерация…');
  const t0 = performance.now();

  try {
    const resp    = await fetch(url);
    const elapsed = ((performance.now() - t0) / 1000).toFixed(2) + 's';

    if (currentFmt !== 'json') {
      const text = await resp.text();
      lastRaw = text;
      showRaw(text);
      setStatus('ok', 'Готов');
      setStats(count, elapsed, byteSize(text));
      return;
    }

    const data = await resp.json();
    const json = JSON.stringify(data, null, 2);
    lastRaw = json;
    setStatus(resp.ok ? 'ok' : 'err', resp.ok ? 'Готов' : 'Ошибка');
    setStats(data.count ?? '—', elapsed, byteSize(json));
    document.getElementById('result').innerHTML = syntaxHL(json);
  } catch (e) {
    setStatus('err', 'Ошибка');
    document.getElementById('result').textContent = '// Ошибка: ' + e.message;
  }
}

// ── Custom schema ─────────────────────────────────────────────────────────
async function generateCustom() {
  const schemaText = document.getElementById('schema-input').value.trim();
  if (!schemaText) return alert('Введите JSON Schema');

  let schema;
  try { schema = JSON.parse(schemaText); }
  catch (e) { alert('Невалидный JSON: ' + e.message); return; }

  const count  = document.getElementById('count').value;
  const locale = document.getElementById('locale').value;
  const url    = `/api/custom?count=${count}&locale=${locale}&format=${currentFmt}`;

  document.getElementById('url-text').textContent = url;
  document.getElementById('url-display').querySelector('.method').textContent = 'POST';
  setStatus('loading', 'Генерация…');
  const t0 = performance.now();

  try {
    const resp    = await fetch(url, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(schema),
    });
    const elapsed = ((performance.now() - t0) / 1000).toFixed(2) + 's';
    const data    = await resp.json();
    const json    = JSON.stringify(data, null, 2);
    lastRaw = json;
    setStatus(resp.ok ? 'ok' : 'err', resp.ok ? 'Готов' : 'Ошибка');
    setStats(data.count ?? '—', elapsed, byteSize(json));
    document.getElementById('result').innerHTML = syntaxHL(json);
  } catch (e) {
    setStatus('err', 'Ошибка');
    document.getElementById('result').textContent = '// Ошибка: ' + e.message;
  }
}

// ── Schema viewer ─────────────────────────────────────────────────────────
async function loadSchema() {
  setStatus('loading', 'Загрузка схемы…');
  try {
    const resp = await fetch(`/api/schema/${currentEntity}`);
    const data = await resp.json();
    const json = JSON.stringify(data, null, 2);
    lastRaw = json;
    document.getElementById('result').innerHTML = syntaxHL(json);
    setStatus('ok', 'Схема загружена');
    document.getElementById('url-text').textContent = `/api/schema/${currentEntity}`;
  } catch (e) {
    setStatus('err', 'Ошибка');
  }
}

// ── Download ──────────────────────────────────────────────────────────────
function downloadData() {
  if (!lastRaw) return alert('Сначала сгенерируйте данные');
  const mime = currentFmt === 'csv' ? 'text/csv'
             : currentFmt === 'xml' ? 'application/xml'
             : 'application/json';
  const blob = new Blob([lastRaw], { type: mime });
  const a = Object.assign(document.createElement('a'), {
    href:     URL.createObjectURL(blob),
    download: `${currentEntity}.${currentFmt}`,
  });
  a.click();
}

function clearResult() {
  document.getElementById('result').textContent = '// Очищено';
  lastRaw = '';
  setStatus('idle', 'Готов');
  setStats('—', '—', '—');
}

async function copyResult() {
  const text = document.getElementById('result').textContent;
  await navigator.clipboard.writeText(text);
  const btn = document.querySelector('.copy-btn');
  btn.textContent = 'COPIED ✓';
  setTimeout(() => btn.textContent = 'COPY', 1500);
}

// ── Schema toggle ─────────────────────────────────────────────────────────
function toggleSchema() {
  document.getElementById('schema-area').classList.toggle('visible');
  document.getElementById('toggle-icon').classList.toggle('open');
}

// ── Helpers ───────────────────────────────────────────────────────────────
function setStatus(state, text) {
  const dot  = document.getElementById('status-dot');
  const stxt = document.getElementById('status-text');
  dot.className = 'dot ' + (state === 'ok' ? '' : state === 'err' ? 'err' : 'idle');
  if (state === 'loading') {
    stxt.innerHTML = `<span class="spin"></span>${text}`;
  } else {
    stxt.textContent = text;
  }
}

function setStats(count, time, size) {
  document.getElementById('stat-count').textContent = count;
  document.getElementById('stat-time').textContent  = time;
  document.getElementById('stat-size').textContent  = size;
}

function byteSize(str) {
  const bytes = new TextEncoder().encode(str).length;
  return bytes < 1024 ? bytes + ' B' : (bytes / 1024).toFixed(1) + ' KB';
}

function showRaw(text) {
  document.getElementById('result').textContent = text;
}

function syntaxHL(json) {
  return json
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
      m => {
        let cls = 't-num';
        if (/^"/.test(m))       cls = /:$/.test(m) ? 't-key' : 't-str';
        else if (/true|false/.test(m)) cls = 't-bool';
        else if (/null/.test(m))       cls = 't-null';
        return `<span class="${cls}">${m}</span>`;
      }
    );
}