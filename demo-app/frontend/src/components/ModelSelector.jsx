import { useState, useEffect } from 'react';
import { fetchModelConfigs, setModelConfig } from '../services/boneragApi';

const GEMINI_MODELS = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash'];

export function ModelSelector({ onConfigChange }) {
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

  if (!configs || !active) return null;

  const encoderName = configs.encoders?.[active.encoder]?.label || active.encoder;
  const generatorName = configs.generators?.[active.generator]?.label || active.generator;

  return (
    <div className="model-selector-wrapper">
      <button
        className="model-badge-btn"
        onClick={() => setOpen((o) => !o)}
        title="Cấu hình Model"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14" />
        </svg>
        <span className="model-badge-enc">{encoderName.split(' ')[0]}</span>
        <span className="model-badge-sep">+</span>
        <span className="model-badge-gen">{generatorName.split(' ')[0]}</span>
      </button>

      {open && (
        <div className="model-selector-panel">
          <div className="model-selector-header">
            <h4>Cấu hình Model Pipeline</h4>
            <button className="model-selector-close" onClick={() => setOpen(false)}>✕</button>
          </div>

          <label className="model-field-label">Encoder (Mã hóa)</label>
          <select
            className="model-select"
            value={active.encoder}
            onChange={(e) => setActive({ ...active, encoder: e.target.value })}
          >
            {Object.entries(configs.encoders || {}).map(([key, info]) => (
              <option key={key} value={key}>
                {info.label}{info.requires_download ? ' ⬇' : ''}
              </option>
            ))}
          </select>

          <label className="model-field-label">Generator (Sinh câu trả lời)</label>
          <select
            className="model-select"
            value={active.generator}
            onChange={(e) => setActive({ ...active, generator: e.target.value })}
          >
            {Object.entries(configs.generators || {}).map(([key, info]) => (
              <option key={key} value={key}>{info.label}</option>
            ))}
          </select>

          {active.generator === 'gemini' && (
            <>
              <label className="model-field-label">Gemini Model</label>
              <select
                className="model-select"
                value={geminiModel}
                onChange={(e) => setGeminiModel(e.target.value)}
              >
                {GEMINI_MODELS.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>

              <label className="model-field-label">
                Gemini API Key
                <span className="model-field-hint"> (lưu trong RAM, không gửi về server log)</span>
              </label>
              <input
                className="model-key-input"
                type="password"
                placeholder="AIzaSy..."
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                autoComplete="off"
              />
            </>
          )}

          <div className="model-selector-footer">
            <button
              className={`model-save-btn ${saved ? 'saved' : ''}`}
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'Đang lưu...' : saved ? '✓ Đã lưu' : 'Áp dụng'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
