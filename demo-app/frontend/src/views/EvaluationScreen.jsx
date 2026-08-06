import React, { useState, useEffect, useRef } from 'react';
import { ScreenHeader } from '../design-system/ScreenHeader';
import { openBenchmarkStream } from '../services/boneragApi';

export function EvaluationScreen() {
  const [encoder, setEncoder] = useState('biomedclip');
  const [generator, setGenerator] = useState('local_context_synth');
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [progress, setProgress] = useState({ current: 0, total: 30 });
  const [completedSummary, setCompletedSummary] = useState(null);
  const [evaluatedCases, setEvaluatedCases] = useState([]);
  const logEndRef = useRef(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const handleRunBenchmark = () => {
    setIsRunning(true);
    setLogs([]);
    setEvaluatedCases([]);
    setCompletedSummary(null);
    setProgress({ current: 0, total: 30 });

    const eventSource = openBenchmarkStream({ encoder, generator });

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'bench-start') {
          setLogs((prev) => [...prev, `[INIT] ${data.message}`]);
          setProgress({ current: 0, total: data.total });
        } else if (data.type === 'bench-case') {
          const logLine = `[CASE ${data.index}/${data.total}] "${data.question.slice(0, 45)}..." | TopMatch: ${data.top_evidence} | Latency: ${data.latency_ms}ms`;
          setLogs((prev) => [...prev, logLine]);
          setProgress({ current: data.index, total: data.total });
          setEvaluatedCases((prev) => [...prev, data]);
        } else if (data.type === 'bench-complete') {
          setLogs((prev) => [...prev, `[COMPLETE] ${data.message}`]);
          setCompletedSummary(data.summary);
          setIsRunning(false);
          eventSource.close();
        } else if (data.type === 'bench-error') {
          setLogs((prev) => [...prev, `[ERROR] ${data.message}`]);
          setIsRunning(false);
          eventSource.close();
        }
      } catch (err) {
        console.error('Failed to parse SSE event:', err);
      }
    };

    eventSource.onerror = (err) => {
      setLogs((prev) => [...prev, `[STREAM ERROR] Kết nối backend bị đóng: ${err?.message || 'không nhận được sự kiện hoàn tất'}. Kiểm tra VITE_API_BASE_URL và Colab URL.`]);
      setIsRunning(false);
      eventSource.close();
    };
  };

  return (
    <section className="screen">
      <ScreenHeader
        eyebrow="So sánh Khoa học Minh bạch"
        title="📊 Thử nghiệm & Benchmark Trực tiếp (Live Execution)"
        description="Chọn cấu hình mô hình và khởi chạy suy luận thực tế trên 30 ca test y khoa. Giám sát luồng xử lý dòng-theo-dòng qua màn hình Terminal."
      />

      {/* Control Panel Panel */}
      <div className="panel" style={{ marginBottom: '1.5rem', background: 'var(--panel-bg, #1a1e29)', padding: '1.5rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', alignItems: 'end' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '0.4rem', fontWeight: '600' }}>Encoder Backbone:</label>
            <select
              value={encoder}
              onChange={(e) => setEncoder(e.target.value)}
              disabled={isRunning}
              style={{ width: '100%', padding: '0.6rem 0.8rem', background: '#0f172a', color: '#f8fafc', border: '1px solid #334155', borderRadius: '8px', fontSize: '0.9rem' }}
            >
              <option value="biomedclip">BiomedCLIP (Microsoft - ViT-B/16)</option>
              <option value="clip_vit_b32">OpenAI CLIP (ViT-B/32)</option>
              <option value="clip_vit_l14">OpenAI CLIP (ViT-L/14 High-Res)</option>
              <option value="resnet_text">ResNet50 + Medical Embedder</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '0.4rem', fontWeight: '600' }}>Answer Generator:</label>
            <select
              value={generator}
              onChange={(e) => setGenerator(e.target.value)}
              disabled={isRunning}
              style={{ width: '100%', padding: '0.6rem 0.8rem', background: '#0f172a', color: '#f8fafc', border: '1px solid #334155', borderRadius: '8px', fontSize: '0.9rem' }}
            >
              <option value="local_context_synth">BoneRAG Evidence Synthesizer (0% Prior Leakage)</option>
              <option value="qwen_05b">Qwen2.5-0.5B Local SLM (0.5B Params)</option>
              <option value="qwen_15b">Qwen2.5-1.5B Local SLM (1.5B Params)</option>
              <option value="smollm_17b">SmolLM2-1.7B Local SLM (1.7B Params)</option>
            </select>
          </div>

          <div>
            <button
              onClick={handleRunBenchmark}
              disabled={isRunning}
              style={{
                width: '100%',
                padding: '0.75rem 1.2rem',
                background: isRunning ? '#475569' : 'linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%)',
                color: '#ffffff',
                fontWeight: '700',
                fontSize: '0.95rem',
                border: 'none',
                borderRadius: '8px',
                cursor: isRunning ? 'not-allowed' : 'pointer',
                boxShadow: '0 4px 12px rgba(14, 165, 233, 0.3)',
                transition: 'all 0.2s ease',
              }}
            >
              {isRunning ? `⏳ Đang chạy (${progress.current}/${progress.total})...` : '▶️ Bắt đầu Chạy Benchmark Thực Tế'}
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        {isRunning && (
          <div style={{ marginTop: '1.2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#38bdf8', marginBottom: '0.3rem' }}>
              <span>Tiến độ thực thi câu hỏi y khoa:</span>
              <span>{Math.round((progress.current / progress.total) * 100)}%</span>
            </div>
            <div style={{ height: '8px', background: '#0f172a', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{ width: `${(progress.current / progress.total) * 100}%`, height: '100%', background: 'linear-gradient(90deg, #38bdf8, #818cf8)', transition: 'width 0.3s ease' }} />
            </div>
          </div>
        )}
      </div>

      {/* Terminal Live Logger */}
      <div className="panel" style={{ marginBottom: '1.5rem', background: '#090d16', padding: '1.2rem', borderRadius: '12px', border: '1px solid #1e293b', fontFamily: 'monospace' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem', borderBottom: '1px solid #1e293b', paddingBottom: '0.5rem' }}>
          <span style={{ color: '#38bdf8', fontSize: '0.85rem', fontWeight: '700' }}>🖥️ LIVE SSE TERMINAL MONITOR</span>
          <span style={{ color: '#64748b', fontSize: '0.75rem' }}>{logs.length} events logged</span>
        </div>
        <div style={{ height: '220px', overflowY: 'auto', fontSize: '0.82rem', lineHeight: '1.5', color: '#e2e8f0' }}>
          {logs.length === 0 ? (
            <p style={{ color: '#475569', fontStyle: 'italic' }}>Ấn nút "Bắt đầu Chạy Benchmark Thực Tế" phía trên để theo dõi kết quả chạy từng ca test dòng-theo-dòng...</p>
          ) : (
            logs.map((log, idx) => (
              <div key={idx} style={{ color: log.includes('COMPLETE') ? '#4ade80' : log.includes('ERROR') ? '#f87171' : log.includes('INIT') ? '#38bdf8' : '#cbd5e1' }}>
                {log}
              </div>
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </div>

      {/* Aggregate Results Cards */}
      {completedSummary && (
        <div style={{ marginBottom: '1.5rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem' }}>
          <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '10px', border: '1px solid #0284c7', textAlign: 'center' }}>
            <p style={{ fontSize: '0.75rem', color: '#38bdf8', margin: 0, fontWeight: '600' }}>DIAGNOSIS ACCURACY</p>
            <h2 style={{ fontSize: '1.8rem', color: '#38bdf8', margin: '0.3rem 0 0 0', fontWeight: '800' }}>
              {(completedSummary.answer_label_accuracy * 100).toFixed(1)}%
            </h2>
          </div>
          <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '10px', border: '1px solid #10b981', textAlign: 'center' }}>
            <p style={{ fontSize: '0.75rem', color: '#34d399', margin: 0, fontWeight: '600' }}>FAITHFULNESS SCORE</p>
            <h2 style={{ fontSize: '1.8rem', color: '#34d399', margin: '0.3rem 0 0 0', fontWeight: '800' }}>
              {(completedSummary.faithfulness_score * 100).toFixed(1)}%
            </h2>
          </div>
          <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '10px', border: '1px solid #818cf8', textAlign: 'center' }}>
            <p style={{ fontSize: '0.75rem', color: '#818cf8', margin: 0, fontWeight: '600' }}>RECALL@4</p>
            <h2 style={{ fontSize: '1.8rem', color: '#818cf8', margin: '0.3rem 0 0 0', fontWeight: '800' }}>
              {completedSummary.recall_at_k.toFixed(4)}
            </h2>
          </div>
          <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '10px', border: '1px solid #a855f7', textAlign: 'center' }}>
            <p style={{ fontSize: '0.75rem', color: '#c084fc', margin: 0, fontWeight: '600' }}>MRR</p>
            <h2 style={{ fontSize: '1.8rem', color: '#c084fc', margin: '0.3rem 0 0 0', fontWeight: '800' }}>
              {completedSummary.mrr.toFixed(4)}
            </h2>
          </div>
          <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '10px', border: '1px solid #f59e0b', textAlign: 'center' }}>
            <p style={{ fontSize: '0.75rem', color: '#fbbf24', margin: 0, fontWeight: '600' }}>AVG LATENCY</p>
            <h2 style={{ fontSize: '1.8rem', color: '#fbbf24', margin: '0.3rem 0 0 0', fontWeight: '800' }}>
              {completedSummary.latency_ms.toFixed(1)} ms
            </h2>
          </div>
        </div>
      )}

      {/* Evaluated Cases Table */}
      {evaluatedCases.length > 0 && (
        <div className="panel" style={{ background: 'var(--panel-bg, #1a1e29)', padding: '1.2rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)' }}>
          <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#f8fafc' }}>📋 Chi tiết Kết quả 30 Ca Test Lâm Sàng</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', color: '#cbd5e1' }}>
              <thead>
                <tr style={{ background: '#0f172a', textAlign: 'left', borderBottom: '2px solid #334155' }}>
                  <th style={{ padding: '0.6rem 0.8rem' }}>#</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Câu hỏi Y Khoa</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Nhãn Chẩn đoán</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Bằng chứng Top-1</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Độ trễ</th>
                </tr>
              </thead>
              <tbody>
                {evaluatedCases.map((c) => (
                  <tr key={c.index} style={{ borderBottom: '1px solid #1e293b' }}>
                    <td style={{ padding: '0.6rem 0.8rem', fontWeight: '700', color: '#38bdf8' }}>{c.index}</td>
                    <td style={{ padding: '0.6rem 0.8rem' }}>{c.question}</td>
                    <td style={{ padding: '0.6rem 0.8rem' }}>
                      <span style={{ padding: '0.2rem 0.5rem', borderRadius: '4px', background: c.expected_diagnosis === 'fracture' ? 'rgba(239,68,68,0.2)' : 'rgba(34,197,94,0.2)', color: c.expected_diagnosis === 'fracture' ? '#f87171' : '#4ade80', fontSize: '0.75rem', fontWeight: '700' }}>
                        {c.expected_diagnosis.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: '0.6rem 0.8rem', fontFamily: 'monospace', color: '#94a3b8' }}>{c.top_evidence}</td>
                    <td style={{ padding: '0.6rem 0.8rem', color: '#fbbf24' }}>{c.latency_ms} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
