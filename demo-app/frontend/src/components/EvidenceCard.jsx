import { Button } from '../design-system/Button';

export function EvidenceCard({ item, onView }) {
  return (
    <article className="evidence-card">
      <div className="xray-tile">
        <span>{item.body_part}</span>
        <strong>{item.diagnosis}</strong>
      </div>
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
