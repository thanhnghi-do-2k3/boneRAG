import { ScreenHeader } from '../design-system/ScreenHeader';

const evaluationRows = [
  ['Retrieval Recall@k', 'Đo evidence đúng có nằm trong top-k không', 'Cần ground truth evidence hoặc ca bệnh gán nhãn'],
  ['Answer accuracy', 'Đo câu trả lời đúng với nhãn bệnh không', 'So sánh với nhãn chẩn đoán hoặc bác sĩ chấm'],
  ['Evidence faithfulness', 'Đo câu trả lời có dựa trên evidence retrieved không', 'Kiểm tra citation, contradiction, unsupported claim'],
  ['Latency', 'Đo thời gian encode, retrieve, rerank, generate', 'Log từng stage rồi tổng hợp theo phiên chạy'],
];

export function EvaluationScreen() {
  return (
    <section className="screen">
      <ScreenHeader
        eyebrow="Đánh giá"
        title="Nơi theo dõi kết quả cải tiến"
        description="Mỗi khi thay encoder, reranker, gate hoặc generator, ghi một phiên đánh giá mới để so sánh khách quan với baseline."
      />

      <section className="evaluation-grid">
        <article className="panel">
          <div className="panel-heading">
            <p className="eyebrow">Protocol</p>
            <h3>Bảng metric nên dùng</h3>
          </div>
          <div className="metric-table">
            {evaluationRows.map(([metric, meaning, note]) => (
              <div className="metric-row" key={metric}>
                <strong>{metric}</strong>
                <p>{meaning}</p>
                <span>{note}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <p className="eyebrow">Experiment log</p>
            <h3>File ghi kết quả</h3>
          </div>
          <p className="empty">
            Dùng `evaluation/experiments.jsonl` để thêm từng lần chạy. Mỗi dòng là một JSON gồm tên cải tiến,
            dataset, metric, ghi chú lỗi và quyết định giữ hay bỏ.
          </p>
        </article>
      </section>
    </section>
  );
}
