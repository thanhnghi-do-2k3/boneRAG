const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

export function resolveImageUrl(url) {
  if (!url) return null;
  if (url.startsWith('data:') || url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  return url.startsWith('/') ? `${API_BASE}${url}` : `${API_BASE}/${url}`;
}

export function fetchRecords() {
  return fetch(`${API_BASE}/api/records`)
    .then((r) => r.json())
    .then((items) =>
      Array.isArray(items)
        ? items.map((rec) => ({
            ...rec,
            image_url: resolveImageUrl(rec.image_url),
          }))
        : []
    );
}

export function openAnswerStream(question, { sessionId, questionRaw, attachedImage } = {}) {
  const params = new URLSearchParams({ question });
  if (sessionId) params.set('session_id', sessionId);
  if (questionRaw) params.set('question_raw', questionRaw);
  if (attachedImage) params.set('attached_image', JSON.stringify(attachedImage));
  return new EventSource(`${API_BASE}/api/answer-stream?${params.toString()}`);
}

export function fetchModelConfigs() {
  return fetch(`${API_BASE}/api/model-configs`).then((r) => r.json());
}

export function setModelConfig(config) {
  return fetch(`${API_BASE}/api/set-config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  }).then((r) => r.json());
}

export function postFeedback(sessionId, rating) {
  return fetch(`${API_BASE}/api/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, rating }),
  }).then((r) => r.json());
}

export function fetchSessions() {
  return fetch(`${API_BASE}/api/sessions`).then((r) => r.json());
}
