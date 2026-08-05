import { useEffect, useMemo, useReducer, useRef, useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { ModelSelector } from './components/ModelSelector';
import { fetchRecords, openAnswerStream } from './services/boneragApi';
import { buildExportPayload, clearStoredHistory, persistHistorySession } from './services/historyStorage';
import { chatReducer, initialChatState, makeSessionId } from './state/chatReducer';
import { EvaluationScreen } from './views/EvaluationScreen';
import { HistoryScreen } from './views/HistoryScreen';
import { ImageLibraryScreen } from './views/ImageLibraryScreen';
import { LogScreen } from './views/LogScreen';
import { PipelineScreen } from './views/PipelineScreen';
import { QuestionScreen } from './views/QuestionScreen';
import ResearchDashboard from './views/ResearchDashboard';

export function App() {
  const [state, dispatch] = useReducer(chatReducer, initialChatState);
  const eventSourceRef = useRef(null);
  const assistantIdRef = useRef(null);
  const sessionIdRef = useRef(makeSessionId());
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [drawerWidth, setDrawerWidth] = useState(460);

  useEffect(() => {
    fetchRecords()
      .then((records) => dispatch({ type: 'records-loaded', records }))
      .catch(() => dispatch({ type: 'records-loaded', records: [] }));

    return () => eventSourceRef.current?.close();
  }, []);

  const evidence = state.result?.evidence ?? [];
  const rawHits = state.result?.debug?.raw_hits ?? [];
  const bestEvidence = evidence[0];
  const stats = useMemo(
    () => [
      ['Records', state.records.length],
      ['Evidence', evidence.length],
      ['Retrieval', state.result?.used_retrieval ? 'ON' : state.result ? 'OFF' : '-'],
      ['Top score', bestEvidence ? bestEvidence.rerank_score.toFixed(3) : '-'],
    ],
    [state.records.length, evidence.length, state.result, bestEvidence],
  );

  function runStream(nextQuestion = state.question) {
    const trimmed = nextQuestion.trim();
    if (!trimmed || state.running) return;

    eventSourceRef.current?.close();
    const imageContext = state.selectedImage
      ? [
          `image_id: ${state.selectedImage.image_id}`,
          `body_part: ${state.selectedImage.body_part}`,
          `title: ${state.selectedImage.title}`,
          `diagnosis_hint: ${state.selectedImage.diagnosis}`,
          `region: ${state.selectedImage.region}`,
          `note: ${state.selectedImage.evidence_note}`,
        ].join('. ')
      : '';
    const pipelineQuestion = imageContext ? `${trimmed}\n\nSelected image context: ${imageContext}` : trimmed;
    const now = Date.now();
    const baseMessages = state.messages;
    const userMessage = {
      id: `user-${now}`,
      role: 'user',
      text: trimmed,
      image: state.selectedImage ?? null,
      evidence: [],
      status: 'done',
    };
    const assistantMessage = {
      id: `assistant-${now}`,
      role: 'assistant',
      text: '',
      evidence: [],
      question: trimmed,
      status: 'streaming',
    };
    assistantIdRef.current = assistantMessage.id;
    dispatch({ type: 'stream-start', question: trimmed, userMessage, assistantMessage });
    dispatch({ type: 'set-question', question: '' });

    const source = openAnswerStream(pipelineQuestion, {
      sessionId: sessionIdRef.current,
      questionRaw: trimmed,
      attachedImage: state.selectedImage
        ? {
            image_id: state.selectedImage.image_id,
            source: state.selectedImage.data_url ? 'clipboard_paste' : 'library',
            data_url: state.selectedImage.data_url || null,
          }
        : null,
    });
    eventSourceRef.current = source;

    source.onmessage = (message) => {
      const payload = JSON.parse(message.data);
      const targetId = assistantIdRef.current;

      if (payload.type === 'stage') {
        dispatch({ type: 'stage-event', event: payload });
        return;
      }

      if (payload.type === 'token') {
        dispatch({ type: 'append-token', messageId: targetId, text: payload.text });
        return;
      }

      if (payload.type === 'done') {
        const rawAnswer = payload.result?.answer ?? '';
        const cleanAnswer = rawAnswer.startsWith(`Câu hỏi: ${pipelineQuestion}`)
          ? rawAnswer.replace(`Câu hỏi: ${pipelineQuestion}`, `Câu hỏi: ${trimmed}`)
          : rawAnswer;

        const displayResult = {
          ...payload.result,
          question: trimmed,
          answer: cleanAnswer,
        };

        const finalAssistantMessage = {
          ...assistantMessage,
          text: displayResult.answer,
          evidence: displayResult.evidence ?? [],
          question: displayResult.question,
          status: 'done',
        };
        const nextMessages = [...baseMessages, userMessage, finalAssistantMessage].map((item) =>
          item.id === targetId
            ? {
                ...item,
                text: displayResult.answer,
                evidence: displayResult.evidence ?? [],
                question: displayResult.question,
                status: 'done',
              }
            : item,
        );
        const history = persistHistorySession({
          sessionId: sessionIdRef.current,
          messages: nextMessages,
          latestQuestion: displayResult.question,
        });
        dispatch({ type: 'stream-done', messageId: targetId, result: displayResult, history });
        source.close();
        return;
      }

      if (payload.type === 'error') {
        dispatch({ type: 'stream-error', messageId: targetId, message: payload.message });
        source.close();
      }
    };

    source.onerror = () => {
      source.close();
      const targetId = assistantIdRef.current;
      // Fallback: If streaming disconnects, fetch answer via POST /api/answer
      fetch('/api/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: pipelineQuestion }),
      })
        .then((r) => r.json())
        .then((data) => {
          if (data && data.answer) {
            const displayResult = {
              ...data,
              question: trimmed,
            };
            dispatch({ type: 'stream-done', messageId: targetId, result: displayResult, history: state.history });
          } else {
            dispatch({ type: 'stream-error', messageId: targetId, message: '⚠️ Lỗi kết nối máy chủ. Vui lòng thử lại!' });
          }
        })
        .catch(() => {
          dispatch({ type: 'stream-error', messageId: targetId, message: '⚠️ Lỗi kết nối mạng. Vui lòng thử lại!' });
        });
    };
  }

  function clearChat() {
    eventSourceRef.current?.close();
    sessionIdRef.current = makeSessionId();
    dispatch({ type: 'reset-chat' });
  }

  function selectPastedImage(file) {
    const reader = new FileReader();
    reader.onload = () => {
      dispatch({
        type: 'select-image',
        image: {
          image_id: `pasted-${Date.now()}`,
          title: file.name || 'Ảnh X-quang đã dán',
          body_part: 'unknown',
          diagnosis: 'pasted image',
          fracture_type: 'unknown',
          region: 'unknown',
          evidence_note: 'Ảnh được dán trực tiếp từ clipboard để hỏi trong phiên chat hiện tại.',
          text: 'pasted xray bone image clipboard user provided',
          data_url: reader.result,
        },
      });
    };
    reader.readAsDataURL(file);
  }

  function exportChat() {
    const blob = new Blob([JSON.stringify(buildExportPayload(state.messages), null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `bonerag-chat-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function beginDrawerResize(event) {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = drawerWidth;

    function handleMove(moveEvent) {
      const nextWidth = startWidth + (startX - moveEvent.clientX);
      setDrawerWidth(Math.min(Math.max(nextWidth, 340), Math.min(window.innerWidth * 0.62, 780)));
    }

    function handleUp() {
      document.body.classList.remove('resizing-drawer');
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
    }

    document.body.classList.add('resizing-drawer');
    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
  }

  return (
    <div className={`app-shell ${sidebarOpen ? 'left-sidebar-open' : 'left-sidebar-closed'}`}>
      <Sidebar
        open={sidebarOpen}
        activeScreen={state.screen}
        stats={stats}
        onClose={() => setSidebarOpen(false)}
        onScreenChange={(screen) => dispatch({ type: 'set-screen', screen })}
        onExport={exportChat}
        onClearChat={clearChat}
      />

      <main>
        {!sidebarOpen && state.screen !== 'qa' && (
          <button className="sidebar-fab" onClick={() => setSidebarOpen(true)} aria-label="Mở menu">
            Menu
          </button>
        )}
        {state.screen === 'qa' && (
          <QuestionScreen
            question={state.question}
            setQuestion={(question) => dispatch({ type: 'set-question', question })}
            running={state.running}
            messages={state.messages}
            selectedImage={state.selectedImage}
            activeEvidenceContext={state.activeEvidenceContext}
            selectedEvidence={state.selectedEvidence}
            onShowMessageEvidence={(message) => dispatch({ type: 'show-message-evidence', message })}
            onSelectEvidence={(item) => dispatch({ type: 'select-evidence', item })}
            onClearImage={() => dispatch({ type: 'select-image', image: null })}
            onPasteImage={selectPastedImage}
            drawerWidth={drawerWidth}
            onBeginDrawerResize={beginDrawerResize}
            sidebarOpen={sidebarOpen}
            onOpenSidebar={() => setSidebarOpen(true)}
            runStream={runStream}
          />
        )}
        {state.screen === 'image-library' && (
          <ImageLibraryScreen
            records={state.records}
            selectedImage={state.selectedImage}
            onSelectImage={(image) => {
              dispatch({ type: 'select-image', image });
              dispatch({ type: 'set-screen', screen: 'qa' });
            }}
          />
        )}
        {state.screen === 'logs' && <LogScreen logs={state.logs} rawHits={rawHits} running={state.running} />}
        {state.screen === 'pipeline' && <PipelineScreen records={state.records} />}
        {state.screen === 'evaluation' && <EvaluationScreen />}
        {state.screen === 'research' && <ResearchDashboard />}
        {state.screen === 'history' && (
          <HistoryScreen
            history={state.history}
            onOpen={(entry) => dispatch({ type: 'open-history-session', entry })}
            onClear={() => dispatch({ type: 'history-loaded', history: clearStoredHistory() })}
          />
        )}
      </main>
    </div>
  );
}
