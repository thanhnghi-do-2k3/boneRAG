export function fetchRecords() {
  return fetch('/api/records').then((r) => r.json());
}

export function openAnswerStream(question, { sessionId, questionRaw, attachedImage } = {}) {
  const params = new URLSearchParams({ question });
  if (sessionId) params.set('session_id', sessionId);
  if (questionRaw) params.set('question_raw', questionRaw);
  if (attachedImage) params.set('attached_image', JSON.stringify(attachedImage));
  return new EventSource(`/api/answer-stream?${params.toString()}`);
}

export function fetchModelConfigs() {
  return fetch('/api/model-configs').then((r) => r.json());
}

export function setModelConfig(config) {
  return fetch('/api/set-config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  }).then((r) => r.json());
}

export function postFeedback(sessionId, rating) {
  return fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, rating }),
  }).then((r) => r.json());
}

export function fetchSessions() {
  return fetch('/api/sessions').then((r) => r.json());
}
