export const stageLabels = {
  start: 'Bắt đầu',
  encode: 'Encode',
  retrieve: 'Retrieve',
  gate: 'Gate',
  rerank: 'Rerank',
  done: 'Hoàn tất',
};

export const pipelineSteps = [
  ['Query', 'Người dùng nhập câu hỏi về ảnh X-quang xương.'],
  ['Encode', 'HashingTextEncoder biến câu hỏi thành vector truy vấn.'],
  ['Retrieve', 'InMemoryVectorIndex lấy top-k case gần nhất.'],
  ['Gate', 'Cổng quyết định có dùng evidence hay không.'],
  ['Rerank', 'Cộng điểm body part, diagnosis và region.'],
  ['Answer', 'Template generator sinh câu trả lời kèm evidence.'],
];

export const welcomeMessage = {
  id: 'welcome',
  role: 'assistant',
  text:
    'Chào bạn, mình là BoneRAG. Hãy hỏi một câu về X-quang xương, mình sẽ stream câu trả lời và gắn evidence vào từng bong bóng chat.',
  evidence: [],
  status: 'done',
};
