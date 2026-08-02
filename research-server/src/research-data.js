export const readingMap = [
  {
    target: 'papers',
    title: 'Ai đã làm gì?',
    desc: 'Paper trước đây: phương pháp, kết quả, triết lý, thiếu sót.',
  },
  {
    target: 'basics',
    title: 'Bắt đầu từ đâu?',
    desc: 'Các bước cơ bản để giải bài toán VQA + Image RAG.',
  },
  {
    target: 'pipeline',
    title: 'Làm pipeline nào?',
    desc: 'Off-line, on-line, công thức và đầu ra từng khối.',
  },
  {
    target: 'improvements',
    title: 'Cải tiến gì?',
    desc: 'ROI, utility rerank, hard negatives, grounding, factuality.',
  },
];

export const papers = [
  {
    id: 'rule',
    kind: 'medical-rag',
    year: '2024',
    venue: 'EMNLP',
    name: 'RULE: Reliable Multimodal RAG for Factuality in Medical Vision Language Models',
    authors: 'Peng Xia, Kangyu Zhu, Haoran Li, Hongtu Zhu, Yun Li, Gang Li, Linjun Zhang, Huaxiu Yao',
    method:
      'RULE xử lý vấn đề factuality của Med-LVLM bằng hai khối: chọn số lượng context retrieved đã hiệu chỉnh rủi ro và preference fine-tuning trên các ca mô hình bị lệ thuộc quá mức vào context sai.',
    result:
      'Bản EMNLP báo cáo cải thiện trung bình 20.8% factual accuracy trên ba medical VQA datasets. Một số ghi chú web/arXiv khác nêu con số 47.4%, nên khi viết báo cáo nên ưu tiên bản ACL Anthology đã kiểm.',
    philosophy:
      'RAG không tự động tốt hơn. Bằng chứng ít quá thì thiếu, nhiều quá thì nhiễu. Mô hình còn có thể trả lời đúng khi không retrieve nhưng lại sai khi bị context kém kéo lệch.',
    gap:
      'Không chuyên bệnh lý xương, không khai thác bbox/mask xương, và trọng tâm là chọn số context hơn là chọn vùng ảnh cụ thể.',
    use:
      'Dùng làm nền lý luận cho cổng retrieve-or-not và cơ chế từ chối khi bằng chứng retrieved yếu.',
  },
  {
    id: 'mmed-rag',
    kind: 'medical-rag',
    year: '2025',
    venue: 'ICLR',
    name: 'MMed-RAG: Versatile Multimodal RAG System for Medical Vision Language Models',
    authors: 'Peng Xia et al.',
    method:
      'MMed-RAG gồm domain-aware retrieval, adaptive retrieved-context selection và RAG-based preference fine-tuning. Nó thiết kế RAG như một hệ căn chỉnh đa nguồn thay vì chỉ nối thêm tài liệu vào prompt.',
    result:
      'Tác giả báo cáo cải thiện trung bình 43.8% factual accuracy trên năm dataset thuộc X-quang, nhãn khoa và giải phẫu bệnh, gồm cả VQA và report generation.',
    philosophy:
      'Bằng chứng y khoa phải đúng miền. Retriever tổng quát có thể lấy ví dụ nhìn giống nhưng sai bệnh, làm generator tưởng có căn cứ.',
    gap:
      'Chưa nhắm riêng cơ-xương-khớp/gãy xương; chưa tận dụng mask FracAtlas hoặc retrieval cấp vùng tổn thương.',
    use:
      'Ánh xạ trực tiếp sang BoneRAG: encoder miền y sinh, chọn context thích ứng, preference tuning cho câu trả lời có căn cứ.',
  },
  {
    id: 'factmm',
    kind: 'medical-rag',
    year: '2025',
    venue: 'NAACL',
    name: 'FactMM-RAG: Fact-Aware Multimodal Retrieval Augmentation',
    authors: 'Liwen Sun, James Zhao, Megan Han, Chenyan Xiong',
    method:
      'FactMM-RAG huấn luyện retriever đa phương thức theo tín hiệu factual từ báo cáo X-quang, thay vì chỉ tối ưu similarity hình thức giữa query và document.',
    result:
      'Repo/paper báo cáo cải thiện tới 6.5 điểm F1CheXbert và 2 điểm F1RadGraph so với retriever trước đó trong sinh báo cáo X-quang.',
    philosophy:
      'Retriever phải học điều gì là hữu ích về mặt lâm sàng. Hai ảnh giống layout chưa chắc giống kết luận bệnh học.',
    gap:
      'Miền chính là radiology report, thường gần chest X-ray/report generation hơn là hỏi đáp bệnh lý xương.',
    use:
      'Fine-tune retriever BoneRAG bằng nhãn fracture, body part, bbox/mask và hard negative cùng vùng cơ thể.',
  },
  {
    id: 'visual-rag-benchmark',
    kind: 'visual-rag',
    year: '2025',
    venue: 'arXiv',
    name: 'Visual-RAG: Benchmarking Text-to-Image Retrieval Augmented Generation',
    authors: 'Yin Wu, Quanyu Long, Jing Li, Jianfei Yu, Wenya Wang',
    method:
      'Benchmark text-to-image RAG: query là text, knowledge base là ảnh iNaturalist, retriever lấy ảnh clue rồi MLLM trả lời câu hỏi chỉ dựa được vào visual evidence.',
    result:
      'Oracle clue giúp open-source models tăng khoảng 15 điểm; hard negatives làm retriever và generator dễ nhầm; text augmentation không thay thế được visual evidence.',
    philosophy:
      'Một số tri thức chỉ nằm trong ảnh: màu, texture, hình dạng, pattern. Với xương, đường gãy và biến dạng cũng là loại tri thức đó.',
    gap:
      'Miền sinh vật học, text-only query, không có ảnh X-quang người dùng và không có grounding vùng bệnh.',
    use:
      'Dùng để biện luận vì sao BoneRAG phải retrieve ảnh/crop, không chỉ retrieve text hoặc mô tả ảnh.',
  },
  {
    id: 'visrag',
    kind: 'visual-rag',
    year: '2025',
    venue: 'ICLR',
    name: 'VisRAG: Vision-Based Retrieval-Augmented Generation on Multi-Modality Documents',
    authors: 'Shi Yu, Chaoyue Tang, Bokai Xu, Junbo Cui et al.',
    method:
      'VisRAG bỏ pipeline OCR/parsing. Toàn bộ trang tài liệu được encode trực tiếp như ảnh bằng VLM; retriever và generator đều làm việc trên biểu diễn thị giác.',
    result:
      'Tác giả báo cáo tăng 20-40% end-to-end so với TextRAG trên nhiều dataset tài liệu đa phương thức.',
    philosophy:
      'Chuyển ảnh sang text quá sớm làm mất layout, hình, bảng và chi tiết thị giác. Giữ ảnh giúp tránh lỗi dây chuyền.',
    gap:
      'Thành công ở tài liệu, không phải y khoa. Page image khác X-quang: tài liệu có chữ/layout, X-quang có cấu trúc giải phẫu và tổn thương nhỏ.',
    use:
      'Làm mẫu kiến trúc image-as-embedding cho BoneRAG: encode ảnh X-quang trực tiếp, chỉ sinh text ở bước cuối.',
  },
  {
    id: 'enhanced-mm',
    kind: 'visual-rag',
    year: '2024',
    venue: 'arXiv',
    name: 'Enhanced Multimodal RAG-LLM for Accurate Visual Question Answering',
    authors: 'Junxiao Xue, Quan Deng, Fei Yu, Yanhao Wang, Jun Wang, Yuehua Li',
    method:
      'Ảnh đầu vào được biến thành structured scene graph: object category, số lượng, vị trí, quan hệ. Sau đó retrieve các chunk graph liên quan và đưa vào Qwen-2-72B.',
    result:
      'Trên VG-150/AUG, điểm overall cao hơn rõ rệt các MLLM hỏi trực tiếp, đặc biệt ở câu hỏi đếm, vị trí và quan hệ không gian.',
    philosophy:
      'MLLM yếu ở chi tiết định lượng/không gian. Biến ảnh thành cấu trúc rõ ràng giúp mô hình bớt đoán.',
    gap:
      'Dùng detector/scene graph cho ảnh tự nhiên; không có ontology giải phẫu xương, không xử lý mask gãy nhỏ.',
    use:
      'Tạo evidence graph cho X-quang: vùng xương, đường gãy, bbox/mask, quan hệ vị trí và mô tả giải phẫu.',
  },
  {
    id: 'mmkb',
    kind: 'visual-rag',
    year: '2025',
    venue: 'arXiv',
    name: 'MMKB-RAG: A Multi-Modal Knowledge-Based RAG Framework',
    authors: 'Zihan Ling, Zhiyao Guo, Yixuan Huang, Yi An, Shuai Xiao, Jinsong Lan, Xiaoyong Zhu, Bo Zheng',
    method:
      'MMKB-RAG dùng hệ token RET/SRT/MCT: quyết định retrieve, chấm từng tài liệu liên quan, rồi kiểm tra mâu thuẫn toàn bộ evidence set trước khi generate.',
    result:
      'Báo cáo tăng khoảng 4-8 điểm trên E-VQA/InfoSeek so với các SOTA RAG tùy split.',
    philosophy:
      'Vấn đề của RAG không chỉ là tìm được tài liệu; còn là biết tài liệu nào không cần, tài liệu nào nhiễu và tài liệu nào mâu thuẫn.',
    gap:
      'Knowledge-based VQA bách khoa, không phải ảnh y khoa. Cần fine-tune MLLM và pipeline khá phức tạp.',
    use:
      'Mượn khung decision -> rerank -> consistency cho BoneRAG, nhưng evidence là ảnh X-quang/crop thay vì Wikipedia.',
  },
  {
    id: 'fracatlas',
    kind: 'bone',
    year: '2023',
    venue: 'Scientific Data',
    name: 'FracAtlas: A Dataset for Fracture Classification, Localization and Segmentation',
    authors: 'Abedeen et al.',
    method:
      'Công bố 4.083 ảnh X-quang cơ-xương-khớp, 717 ảnh gãy với 922 fracture instances, có mask COCO, bbox YOLO/PASCAL-VOC và nhãn phân lớp.',
    result:
      'Baseline YOLOv8s-seg đạt mask mAP50 0.589; box mAP50 0.627 trên validation theo báo cáo gốc.',
    philosophy:
      'Muốn hỏi đáp có căn cứ về gãy xương thì cần dữ liệu vừa có ảnh thật vừa có vị trí tổn thương.',
    gap:
      'Dataset là classification/detection/segmentation, chưa có cặp câu hỏi-trả lời tự nhiên.',
    use:
      'Làm knowledge base chính, sinh Bone-VQA bằng template và dùng mask làm chuẩn grounding.',
  },
  {
    id: 'yolov7-fracture',
    kind: 'bone',
    year: '2024',
    venue: 'Biomedical Signal Processing and Control',
    name: 'Detection of Whole Body Bone Fractures Based on Improved YOLOv7',
    authors: 'Không nêu đủ trong ghi chú repo; cần điền khi trích BibTeX',
    method:
      'Cải tiến YOLOv7 bằng attention mechanism và Enhanced IoU loss, phân biệt bốn dạng gãy toàn thân và kiểm tra tổng quát trên FracAtlas.',
    result:
      'Bài báo báo cáo mAP 80.2% trên dữ liệu của họ và mAP 86.2% khi generalize trên FracAtlas.',
    philosophy:
      'Nếu crop vùng gãy tốt hơn, phần Image RAG phía sau sẽ nhận bằng chứng sạch hơn thay vì cả tấm ảnh nhiều nhiễu.',
    gap:
      'Đây là detection, không trả lời câu hỏi; cần kiểm protocol mAP khi so với baseline FracAtlas.',
    use:
      'Dùng detector/segmenter như module ROI proposal cho BoneRAG-ROI.',
  },
  {
    id: 'regionrag',
    kind: 'region',
    year: '2025',
    venue: 'arXiv',
    name: 'RegionRAG: Region-level Retrieval-Augmented Generation for Visual Document Understanding',
    authors: 'Yinglu Li, Zhiying Lu, Zhihang Liu, Yiwei Sun, Chuanbin Liu, Hongtao Xie',
    method:
      'Thay retrieval cấp document bằng retrieval cấp region. Mô hình tìm patch/vùng liên quan, nhóm chúng thành semantic region rồi chỉ đưa vùng cần thiết cho generator.',
    result:
      'Báo cáo tăng trung bình 10.02% R@1, tăng 3.56% QA accuracy và dùng 71.42% visual tokens so với phương pháp trước.',
    philosophy:
      'Thông tin đúng thường nằm ở một phần nhỏ của ảnh/trang; đưa cả ảnh vào generator làm loãng attention và tốn token.',
    gap:
      'Miền visual document, không phải X-quang; cần thay region supervision bằng mask/bbox bệnh lý.',
    use:
      'Đưa retrieval cấp vùng vào BoneRAG: index cả crop fracture, không chỉ ảnh nguyên.',
  },
  {
    id: 'evisrag',
    kind: 'region',
    year: '2025',
    venue: 'arXiv',
    name: 'VisRAG 2.0 / EVisRAG: Evidence-Guided Multi-Image Reasoning',
    authors: 'Yubo Sun, Chunyi Peng, Yukun Yan, Shi Yu, Zhenghao Liu, Chi Chen, Zhiyuan Liu, Maosong Sun',
    method:
      'EVisRAG buộc VLM quan sát từng ảnh retrieved, ghi lại evidence từng ảnh, rồi mới tổng hợp câu trả lời; dùng RS-GRPO để gắn reward vào token perception và reasoning.',
    result:
      'Tác giả báo cáo cải thiện trung bình khoảng 27% trên nhiều benchmark VQA đa ảnh.',
    philosophy:
      'Multi-image RAG thất bại khi mô hình chỉ nhìn lướt nhiều ảnh. Cần bắt nó trích evidence cục bộ trước khi kết luận.',
    gap:
      'Đòi training RL và không chuyên y khoa; chi phí cao hơn baseline học phần nhẹ.',
    use:
      'Thiết kế prompt/generator hai pha cho BoneRAG: observe evidence per image -> answer from evidence.',
  },
  {
    id: 'mkg-rag',
    kind: 'region',
    year: '2026',
    venue: 'SIGIR',
    name: 'mKG-RAG: Leveraging Multimodal Knowledge Graphs in RAG for Knowledge-Intensive VQA',
    authors: 'Xu Yuan, Liangbo Ning, Qingqing Ye, Wenqi Fan, Qing Li',
    method:
      'Xây multimodal knowledge graph từ tài liệu ảnh-văn bản, dùng query-aware multimodal retriever và retrieval hai tầng trên graph.',
    result:
      'Bản paper báo cáo E-VQA All 36.3% và InfoSeek All 40.5%, vượt nhiều baseline RAG/zero-shot trong cùng thiết lập.',
    philosophy:
      'Tri thức không chỉ là danh sách document rời rạc; quan hệ giữa entity, ảnh và text giúp truy xuất có cấu trúc hơn.',
    gap:
      'Tri thức bách khoa, không phải lâm sàng. Graph extraction trên X-quang cần ontology giải phẫu và nhãn vùng đáng tin.',
    use:
      'Xây mini graph cho BoneRAG: image -> body part -> lesion ROI -> diagnosis label -> similar cases.',
  },
  {
    id: 'ref-visual-rag-lqn',
    kind: 'reference',
    year: '2025',
    venue: 'Local PDF',
    name: '[2025] VISUAL-RAG-LQN',
    authors: 'Tổng hợp từ docs/reference-papers',
    method:
      'Paper nền về Visual RAG dùng ảnh làm evidence thay vì chỉ dựa vào text. Trọng tâm là truy xuất ảnh có tri thức thị giác liên quan rồi đưa vào MLLM để trả lời.',
    result:
      'Được dùng trong repo như paper gốc để lập bảng so sánh Visual RAG và xác định vấn đề hard negative, clue image, oracle evidence.',
    philosophy:
      'Có những câu hỏi mà đáp án nằm trong tín hiệu thị giác, nên text retrieval không đủ.',
    gap:
      'Không chuyên y khoa/xương; query và evidence không có cấu trúc giải phẫu hay mask tổn thương.',
    use:
      'Dùng làm nền cho lập luận retrieve ảnh/crop X-quang thay vì chỉ retrieve mô tả văn bản.',
  },
  {
    id: 'ref-visrag-lqn',
    kind: 'reference',
    year: '2025',
    venue: 'Local PDF',
    name: '[2025] VISRAG-LQN',
    authors: 'Shi Yu et al. / bản PDF trong reference-papers',
    method:
      'VisRAG encode trực tiếp toàn bộ tài liệu dưới dạng ảnh, bỏ bước OCR/parsing, rồi dùng VLM retriever và VLM generator.',
    result:
      'Trong bảng survey của repo, VisRAG được ghi nhận cải thiện end-to-end 20-40% so với TextRAG trên tài liệu đa phương thức.',
    philosophy:
      'Không chuyển ảnh sang text quá sớm; giữ ảnh nguyên giúp không mất layout và chi tiết trực quan.',
    gap:
      'Miền tài liệu, chưa xử lý ảnh y khoa hoặc lesion grounding.',
    use:
      'Làm mẫu cho bước image-as-embedding của BoneRAG.',
  },
  {
    id: 'ref-enhanced-mm-rag',
    kind: 'reference',
    year: '2024',
    venue: 'Local PDF',
    name: '[2024] ENHANCED MULTIMODAL RAG-LLM-LQN',
    authors: 'Junxiao Xue et al. / bản PDF trong reference-papers',
    method:
      'Dựng structured scene graph từ ảnh, gồm object, số lượng, vị trí và quan hệ; sau đó retrieve chunk liên quan để prompt LLM.',
    result:
      'Repo dùng paper này để minh họa lợi ích của biểu diễn có cấu trúc khi MLLM yếu ở đếm, vị trí và quan hệ không gian.',
    philosophy:
      'Ảnh phức tạp cần được biến thành facts có cấu trúc trước khi hỏi LLM.',
    gap:
      'Scene graph ảnh tự nhiên không chuyển thẳng sang X-quang; cần ontology giải phẫu và ROI bệnh lý.',
    use:
      'Gợi ý xây evidence graph: body part, lesion ROI, region, diagnosis, similar case.',
  },
  {
    id: 'ref-mmkg-rag-lqn',
    kind: 'reference',
    year: '2025',
    venue: 'Local PDF',
    name: '[2025] MULTIMODAL KNOWLEDGE BASED RAG-LQN',
    authors: 'Zihan Ling et al. / bản PDF trong reference-papers',
    method:
      'MMKB-RAG dùng token system RET/SRT/MCT để quyết định có retrieve không, lọc tài liệu liên quan và kiểm tra mâu thuẫn evidence.',
    result:
      'Theo bảng survey của repo, paper này tăng khoảng 4-8 điểm trên E-VQA/InfoSeek tùy split.',
    philosophy:
      'RAG phải biết khi nào không cần retrieve, tài liệu nào liên quan, và tài liệu nào mâu thuẫn.',
    gap:
      'Knowledge VQA bách khoa, không phải VQA X-quang xương.',
    use:
      'Mượn cấu trúc gate -> rerank -> consistency cho BoneRAG.',
  },
  {
    id: 'ref-visual-rag-benchmarking',
    kind: 'reference',
    year: '2025',
    venue: 'Local PDF',
    name: '[2025] Visual-RAG Benchmarking - LQN',
    authors: 'Bản v2 trong docs/reference-papers',
    method:
      'Bản benchmark cập nhật thêm mô hình/retriever và bộ câu hỏi nhỏ hơn để đánh giá text-to-image Visual RAG.',
    result:
      'Repo ghi chú bản v2 có 374 câu hỏi, 99.017 ảnh, và thêm BGE-VL-large, VLM2Vec-Qwen2-2B.',
    philosophy:
      'Đánh giá RAG không chỉ đo generation; phải đo cả retrieval như NDCG@k, Recall@k, Hit@k.',
    gap:
      'Benchmark sinh vật học, không chuyên xương; chỉ làm chuẩn phương pháp đánh giá.',
    use:
      'Dùng để thiết kế metric cho BoneRAG: retrieval hit@k trước, answer accuracy sau.',
  },
  {
    id: 'ref-motor',
    kind: 'reference',
    year: '2025',
    venue: 'Extra PDF',
    name: '[2025] MOTOR',
    authors: 'Extra reference paper trong docs/reference-papers',
    method:
      'Gợi ý so khớp đa mức/đa vùng thay vì chỉ so embedding toàn ảnh hoặc toàn tài liệu.',
    result:
      'Trong ghi chú dự án, MOTOR được dùng để chỉ ra lọc ảnh mà không nhìn đúng vùng có thể phản tác dụng.',
    philosophy:
      'Relevance phải được đo ở vùng ảnh/chứng cứ cụ thể, không chỉ ở document-level.',
    gap:
      'Cần triển khai và kiểm lại chi tiết paper trước khi trích số vào báo cáo chính.',
    use:
      'Dùng cho hướng ROI matching và region-aware rerank của BoneRAG.',
  },
  {
    id: 'ref-amf',
    kind: 'reference',
    year: '2025',
    venue: 'Extra PDF',
    name: '[2025] AMF-Alignment-Mining-Fusion',
    authors: 'Extra reference paper trong docs/reference-papers',
    method:
      'Alignment, mining và fusion: thay vì giữ/loại evidence cứng, học hoặc tính trọng số mềm để trộn bằng chứng.',
    result:
      'Được repo dùng như ý tưởng cho gated/weighted evidence fusion trong BoneRAG++.',
    philosophy:
      'Không phải evidence nào cũng quan trọng như nhau; nên trộn theo mức tin cậy và mức hữu ích.',
    gap:
      'Chưa chuyên X-quang xương; cần chuyển thành công thức đơn giản để làm ablation.',
    use:
      'Dùng cho weighted generation: gamma_i = softmax(score_i).',
  },
  {
    id: 'ref-utility',
    kind: 'reference',
    year: '2026',
    venue: 'Extra PDF',
    name: '[2026] Utility-Oriented Evidence Selection',
    authors: 'Extra reference paper trong docs/reference-papers',
    method:
      'Chọn evidence theo utility: ảnh/tài liệu nào thật sự giúp câu trả lời đúng hơn, không chỉ giống query hơn.',
    result:
      'Trong báo cáo bản 3 của repo, paper này là nền cho BoneRAG-Utility và phép ablation một biến.',
    philosophy:
      'Similarity là điều kiện cần, utility mới là điều kiện đủ cho evidence tốt.',
    gap:
      'Cần tự hiện thực surrogate utility scorer cho domain X-quang.',
    use:
      'Thay top-k fixed bằng chọn tập evidence tối đa hóa utility, giảm redundant và conflicting context.',
  },
];

