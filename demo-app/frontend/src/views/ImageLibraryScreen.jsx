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
    const url = record.image_url || record.data_url;

    // Attempt 1: Try clipboard API with canvas
    try {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');

      if (url) {
        // Fetch image as blob through API to avoid CORS tainting
        const res = await fetch(url, { headers: { 'ngrok-skip-browser-warning': 'true', 'Bypass-Tunnel-Remainder': 'true' } });
        const blob = await res.blob();
        const bmp = await createImageBitmap(blob);
        canvas.width = bmp.width;
        canvas.height = bmp.height;
        ctx.drawImage(bmp, 0, 0);
      } else {
        canvas.width = 400; canvas.height = 300;
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(0, 0, 400, 300);
        ctx.fillStyle = '#f8fafc';
        ctx.font = 'bold 20px sans-serif';
        ctx.fillText(record.title || 'X-ray', 20, 60);
      }

      const pngBlob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
      if (!pngBlob) throw new Error('blob null');

      if (!navigator.clipboard?.write) throw new Error('No clipboard.write');
      await navigator.clipboard.write([new ClipboardItem({ [pngBlob.type]: pngBlob })]);
      setToast({ type: 'success', message: '✅ Đã copy ảnh vào clipboard!' });
      return;
    } catch (_clipboardErr) {
      // Clipboard blocked — fall through to download
    }

    // Attempt 2: Download ảnh trực tiếp xuống máy
    try {
      if (url) {
        const res = await fetch(url, { headers: { 'ngrok-skip-browser-warning': 'true', 'Bypass-Tunnel-Remainder': 'true' } });
        const blob = await res.blob();
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `${record.image_id || 'xray'}.jpg`;
        a.click();
        URL.revokeObjectURL(a.href);
        setToast({ type: 'success', message: '⬇️ Clipboard bị chặn — đã tải ảnh xuống máy!' });
      } else {
        // No URL — copy description as text
        await navigator.clipboard.writeText(`${record.image_id}: ${record.title}. ${record.evidence_note}`);
        setToast({ type: 'success', message: '📋 Đã copy mô tả (không có ảnh URL).' });
      }
    } catch (finalErr) {
      console.error('Copy/Download image error:', finalErr);
      setToast({ type: 'error', message: '❌ Không thể copy hoặc tải ảnh. Kiểm tra console.' });
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
