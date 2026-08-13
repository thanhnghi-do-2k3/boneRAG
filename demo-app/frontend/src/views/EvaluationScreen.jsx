import React, { useEffect, useRef, useState } from 'react';
import { ScreenHeader } from '../design-system/ScreenHeader';
import {
  analyzeBenchmarkRun,
  exportBenchmarkArtifacts,
  fetchBenchmarkRuns,
  openBenchmarkStream,
} from '../services/boneragApi';

const percent = (value) => (Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(1)}%` : '—');
const decimal = (value) => (Number.isFinite(Number(value)) ? Number(value).toFixed(3) : '—');
const ciText = (ci, asPercent = true) => (
  Array.isArray(ci) && ci.length === 2
    ? `[${asPercent ? percent(ci[0]) : decimal(ci[0])}, ${asPercent ? percent(ci[1]) : decimal(ci[1])}]`
    : '—'
);

const chartMetrics = [
  ['decision_label_accuracy', 'Decision'],
  ['decision_f1', 'Decision F1'],
  ['decision_balanced_accuracy', 'Decision BalAcc'],
  ['retrieval_top1_label_accuracy', 'Retrieval Top-1'],
  ['evidence_label_precision_at_4', 'Evidence P@4'],
  ['evidence_label_mrr', 'MRR'],
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

function PaperEvaluationPanel({ paperEvaluation }) {
  if (!paperEvaluation) return null;
  const claims = paperEvaluation.claim_guidance || {};
  const paired = Array.isArray(paperEvaluation.paired_comparisons)
    ? paperEvaluation.paired_comparisons
    : [];
  const discriminationAudit = paperEvaluation.discrimination_audit || {};
  const auditWarnings = Array.isArray(discriminationAudit.warnings)
    ? discriminationAudit.warnings
    : [];
  const duplicatePairs = Array.isArray(discriminationAudit.effective_duplicate_pairs)
    ? discriminationAudit.effective_duplicate_pairs
    : [];
  return (
    <div className="paper-eval-panel panel">
      <div className="benchmark-panel-heading">
        <div><span className="eyebrow">Paper readiness</span><h3>Đánh giá có thể viết vào paper</h3></div>
        <span>{paperEvaluation.schema_version || 'paper-eval'}</span>
      </div>
      <div className="paper-claim-grid">
        <div>
          <strong>Allowed</strong>
          {(claims.allowed || []).map((item) => <p key={item}>{item}</p>)}
        </div>
        <div>
          <strong>Warnings</strong>
          {(claims.warnings || []).map((item) => <p key={item}>{item}</p>)}
        </div>
        <div>
          <strong>Blocked</strong>
          {(claims.blocked || []).map((item) => <p key={item}>{item}</p>)}
        </div>
      </div>
      <div className="benchmark-panel-heading paper-audit-heading">
        <div><span className="eyebrow">Sanity audit</span><h3>Khả năng phân biệt system</h3></div>
        <span>{duplicatePairs.length} duplicate pairs</span>
      </div>
      <div className="paper-audit-warnings">
        {auditWarnings.length === 0 ? (
          <p>Không phát hiện cặp system gần như trùng nhau trong run này.</p>
        ) : (
          auditWarnings.slice(0, 6).map((item) => <p key={item}>{item}</p>)
        )}
      </div>
      {duplicatePairs.length > 0 && (
        <div className="benchmark-table-wrap paper-paired-table">
          <table className="benchmark-table">
            <thead>
              <tr>
                <th>System A</th>
                <th>System B</th>
                <th>Decision agreement</th>
                <th>Top-1 agreement</th>
                <th>Top-4 overlap</th>
              </tr>
            </thead>
            <tbody>
              {duplicatePairs.slice(0, 8).map((item) => (
                <tr key={`${item.left_system_key}-${item.right_system_key}`}>
                  <td>{item.left_system_label}</td>
                  <td>{item.right_system_label}</td>
                  <td>{percent(item.decision_agreement)}</td>
                  <td>{percent(item.top1_agreement)}</td>
                  <td>{percent(item.top4_evidence_jaccard)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {paired.length > 0 && (
        <div className="benchmark-table-wrap paper-paired-table">
          <table className="benchmark-table">
            <thead>
              <tr>
                <th>Baseline</th>
                <th>Metric</th>
                <th>Baseline</th>
                <th>BoneRAG</th>
                <th>Delta</th>
                <th>95% CI</th>
                <th>McNemar p</th>
                <th>Direction</th>
              </tr>
            </thead>
            <tbody>
              {paired.map((item) => {
                const isLatency = item.metric === 'latency_ms';
                return (
                  <tr key={`${item.baseline_system_key}-${item.metric}`}>
                    <td>{item.baseline_system_label || item.baseline_system_key}</td>
                    <td><strong>{item.metric}</strong><small>{item.n_paired_cases} paired cases</small></td>
                    <td>{isLatency ? `${decimal(item.baseline_mean)} ms` : percent(item.baseline_mean)}</td>
                    <td>{isLatency ? `${decimal(item.method_mean)} ms` : percent(item.method_mean)}</td>
                    <td>{isLatency ? `${decimal(item.delta)} ms` : percent(item.delta)}</td>
                    <td>{ciText(item.delta_ci95, !isLatency)}</td>
                    <td>{item.mcnemar_exact_p == null ? '—' : decimal(item.mcnemar_exact_p)}</td>
                    <td>{item.claim_direction}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function EvaluationScreen() {
  const [encoder, setEncoder] = useState('biomedclip');
  const [generator, setGenerator] = useState('local_context_synth');
  const [caseCount, setCaseCount] = useState(32);
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

    const eventSource = openBenchmarkStream({
      encoder,
      generator,
      cases: caseCount,
      includeControls,
    });
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'bench-start') {
          setLogs((prev) => [...prev, `[INIT] ${data.message}`, `[PROTOCOL] ${data.protocol?.dataset_fingerprint || 'pending'} | ${data.total_cases} cases x ${data.systems.length} systems`]);
          setProgress({ current: 0, total: data.total });
        } else if (data.type === 'bench-case') {
          const fallbackNote = data.generator_fallback ? ' | GENERATOR_FALLBACK' : '';
          const answerNote = data.answer_predicted_diagnosis ? ` | answer=${data.answer_predicted_diagnosis}` : ' | answer=unknown';
          const decisionNote = data.decision_predicted_diagnosis ? ` | decision=${data.decision_predicted_diagnosis}` : ' | decision=unknown';
          const logLine = `[${data.system_label}] ${data.case_id} | expected=${data.expected_diagnosis} | top=${data.predicted_top_diagnosis || 'none'}${decisionNote}${answerNote} | decision_acc=${percent(data.decision_label_accuracy)} | retrieval=${percent(data.retrieval_top1_label_accuracy)} | latency=${data.latency_ms}ms${fallbackNote}`;
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
            cases: caseCount,
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

  const downloadTextArtifact = (filename, content, type = 'text/plain') => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const handleExportArtifact = async (artifactKey, filename, type) => {
    if (!completedSummary) return;
    try {
      const result = await exportBenchmarkArtifacts({
        summary: completedSummary,
        cases: evaluatedCases,
        encoder,
        generator,
      });
      const content = result?.artifacts?.[artifactKey];
      if (content) {
        downloadTextArtifact(filename, content, type);
      }
    } catch (err) {
      setLogs((prev) => [...prev, `[EXPORT ERROR] ${err?.message || 'Không xuất được artifact.'}`]);
    }
  };

  const systems = completedSummary?.systems || [];
  const paperEvaluation = completedSummary?.paper_evaluation;

  return (
    <section className="screen">
      <ScreenHeader
        eyebrow="Đánh giá reproducible"
        title="Benchmark Image RAG thật"
        description="Binary FracAtlas retrieval/classification proxy: test hold-out bị loại khỏi corpus, rồi chạy NN, zero-shot prompt, kNN, centroid và BoneRAG trên cùng bộ ảnh."
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
          <label>
            <span className="config-field-label">Số ảnh test</span>
            <select
              className="config-select"
              value={caseCount}
              onChange={(event) => setCaseCount(Number(event.target.value))}
              disabled={isRunning}
            >
              <option value={32}>32 ảnh</option>
              <option value={64}>64 ảnh</option>
              <option value={128}>128 ảnh</option>
              <option value={256}>256 ảnh</option>
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
              Chạy answer ablation
              <small>Thêm BoneRAG + Answer Calibration; không phải retrieval claim.</small>
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
              <button className="secondary-button" onClick={() => handleExportArtifact('markdown_report', 'bonerag-paper-evaluation.md', 'text/markdown')}>
                Tải report paper
              </button>
              <button className="secondary-button" onClick={() => handleExportArtifact('paired_comparisons_csv', 'bonerag-paired-comparisons.csv', 'text/csv')}>
                Tải CSV paired
              </button>
              <button className="secondary-button" onClick={() => handleExportArtifact('summary_svg', 'bonerag-paper-chart.svg', 'image/svg+xml')}>
                Tải SVG chart
              </button>
              <button className="secondary-button" onClick={downloadRun}>Tải JSON kết quả</button>
            </div>
          </div>
          <BenchmarkChart systems={systems} />
          <PaperEvaluationPanel paperEvaluation={paperEvaluation} />
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
                  <th>Decision</th>
                  <th>Decision F1</th>
                  <th>Decision BalAcc</th>
                  <th>Top-1 label</th>
                  <th>Retrieval F1</th>
                  <th>Sens / Spec</th>
                  <th>Evidence P@4</th>
                  <th>Recall/MRR/nDCG</th>
                  <th>Answer label</th>
                  <th>Answer F1</th>
                  <th>Answer BalAcc</th>
                  <th>Ans/Evidence</th>
                  <th>Factuality</th>
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
                      <small>{system.description}</small>
                    </td>
                    <td>
                      {percent(system.decision_label_accuracy)}
                      <small>Conf {decimal(system.decision_confidence)}</small>
                    </td>
                    <td>{percent(system.decision_f1)}</td>
                    <td>{percent(system.decision_balanced_accuracy)}</td>
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
                      <small>MRR {decimal(system.evidence_label_mrr)} · nDCG {decimal(system.evidence_label_ndcg_at_4)} · Cons {percent(system.evidence_label_consensus)}</small>
                    </td>
                    <td>{percent(system.answer_label_accuracy)}</td>
                    <td>
                      {percent(system.answer_f1)}
                      <small>Unknown {system.answer_unknown ?? 0}</small>
                    </td>
                    <td>{percent(system.answer_balanced_accuracy)}</td>
                    <td>
                      {percent(system.answer_matches_evidence_majority)}
                      <small>Top {percent(system.answer_matches_top_evidence)}</small>
                    </td>
                    <td>
                      {percent(system.answer_factuality_score)}
                      <small>Warn {percent(system.answer_hallucination_warning_rate)} · Unsup {system.answer_unsupported_claims ?? 0}</small>
                    </td>
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
            <thead><tr><th>Case</th><th>System</th><th>Expected</th><th>Decision</th><th>Top evidence</th><th>Evidence majority</th><th>Answer label</th><th>Evidence</th><th>Answer</th><th>Faithful</th><th>Latency</th></tr></thead>
            <tbody>
              {evaluatedCases.map((item, index) => (
                <tr key={`${item.system_key}-${item.case_id}-${index}`}>
                  <td><strong>{item.case_id}</strong><small>{item.query_image_id}</small></td>
                  <td>{item.system_label}</td>
                  <td>{item.expected_diagnosis}</td>
                  <td>{item.decision_predicted_diagnosis || 'unknown'}<small>{item.decision_source || '—'}</small></td>
                  <td>{item.predicted_top_diagnosis || 'none'}</td>
                  <td>{item.evidence_majority_diagnosis || 'tie'}<small>{percent(item.evidence_label_consensus)}</small></td>
                  <td>{item.answer_predicted_diagnosis || 'unknown'}</td>
                  <td>{percent(item.retrieval_top1_label_accuracy)}</td>
                  <td>{percent(item.answer_label_accuracy)}</td>
                  <td>{percent(item.answer_factuality_score)}</td>
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
