import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { fetchModelConfigs, setModelConfig } from '../services/boneragApi';

const GEMINI_MODELS = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash'];

export function ModelSelector({ onConfigChange, variant = 'sidebar' }) {
  const [configs, setConfigs] = useState(null);
  const [active, setActive] = useState(null);
  const [geminiKey, setGeminiKey] = useState('');
  const [geminiModel, setGeminiModel] = useState('gemini-1.5-flash');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    fetchModelConfigs()
      .then((data) => {
        setConfigs(data);
        setActive(data.active);
        setGeminiKey(data.active?.gemini_api_key || '');
        setGeminiModel(data.active?.gemini_model || 'gemini-1.5-flash');
      })
      .catch(() => {});
  }, []);

  const handleSave = async () => {
    if (!active) return;
    setSaving(true);
    try {
      const payload = {
        ...active,
        gemini_api_key: geminiKey,
        gemini_model: geminiModel,
      };
      const result = await setModelConfig(payload);
      if (result.ok) {
        setActive(result.active || payload);
        setSaved(true);
        onConfigChange?.(result.active || payload);
        setTimeout(() => setSaved(false), 2000);
      }
    } finally {
      setSaving(false);
    }
  };

  const isSidebar = variant === 'sidebar';

  if (!configs || !active) {
    if (isSidebar) {
      return (
        <button className="sidebar-model-btn loading" disabled title="Đang kết nối tải cấu hình...">
          <div className="sidebar-model-icon-box">⏳</div>
          <div className="sidebar-model-text">
            <span className="sidebar-model-title">Model Pipeline</span>
            <span className="sidebar-model-val" style={{ color: 'var(--muted)' }}>Đang tải...</span>
          </div>
        </button>
      );
    }
    return (
      <button className="topbar-model-btn loading" disabled title="Đang kết nối tải cấu hình...">
        <span className="topbar-model-icon">⏳</span>
        <span>Đang kết nối tải Foundation Model...</span>
      </button>
    );
  }

  const encoderName = configs.encoders?.[active.encoder]?.label || active.encoder;
  const generatorName = configs.generators?.[active.generator]?.label || active.generator;
  const shortEnc = encoderName.split(' ')[0];
  const shortGen = generatorName.split(' ')[0];

  return (
    <>
      {isSidebar ? (
        <button
          className="sidebar-model-btn"
          onClick={() => setOpen(true)}
          title="Bấm để đổi cấu hình Foundation Model & Generator"
        >
          <div className="sidebar-model-icon-box">🎛️</div>
          <div className="sidebar-model-text">
            <span className="sidebar-model-title">Foundation Model</span>
            <span className="sidebar-model-val">{shortEnc} + {shortGen}</span>
          </div>
          <span className="sidebar-model-arrow" title="Cài đặt">⚙️</span>
        </button>
      ) : (
        <button
          className="topbar-model-btn"
          onClick={() => setOpen(true)}
          title="Bấm để thiết lập Foundation Model (BiomedCLIP, CLIP, Gemini...)"
        >
          <span className="topbar-model-icon">🎛️</span>
          <span className="topbar-model-label">Foundation Model:</span>
          <span className="topbar-model-enc">{shortEnc}</span>
          <span className="topbar-model-sep">|</span>
          <span className="topbar-model-label">Gen:</span>
          <span className="topbar-model-gen">{shortGen}</span>
          <span className="topbar-model-action">⚙️ Đổi</span>
        </button>
      )}

      {open && createPortal(
        <div className="config-modal-backdrop" onClick={(e) => { if (e.target.className === 'config-modal-backdrop') setOpen(false); }}>
          <article className="config-modal-content" role="dialog" aria-modal="true">
            <div className="config-modal-header">
              <div>
                <p className="eyebrow" style={{ margin: 0 }}>BoneRAG Pipeline Settings</p>
                <h3>🎛️ Cấu hình Foundation Model & Generator</h3>
                <p className="config-subhint">Thiết lập mô hình thị giác y khoa SOTA và mô hình sinh ngữ cảnh cho RAG</p>
              </div>
              <button className="config-modal-close" onClick={() => setOpen(false)} aria-label="Đóng bảng cấu hình">✕</button>
            </div>

            <div className="config-modal-body">
              <div className="config-group">
                <label className="config-field-label">Vision-Language Encoder (Mã hóa đa phương thức)</label>
                <select
                  className="config-select"
                  value={active.encoder}
                  onChange={(e) => setActive({ ...active, encoder: e.target.value })}
                >
                  {Object.entries(configs.encoders || {}).map(([key, info]) => (
                    <option key={key} value={key}>
                      {info.label}{info.requires_download ? ' (⬇ Tải xuống trọng số tự động)' : ''}
                    </option>
                  ))}
                </select>
                {configs.encoders?.[active.encoder]?.description && (
                  <p className="config-field-desc">💡 {configs.encoders[active.encoder].description}</p>
                )}
              </div>

              <div className="config-group">
                <label className="config-field-label">Generator (Mô hình sinh câu trả lời)</label>
                <select
                  className="config-select"
                  value={active.generator}
                  onChange={(e) => setActive({ ...active, generator: e.target.value })}
                >
                  {Object.entries(configs.generators || {}).map(([key, info]) => (
                    <option key={key} value={key}>{info.label}</option>
                  ))}
                </select>
                {configs.generators?.[active.generator]?.description && (
                  <p className="config-field-desc">💡 {configs.generators[active.generator].description}</p>
                )}
              </div>

              {active.generator === 'ollama_local' && (
                <div className="config-group gemini-group">
                  <label className="config-field-label">Ollama Endpoint URL</label>
                  <input
                    className="config-key-input"
                    type="text"
                    placeholder="http://localhost:11434"
                    value="http://localhost:11434"
                    readOnly
                  />
                  <p className="config-field-desc" style={{ marginTop: '6px' }}>
                    💡 Đảm bảo bạn đã mở server Ollama (`ollama serve`) tại máy cục bộ.
                  </p>
                </div>
              )}
            </div>

            <div className="config-modal-footer">
              <button
                className={`config-save-btn ${saved ? 'saved' : ''}`}
                onClick={() => { handleSave(); setTimeout(() => setOpen(false), 700); }}
                disabled={saving}
              >
                {saving ? '⏳ Đang lưu & khởi tạo...' : saved ? '✓ Đã cập nhật!' : '💾 Lưu cấu hình & Áp dụng'}
              </button>
            </div>
          </article>
        </div>,
        document.body
      )}
    </>
  );
}