export const basicSteps = [
  {
    title: 'Định nghĩa câu hỏi và đáp án',
    plain:
      'Trước khi chọn model, phải biết người dùng sẽ hỏi gì: phát hiện có gãy không, hỏi vùng nào bất thường, hỏi ca nào tương tự, hay hỏi giải thích.',
    input: 'Ảnh, nhãn FracAtlas, nhu cầu người dùng.',
    output: 'Bộ loại câu hỏi và format đáp án.',
    risk: 'Nếu câu hỏi quá rộng, metric sẽ mơ hồ và không biết mô hình sai ở đâu.',
  },
  {
    title: 'Tạo kho ảnh bằng chứng',
    plain:
      'Mỗi ảnh trong dataset phải trở thành một hồ sơ có ảnh gốc, nhãn, vùng tổn thương và metadata để retrieve được.',
    input: 'FracAtlas/MURA/BTRXD, mask, bbox, label.',
    output: 'Image knowledge base.',
    risk: 'Metadata sai hoặc thiếu làm retriever lấy bằng chứng nhìn giống nhưng sai bệnh.',
  },
  {
    title: 'Mã hóa ảnh và câu hỏi',
    plain:
      'Dùng encoder biến ảnh/câu hỏi thành vector. Vector gần nhau nghĩa là có khả năng liên quan về mặt thị giác hoặc ngữ nghĩa.',
    input: 'Ảnh/crop/câu hỏi.',
    output: 'Embedding trong cùng không gian.',
    risk: 'CLIP tổng quát có thể học tư thế chụp hơn là dấu hiệu gãy.',
  },
  {
    title: 'Truy xuất top-k',
    plain:
      'Tìm các ảnh/crop gần query nhất bằng FAISS. Đây là bước gọi lại các ca tương tự.',
    input: 'Embedding query và index ảnh.',
    output: 'Danh sách ứng viên C.',
    risk: 'Top-k cao tăng recall nhưng kéo nhiều hard negative vào context.',
  },
  {
    title: 'Rerank và chọn bằng chứng',
    plain:
      'Chấm lại ứng viên theo độ giống, độ khớp vùng, độ hữu ích và độ nhất quán; chỉ giữ evidence thật sự giúp trả lời.',
    input: 'Top-k candidates.',
    output: 'Evidence set E*.',
    risk: 'Reranker đắt và có thể thiên lệch nếu prompt không ổn định.',
  },
  {
    title: 'Sinh câu trả lời có căn cứ',
    plain:
      'MLLM nhận ảnh người dùng, evidence và vùng nghi ngờ; trả lời theo format có kết luận, bằng chứng, độ tin cậy.',
    input: 'q, Iu, E*, mask/crop.',
    output: 'Answer, grounding, confidence.',
    risk: 'Nếu prompt không ép evidence, mô hình vẫn có thể trả lời theo trí nhớ.',
  },
];

