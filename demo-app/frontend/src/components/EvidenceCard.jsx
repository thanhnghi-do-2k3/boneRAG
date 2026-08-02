import { Button } from '../design-system/Button';
import { XrayPreview } from './XrayPreview';

export function EvidenceCard({ item, onView }) {
  return (
    <article className="evidence-card">
      <XrayPreview
        imageUrl={item.image_url}
        bodyPart={item.body_part}
        diagnosis={item.diagnosis}
        title={item.title}
      />
      <div>
        <div className="card-topline">
          <span>{item.image_id}</span>
          <span>{item.rerank_score.toFixed(3)}</span>
        </div>
        <h4>{item.title}</h4>
        <p>{item.evidence_note}</p>
        <div className="tags">
          <span>{item.region}</span>
          <span>{item.fracture_type}</span>
        </div>
        <Button className="evidence-detail-button" onClick={onView}>
          Xem chi tiết
        </Button>
      </div>
    </article>
  );
}
