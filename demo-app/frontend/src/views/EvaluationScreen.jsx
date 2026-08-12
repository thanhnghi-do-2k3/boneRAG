import React, { useEffect, useRef, useState } from 'react';
import { ScreenHeader } from '../design-system/ScreenHeader';
import { analyzeBenchmarkRun, fetchBenchmarkRuns, openBenchmarkStream } from '../services/boneragApi';

const percent = (value) => (Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(1)}%` : '—');
const decimal = (value) => (Number.isFinite(Number(value)) ? Number(value).toFixed(3) : '—');

const chartMetrics = [
  ['retrieval_top1_label_accuracy', 'Top-1'],
  ['evidence_label_precision_at_4', 'P@4'],
  ['evidence_label_mrr', 'MRR'],
  ['evidence_label_ndcg_at_4', 'nDCG@4'],
  ['answer_label_accuracy', 'Answer'],
];

function BenchmarkChart({ systems }) {
  if (!systems.length) return null;
  return (
    <div className="benchmark-chart panel">
      <div className="benchmark-panel-heading">
        <div><span className="eyebrow">Metric chart</span><h3>Biểu đồ so sánh nhanh</h3></div>
        <span>{systems.length} systems</span>
      </div>
      <div className="benchmark-chart-grid">
        {chartMetrics.map(([key, label]) => (
          <div className="benchmark-chart-metric" key={key}>
            <strong>{label}</strong>
            <div className="benchmark-bars">
              {systems.map((system) => {
                const value = Number(system[key]) || 0;
                return (
                  <div className="benchmark-bar-row" key={`${key}-${system.system_key}`}>
                    <span>{system.system_label}</span>
                    <div><i style={{ width: `${Math.max(2, value * 100)}%` }} /></div>
                    <em>{percent(value)}</em>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function EvaluationScreen() {
  const [encoder, setEncoder] = useState('biomedclip');
  const [generator, setGenerator] = useState('local_context_synth');
  const [includeControls, setIncludeControls] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [progress, setProgress] = useState({ current: 0, total: 128 });
  const [completedSummary, setCompletedSummary] = useState(null);
  const [evaluatedCases, setEvaluatedCases] = useState([]);
  const [savedRuns, setSavedRuns] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const logEndRef = useRef(null);

  useEffect(() => {
    fetchBenchmarkRuns().then(setSavedRuns).catch(() => setSavedRuns([]));
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const handleRunBenchmark = () => {
    setIsRunning(true);
    setLogs([]);
    setEvaluatedCases([]);
    setCompletedSummary(null);
    setAnalysis(null);

    const eventSource = openBenchmarkStream({ encoder, generator, includeControls });
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'bench-start') {
          setLogs((prev) => [...prev, `[INIT] ${data.message}`, `[PROTOCOL] ${data.protocol?.dataset_fingerprint || 'pending'} | ${data.total_cases} cases x ${data.systems.length} systems`]);
          setProgress({ current: 0, total: data.total });
        } else if (data.type === 'bench-case') {
          const fallbackNote = data.generator_fallback ? ' | GENERATOR_FALLBACK' : '';
          const answerNote = data.answer_predicted_diagnosis ? ` | answer=${data.answer_predicted_diagnosis}` : ' | answer=unknown';
          const logLine = `[${data.system_label}] ${data.case_id} | expected=${data.expected_diagnosis} | top=${data.predicted_top_diagnosis || 'none'}${answerNote} | retrieval=${percent(data.retrieval_top1_label_accuracy)} | latency=${data.latency_ms}ms${fallbackNote}`;
          setLogs((prev) => [...prev, logLine]);
          setProgress({ current: data.index, total: data.total });
          setEvaluatedCases((prev) => [...prev, data]);
        } else if (data.type === 'bench-case-error') {
          setLogs((prev) => [...prev, `[ERROR] ${data.system_label} ${data.case_id}: ${data.message}`]);
          setProgress({ current: data.index, total: data.total });
        } else if (data.type === 'bench-complete') {
          setLogs((prev) => [...prev, `[COMPLETE] ${data.message}`, `[RUN] ${data.run_id}`]);
          setCompletedSummary(data.summary);
          setSavedRuns((prev) => [{
            run_id: data.run_id,
            protocol: data.summary,
            encoder,
            generator,
            include_controls: includeControls,
            systems: data.summary.systems,
          }, ...prev.filter((run) => run.run_id !== data.run_id)].slice(0, 20));
          setIsRunning(false);
          eventSource.close();
        } else if (data.type === 'bench-error') {
          setLogs((prev) => [...prev, `[ERROR] ${data.message}`]);
          setIsRunning(false);
          eventSource.close();
        }
      } catch (err) {
        console.error('Failed to parse benchmark SSE event:', err);
      }
    };

    eventSource.onerror = (err) => {
      setLogs((prev) => [...prev, `[STREAM ERROR] ${err?.message || 'Kết nối benchmark bị đóng.'}`]);
      setIsRunning(false);
      eventSource.close();
    };
  };

  const downloadRun = () => {
    const payload = {
      protocol: completedSummary,
      cases: evaluatedCases,
      exported_at: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `bonerag-benchmark-${Date.now()}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const handleAnalyze = async () => {
    if (!completedSummary) return;
    setIsAnalyzing(true);
    setAnalysis(null);
    try {
      const result = await analyzeBenchmarkRun({
        summary: completedSummary,
        cases: evaluatedCases,
      });
      setAnalysis(result);
    } catch (err) {
      setAnalysis({ ok: false, source: 'client_error', analysis: err?.message || 'Không gọi được API nhận xét.' });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const systems = completedSummary?.systems || [];

  return (
    <section className="screen">
      <ScreenHeader
        eyebrow="Đánh giá reproducible"
        title="Benchmark Image RAG thật"
        description="Một bộ ảnh FracAtlas cố định, toàn bộ test hold-out bị loại khỏi corpus, rồi chạy các ablation chính để so sánh công bằng."
      />

      <div className="panel benchmark-history-panel">
        <div className="benchmark-panel-heading">
          <div><span className="eyebrow">Run history</span><h3>Các lần benchmark gần đây</h3></div>
          <span>{savedRuns.length} runs</span>
        </div>
        {savedRuns.length === 0 ? (
          <p className="benchmark-empty-history">Chưa có run được lưu trên backend.</p>
        ) : (
          <div className="benchmark-history-list">
            {savedRuns.map((run) => (
              <div className="benchmark-history-item" key={run.run_id}>
                <strong>{run.run_id}</strong>
                <span>{run.encoder || 'biomedclip'} · {run.generator || 'synth'} · {run.protocol?.dataset_fingerprint || '—'}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="panel" style={{ marginBottom: '1.5rem', padding: '1.25rem', borderRadius: '16px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '1rem', alignItems: 'end' }}>
          <label>
            <span className="config-field-label">Encoder dùng chung</span>
            <select className="config-select" value={encoder} onChange={(event) => setEncoder(event.target.value)} disabled={isRunning}>
              <option value="biomedclip">BiomedCLIP (medical)</option>
              <option value="clip_vit_b32">OpenAI CLIP ViT-B/32</option>
              <option value="clip_vit_l14">OpenAI CLIP ViT-L/14</option>
            </select>
          </label>
          <label>
            <span className="config-field-label">Generator dùng chung</span>
            <select className="config-select" value={generator} onChange={(event) => setGenerator(event.target.value)} disabled={isRunning}>
              <option value="local_context_synth">Evidence Synthesizer</option>
              <option value="qwen_05b">Qwen2.5-0.5B</option>
              <option value="qwen_15b">Qwen2.5-1.5B</option>
              <option value="smollm_17b">SmolLM2-1.7B</option>
            </select>
          </label>
          <label className="benchmark-control-toggle">
            <input
              type="checkbox"
              checked={includeControls}
              onChange={(event) => setIncludeControls(event.target.checked)}
              disabled={isRunning}
            />
            <span>
              Chạy thêm control
              <small>Text-only và answer calibration; dùng để audit, không phải bảng chính.</small>
            </span>
          </label>
          <button className="primary-button" onClick={handleRunBenchmark} disabled={isRunning}>
            {isRunning ? `Đang chạy ${progress.current}/${progress.total}` : 'Chạy benchmark thật'}
          </button>
        </div>
        {isRunning && (
          <div style={{ marginTop: '1rem' }}>
            <div className="benchmark-progress-label"><span>Tiến độ ma trận</span><span>{Math.round((progress.current / progress.total) * 100)}%</span></div>
            <div className="benchmark-progress"><span style={{ width: `${(progress.current / progress.total) * 100}%` }} /></div>
          </div>
        )}
      </div>

      <div className="panel benchmark-log-panel">
        <div className="benchmark-panel-heading">
          <div><span className="eyebrow">Live log</span><h3>Luồng chạy từng case</h3></div>
          <span>{logs.length} events</span>
        </div>
        <div className="benchmark-log-lines">
          {logs.length === 0 ? <p>Chưa chạy. Backend sẽ từ chối chạy nếu không tìm thấy dataset FracAtlas thật.</p> : logs.map((log, index) => <div key={`${log}-${index}`}>{log}</div>)}
          <div ref={logEndRef} />
        </div>
      </div>

      {completedSummary && (
        <>
          <div className="benchmark-result-heading">
            <div><span className="eyebrow">Result matrix</span><h3>So sánh trên cùng bộ test</h3><p>{completedSummary.dataset} · fingerprint {completedSummary.dataset_fingerprint} · {completedSummary.n_cases} ảnh · test hold-out excluded</p></div>
            <div className="benchmark-result-actions">
              <button className="secondary-button" onClick={handleAnalyze} disabled={isAnalyzing}>
                {isAnalyzing ? 'Đang nhận xét...' : 'Nhận xét bằng Gemini'}
              </button>
              <button className="secondary-button" onClick={downloadRun}>Tải JSON kết quả</button>
            </div>
          </div>
          <BenchmarkChart systems={systems} />
          {analysis && (
            <div className="benchmark-analysis panel">
              <div className="benchmark-panel-heading">
                <div><span className="eyebrow">Analysis</span><h3>Nhận xét benchmark</h3></div>
                <span>{analysis.source || 'local'}</span>
              </div>
              <pre>{analysis.analysis}</pre>
            </div>
          )}
          <div className="benchmark-table-wrap panel">
            <table className="benchmark-table">
              <thead>
                <tr>
                  <th>System</th>
                  <th>Top-1 label</th>
                  <th>Retrieval F1</th>
                  <th>Sens / Spec</th>
                  <th>Evidence P@4</th>
                  <th>Recall/MRR/nDCG</th>
                  <th>Answer label</th>
                  <th>Answer F1</th>
                  <th>Answer BalAcc</th>
                  <th>Latency</th>
                  <th>Fallback generator</th>
                  <th>Cases</th>
                </tr>
              </thead>
              <tbody>
                {systems.map((system) => (
                  <tr key={system.system_key} className={system.system_key === 'bonerag' ? 'highlight-row' : ''}>
                    <td>
                      <strong>{system.system_label}</strong>
                      {system.paper_reference && <small className="paper-proxy">{system.paper_reference}</small>}
                      <small>{system.description}</small>
                    </td>
                    <td>{percent(system.retrieval_top1_label_accuracy)}</td>
                    <td>
                      {percent(system.retrieval_f1)}
                      <small>Bal {percent(system.retrieval_balanced_accuracy)}</small>
                    </td>
                    <td>
                      {percent(system.retrieval_sensitivity)} / {percent(system.retrieval_specificity)}
                      <small>TP {system.retrieval_tp ?? '—'} · TN {system.retrieval_tn ?? '—'} · FP {system.retrieval_fp ?? '—'} · FN {system.retrieval_fn ?? '—'}</small>
                    </td>
                    <td>{percent(system.evidence_label_precision_at_4)}</td>
                    <td>
                      {percent(system.evidence_label_recall_at_4)}
                      <small>MRR {decimal(system.evidence_label_mrr)} · nDCG {decimal(system.evidence_label_ndcg_at_4)}</small>
                    </td>
                    <td>{percent(system.answer_label_accuracy)}</td>
                    <td>
                      {percent(system.answer_f1)}
                      <small>Unknown {system.answer_unknown ?? 0}</small>
                    </td>
                    <td>{percent(system.answer_balanced_accuracy)}</td>
                    <td>{decimal(system.latency_ms)} ms</td>
                    <td>{percent(system.generator_fallback_rate)}</td>
                    <td>{system.n_cases}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {evaluatedCases.length > 0 && (
        <div className="benchmark-table-wrap panel">
          <div className="benchmark-panel-heading"><div><span className="eyebrow">Case audit</span><h3>Chi tiết từng ảnh và từng system</h3></div><span>{evaluatedCases.length} rows</span></div>
          <table className="benchmark-table case-table">
            <thead><tr><th>Case</th><th>System</th><th>Expected</th><th>Top evidence</th><th>Answer label</th><th>Evidence</th><th>Answer</th><th>Latency</th></tr></thead>
            <tbody>
              {evaluatedCases.map((item, index) => (
                <tr key={`${item.system_key}-${item.case_id}-${index}`}>
                  <td><strong>{item.case_id}</strong><small>{item.query_image_id}</small></td>
                  <td>{item.system_label}</td>
                  <td>{item.expected_diagnosis}</td>
                  <td>{item.predicted_top_diagnosis || 'none'}</td>
                  <td>{item.answer_predicted_diagnosis || 'unknown'}</td>
                  <td>{percent(item.retrieval_top1_label_accuracy)}</td>
                  <td>{percent(item.answer_label_accuracy)}</td>
                  <td>{item.latency_ms} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
