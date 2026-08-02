const form = document.querySelector("#ask-form");
const questionInput = document.querySelector("#question");
const answerBox = document.querySelector("#answer-box");
const evidenceList = document.querySelector("#evidence-list");
const recordList = document.querySelector("#record-list");
const exampleButton = document.querySelector("#example-button");

const exampleQuestion = "Does this wrist X-ray show a distal radius fracture?";

function card(title, body, metaItems = []) {
  const article = document.createElement("article");
  article.className = "card";

  const heading = document.createElement("h4");
  heading.textContent = title;
  article.appendChild(heading);

  if (metaItems.length > 0) {
    const meta = document.createElement("div");
    meta.className = "meta";
    for (const item of metaItems) {
      const chip = document.createElement("span");
      chip.textContent = item;
      meta.appendChild(chip);
    }
    article.appendChild(meta);
  }

  const paragraph = document.createElement("p");
  paragraph.textContent = body;
  article.appendChild(paragraph);
  return article;
}

async function loadRecords() {
  const response = await fetch("/api/records");
  const records = await response.json();
  recordList.replaceChildren(
    ...records.map((record) =>
      card(record.title, record.evidence_note, [
        record.image_id,
        record.body_part,
        record.diagnosis,
        record.fracture_type,
      ]),
    ),
  );
}

async function ask(question) {
  answerBox.textContent = "Đang chạy pipeline...";
  evidenceList.replaceChildren();

  const response = await fetch("/api/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  const result = await response.json();
  if (!response.ok) {
    answerBox.textContent = result.error || "Có lỗi khi gọi server.";
    return;
  }

  answerBox.textContent = result.answer;
  evidenceList.replaceChildren(
    ...result.evidence.map((item) =>
      card(item.title, item.evidence_note, [
        item.image_id,
        `rerank ${item.rerank_score.toFixed(3)}`,
        item.body_part,
        item.diagnosis,
      ]),
    ),
  );
}

exampleButton.addEventListener("click", () => {
  questionInput.value = exampleQuestion;
  questionInput.focus();
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) {
    answerBox.textContent = "Bạn cần nhập câu hỏi trước.";
    return;
  }
  ask(question);
});

loadRecords();
