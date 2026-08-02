import { Button } from '../design-system/Button';
import { EvidenceCard } from './EvidenceCard';
import { XrayPreview } from './XrayPreview';

export function EvidenceDrawer({
  context,
  selectedImage,
  width,
  onClearImage,
  onSelectEvidence,
  onBeginResize,
}) {
  return (
    <aside className="panel evidence-drawer" style={{ width }}>
      <button
        type="button"
        className="drawer-resize-handle"
        onMouseDown={onBeginResize}
        aria-label="Kéo để đổi kích thước sidebar evidence"
      />
      <div className="panel-heading drawer-heading">
        <div>
          <p className="eyebrow">Evidence</p>
          <h3>Bằng chứng của câu trả lời</h3>
          {context.question && <p className="drawer-question">Cho câu hỏi: {context.question}</p>}
        </div>
      </div>
      <div className="evidence-stack">
        {context.evidence.length === 0 && <p className="empty">Chưa có evidence cho bong bóng đang chọn.</p>}
        {context.evidence.slice(0, 4).map((item) => (
          <EvidenceCard item={item} key={item.image_id} onView={() => onSelectEvidence(item)} />
        ))}
      </div>
      <div className="selected-drawer-block">
        <div className="panel-heading">
          <p className="eyebrow">Ảnh đang hỏi</p>
          <h3>Ảnh đã chọn</h3>
        </div>
        {selectedImage ? (
          <article className="selected-drawer-image">
            <XrayPreview
              imageUrl={selectedImage.data_url || selectedImage.image_url}
              bodyPart={selectedImage.body_part}
              diagnosis={selectedImage.diagnosis}
              title={selectedImage.title}
              className="selected-drawer-preview"
            />
            <div>
              <div className="card-topline">
                <span>{selectedImage.image_id}</span>
                <span>{selectedImage.fracture_type}</span>
              </div>
              <h4>{selectedImage.title}</h4>
              <p>{selectedImage.evidence_note}</p>
              <div className="tags">
                <span>{selectedImage.region}</span>
                <span>{selectedImage.body_part}</span>
              </div>
              <Button className="evidence-detail-button" onClick={onClearImage}>Bỏ ảnh</Button>
            </div>
          </article>
        ) : (
          <p className="empty">Chưa chọn ảnh. Vào tab Ảnh test để chọn một case trước khi hỏi.</p>
        )}
      </div>
    </aside>
  );
}
