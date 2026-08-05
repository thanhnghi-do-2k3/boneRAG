# Dockerfile for BoneRAG Backend API Server (Hugging Face Spaces)
FROM python:3.12-slim

# Install system dependencies for OpenCV / Torch
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install core PyTorch & RAG dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install PyTorch CPU / MPS / CUDA compatible packages
RUN pip install --no-cache-dir \
    torch \
    torchvision \
    transformers \
    open_clip_torch \
    faiss-cpu \
    pillow \
    numpy \
    huggingface_hub

# Copy full repository
COPY . /app/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV BONERAG_RECORD_LIMIT=4085

# Expose Hugging Face Space default port 7860
EXPOSE 7860

# Run BoneRAG Demo Server on 0.0.0.0:7860
CMD ["python3", "demo-app/server.py", "--host", "0.0.0.0", "--port", "7860"]
