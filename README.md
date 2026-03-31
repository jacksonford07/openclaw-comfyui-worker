# OpenClaw ComfyUI Worker

RunPod serverless worker for AI image/video generation using ComfyUI with zimg and wan checkpoints.

## Architecture

- **Docker image**: ComfyUI core + handler (lightweight, ~5GB)
- **Network volume**: Models, custom nodes, LoRAs (loaded at runtime)
- **Handler**: Receives workflow JSON → runs ComfyUI → returns base64 outputs

## Setup

### 1. Link repo to RunPod
Connect this GitHub repo to RunPod serverless. It auto-builds the Docker image on push.

### 2. Create network volumes
Create two volumes in the same region:
- `openclaw-image` (250GB) — for zimg image models
- `openclaw-video` (250GB) — for wan video models

### 3. Install models on volumes
Start a GPU pod with each volume attached, then run:
```bash
# For image volume
python /workspace/scripts/install_image_models.py

# For video volume
python /workspace/scripts/install_video_models.py
```

### 4. Create serverless endpoints
Create two endpoints pointing to this worker's Docker build:
- `openclaw-image` — attach image volume, 24-48GB GPU
- `openclaw-video` — attach video volume, 48-80GB GPU

## Usage

Submit workflows via RunPod API:
```bash
curl -X POST "https://api.runpod.ai/v2/{ENDPOINT_ID}/run" \
  -H "Authorization: Bearer {RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"input": {"workflow": {COMFYUI_WORKFLOW_JSON}}}'
```

### LoRA Transfer
Upload a LoRA file from S3 to the network volume:
```bash
curl -X POST "https://api.runpod.ai/v2/{ENDPOINT_ID}/run" \
  -H "Authorization: Bearer {RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"input": {"action": "download_lora", "lora_url": "https://s3-presigned-url", "dest_filename": "character-id.safetensors"}}'
```