export const pipelineGroups = [
  {
    title: 'Off-line: xây kho tri thức',
    steps: [
      {
        tag: 'D1',
        title: 'Chuẩn hóa dataset',
        body: 'Gộp FracAtlas/MURA/BTRXD, chuẩn hóa ảnh, nhãn, body part, split và loại ảnh lỗi.',
      },
      {
        tag: 'D2',
        title: 'Tạo QA và metadata',
        body: 'Sinh QA template từ nhãn/mask, sau đó kiểm thủ công một phần để tránh câu hỏi máy móc.',
      },
      {
        tag: 'D3',
        title: 'Tạo ROI/crop',
        body: 'Dùng mask/bbox FracAtlas để tạo crop tổn thương; dataset không có mask thì dùng detector hoặc Grad-CAM.',
      },
      {
        tag: 'D4',
        title: 'Encode và index',
        body: 'Lưu embedding ảnh nguyên, crop ROI và text metadata vào FAISS.',
        formula: 'zi = fv(Ii), zij = fv(ROIij)',
      },
    ],
  },
  {
    title: 'On-line: trả lời câu hỏi',
    steps: [
      {
        tag: 'Q1',
        title: 'Phân loại câu hỏi',
        body: 'Xác định câu hỏi global, ROI, so sánh hay giải thích; quyết định có cần retrieve không.',
        formula: 'delta(q, Iu) in {0, 1}',
      },
      {
        tag: 'Q2',
        title: 'Trộn query đa phương thức',
        body: 'Kết hợp embedding câu hỏi, ảnh người dùng và vùng nghi ngờ theo trọng số.',
        formula: 'eq = alpha etxt + beta eimg + eta eroi',
      },
      {
        tag: 'Q3',
        title: 'Retrieve đa mức',
        body: 'Tìm ứng viên từ index ảnh nguyên, ROI và text metadata; gộp và khử trùng lặp.',
        formula: 'C = Rimg union Rroi union Rtxt',
      },
      {
        tag: 'Q4',
        title: 'Utility rerank',
        body: 'Chấm lại ứng viên bằng similarity, khớp vùng, utility và consistency.',
        formula: 'si = l1 sim + l2 ROI + l3 U + l4 Cons',
      },
      {
        tag: 'Q5',
        title: 'Generate có grounding',
        body: 'MLLM quan sát từng evidence, nêu vùng căn cứ, rồi trả lời kèm độ tin cậy.',
        formula: 'a, Z, c = G(q, Iu, E*)',
      },
    ],
  },
];

