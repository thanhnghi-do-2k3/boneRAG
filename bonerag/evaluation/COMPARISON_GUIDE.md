# Cách so sánh BoneRAG với công trình trước

## Kết luận ngắn

Bộ benchmark hiện tại là **FracAtlas-derived closed grounded VQA pilot**. Nó đủ
để trả lời câu hỏi BoneRAG có tốt hơn các baseline đã chạy thật trên cùng
FracAtlas hold-out hay không. Nó chưa đủ để tuyên bố BoneRAG hơn MMed-RAG, RULE
hoặc FactMM-RAG, và cũng chưa phải native clinician-authored VQA vì câu hỏi
yes/no đang được sinh từ annotation/folder label.

## Ma trận bài toán liên quan

| Nhóm | Dataset / benchmark | Bài toán | Metric chính | Đặt cạnh BoneRAG thế nào |
|---|---|---|---|---|
| MSK fracture | [FracAtlas](https://pmc.ncbi.nlm.nih.gov/articles/PMC10404222/) / [Figshare](https://figshare.com/articles/dataset/The_dataset/22363012) | Classification, localization, segmentation gãy xương | Accuracy/F1 cho label; mAP/IoU cho box/mask | Cùng domain nhất. Hiện BoneRAG mới dùng binary label; bước hợp lệ tiếp theo là thêm localization/mask grounding. |
| Bone tumor | [BTXRD/BTRXD](https://www.nature.com/articles/s41597-024-04311-y) | Classification, localization, segmentation u xương | Macro-F1 cho normal/benign/malignant; mAP/IoU/Dice cho box/mask | Rất khớp đề tài bệnh lý xương. Cần loader riêng, không trộn trực tiếp vào fracture benchmark. |
| MSK abnormality | [MURA](https://stanfordmlgroup.github.io/competitions/mura/) | Normal/abnormal trên upper-extremity X-ray studies | Cohen's kappa; hidden test leaderboard | Không so số trực tiếp với FracAtlas. Dùng làm external transfer nếu implement loader và study-level evaluation. |
| Pediatric wrist trauma | [GRAZPEDWRI-DX](https://pmc.ncbi.nlm.nih.gov/articles/PMC9122976/) | Wrist fracture/object detection với tags, boxes, polygons | Detection F1/mAP, tag accuracy | Rất phù hợp để kiểm tra BoneRAG có học được localization/evidence không, nhưng cần dataset loader riêng. |
| Hand radiograph regression | [RSNA Pediatric Bone Age](https://www.rsna.org/artificial-intelligence/ai-image-challenge/rsna-pediatric-bone-age-challenge-2017) | Dự đoán tuổi xương từ hand X-ray | Mean absolute distance/error theo tháng | Liên quan xương nhưng không phải fracture/RAG; chỉ dùng cho discussion hoặc transfer encoder. |
| Plain-film radiology VQA | [RadBench](https://harrison-ai.github.io/radbench/datasets/radbench/) | Clinician-curated QA trên plain X-ray, có closed/open và multi-turn | Closed accuracy, open answer score, case-level accuracy | External native-VQA sanity check gần nhất với "hỏi đáp trực quan"; không chuyên xương nhưng có plain-film/fracture-style cases. |
| Radiology MedVQA | [VQA-RAD](https://www.nature.com/articles/sdata2018251) | Clinician-generated QA trên ảnh radiology | Accuracy cho closed/open answer; BLEU/semantic variants tùy paper | Benchmark hợp lệ nếu muốn nói VQA thật, vì có câu hỏi và reference answer. |
| Radiology MedVQA + KG | [SLAKE](https://www.med-vqa.com/slake/) | English/Chinese medical VQA, có semantic labels, masks, KG | Open/closed accuracy, reasoning/category breakdown | Phù hợp để test RAG/knowledge retrieval; cần loader và split chính thức. |
| Pathology VQA | [PathVQA](https://aclanthology.org/2021.acl-short.90/) | Open/closed QA trên pathology images | Accuracy/BLEU theo open/closed | Liên quan explanation/reasoning, nhưng khác modality; dùng để kiểm tra general Medical VQA. |
| Large-scale MedVQA | [PMC-VQA](https://pmc.ncbi.nlm.nih.gov/articles/PMC11663219/) | Large-scale generated medical VQA từ PMC figures | MCQ accuracy, open-ended ACC/BLEU | Có ích để pretrain/evaluate VQA quy mô lớn; không thay thế FracAtlas fracture benchmark. |
| Challenge VQA | [ImageCLEF VQA-Med 2019](https://www.imageclef.org/2019/medical/vqa/) | Radiology QA theo modality/plane/organ/abnormality, có ca musculoskeletal/fracture/tumor | Challenge accuracy/BLEU/WBSS tùy year | Lọc musculoskeletal subset để có external native-VQA gần với xương. |
| Explanation/rationale | [MedThink / R-RAD, R-SLAKE, R-Path](https://aclanthology.org/2025.findings-naacl.415/) | VQA kèm rationale trung gian | Answer accuracy + rationale/explanation metric | Hướng đúng nếu muốn đánh giá giải thích, không chỉ đúng/sai label. |

## Phương pháp liên quan nên thảo luận

| Phương pháp | Bài toán gốc | Thành phần đáng học | Có được thêm vào benchmark hiện tại không? |
|---|---|---|---|
| [MIRAGE / MedRAG](https://arxiv.org/abs/2402.13178) | Text medical QA với nhiều corpus/retriever/backbone | Matrix hóa corpus, retriever, generator; question-only retrieval; báo nhiều dataset | Không. Đây là text QA, nên chỉ đưa vào Related Work/protocol design. |
| [MMed-RAG](https://arxiv.org/abs/2410.13085) | Multimodal medical VQA/report generation | Domain-aware retrieval, adaptive context selection, RAG preference tuning | Chỉ thêm khi chạy official code hoặc implement đủ ba thành phần trên cùng split. |
| [RULE](https://arxiv.org/abs/2407.05131) | Factuality cho Med-LVLM trong VQA/report generation | Calibrated context count, preference data chống over-reliance vào retrieval | Không thêm row proxy. Có thể implement thành ablation `adaptive_k` thật sau này. |
| [FactMM-RAG](https://arxiv.org/abs/2407.15268) | Radiology report generation trên MIMIC-CXR/CheXpert | RadGraph/CheXbert-guided factual retriever, factual report-pair mining | Không so trực tiếp với FracAtlas; chỉ hợp lệ nếu có report corpus và RadGraph-style labels. |
| [MR-RAG](https://openaccess.thecvf.com/content/CVPR2026/html/Li_MR-RAG_Multimodal_Relevance-Aware_Retrieval-Augmented_Generation_for_Medical_Visual_Question_Answering_CVPR_2026_paper.html) | Medical VQA multimodal RAG | Cooperative retrieval bằng intra/cross-modal relevance và relevance-aware generation | Có thể học thiết kế retrieval, nhưng cần implement module thật và test trên MedVQA datasets. |
| [MKGF](https://github.com/ehnal/MKGF) | MedVQA với multimodal knowledge graph | Question-knowledge relations, KG retrieval, BiomedCLIP/BGE retriever | Không phù hợp FracAtlas hiện tại vì chưa có KG; phù hợp cho SLAKE/VQA-RAD extension. |
| [Path-RAG](https://proceedings.mlr.press/v259/naeem25a.html) | Open-ended pathology VQA | Region/key-patch retrieval có domain guidance | Ý tưởng tốt cho fracture box/mask retrieval, nhưng khác modality và cần localization implementation. |
| [VisRAG](https://arxiv.org/abs/2410.10594) | RAG trên multimodal documents | Embed trang/tài liệu như ảnh thay vì parse text trước | Chỉ là inspiration cho image-first retrieval, không phải medical X-ray baseline. |

## Baseline thật nên thêm vào trước khi nói tiến bộ

| Baseline | Vì sao cần | Có thể chạy trên FracAtlas hiện tại? |
|---|---|---|
| kNN majority vote trên image embedding | Kiểm tra RAG có hơn một classifier cực đơn giản không | Đã thêm vào benchmark mặc định. Dùng cùng FAISS top-k, vote fracture/normal, không gọi generator. |
| Similarity-weighted kNN trên image embedding | Kiểm tra top-k vote có tốt hơn nearest neighbor/top-1 không | Đã thêm vào benchmark mặc định. Dùng trọng số cosine similarity, không gọi generator. |
| Class-centroid/prototype classifier | Kiểm tra embedding space có phân tách fracture/normal bằng prototype lớp không | Đã thêm vào benchmark mặc định. Centroid được tính sau khi loại full test hold-out. |
| Zero-shot BiomedCLIP prompt classifier | Kiểm tra encoder image-text có tự phân biệt fracture/normal bằng prompt không | Đã thêm vào benchmark mặc định. So query image embedding với prototype prompt fracture/normal. |
| Linear probe / logistic regression trên frozen embeddings | Baseline supervised nhẹ, thường mạnh hơn retrieval label proxy | Đã thêm vào benchmark mặc định. Train trên non-test records sau khi loại full test hold-out; dùng để kiểm tra BoneRAG có hơn classifier cùng bài toán không. |
| Supervised ViT/DenseNet/ResNet classifier | Baseline classification chuẩn cho paper | Có, nhưng cần training pipeline và confidence interval. |
| YOLO/Mask-RCNN/segmentation baseline | Đánh giá localization/explanation bằng box/mask thay vì lời giải thích tự do | Có, vì FracAtlas có annotations; cần mAP/IoU metric. |
| Official MURA/GRAZPEDWRI-DX transfer | Kiểm tra generalization ngoài FracAtlas | Có sau khi thêm dataset loaders và protocol riêng. |

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
4. **Bone dataset expansion:** thêm BTXRD/BTRXD cho u xương và GRAZPEDWRI-DX
   cho wrist trauma. Đây vẫn là annotation-derived QA, nên chấm decision,
   grounding và evidence bằng label/box/mask.
5. **External native VQA:** thêm RadBench hoặc ImageCLEF VQA-Med
   musculoskeletal subset với câu hỏi và câu trả lời gốc. Không trộn câu hỏi
   của test vào index.
6. **Method transfer:** chỉ sau khi có bước 1-5 mới thêm adaptive-k, factual
   reranker, hard-negative mining hoặc preference tuning. Mỗi thay đổi chạy
   lại cùng fingerprint và có ablation riêng.
7. **Cross-dataset validation:** nếu FracAtlas có cải thiện, chạy lại trên
   MURA hoặc GRAZPEDWRI-DX. Nếu không transfer được thì chỉ claim trong phạm vi
   FracAtlas.

## Cách viết claim trong báo cáo

Claim có thể bảo vệ được với protocol hiện tại:

> Trên `bonerag-grounded-vqa-v5`, với cùng encoder, FAISS image index,
> generator và 64 ảnh FracAtlas-derived VQA test hold-out, BoneRAG đạt ... so
> với các baseline đã chạy thật.

Claim chưa được phép viết:

> BoneRAG tốt hơn MMed-RAG/RULE/FactMM-RAG.

Muốn viết claim thứ hai, cần lấy đúng public benchmark của công trình đó,
đúng split, đúng input modality, chạy lại baseline của họ hoặc dùng checkpoint
được công bố, rồi báo confidence interval hoặc ít nhất kết quả trên nhiều seed.
