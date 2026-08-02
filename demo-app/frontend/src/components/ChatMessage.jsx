import { Button } from '../design-system/Button';

export function ChatMessage({ message, onShowEvidence }) {
  const hasEvidence = (message.evidence ?? []).length > 0;
  return (
    <div className={`message-row ${message.role}`}>
      <article className={`chat-bubble ${message.status === 'streaming' ? 'streaming' : ''}`}>
        <div className="bubble-meta">
          <span>{message.role === 'user' ? 'Bạn' : 'BoneRAG'}</span>
          {message.status === 'streaming' && <span>đang trả lời...</span>}
        </div>
        <p>{message.text || 'Đang suy nghĩ và stream câu trả lời...'}</p>
        {message.image && (
          <div className="bubble-image-context">
            <div className="xray-thumb">
              <span>{message.image.body_part}</span>
              <strong>{message.image.diagnosis}</strong>
            </div>
            <div>
              <strong>{message.image.title}</strong>
              <span>{message.image.image_id}</span>
            </div>
          </div>
        )}
        {hasEvidence && (
          <Button className="evidence-link" onClick={onShowEvidence}>
            Xem {message.evidence.length} evidence
          </Button>
        )}
      </article>
    </div>
  );
}