export const improvementIdeas = [
  {
    level: 'Dễ làm',
    title: 'Bone-VQA bằng template từ FracAtlas',
    why: 'Hiện chưa có benchmark VQA chuyên xương. Tạo bộ QA riêng là đóng góp nền tảng và giúp đo end-to-end.',
    how: 'Sinh câu hỏi theo nhãn fracture/non-fracture, vị trí bbox, body part; kiểm thủ công 100-300 mẫu đại diện.',
    metric: 'Answer accuracy, macro-F1, split theo body part và fracture/non-fracture.',
  },
  {
    level: 'Dễ làm',
    title: 'RAG baseline vs no-RAG',
    why: 'Cần chứng minh Image RAG thật sự giúp hơn mô hình trả lời chay.',
    how: 'So LLaVA-Med/Qwen2.5-VL zero-shot với cùng model nhưng thêm top-k ảnh retrieved.',
    metric: 'Accuracy, hallucination rate, evidence hit@k.',
  },
  {
    level: 'Trung bình',
    title: 'ROI retrieval',
    why: 'Dấu gãy thường nhỏ. Retrieval ảnh nguyên dễ bị body part/góc chụp lấn át.',
    how: 'Index crop từ mask/bbox FracAtlas; query dùng crop vùng nghi ngờ của ảnh người dùng.',
    metric: 'Recall@k evidence, IoU/Dice grounding, accuracy câu hỏi vùng tổn thương.',
  },
  {
    level: 'Trung bình',
    title: 'Utility-oriented evidence selection',
    why: 'Ảnh giống không đồng nghĩa ảnh hữu ích. Cần chọn ảnh làm tăng khả năng trả lời đúng.',
    how: 'Rerank top-k bằng score hữu ích: ảnh đó có giúp trả lời câu hỏi cụ thể không, có mâu thuẫn không.',
    metric: 'Accuracy sau generation, nDCG@k, số evidence/token cần dùng.',
  },
  {
    level: 'Khó hơn',
    title: 'Hard-negative contrastive fine-tuning',
    why: 'Ca dễ nhầm là ảnh cùng vùng cơ thể nhưng khác bệnh. Retriever cần học phân biệt lâm sàng.',
    how: 'Tạo triplet/query-positive-hard negative; fine-tune BiomedCLIP/BGE-VL bằng InfoNCE.',
    metric: 'Recall@1/5 trên split hard-negative, improvement so frozen encoder.',
  },
  {
    level: 'Khó hơn',
    title: 'Evidence graph cho xương',
    why: 'Một chẩn đoán tốt cần biết quan hệ giữa vùng xương, đường gãy, khớp và vị trí giải phẫu.',
    how: 'Tạo graph image -> body part -> ROI -> label -> similar case; retrieve node/edge thay vì document phẳng.',
    metric: 'QA nhiều bước, consistency, khả năng giải thích.',
  },
];

