import { stageLabels } from '../data/demoContent';
import { ScreenHeader } from '../design-system/ScreenHeader';

export function LogScreen({ logs, rawHits, running }) {
  return (
    <section className="screen">
      <ScreenHeader
        eyebrow="Log"
        title="Log sinh câu trả lời"
        description="Màn hình này ghi các sự kiện quan trọng trong lúc hệ thống sinh câu trả lời. Muốn chỉnh hoặc thêm log, sửa event trong pipeline và mapping ở frontend."
      />

      <section className="log-grid">
        <article className="panel">
          <div className="panel-heading">
            <p className="eyebrow">Runtime events</p>
            <h3>Các log vừa ghi</h3>
          </div>
          <div className="timeline">
            {logs.length === 0 && (
              <p className="empty">{running ? 'Đang chờ event...' : 'Chưa có log. Hãy chạy một câu hỏi trước.'}</p>
            )}
            {logs.map((entry) => (
              <article key={entry.id} className="event-card">
                <span>{stageLabels[entry.type] ?? entry.type}</span>
                <h4>{entry.title}</h4>
                <p>{entry.message}</p>
                {entry.details && <small>{entry.details}</small>}
                <time>{entry.time}</time>
              </article>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <p className="eyebrow">Raw hits</p>
            <h3>Kết quả retrieve trước rerank</h3>
          </div>
          <div className="hit-list">
            {rawHits.length === 0 && <p className="empty">Chưa có raw hit.</p>}
            {rawHits.map((hit) => (
              <div className="hit-row" key={hit.record_id}>
                <span>{hit.record_id}</span>
                <strong>{hit.score.toFixed(3)}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>
    </section>
  );
}
