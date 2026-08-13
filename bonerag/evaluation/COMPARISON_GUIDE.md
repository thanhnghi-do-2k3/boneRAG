# Cách so sánh BoneRAG với công trình trước

## Kết luận ngắn

Bộ benchmark FracAtlas hiện tại chỉ đủ để trả lời câu hỏi **BoneRAG có tốt hơn
Image-only retrieval trên binary fracture proxy của chính mình hay không**. Nó
chưa đủ để tuyên bố BoneRAG hơn MMed-RAG, RULE hoặc FactMM-RAG, và cũng chưa
phải benchmark VQA/explanation đầy đủ vì câu hỏi yes/no đang được tự sinh từ
folder label.

## Những công trình nên đặt cạnh BoneRAG

| Công trình | Bài toán chính | Học được gì | Có thể so trực tiếp với FracAtlas v1? |
|---|---|---|---|
| [MIRAGE / MedRAG](https://arxiv.org/abs/2402.13178) | Medical QA với nhiều corpus/retriever/backbone | Chuẩn hóa matrix retriever-corpus-generator và đánh giá factuality | Không trực tiếp; có thể học protocol và chạy thêm trên medical QA |
| [MMed-RAG](https://arxiv.org/abs/2410.13085) | Multimodal medical RAG, adaptive context, preference tuning | So sánh context selection và generator grounding | Không, nếu không chạy cùng dataset/task |
| [RULE](https://arxiv.org/abs/2407.05131) | Reliability/factuality cho Med-LVLM | Chọn số context thích nghi và preference data | Không, nhưng có thể mượn adaptive-k và factuality metric |
| [FactMM-RAG](https://arxiv.org/abs/2407.15268) | Fact-aware multimodal report generation | Rerank theo quan hệ factual thay vì similarity hình thức | Không, nhưng có thể mượn fact-aware reranker |
| [VisRAG](https://arxiv.org/abs/2410.10594) | Visual document RAG | Encode trực tiếp trang ảnh thay cho OCR-only | Không phải X-quang, nhưng phù hợp để học image-first retrieval |
| [FracAtlas](https://pmc.ncbi.nlm.nih.gov/articles/PMC10404222/) | Localization/segmentation gãy xương | Dataset và baseline task về xương | Dataset phù hợp; metric detection/segmentation khác VQA |

## Thang thực nghiệm đề xuất

1. **Retrieval-only/classification proxy:** Image-only và BoneRAG trên cùng
   FracAtlas test hold-out. Không dùng Text-only hoặc Metadata RAG nếu không có
   external clinical text/document corpus thật. Dùng `Top-1 label`, `Evidence
   P@4`, sensitivity/specificity và latency.
2. **Generator-controlled:** giữ nguyên encoder, index, evidence và prompt;
   thay Local Evidence Synthesizer bằng Qwen2.5-0.5B, Qwen2.5-1.5B hoặc
   SmolLM2. Báo thêm `generator_fallback_rate`, bắt buộc bằng 0 trước khi
   gọi đó là kết quả của model neural.
3. **Explanation/grounding:** nếu muốn đánh giá lời giải thích, cần reference
   rationale/report hoặc yêu cầu model xuất localization rồi chấm với mask/box
   FracAtlas. Metric `answer_factuality_score` hiện tại chỉ là heuristic bám
   evidence, không phải clinical explanation score.
4. **Dataset transfer:** thêm VQA-RAD, SLAKE, PathVQA hoặc OmniMedVQA với
   split công khai, câu hỏi và câu trả lời gốc. Không trộn câu hỏi của test
   vào index.
5. **Method transfer:** chỉ sau khi có bước 1-4 mới thêm adaptive-k, factual
   reranker, hard-negative mining hoặc preference tuning. Mỗi thay đổi chạy
   lại cùng fingerprint và có ablation riêng.

## Cách viết claim trong báo cáo

Claim có thể bảo vệ được với protocol hiện tại:

> Trên `bonerag-fracatlas-image-v3`, với cùng encoder, FAISS image index,
> generator và 64 ảnh test hold-out, BoneRAG đạt ... so với Image-only RAG.

Claim chưa được phép viết:

> BoneRAG tốt hơn MMed-RAG/RULE/FactMM-RAG.

Muốn viết claim thứ hai, cần lấy đúng public benchmark của công trình đó,
đúng split, đúng input modality, chạy lại baseline của họ hoặc dùng checkpoint
được công bố, rồi báo confidence interval hoặc ít nhất kết quả trên nhiều seed.