export const comparisonRows = [
  {
    axis: 'Nguồn tri thức',
    baseline: 'VLM trả lời từ ảnh hiện tại hoặc trí nhớ model.',
    proposed: 'Image KB gồm ảnh X-quang, ROI, mask, metadata và ca tương tự.',
    papers: 'VISUAL-RAG, VisRAG, FracAtlas',
  },
  {
    axis: 'Đơn vị retrieve',
    baseline: 'Cả ảnh hoặc text description.',
    proposed: 'Ảnh nguyên + crop vùng tổn thương + metadata text.',
    papers: 'RegionRAG, Enhanced MM RAG-LLM',
  },
  {
    axis: 'Chọn evidence',
    baseline: 'Top-k cosine similarity.',
    proposed: 'Utility rerank theo similarity, ROI match, usefulness, consistency.',
    papers: 'MMKB-RAG, EVisRAG, Region-R1',
  },
  {
    axis: 'Factuality',
    baseline: 'Prompt trả lời trực tiếp, dễ overclaim.',
    proposed: 'Gate retrieve-or-not, preference/factual tuning, confidence threshold.',
    papers: 'RULE, MMed-RAG, FactMM-RAG',
  },
  {
    axis: 'Giải thích',
    baseline: 'Câu trả lời text không chỉ rõ bằng chứng.',
    proposed: 'Answer + evidence images + highlighted ROI + confidence.',
    papers: 'FracAtlas, EVisRAG, medical VQA faithfulness work',
  },
  {
    axis: 'Đánh giá',
    baseline: 'Chỉ đo accuracy câu trả lời.',
    proposed: 'Tách retrieval, grounding, answer, factuality và hallucination.',
    papers: 'VQA-RAD, RULE, RAG-X',
  },
];

