import { pipelineSteps } from '../data/demoContent';
import { ScreenHeader } from '../design-system/ScreenHeader';

export function PipelineScreen({ records }) {
  return (
    <section className="screen">
      <ScreenHeader
        eyebrow="Pipeline"
        title="Pipeline hiện tại"
        description="Đây là sơ đồ logic đang chạy trong demo. Khi nâng cấp, có thể thay từng khối bằng BiomedCLIP, FAISS, ROI retrieval hoặc MLLM thật."
      />

      <section className="pipeline-board">
        {pipelineSteps.map(([title, body], index) => (
          <article className="pipeline-step" key={title}>
            <span>{String(index + 1).padStart(2, '0')}</span>
            <h3>{title}</h3>
            <p>{body}</p>
          </article>
        ))}
      </section>

      <section className="panel pipeline-kb">
        <div className="panel-heading">
          <p className="eyebrow">Knowledge base</p>
          <h3>{records.length} case mẫu đang được index</h3>
        </div>
        <div className="record-grid">
          {records.map((record) => (
            <article key={record.image_id}>
              <strong>{record.title}</strong>
              <p>{record.evidence_note}</p>
              <div className="tags">
                <span>{record.body_part}</span>
                <span>{record.diagnosis}</span>
                <span>{record.fracture_type}</span>
              </div>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
