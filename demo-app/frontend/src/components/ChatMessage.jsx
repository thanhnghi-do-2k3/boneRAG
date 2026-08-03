import { Button } from '../design-system/Button';
import { XrayPreview } from './XrayPreview';

export function ChatMessage({ message, onShowEvidence }) {
  const hasEvidence = (message.evidence ?? []).length > 0;
  const images = Array.isArray(message.images)
    ? message.images
    : message.image
    ? [message.image]
    : [];

  return (
    <div className={`message-row ${message.role}`}>
      <article className={`chat-bubble ${message.status === 'streaming' ? 'streaming' : ''}`}>
        <div className="bubble-meta">
          <span>{message.role === 'user' ? 'Bạn' : 'BoneRAG'}</span>
          {message.status === 'streaming' && <span>đang trả lời...</span>}
        </div>

        {images.length > 0 && (
          <div className={`bubble-images-gallery ${images.length > 1 ? 'multi-images' : 'single-image'}`}>
            {images.map((imgItem, idx) => (
              <figure className="attached-image-card" key={imgItem.image_id || idx}>
                <div className="attached-image-frame">
                  <XrayPreview
                    imageUrl={imgItem.data_url || imgItem.image_url}
                    bodyPart={imgItem.body_part}
                    diagnosis={imgItem.diagnosis}
                    title={imgItem.title}
                    className="attached-xray-preview"
                  />
                </div>
                <figcaption className="attached-image-caption">
                  <strong title={imgItem.title}>{imgItem.title || 'Ảnh X-quang'}</strong>
                  {imgItem.image_id && <span title={imgItem.image_id}>{imgItem.image_id}</span>}
                </figcaption>
              </figure>
            ))}
          </div>
        )}

        <p>{message.text || 'Đang suy nghĩ và stream câu trả lời...'}</p>

        {hasEvidence && (
          <Button className="evidence-link" onClick={onShowEvidence}>
            Xem {message.evidence.length} evidence
          </Button>
        )}
      </article>
    </div>
  );
}