export const roadmap = [
  {
    time: 'Milestone 1',
    title: 'Baseline chạy được',
    goal: 'Có demo end-to-end đơn giản để trả lời câu hỏi trên FracAtlas.',
    tasks: [
      'Tạo 300-1000 QA template từ FracAtlas.',
      'Encode ảnh bằng CLIP/BiomedCLIP.',
      'FAISS top-k retrieval.',
      'Prompt MLLM trả lời với evidence.',
    ],
  },
  {
    time: 'Milestone 2',
    title: 'Đo và so sánh nghiêm túc',
    goal: 'Biết sai ở retrieval hay generation.',
    tasks: [
      'Tạo split train/val/test không rò ảnh.',
      'Đo Recall@k, Hit@k, answer accuracy.',
      'So no-RAG, top-k RAG, rerank RAG.',
      'Lưu ví dụ thành công/thất bại để phân tích.',
    ],
  },
  {
    time: 'Milestone 3',
    title: 'ROI-BoneRAG',
    goal: 'Làm mô hình nhìn đúng vùng gãy.',
    tasks: [
      'Index crop từ mask/bbox.',
      'Train hoặc dùng detector để đề xuất vùng nghi ngờ.',
      'So ảnh nguyên vs crop vs ảnh nguyên + crop.',
      'Hiển thị grounding trong giao diện.',
    ],
  },
  {
    time: 'Milestone 4',
    title: 'Retriever chuyên xương',
    goal: 'Giảm nhầm hard negative cùng body part.',
    tasks: [
      'Tạo hard negative theo body part/góc chụp.',
      'Fine-tune contrastive retriever.',
      'Thử utility rerank và consistency filter.',
      'Viết ablation table cho báo cáo.',
    ],
  },
];

