import { useState, useEffect } from 'react';
import { fetchSessions } from '../services/boneragApi';

function MetricBadge({ value, label }) {
  if (value === null || value === undefined) return <span className="metric-na">—</span>;
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? 'good' : pct >= 40 ? 'medium' : 'poor';
  return (
    <span className={`metric-badge ${color}`} title={label}>
      {pct}%
    </span>
  );
}

function FeedbackBadge({ rating }) {
  if (rating === 1) return <span className="feedback-pos">👍</span>;
  if (rating === -1) return <span className="feedback-neg">👎</span>;
  return <span className="feedback-none">—</span>;
}

export default function ResearchDashboard() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState('timestamp_iso');
  const [sortDir, setSortDir] = useState('desc');

  const load = () => {
    setLoading(true);
    fetchSessions()
      .then((data) => setSessions(Array.isArray(data) ? data : []))
      .catch(() => setSessions([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const filtered = sessions
    .filter((s) => {
      const q = search.toLowerCase();
      return (
        !q ||
        (s.question_raw || '').toLowerCase().includes(q) ||
        (s.model_config?.generator || '').toLowerCase().includes(q) ||
        (s.model_config?.encoder || '').toLowerCase().includes(q)
      );
    })
    .sort((a, b) => {
      let va = a[sortKey] ?? a.eval_scores?.[sortKey] ?? '';
      let vb = b[sortKey] ?? b.eval_scores?.[sortKey] ?? '';
      if (typeof va === 'string') va = va.toLowerCase();
      if (typeof vb === 'string') vb = vb.toLowerCase();
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });

  const handleSort = (key) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortKey(key); setSortDir('desc'); }
  };

  const handleExport = () => {
    const jsonl = filtered.map((s) => JSON.stringify(s)).join('\n');
    const blob = new Blob([jsonl], { type: 'application/jsonlines' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bonerag_sessions_${new Date().toISOString().slice(0, 10)}.jsonl`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const SortIcon = ({ col }) => {
    if (sortKey !== col) return <span className="sort-icon">↕</span>;
    return <span className="sort-icon active">{sortDir === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <div className="research-dashboard">
      <div className="dashboard-header">
        <div>
          <p className="eyebrow">Research</p>
          <h2>Session Logs</h2>
          <p className="dashboard-subtitle">
            {sessions.length} sessions được ghi lại • Dữ liệu nghiên cứu BoneRAG
          </p>
        </div>
        <div className="dashboard-actions">
          <button className="dashboard-refresh-btn" onClick={load}>↺ Tải lại</button>
          <button className="dashboard-export-btn" onClick={handleExport} disabled={filtered.length === 0}>
            ⬇ Export JSONL ({filtered.length})
          </button>
        </div>
      </div>

      <div className="dashboard-search">
        <input
          type="search"
          className="session-search-input"
          placeholder="Tìm theo câu hỏi, model..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="dashboard-empty">Đang tải...</div>
      ) : filtered.length === 0 ? (
        <div className="dashboard-empty">
          {sessions.length === 0
            ? 'Chưa có session nào. Hãy gửi câu hỏi để bắt đầu ghi log.'
            : 'Không tìm thấy session phù hợp.'}
        </div>
      ) : (
        <div className="sessions-table-wrap">
          <table className="sessions-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('timestamp_iso')}>
                  Thời gian <SortIcon col="timestamp_iso" />
                </th>
                <th onClick={() => handleSort('question_raw')}>
                  Câu hỏi <SortIcon col="question_raw" />
                </th>
                <th>Model</th>
                <th onClick={() => handleSort('latency_ms')}>
                  Latency <SortIcon col="latency_ms" />
                </th>
                <th>Recall@4</th>
                <th>Faithfulness</th>
                <th>Evidence</th>
                <th>Feedback</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s, i) => {
                const scores = s.eval_scores || {};
                const ts = s.timestamp_iso
                  ? new Date(s.timestamp_iso).toLocaleString('vi-VN')
                  : '—';
                const genName = s.model_config?.generator || '—';
                const encName = s.model_config?.encoder || '—';
                const evidenceCount = (s.evidence || []).length;
                return (
                  <tr key={s.session_id || i} className="session-row">
                    <td className="session-ts">{ts}</td>
                    <td className="session-question">
                      <span title={s.question_raw}>{(s.question_raw || '').slice(0, 60)}{(s.question_raw || '').length > 60 ? '…' : ''}</span>
                    </td>
                    <td className="session-model">
                      <span className="model-pill enc">{encName}</span>
                      <span className="model-pill gen">{genName}</span>
                    </td>
                    <td className="session-latency">
                      {s.latency_ms != null ? `${s.latency_ms}ms` : '—'}
                    </td>
                    <td><MetricBadge value={scores.recall_at_4} label="Recall@4" /></td>
                    <td><MetricBadge value={scores.faithfulness_score} label="Faithfulness" /></td>
                    <td className="session-evidence-count">
                      {evidenceCount > 0
                        ? <span className="evidence-count-badge">{evidenceCount}</span>
                        : <span className="metric-na">0</span>}
                    </td>
                    <td><FeedbackBadge rating={s.user_feedback} /></td>
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
