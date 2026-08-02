export function fetchRecords() {
  return fetch('/api/records').then((response) => response.json());
}

export function openAnswerStream(question) {
  return new EventSource(`/api/answer-stream?question=${encodeURIComponent(question)}`);
}
