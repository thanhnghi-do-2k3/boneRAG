import { useEffect, useState } from 'react';
import { Button } from '../design-system/Button';
import { ScreenHeader } from '../design-system/ScreenHeader';
import { XrayPreview } from '../components/XrayPreview';

export function ImageLibraryScreen({ records, selectedImage, onSelectImage }) {
  const [toast, setToast] = useState(null);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(null), 1800);
    return () => window.clearTimeout(timer);
  }, [toast]);

  async function copyRecordDescription(record) {
    const text = `${record.image_id}: ${record.title}. ${record.evidence_note}`;
    try {
      await navigator.clipboard.writeText(text);
      setToast({ type: 'success', message: 'Đã copy mô tả vào clipboard.' });
    } catch {
      setToast({ type: 'error', message: 'Không thể copy mô tả. Trình duyệt đang chặn clipboard.' });
    }
  }

  async function copyRecordImage(record) {
    try {
      const url = record.image_url || record.data_url;
      const canvas = document.createElement('canvas');
      canvas.width = 400;
      canvas.height = 300;
      const ctx = canvas.getContext('2d');

      if (url) {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        await new Promise((resolve, reject) => {
          img.onload = resolve;
          img.onerror = () => reject(new Error('Failed to load image'));
          img.src = url;
        });
        canvas.width = img.naturalWidth || 400;
        canvas.height = img.naturalHeight || 300;
        ctx.drawImage(img, 0, 0);
      } else {
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(0, 0, 400, 300);
        ctx.fillStyle = '#94a3b8';
        ctx.font = '16px sans-serif';
        ctx.fillText(record.body_part || 'X-ray', 20, 40);
        ctx.fillStyle = '#f8fafc';
        ctx.font = 'bold 20px sans-serif';
        ctx.fillText(record.diagnosis || record.title || 'Bone Image', 20, 80);
      }

      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
      if (!blob) throw new Error('Could not create PNG blob');

      if (!navigator.clipboard?.write) {
        throw new Error('Clipboard write API not available');
      }

      await navigator.clipboard.write([
        new ClipboardItem({
          [blob.type]: blob,
        }),
      ]);
      setToast({ type: 'success', message: 'Đã copy ảnh vào clipboard!' });
    } catch (err) {
      console.error('Copy image error:', err);
      setToast({ type: 'error', message: 'Không thể copy ảnh. Trình duyệt đang chặn clipboard.' });
    }
  }

  return (
    <section className="screen">
      <ScreenHeader
        eyebrow="Ảnh test"
        title="Thư viện ảnh/case mẫu"
        description="Chọn một case để đưa vào ô chat như ảnh đang được hỏi. Nhấn Copy ảnh để copy trực tiếp ảnh vào clipboard."
      />

      <section className="image-library-grid">
        {records.map((record) => (
          <article
            className={`image-case-card ${selectedImage?.image_id === record.image_id ? 'selected' : ''}`}
            key={record.image_id}
          >
            <XrayPreview
              imageUrl={record.image_url}
              bodyPart={record.body_part}
              diagnosis={record.diagnosis}
              title={record.title}
              className="image-case-preview"
            />
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
                <Button onClick={() => onSelectImage?.(record)}>📌 Chọn case để RAG</Button>
                <Button className="ghost-button" onClick={() => copyRecordImage(record)}>Copy ảnh</Button>
                <Button className="ghost-button" onClick={() => copyRecordDescription(record)}>Copy mô tả</Button>
              </div>
            </div>
          </article>
        ))}
      </section>

      {toast && (
        <div className={`copy-toast ${toast.type}`} role="status" aria-live="polite">
          {toast.message}
        </div>
      )}
    </section>
  );
}
