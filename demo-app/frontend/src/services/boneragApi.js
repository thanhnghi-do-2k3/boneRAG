const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

const DEFAULT_HEADERS = {
  'Bypass-Tunnel-Remainder': 'true',
  'ngrok-skip-browser-warning': 'true',
};

function backendConfigurationError() {
  return new Error(
    'Chưa cấu hình backend. Hãy đặt VITE_API_BASE_URL bằng URL Colab/ngrok rồi build và redeploy lại Vercel.',
  );
}

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
  if (!API_BASE) {
    const error = backendConfigurationError();
    logError(path, error);
    throw error;
  }
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
function openSSEStream(path, params) {
  const query = new URLSearchParams(params);
  const url = `${API_BASE}${path}?${query.toString()}`;
  console.log(`[BoneRAG API] 🔵 SSE OPEN (fetch) ${url}`);

  const ctrl = { onmessage: null, onerror: null, _aborted: false };
  const abortController = new AbortController();

  if (!API_BASE) {
    const error = backendConfigurationError();
    console.error(`[BoneRAG API] ${error.message}`);
    queueMicrotask(() => ctrl.onerror?.({ message: error.message }));
    return ctrl;
  }

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
        const contentType = res.headers.get('content-type') || '';
        const htmlFallback = contentType.includes('text/html') || /^\s*<!doctype html/i.test(text);
        const message = htmlFallback
          ? 'Backend URL đang trỏ về frontend Vercel hoặc chưa được cấu hình. Kiểm tra VITE_API_BASE_URL rồi build lại.'
          : `HTTP ${res.status}`;
        console.error('[BoneRAG API] SSE non-OK response:', message, text.slice(0, 200));
        ctrl.onerror?.({ message });
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let receivedDone = false;
      while (true) {
        const { done, value } = await reader.read();
        if (done || ctrl._aborted) {
          // Process any remaining data in buffer before exiting
          if (buffer.trim()) {
            for (const line of buffer.split(/\r?\n/)) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6).trim();
                if (data) {
                  try {
                    const parsed = JSON.parse(data);
                    if (parsed.type === 'done') receivedDone = true;
                    ctrl.onmessage?.({ data });
                  } catch (e) {
                    console.error('[BoneRAG SSE] Error in final buffer parse:', e);
                  }
                }
              }
            }
          }
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() || '';
        for (const block of blocks) {
          for (const line of block.split(/\r?\n/)) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim();
              if (data) {
                try {
                  const parsed = JSON.parse(data);
                  if (parsed.type === 'done') receivedDone = true;
                  ctrl.onmessage?.({ data });
                } catch (e) {
                  console.error('[BoneRAG SSE] Error in onmessage:', e);
                }
              }
            }
          }
        }
      }
      // If stream ended without a 'done' event, fire error so UI stops spinning
      if (!receivedDone && !ctrl._aborted) {
        console.warn('[BoneRAG SSE] Stream ended without done event — firing error');
        ctrl.onerror?.({ message: 'Stream ended unexpectedly' });
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

export function openAnswerStream(question, { sessionId, questionRaw, attachedImage } = {}) {
  const params = { question };
  if (sessionId) params.session_id = sessionId;
  if (questionRaw) params.question_raw = questionRaw;
  if (attachedImage) params.attached_image = JSON.stringify(attachedImage);
  return openSSEStream('/api/answer-stream', params);
}

export function openBenchmarkStream({
  encoder,
  generator,
  cases,
  includeControls,
} = {}) {
  return openSSEStream('/api/run-live-benchmark', {
    encoder: encoder || 'biomedclip',
    generator: generator || 'local_context_synth',
    cases: String(cases || 32),
    include_controls: includeControls ? '1' : '0',
  });
}

export function fetchBenchmarkRuns() {
  return apiFetch('/api/benchmark-runs')
    .then((response) => response.json())
    .then((runs) => (Array.isArray(runs) ? runs : []));
}

export function analyzeBenchmarkRun(payload) {
  return apiFetch('/api/analyze-benchmark', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...DEFAULT_HEADERS },
    body: JSON.stringify(payload),
  }).then((response) => response.json());
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
