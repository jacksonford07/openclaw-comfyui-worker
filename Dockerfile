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
    && pip install --no-cache-dir "runpod>=1.7.0,<2.0.0" sageattention kernels \
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

# Z-Image Turbo (main diffusion model ~12GB)
RUN curl -L -o diffusion_models/z_image_turbo_bf16.safetensors \
    "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_bf16.safetensors"

# Qwen 3 4B text encoder
RUN curl -L -o text_encoders/qwen_3_4b.safetensors \
    "https://huggingface.co/Comfy-Org/flux2-klein-4B/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors"

# CLIP Vision
RUN curl -L -o clip_vision/clip_vision_h.safetensors \
    "https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors"

# Z-Image VAE
RUN curl -L -o vae/ae.safetensors \
    "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/vae/ae.safetensors"

# SD VAE
RUN curl -L -o vae/ema_vae_fp16.safetensors \
    "https://huggingface.co/stabilityai/sd-vae-ft-ema/resolve/main/diffusion_pytorch_model.safetensors"

# BFS Face Swap LoRA (default — always included)
RUN curl -L -o loras/bfs_head_v1_flux-klein_9b_step3500_rank128.safetensors \
    "https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/resolve/main/bfs_head_v1_flux-klein_9b_step3500_rank128.safetensors"

# SAM ViT-H for Impact Pack
RUN curl -L -o sams/sam_vit_h_4b8939.pth \
    https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth

# Nipples YOLO detection model
RUN curl -L -o ultralytics/bbox/nipples_yolov8s.pt \
    https://huggingface.co/ashllay/YOLO_Models/resolve/e07b01219ff1807e1885015f439d788b038f49bd/bbox/nipples_yolov8s.pt

# SeedVR2 upscaler
RUN curl -L -o SEEDVR2/seedvr2_ema_3b_fp16.safetensors \
    https://huggingface.co/numz/SeedVR2_comfyUI/resolve/main/seedvr2_ema_3b_fp16.safetensors

# CyberRealisticPony checkpoint
RUN curl -L -o checkpoints/CyberRealisticPony_V14.1_FP16.safetensors \
    https://huggingface.co/cyberdelia/CyberRealisticPony/resolve/main/CyberRealisticPony_V14.1_FP16.safetensors

# CivitAI models (optional — requires token)
RUN if [ -n "${CIVITAI_TOKEN}" ]; then \
      curl -L -H "Authorization: Bearer ${CIVITAI_TOKEN}" -o checkpoints/bigLust_v16.safetensors \
        https://civitai.com/api/download/models/1081768 && \
      curl -L -H "Authorization: Bearer ${CIVITAI_TOKEN}" -o checkpoints/lustifySDXLNSFW_endgame.safetensors \
        https://civitai.com/api/download/models/1094291; \
    else echo "Skipping CivitAI models (no token)"; fi

# ============================================================
# HANDLER + START SCRIPT
# ============================================================
WORKDIR /workspace

COPY handler.py /workspace/handler.py
COPY start.sh /workspace/start.sh
RUN chmod +x /workspace/start.sh

COPY scripts/ /workspace/scripts/

CMD ["python", "-u", "/workspace/handler.py"]
