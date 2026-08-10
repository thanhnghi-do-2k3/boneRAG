# BoneRAG Image RAG Benchmark v1

## Purpose

Measure whether retrieval and grounding improve fracture screening on the same
real FracAtlas images. This protocol is an internal controlled comparison; its
numbers must not be presented as a direct reproduction of RULE, MMed-RAG, or
FactMM-RAG because those papers use different datasets and tasks.

## Dataset and split

- Dataset: FracAtlas, mounted in Colab under `BONERAG_DATASET_IMAGES_ROOT`.
- Cases: 32 real images, balanced to 16 `Fractured` and 16 `Non_fractured`.
- Selection: sorted image paths and evenly spaced sampling, so the same dataset
  produces the same case set on every run.
- Query leakage: all selected test image IDs are excluded from retrieval before
  scoring, not only the image currently being asked about. The remaining
  FracAtlas records form the retrieval corpus for this run.
- Fingerprint: every run reports a SHA-256 fingerprint of the selected paths and
  labels.

## Systems

Every system uses the same encoder, FAISS index, corpus, top-k, generator, and
case order. Only the retrieval condition changes:

1. `Text-only RAG`: text query, no image vector.
2. `Image-only RAG`: image vector weight 1.0.
3. `Image + Text RAG`: image weight 0.6 and text weight 0.4.
4. `BoneRAG (ours)`: image/text blend plus anatomical-pathology reranking and
   evidence gate.

## Metrics

- `retrieval_top1_label_accuracy`: top retrieved evidence has the true folder
  label.
- `evidence_label_precision_at_4`: fraction of top-4 evidence with the true
  folder label.
- `answer_label_accuracy`: generated answer contains the correct fracture or
  normal label.
- `latency_ms`: end-to-end per-case latency, including retrieval and generation.
- `generator_fallback_rate`: fraction of cases where a requested neural
  generator could not load and fell back to the evidence synthesizer; this must
  be `0.0` before reporting a neural-model result.

The web result shows per-system aggregates and every case. The backend appends
the complete run to `benchmark_runs.jsonl`; the UI can export the current run
as JSON.

On Colab, `colab/02_BoneRAG_GPU_Server_Deploy.ipynb` sets
`BONERAG_RUNTIME_DATA_DIR` to `Google Drive/BoneRAG_Data/runtime`. Therefore
these files survive a server restart or a new Colab runtime:

- `sessions.jsonl`: chat/session logs and feedback
- `benchmark_runs.jsonl`: completed benchmark runs
- `bonerag_server.log`: backend startup/runtime log
- `indexes/`: regenerated FAISS and metadata artifacts
- `model_cache/`: Hugging Face and Torch model cache

## Reproduction

1. Run the FracAtlas indexing notebook after mounting the dataset. The index
   notebook must be rerun after any change to label generation.
2. Start the Colab server with the same encoder/generator used for the run.
3. Open the Evaluation tab and run the matrix.
4. Record the dataset fingerprint, encoder, generator, case count, and commit
   hash with any reported result.

The same run can be started without the web UI:

```bash
python3 -m bonerag.evaluation.run_benchmark \
  --encoder biomedclip --generator synth --cases 32
```

For a local environment, install
`bonerag/evaluation/requirements-benchmark.txt` first. The Colab notebook has
the equivalent install cell. The benchmark uses strict encoder/generator
loading: missing packages or model weights stop the run rather than silently
changing the model being measured.

Use `--generator qwen05`, `qwen15`, or `smol` to compare a local foundation
model. `--generator all` runs all four generator choices sequentially. If an
index, metadata file, or real dataset is missing, the command fails instead of
silently switching to the toy corpus.

## What it can support

This benchmark supports claims such as: “BoneRAG improves top-1 label
retrieval over our text-only and un-reranked multimodal baselines on the fixed
FracAtlas protocol.” It does not support a claim that BoneRAG is superior to a
published medical VQA system unless that system is run on this exact protocol
or both methods are evaluated on a shared public benchmark.
