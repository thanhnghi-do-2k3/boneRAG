const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

const DEFAULT_HEADERS = {
  'Bypass-Tunnel-Remainder': 'true',
  'ngrok-skip-browser-warning': 'true',
};

function logRequest(method, url) {
  console.log(`[BoneRAG API] 🔵 ${method} ${url}`);
  console.log(`[BoneRAG API]    API_BASE="${API_BASE || '(empty — same origin)'}"`);
}

function logResponse(url, res) {
  const icon = res.ok ? '✅' : '❌';
  console.log(`[BoneRAG API] ${icon} ${res.status} ${res.statusText} ← ${url}`);
}

function logError(url, err) {
  console.error(`[BoneRAG API] 💥 FETCH ERROR ← ${url}`, err);
}

async function apiFetch(path, opts = {}) {
  const url = `${API_BASE}${path}`;
  logRequest(opts.method || 'GET', url);
  try {
    const res = await fetch(url, { headers: DEFAULT_HEADERS, ...opts });
    logResponse(url, res);
    return res;
  } catch (err) {
    logError(url, err);
    throw err;
  }
}

export function resolveImageUrl(url) {
  if (!url) return null;
  if (url.startsWith('data:') || url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  return url.startsWith('/') ? `${API_BASE}${url}` : `${API_BASE}/${url}`;
}

export function fetchRecords() {
  return apiFetch('/api/records')
    .then((r) => r.json())
    .then((items) => {
      console.log(`[BoneRAG API] 📦 fetchRecords → ${Array.isArray(items) ? items.length : 0} records`);
      return Array.isArray(items)
        ? items.map((rec) => ({ ...rec, image_url: resolveImageUrl(rec.image_url) }))
        : [];
    });
}

/**
 * Opens an SSE stream using fetch (not EventSource) so we can send
 * custom headers (e.g. ngrok-skip-browser-warning) that EventSource
 * does not support. Returns a controller object compatible with the
 * EventSource-like interface App.jsx expects: { onmessage, onerror, close }.
 */
export function openAnswerStream(question, { sessionId, questionRaw, attachedImage } = {}) {
  const params = new URLSearchParams({ question });
  if (sessionId) params.set('session_id', sessionId);
  if (questionRaw) params.set('question_raw', questionRaw);
  if (attachedImage) params.set('attached_image', JSON.stringify(attachedImage));
  const url = `${API_BASE}/api/answer-stream?${params.toString()}`;
  console.log(`[BoneRAG API] 🔵 SSE OPEN (fetch) ${url}`);

  const ctrl = { onmessage: null, onerror: null, _aborted: false };
  const abortController = new AbortController();

  ctrl.close = () => {
    ctrl._aborted = true;
    abortController.abort();
  };

  (async () => {
    try {
      const res = await fetch(url, {
        headers: { ...DEFAULT_HEADERS },
        signal: abortController.signal,
      });
      logResponse(url, res);
      if (!res.ok || !res.body) {
        const text = await res.text().catch(() => '');
        console.error('[BoneRAG API] SSE non-OK response body:', text.slice(0, 200));
        ctrl.onerror?.({ message: `HTTP ${res.status}` });
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done || ctrl._aborted) break;
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() || '';
        for (const block of blocks) {
          for (const line of block.split(/\r?\n/)) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim();
              if (data) {
                try {
                  ctrl.onmessage?.({ data });
                } catch (e) {
                  console.error('[BoneRAG SSE] Error in onmessage:', e);
                }
              }
            }
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        logError(url, err);
        ctrl.onerror?.(err);
      }
    }
  })();

  return ctrl;
}


export function fetchModelConfigs() {
  return apiFetch('/api/model-configs').then((r) => r.json());
}

export function setModelConfig(config) {
  return apiFetch('/api/set-config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...DEFAULT_HEADERS },
    body: JSON.stringify(config),
  }).then((r) => r.json());
}

export function postFeedback(sessionId, rating) {
  return apiFetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...DEFAULT_HEADERS },
    body: JSON.stringify({ session_id: sessionId, rating }),
  }).then((r) => r.json());
}

export function fetchSessions() {
  return apiFetch('/api/sessions').then((r) => r.json());
}

export function postAnswer(question) {
  return apiFetch('/api/answer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...DEFAULT_HEADERS },
    body: JSON.stringify({ question }),
  }).then((r) => r.json());
}
