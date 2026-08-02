import React, { useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  basicSteps,
  comparisonRows,
  improvementIdeas,
  papers,
  pipelineGroups,
  readingMap,
  roadmap,
  sources,
} from './research-data.js';
import './styles.css';

const pages = [
  { id: 'overview', label: 'Tổng quan' },
  { id: 'papers', label: 'Paper trước đây' },
  { id: 'basics', label: 'Bước cơ bản' },
  { id: 'pipeline', label: 'Pipeline đề xuất' },
  { id: 'improvements', label: 'Cải tiến' },
  { id: 'compare', label: 'So sánh' },
  { id: 'roadmap', label: 'Lộ trình' },
  { id: 'sources', label: 'Nguồn' },
];

function App() {
  const [page, setPage] = useState('overview');
  const currentIndex = pages.findIndex((item) => item.id === page);
  const nextPage = pages[Math.min(currentIndex + 1, pages.length - 1)];
  const prevPage = pages[Math.max(currentIndex - 1, 0)];

  return (
    <div className="shell">
      <aside className="sidebar" aria-label="Điều hướng nghiên cứu">
        <div className="brand-block">
          <span className="eyebrow">Research Hub</span>
          <h1>BoneRAG cho VQA bệnh lý xương</h1>
          <p>
            Web report nhiều trang, dùng để đọc nhanh nghiên cứu, so sánh paper và mở rộng thêm hướng mới.
          </p>
        </div>
        <nav className="nav-list">
          {pages.map((item) => (
            <button
              key={item.id}
              className={page === item.id ? 'active' : ''}
              onClick={() => setPage(item.id)}
            >
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </aside>

      <main className="content">
        {page === 'overview' && <Overview onJump={setPage} />}
        {page === 'papers' && <PapersPage />}
        {page === 'basics' && <BasicsPage />}
        {page === 'pipeline' && <PipelinePage />}
        {page === 'improvements' && <ImprovementsPage />}
        {page === 'compare' && <ComparePage />}
        {page === 'roadmap' && <RoadmapPage />}
        {page === 'sources' && <SourcesPage />}

        <div className="pager">
          <button disabled={currentIndex === 0} onClick={() => setPage(prevPage.id)}>
            ← {prevPage.label}
          </button>
          <button disabled={currentIndex === pages.length - 1} onClick={() => setPage(nextPage.id)}>
            {nextPage.label} →
          </button>
        </div>
      </main>
    </div>
  );
}

function PageHeader({ kicker, title, children }) {
  return (
    <header className="page-header">
      <span className="eyebrow">{kicker}</span>
      <h2>{title}</h2>
      {children && <p>{children}</p>}
    </header>
  );
}

function Overview({ onJump }) {
  return (
    <section>
      <PageHeader kicker="Mục tiêu" title="Đọc xong là nắm vấn đề, không phải lạc trong 30 trang PDF">
        BoneRAG đặt câu hỏi: khi AI trả lời về ảnh X-quang xương, liệu nó có thể tra lại các ca tương tự,
        nhìn đúng vùng nghi ngờ, rồi trả lời có căn cứ thay vì dựa vào trí nhớ của mô hình?
      </PageHeader>

      <div className="hero-grid">
        <div className="hero-card primary">
          <h3>Bài toán nói đơn giản</h3>
          <p>
            Đầu vào là ảnh X-quang và câu hỏi. Hệ thống tìm ảnh/crop tương tự trong kho FracAtlas/MURA/BTRXD,
            chọn bằng chứng thật sự hữu ích, rồi đưa cho MLLM sinh câu trả lời có giải thích.
          </p>
        </div>
        <div className="hero-card">
          <h3>Khoảng trống nghiên cứu</h3>
          <p>
            Có Medical VQA tổng quát và có fracture detection, nhưng gần như chưa có benchmark VQA chuyên
            bệnh lý xương kết hợp Image RAG và grounding vùng tổn thương.
          </p>
        </div>
      </div>

      <div className="question-strip">
        {readingMap.map((item) => (
          <button key={item.target} onClick={() => onJump(item.target)}>
            <strong>{item.title}</strong>
            <span>{item.desc}</span>
          </button>
        ))}
      </div>

      <section className="two-col">
        <article>
          <h3>Triết lý hệ thống</h3>
          <p>
            Một mô hình thị giác-ngôn ngữ mạnh vẫn có thể ảo giác khi bị hỏi về chi tiết y khoa nhỏ. Vì vậy
            pipeline nên hoạt động giống một quy trình kiểm chứng: nhìn ảnh, tìm ca tương tự, chọn bằng chứng,
            kiểm tra nhất quán, rồi mới kết luận.
          </p>
        </article>
        <article>
          <h3>Công thức tổng quát</h3>
          <div className="formula">
            a, E*, Z, c = G(q, Iu, Select(Retrieve(q, Iu, D)))
          </div>
          <p>
            Trong đó <code>a</code> là câu trả lời, <code>E*</code> là bằng chứng đã chọn,
            <code>Z</code> là vùng căn cứ, và <code>c</code> là độ tin cậy.
          </p>
        </article>
      </section>
    </section>
  );
}

function PapersPage() {
  const [filter, setFilter] = useState('all');
  const visible = useMemo(
    () => (filter === 'all' ? papers : papers.filter((paper) => paper.kind === filter)),
    [filter],
  );

  return (
    <section>
      <PageHeader kicker="Related Work" title="Tác giả trước đã làm gì, thiếu gì, mình học được gì">
        Mỗi paper được tóm tắt theo cùng một khung: phương pháp, kết quả, triết lý, hạn chế và cách đem vào
        BoneRAG.
      </PageHeader>

      <div className="segmented" role="tablist" aria-label="Lọc paper">
        {[
          ['all', 'Tất cả'],
          ['medical-rag', 'Medical RAG'],
          ['visual-rag', 'Visual RAG'],
          ['bone', 'Ảnh xương'],
          ['region', 'Region/Utility'],
          ['reference', 'Reference papers'],
        ].map(([id, label]) => (
          <button key={id} className={filter === id ? 'active' : ''} onClick={() => setFilter(id)}>
            {label}
          </button>
        ))}
      </div>

      <div className="paper-grid">
        {visible.map((paper) => (
          <article className="paper-card" key={paper.id}>
            <div className="paper-topline">
              <span>{paper.year}</span>
              <span>{paper.venue}</span>
            </div>
            <h3>{paper.name}</h3>
            <p className="authors">{paper.authors}</p>
            <dl>
              <dt>Họ làm gì?</dt>
              <dd>{paper.method}</dd>
              <dt>Kết quả chính</dt>
              <dd>{paper.result}</dd>
              <dt>Triết lý</dt>
              <dd>{paper.philosophy}</dd>
              <dt>Thiếu sót</dt>
              <dd>{paper.gap}</dd>
              <dt>Áp dụng cho BoneRAG</dt>
              <dd>{paper.use}</dd>
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}

function BasicsPage() {
  return (
    <section>
      <PageHeader kicker="Từ con số 0" title="Những bước cơ bản nhất để giải bài toán">
        Trang này dành cho người mới: mỗi bước trả lời một câu hỏi "vì sao cần bước này?" trước khi đi vào
        kỹ thuật.
      </PageHeader>

      <div className="step-stack">
        {basicSteps.map((step, index) => (
          <article className="step-card" key={step.title}>
            <span className="step-index">{String(index + 1).padStart(2, '0')}</span>
            <div>
              <h3>{step.title}</h3>
              <p>{step.plain}</p>
              <div className="mini-grid">
                <span><strong>Input:</strong> {step.input}</span>
                <span><strong>Output:</strong> {step.output}</span>
                <span><strong>Rủi ro:</strong> {step.risk}</span>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function PipelinePage() {
  return (
    <section>
      <PageHeader kicker="Thiết kế đề xuất" title="Pipeline BoneRAG có thể triển khai và mở rộng">
        Pipeline tách rõ off-line và on-line để dễ thay encoder, reranker, detector hoặc generator mà không
        phải viết lại toàn bộ hệ thống.
      </PageHeader>

      <div className="pipeline-board">
        {pipelineGroups.map((group) => (
          <section className="pipeline-column" key={group.title}>
            <h3>{group.title}</h3>
            {group.steps.map((step) => (
              <article className="pipeline-node" key={step.title}>
                <span>{step.tag}</span>
                <h4>{step.title}</h4>
                <p>{step.body}</p>
                {step.formula && <div className="formula small">{step.formula}</div>}
              </article>
            ))}
          </section>
        ))}
      </div>
    </section>
  );
}

function ImprovementsPage() {
  return (
    <section>
      <PageHeader kicker="Cải tiến" title="Những hướng có thể học từ paper khác hoặc tự sáng tạo">
        Ưu tiên các cải tiến đo được bằng ablation: thay một khối, giữ các khối khác cố định, rồi so trực tiếp.
      </PageHeader>

      <div className="idea-list">
        {improvementIdeas.map((idea) => (
          <article className="idea-card" key={idea.title}>
            <div className="idea-header">
              <span>{idea.level}</span>
              <h3>{idea.title}</h3>
            </div>
            <p>{idea.why}</p>
            <div className="idea-detail">
              <strong>Cách làm:</strong> {idea.how}
            </div>
            <div className="idea-detail">
              <strong>Đo bằng:</strong> {idea.metric}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ComparePage() {
  return (
    <section>
      <PageHeader kicker="Bảng so sánh" title="So sánh vấn đề, giải pháp và giá trị cho BoneRAG">
        Bảng này dùng để đưa thẳng vào thuyết trình: mỗi dòng nêu một quyết định thiết kế và paper nào ủng hộ.
      </PageHeader>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Khía cạnh</th>
              <th>Cách cũ / baseline</th>
              <th>Cải tiến đề xuất</th>
              <th>Paper gợi ý</th>
            </tr>
          </thead>
          <tbody>
            {comparisonRows.map((row) => (
              <tr key={row.axis}>
                <th>{row.axis}</th>
                <td>{row.baseline}</td>
                <td>{row.proposed}</td>
                <td>{row.papers}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function RoadmapPage() {
  return (
    <section>
      <PageHeader kicker="Thực hiện" title="Lộ trình làm từ bản tối thiểu đến bản nghiên cứu mạnh">
        Mỗi phase có đầu ra rõ ràng để tránh làm quá rộng ngay từ đầu.
      </PageHeader>

      <div className="roadmap">
        {roadmap.map((phase) => (
          <article key={phase.title}>
            <span>{phase.time}</span>
            <h3>{phase.title}</h3>
            <p>{phase.goal}</p>
            <ul>
              {phase.tasks.map((task) => (
                <li key={task}>{task}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </section>
  );
}

function SourcesPage() {
  return (
    <section>
      <PageHeader kicker="Mở rộng" title="Nguồn và cách thêm nghiên cứu mới">
        Nội dung chính được rút từ thư mục paper/research của repo và vài nguồn web đã đối chiếu.
      </PageHeader>

      <div className="source-grid">
        {sources.map((source) => (
          <a href={source.url} target="_blank" rel="noreferrer" key={source.title}>
            <strong>{source.title}</strong>
            <span>{source.note}</span>
          </a>
        ))}
      </div>

      <section className="edit-guide">
        <h3>Muốn thêm paper mới?</h3>
        <p>
          Mở <code>research/src/research-data.js</code>, thêm một object vào mảng <code>papers</code>.
          App tự hiện paper trong trang "Paper trước đây" và có thể lọc bằng trường <code>kind</code>.
        </p>
      </section>
    </section>
  );
}

createRoot(document.getElementById('root')).render(<App />);
