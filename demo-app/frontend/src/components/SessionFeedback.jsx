import { useState } from 'react';
import { postFeedback } from '../services/boneragApi';

export function SessionFeedback({ sessionId }) {
  const [rating, setRating] = useState(null); // null | 1 | -1
  const [sending, setSending] = useState(false);

  const handleFeedback = async (value) => {
    if (rating !== null || sending || !sessionId) return;
    setSending(true);
    try {
      await postFeedback(sessionId, value);
      setRating(value);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="session-feedback">
      <span className="feedback-label">Câu trả lời hữu ích?</span>
      <button
        className={`feedback-btn thumbs-up ${rating === 1 ? 'active' : ''}`}
        onClick={() => handleFeedback(1)}
        disabled={rating !== null || sending}
        title="Hữu ích"
        aria-label="Phản hồi tích cực"
      >
        👍
      </button>
      <button
        className={`feedback-btn thumbs-down ${rating === -1 ? 'active' : ''}`}
        onClick={() => handleFeedback(-1)}
        disabled={rating !== null || sending}
        title="Không hữu ích"
        aria-label="Phản hồi tiêu cực"
      >
        👎
      </button>
      {rating !== null && (
        <span className="feedback-thanks">
          {rating === 1 ? 'Cảm ơn bạn! 🙏' : 'Cảm ơn phản hồi, chúng tôi sẽ cải thiện.'}
        </span>
      )}
    </div>
  );
}
