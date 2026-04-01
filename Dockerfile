# OpenClaw ComfyUI Worker
# Base: RunPod PyTorch with CUDA 12.4
# Models + custom nodes loaded from network volume at runtime
# Only ComfyUI core + handler baked into the image

FROM runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04

# Cache buster — change this to force a full rebuild
ARG CACHE_BUST=v0.2.0

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

# System deps
RUN echo "Build: ${CACHE_BUST}" && apt-get update && apt-get install -y --no-install-recommends \
    git wget curl ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Clone ComfyUI
RUN git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git

# Install ComfyUI requirements
RUN pip install --no-cache-dir -r /workspace/ComfyUI/requirements.txt

# Install RunPod SDK
RUN pip install --no-cache-dir runpod

# Install SageAttention for optimized inference
RUN pip install --no-cache-dir sageattention

# Create required directories
RUN mkdir -p /workspace/ComfyUI/output \
    /workspace/ComfyUI/input \
    /workspace/ComfyUI/models/loras

# Copy handler
COPY handler.py /workspace/handler.py

# Copy install scripts (for reference / manual setup on volume)
COPY scripts/ /workspace/scripts/

CMD ["python", "-u", "/workspace/handler.py"]
