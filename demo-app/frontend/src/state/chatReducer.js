import { welcomeMessage } from '../data/demoContent';
import { loadHistory } from '../services/historyStorage';

export const initialChatState = {
  screen: 'qa',
  question: '',
  records: [],
  events: [],
  logs: [],
  messages: [welcomeMessage],
  history: loadHistory(),
  activeEvidenceContext: {
    messageId: null,
    question: '',
    evidence: [],
  },
  selectedEvidence: null,
  selectedImage: null,
  result: null,
  running: false,
};

export function makeSessionId() {
  return `session-${Date.now()}`;
}

export function createLogEntry({ type, title, message, details }) {
  return {
    id: `log-${Date.now()}-${type}-${Math.random().toString(16).slice(2)}`,
    time: new Date().toLocaleTimeString('vi-VN'),
    type,
    title,
    message,
    details,
  };
}

export function chatReducer(state, action) {
  switch (action.type) {
    case 'set-screen':
      return { ...state, screen: action.screen };
    case 'set-question':
      return { ...state, question: action.question };
    case 'select-image':
      return {
        ...state,
        screen: 'qa',
        selectedImage: action.image,
      };
    case 'records-loaded':
      return { ...state, records: action.records };
    case 'stream-start':
      return {
        ...state,
        screen: 'qa',
        question: action.question,
        events: [],
        logs: [
          createLogEntry({
            type: 'start',
            title: 'Bắt đầu câu hỏi',
            message: action.question,
          }),
        ],
        result: null,
        running: true,
        messages: [...state.messages, action.userMessage, action.assistantMessage],
        activeEvidenceContext: {
          messageId: action.assistantMessage.id,
          question: action.question,
          evidence: [],
        },
      };
    case 'stage-event':
      return {
        ...state,
        events: [...state.events, action.event],
        logs: [
          ...state.logs,
          createLogEntry({
            type: action.event.stage,
            title: action.event.title,
            message: action.event.message,
            details: action.event.hits ? `${action.event.hits.length} raw hits` : '',
          }),
        ],
      };
    case 'append-token':
      return {
        ...state,
        messages: state.messages.map((message) =>
          message.id === action.messageId ? { ...message, text: message.text + action.text } : message,
        ),
      };
    case 'stream-done':
      return {
        ...state,
        result: action.result,
        running: false,
        history: action.history,
        activeEvidenceContext: {
          messageId: action.messageId,
          question: action.result.question,
          evidence: action.result.evidence ?? [],
        },
        logs: [
          ...state.logs,
          createLogEntry({
            type: 'done',
            title: 'Hoàn tất sinh câu trả lời',
            message: `Trả về ${(action.result.evidence ?? []).length} evidence, retrieval ${
              action.result.used_retrieval ? 'được dùng' : 'bị bỏ qua'
            }.`,
          }),
        ],
        messages: state.messages.map((message) =>
          message.id === action.messageId
            ? {
                ...message,
                text: action.result.answer,
                evidence: action.result.evidence ?? [],
                question: action.result.question,
                status: 'done',
              }
            : message,
        ),
      };
    case 'stream-error':
      return {
        ...state,
        running: false,
        messages: state.messages.map((message) =>
          message.id === action.messageId ? { ...message, text: action.message, status: 'error' } : message,
        ),
      };
    case 'set-running':
      return { ...state, running: action.running };
    case 'reset-chat':
      return {
        ...state,
        running: false,
        events: [],
        logs: [],
        result: null,
        activeEvidenceContext: { messageId: null, question: '', evidence: [] },
        selectedEvidence: null,
        selectedImage: null,
        messages: [welcomeMessage],
      };
    case 'show-message-evidence':
      return {
        ...state,
        activeEvidenceContext: {
          messageId: action.message.id,
          question: action.message.question ?? '',
          evidence: action.message.evidence ?? [],
        },
      };
    case 'select-evidence':
      return { ...state, selectedEvidence: action.item };
    case 'history-loaded':
      return { ...state, history: action.history };
    case 'open-history-session':
      return {
        ...state,
        screen: 'qa',
        messages: action.entry.messages,
        activeEvidenceContext: { messageId: null, question: action.entry.title, evidence: [] },
      };
    default:
      return state;
  }
}
