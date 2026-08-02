import { Button } from '../design-system/Button';
import { XrayPreview } from './XrayPreview';

export function EvidenceModal({ item, onClose }) {
  const fractureBoxes = Array.isArray(item.fracture_boxes) ? item.fracture_boxes : [];
  const hasFractureOverlay = Boolean(item.image_url) && fractureBoxes.length > 0 && item.image_width && item.image_height;

  const rows = [
    ['Image ID', item.image_id],
    ['Tiêu đề', item.title],
    ['Vùng cơ thể', item.body_part],
    ['Chẩn đoán', item.diagnosis],
    ['Kiểu gãy / nguy cơ', item.fracture_type],
    ['Vùng giải phẫu', item.region],
    ['Retrieval score', item.retrieval_score?.toFixed?.(4) ?? item.retrieval_score],
    ['Rerank score', item.rerank_score?.toFixed?.(4) ?? item.rerank_score],
    ['Vùng nghi gãy (bbox)', fractureBoxes.length > 0 ? fractureBoxes.length : 'Không có annotation'],
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
          {item.image_url ? (
            <div className="modal-xray-frame">
              <img className="xray-image modal-xray" src={item.image_url} alt={item.title} />
              {hasFractureOverlay && (
                <svg
                  className="fracture-overlay"
                  viewBox={`0 0 ${item.image_width} ${item.image_height}`}
                  preserveAspectRatio="xMidYMid slice"
                  aria-label="Vùng nghi gãy"
                >
                  {fractureBoxes.map((bbox, index) => {
                    const [x, y, width, height] = bbox;
                    return (
                      <g key={`${item.image_id}-bbox-${index}`}>
                        <rect x={x} y={y} width={width} height={height} className="fracture-box" />
                        <text x={x + 8} y={y + 22} className="fracture-label">
                          fracture
                        </text>
                      </g>
                    );
                  })}
                </svg>
              )}
            </div>
          ) : (
            <XrayPreview
              imageUrl={item.image_url}
              bodyPart={item.body_part}
              diagnosis={item.diagnosis}
              title={item.title}
              className="modal-xray"
            />
          )}
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
