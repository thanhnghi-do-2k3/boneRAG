import { useEffect, useRef } from 'react';
import { ModelSelector } from '../components/ModelSelector';
import { ChatComposer } from '../components/ChatComposer';
import { ChatMessage } from '../components/ChatMessage';
import { EvidenceDrawer } from '../components/EvidenceDrawer';
import { EvidenceModal } from '../components/EvidenceModal';

export function QuestionScreen({
  question,
  setQuestion,
  running,
  messages,
  activeEvidenceContext,
  selectedEvidence,
  selectedImage,
  onShowMessageEvidence,
  onSelectEvidence,
  onClearImage,
  onPasteImage,
  drawerWidth,
  onBeginDrawerResize,
  sidebarOpen,
  onOpenSidebar,
  runStream,
}) {
  const transcriptRef = useRef(null);

  useEffect(() => {
    transcriptRef.current?.scrollTo({ top: transcriptRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  return (
    <section className="screen chat-screen with-evidence" style={{ '--evidence-width': `${drawerWidth}px` }}>
      <header className="chat-topbar">
        <div className="topbar-left">
          {!sidebarOpen && (
            <button className="sidebar-topbar-button" onClick={onOpenSidebar} aria-label="Mở menu">
              Menu
            </button>
          )}
          <div>
            <p className="eyebrow">Hỏi đáp</p>
            <h2>Chat với BoneRAG</h2>
            <span>F5 tạo phiên mới. Lịch sử xem lại nằm ở tab riêng.</span>
          </div>
        </div>
        <div className="topbar-model-selector">
          <ModelSelector />
        </div>
      </header>

      <section className="chat-layout">
        <article className="chat-panel panel">
          <div className="chat-transcript" ref={transcriptRef}>
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                onShowEvidence={() => onShowMessageEvidence(message)}
              />
            ))}
          </div>
          <ChatComposer
            question={question}
            setQuestion={setQuestion}
            running={running}
            selectedImage={selectedImage}
            onPasteImage={onPasteImage}
            runStream={runStream}
          />
        </article>

        <EvidenceDrawer
          context={activeEvidenceContext}
          selectedImage={selectedImage}
          width={drawerWidth}
          onClearImage={onClearImage}
          onSelectEvidence={onSelectEvidence}
          onBeginResize={onBeginDrawerResize}
        />
      </section>

      {selectedEvidence && <EvidenceModal item={selectedEvidence} onClose={() => onSelectEvidence(null)} />}
    </section>
  );
}
