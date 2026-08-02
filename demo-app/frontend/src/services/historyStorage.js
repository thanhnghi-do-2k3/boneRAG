export const HISTORY_KEY = 'bonerag.chat.history.v1';

export function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function persistHistorySession({ sessionId, messages, latestQuestion }) {
  const usefulMessages = messages.filter((message) => message.id !== 'welcome');
  if (usefulMessages.length === 0) return loadHistory();

  const previous = loadHistory();
  const entry = {
    id: sessionId,
    title: latestQuestion || usefulMessages.find((message) => message.role === 'user')?.text || 'Phiên chat',
    updated_at: new Date().toISOString(),
    messages,
  };
  const withoutCurrent = previous.filter((item) => item.id !== entry.id);
  const nextHistory = [entry, ...withoutCurrent].slice(0, 20);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(nextHistory));
  return nextHistory;
}

export function clearStoredHistory() {
  localStorage.removeItem(HISTORY_KEY);
  return [];
}

export function buildExportPayload(messages) {
  return {
    exported_at: new Date().toISOString(),
    messages,
  };
}
