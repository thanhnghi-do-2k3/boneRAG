import { Button } from '../design-system/Button';

export function EvidenceModal({ item, onClose }) {
  const rows = [
    ['Image ID', item.image_id],
    ['Tiêu đề', item.title],
    ['Vùng cơ thể', item.body_part],
    ['Chẩn đoán', item.diagnosis],
    ['Kiểu gãy / nguy cơ', item.fracture_type],
    ['Vùng giải phẫu', item.region],
    ['Retrieval score', item.retrieval_score?.toFixed?.(4) ?? item.retrieval_score],
    ['Rerank score', item.rerank_score?.toFixed?.(4) ?? item.rerank_score],
    ['Ghi chú evidence', item.evidence_note],
  ];

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <article className="evidence-modal">
        <div className="modal-head">
          <div>
            <p className="eyebrow">Evidence detail</p>
            <h3>{item.title}</h3>
          </div>
          <Button className="icon-button" onClick={onClose} aria-label="Đóng chi tiết evidence">
            x
          </Button>
        </div>
        <div className="modal-body">
          <div className="xray-tile modal-xray">
            <span>{item.body_part}</span>
            <strong>{item.diagnosis}</strong>
          </div>
          <dl className="detail-list">
            {rows.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </article>
    </div>
  );
}
