import { Button } from '../design-system/Button';
import { ScreenHeader } from '../design-system/ScreenHeader';

export function ImageLibraryScreen({ records, selectedImage, onUseImage }) {
  async function copyRecord(record) {
    const text = `${record.image_id}: ${record.title}. ${record.evidence_note}`;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard can be blocked in some browsers; selecting for chat is the primary flow.
    }
  }

  return (
    <section className="screen">
      <ScreenHeader
        eyebrow="Ảnh test"
        title="Thư viện ảnh/case mẫu"
        description="Chọn một case để đưa vào ô chat như ảnh đang được hỏi. Có thể copy mô tả nhanh để test prompt."
      />

      <section className="image-library-grid">
        {records.map((record) => (
          <article
            className={`image-case-card ${selectedImage?.image_id === record.image_id ? 'selected' : ''}`}
            key={record.image_id}
          >
            <div className="xray-tile image-case-preview">
              <span>{record.body_part}</span>
              <strong>{record.diagnosis}</strong>
            </div>
            <div className="image-case-body">
              <div className="card-topline">
                <span>{record.image_id}</span>
                <span>{record.fracture_type}</span>
              </div>
              <h3>{record.title}</h3>
              <p>{record.evidence_note}</p>
              <div className="tags">
                <span>{record.region}</span>
                <span>{record.body_part}</span>
                <span>{record.diagnosis}</span>
              </div>
              <div className="image-case-actions">
                <Button onClick={() => onUseImage(record)}>Dùng để hỏi</Button>
                <Button className="ghost-button" onClick={() => copyRecord(record)}>Copy mô tả</Button>
              </div>
            </div>
          </article>
        ))}
      </section>
    </section>
  );
}
