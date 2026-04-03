# OpenClaw ComfyUI Worker — Self-Contained Image
# All models, custom nodes, and deps baked in.
# LoRAs downloaded from S3 at runtime (small, fast).
# Works in ANY RunPod datacenter — no network volume required.

FROM runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04

ARG CACHE_BUST=v1.0.0
ARG HF_TOKEN
ARG CIVITAI_TOKEN

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

# System deps
RUN echo "Build: ${CACHE_BUST}" && apt-get update && apt-get install -y --no-install-recommends \
    git wget curl ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Clone ComfyUI
RUN git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git

# Install ComfyUI requirements + core packages
RUN pip install --no-cache-dir -r /workspace/ComfyUI/requirements.txt \
    && pip install --no-cache-dir "runpod~=1.7.9" sageattention kernels \
    && pip install --no-cache-dir -U "huggingface_hub[cli]"

# Create model directories
RUN mkdir -p /workspace/ComfyUI/output \
    /workspace/ComfyUI/input \
    /workspace/ComfyUI/models/{checkpoints,clip,clip_vision,vae,loras,unet,upscale_models,controlnet,diffusion_models,text_encoders,sams,ultralytics/bbox,SEEDVR2,onnx,LLM}

# ============================================================
# CUSTOM NODES — clone and install deps at build time
# ============================================================
WORKDIR /workspace/ComfyUI/custom_nodes

# Problematic nodes (force-reinstall)
RUN git clone --depth 1 https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler.git \
    && git clone --depth 1 https://github.com/1038lab/ComfyUI-QwenVL.git \
    && git clone --depth 1 https://github.com/IuvenisSapiens/ComfyUI_Qwen3-VL-Instruct.git \
    && git clone --depth 1 https://github.com/MaraScott/ComfyUI_MaraScott_Nodes.git

RUN for d in ComfyUI-SeedVR2_VideoUpscaler ComfyUI-QwenVL ComfyUI_Qwen3-VL-Instruct ComfyUI_MaraScott_Nodes; do \
      [ -f "$d/requirements.txt" ] && pip install --no-cache-dir --force-reinstall -r "$d/requirements.txt" || true; \
      [ -f "$d/install.py" ] && (cd "$d" && python3 install.py) || true; \
    done

# Regular nodes
RUN git clone --depth 1 https://github.com/Lightricks/ComfyUI-LTXVideo.git \
    && git clone --depth 1 https://github.com/kijai/ComfyUI-segment-anything-2.git \
    && git clone --depth 1 https://github.com/omar92/ComfyUI-QualityOfLifeSuit_Omar92.git \
    && git clone --depth 1 https://github.com/MixLabPro/comfyui-mixlab-nodes.git \
    && git clone --depth 1 https://github.com/BadCafeCode/masquerade-nodes-comfyui.git \
    && git clone --depth 1 https://github.com/lquesada/ComfyUI-Inpaint-CropAndStitch.git \
    && git clone --depth 1 https://github.com/WASasquatch/was-node-suite-comfyui.git \
    && git clone --depth 1 https://github.com/1038lab/ComfyUI-RMBG.git \
    && git clone --depth 1 https://github.com/rgthree/rgthree-comfy.git \
    && git clone --depth 1 https://github.com/kijai/ComfyUI-KJNodes.git \
    && git clone --depth 1 https://github.com/chflame163/ComfyUI_LayerStyle.git \
    && git clone --depth 1 https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes.git \
    && git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Impact-Pack.git \
    && git clone --depth 1 https://github.com/yolain/ComfyUI-Easy-Use.git \
    && git clone --depth 1 https://github.com/pythongosssss/ComfyUI-Custom-Scripts.git \
    && git clone --depth 1 https://github.com/TinyTerra/ComfyUI_tinyterraNodes.git \
    && git clone --depth 1 https://github.com/giriss/comfy-image-saver.git \
    && git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Impact-Subpack.git \
    && git clone --depth 1 https://github.com/ClownsharkBatwing/RES4LYF.git \
    && git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Manager.git

# Install all regular node deps
RUN for d in */; do \
      [ -f "${d}requirements.txt" ] && pip install --no-cache-dir -r "${d}requirements.txt" 2>/dev/null || true; \
      [ -f "${d}install.py" ] && (cd "$d" && python3 install.py 2>/dev/null) || true; \
    done

# ============================================================
# MODELS — download at build time
# ============================================================
WORKDIR /workspace/ComfyUI/models

# All models in a single layer to minimize intermediate disk usage
RUN curl -L -o diffusion_models/z_image_turbo_bf16.safetensors \
      "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_bf16.safetensors" && \
    curl -L -o text_encoders/qwen_3_4b.safetensors \
      "https://huggingface.co/Comfy-Org/flux2-klein-4B/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors" && \
    curl -L -o clip_vision/clip_vision_h.safetensors \
      "https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors" && \
    curl -L -o vae/ae.safetensors \
      "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/vae/ae.safetensors" && \
    curl -L -o vae/ema_vae_fp16.safetensors \
      "https://huggingface.co/stabilityai/sd-vae-ft-ema/resolve/main/diffusion_pytorch_model.safetensors" && \
    curl -L -o loras/bfs_head_v1_flux-klein_9b_step3500_rank128.safetensors \
      "https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/resolve/main/bfs_head_v1_flux-klein_9b_step3500_rank128.safetensors" && \
    curl -L -o sams/sam_vit_h_4b8939.pth \
      "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth" && \
    curl -L -o ultralytics/bbox/nipples_yolov8s.pt \
      "https://huggingface.co/ashllay/YOLO_Models/resolve/e07b01219ff1807e1885015f439d788b038f49bd/bbox/nipples_yolov8s.pt" && \
    curl -L -o SEEDVR2/seedvr2_ema_3b_fp16.safetensors \
      "https://huggingface.co/numz/SeedVR2_comfyUI/resolve/main/seedvr2_ema_3b_fp16.safetensors"

# Note: SDXL checkpoints (CyberRealisticPony, bigLust, lustifySDXL) removed —
# zimg workflows use z_image_turbo, not SDXL. Add back if needed for other workflows.

# ============================================================
# HANDLER + START SCRIPT
# ============================================================
WORKDIR /workspace

# Remove base image's start.sh and test_input.json that interfere with serverless
RUN rm -f /start.sh /test_input.json

COPY handler.py /workspace/handler.py
COPY start.sh /workspace/start.sh
RUN chmod +x /workspace/start.sh

COPY scripts/ /workspace/scripts/

# Override both ENTRYPOINT and CMD to bypass nvidia_entrypoint.sh
ENTRYPOINT []
CMD ["python", "-u", "/workspace/handler.py"]
