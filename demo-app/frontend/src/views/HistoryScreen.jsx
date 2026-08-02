import { Button } from '../design-system/Button';
import { ScreenHeader } from '../design-system/ScreenHeader';

export function HistoryScreen({ history, onOpen, onClear }) {
  return (
    <section className="screen">
      <ScreenHeader
        eyebrow="Lịch sử"
        title="Các phiên chat đã lưu"
        description="F5 sẽ mở một màn chat mới. Các phiên cũ được lưu riêng ở đây trong localStorage và chỉ dùng để xem lại."
        action={
          <Button className="theme-toggle danger history-clear" onClick={onClear}>
            Xóa lịch sử
          </Button>
        }
      />

      <section className="history-list">
        {history.length === 0 && <p className="empty">Chưa có phiên chat nào được lưu.</p>}
        {history.map((entry) => (
          <article className="history-card" key={entry.id}>
            <div>
              <p className="eyebrow">{new Date(entry.updated_at).toLocaleString('vi-VN')}</p>
              <h3>{entry.title}</h3>
              <p>{entry.messages.filter((message) => message.id !== 'welcome').length} tin nhắn</p>
            </div>
            <Button onClick={() => onOpen(entry)}>Xem lại</Button>
          </article>
        ))}
      </section>
    </section>
  );
}
