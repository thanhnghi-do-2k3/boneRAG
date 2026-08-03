import { Button } from '../design-system/Button';
import { StatGrid } from '../design-system/StatGrid';
import { ModelSelector } from './ModelSelector';

const screens = [
  ['qa', 'Hỏi đáp'],
  ['image-library', 'Ảnh test'],
  ['logs', 'Log'],
  ['pipeline', 'Pipeline'],
  ['evaluation', 'Đánh giá'],
  ['research', '🔬 Nghiên cứu'],
  ['history', 'Lịch sử'],
];

export function Sidebar({ open, activeScreen, stats, onClose, onScreenChange, onExport, onClearChat }) {
  return (
    <aside className={`sidebar ${open ? 'open' : 'closed'}`}>
      <div>
        <div className="sidebar-title-row">
          <p className="eyebrow">BoneRAG main algorithm</p>
          <Button className="icon-button sidebar-close" onClick={onClose} aria-label="Đóng menu">
            x
          </Button>
        </div>
        <h1>Image RAG QA Demo</h1>
        <p>Chat nhiều lượt với evidence, log pipeline, đánh giá kết quả và tài liệu nghiên cứu tách riêng.</p>
      </div>

      <nav className="screen-nav" aria-label="Chọn màn hình">
        {screens.map(([id, label]) => (
          <Button key={id} className={activeScreen === id ? 'active' : ''} onClick={() => onScreenChange(id)}>
            {label}
          </Button>
        ))}
      </nav>

      <div className="side-actions">
        <Button className="theme-toggle" onClick={onExport}>
          Export chat
        </Button>
        <Button className="theme-toggle danger" onClick={onClearChat}>
          Xóa chat
        </Button>
      </div>

      <StatGrid stats={stats} />
    </aside>
  );
}
