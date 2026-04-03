# OpenClaw ComfyUI Worker
# Models + custom nodes loaded from network volume at /runpod-volume
FROM runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget curl ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Clone ComfyUI
RUN git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git

# Install ComfyUI requirements
RUN pip install --no-cache-dir -r /workspace/ComfyUI/requirements.txt

# Install RunPod SDK + extras
RUN pip install --no-cache-dir runpod sageattention

# Create required directories
RUN mkdir -p /workspace/ComfyUI/output \
    /workspace/ComfyUI/input \
    /workspace/ComfyUI/models/loras

# Copy handler
COPY handler.py /workspace/handler.py
COPY start.sh /workspace/start.sh
RUN chmod +x /workspace/start.sh

CMD ["/workspace/start.sh"]
