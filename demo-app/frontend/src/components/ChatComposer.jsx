import { useEffect, useRef } from 'react';
import { Button } from '../design-system/Button';

export function ChatComposer({ question, setQuestion, running, selectedImage, onPasteImage, runStream }) {
  const textareaRef = useRef(null);
  const canSend = Boolean(question.trim()) && !running;

  useEffect(() => {
    const node = textareaRef.current;
    if (!node) return;
    node.style.height = 'auto';
    node.style.height = `${Math.min(node.scrollHeight, 132)}px`;
  }, [question]);

  function submit(event) {
    event.preventDefault();
    if (!canSend) return;
    runStream();
  }

  function tryPasteImage(event) {
    const imageItem = Array.from(event.clipboardData?.items ?? []).find((item) => item.type.startsWith('image/'));
    if (!imageItem) return;
    const file = imageItem.getAsFile();
    if (!file) return;
    event.preventDefault();
    onPasteImage(file);
  }

  function handlePaste(event) {
    tryPasteImage(event);
  }

  return (
    <form className="composer" onSubmit={submit} onPaste={handlePaste}>
      <div className="composer-row">
        <textarea
          ref={textareaRef}
          rows="1"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onPaste={handlePaste}
          placeholder={selectedImage ? 'Nhập câu hỏi về ảnh đã chọn (Ctrl+V để dán ảnh khác)...' : 'Ctrl+V để dán ảnh hoặc nhập câu hỏi...'}
        />
        <Button type="submit" className="send-button" disabled={!canSend} aria-label="Gửi câu hỏi">
          {running ? (
            '...'
          ) : (
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M12 19V5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M6 11L12 5L18 11" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
        </Button>
      </div>
    </form>
  );
}