export const sources = [
  {
    title: 'RULE - ACL Anthology',
    note: 'Medical multimodal RAG, factuality, EMNLP 2024.',
    url: 'https://aclanthology.org/2024.emnlp-main.62/',
  },
  {
    title: 'MMed-RAG',
    note: 'Domain-aware retrieval, adaptive context, preference tuning.',
    url: 'https://arxiv.org/abs/2410.13085',
  },
  {
    title: 'FactMM-RAG',
    note: 'Fact-aware retriever for radiology report generation.',
    url: 'https://github.com/cxcscmu/FactMM-RAG',
  },
  {
    title: 'VisRAG',
    note: 'Image-as-embedding, parsing-free visual RAG.',
    url: 'https://github.com/openbmb/visrag',
  },
  {
    title: 'RegionRAG',
    note: 'Region-level retrieval for visual document understanding.',
    url: 'https://huggingface.co/papers/2510.27261',
  },
  {
    title: 'mKG-RAG',
    note: 'Multimodal knowledge graph for knowledge-intensive VQA.',
    url: 'https://www.alphaxiv.org/abs/2508.05318v2',
  },
  {
    title: 'FracAtlas',
    note: 'Dataset xương chính: ảnh, bbox, mask, nhãn gãy.',
    url: 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10404222/',
  },
  {
    title: 'VQA-RAD',
    note: 'Dataset VQA radiology nền tảng.',
    url: 'https://pmc.ncbi.nlm.nih.gov/articles/PMC6244189/',
  },
];
