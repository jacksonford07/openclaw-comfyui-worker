# OpenClaw ComfyUI Worker

[![Deploy | RunPod Serverless](https://img.shields.io/badge/RunPod-Deploy-purple?logo=runpod)](https://www.runpod.io/console/hub/jacksonford07-openclaw-comfyui-worker)

RunPod serverless worker for AI image/video generation using ComfyUI with zimg and wan checkpoints.

## Architecture

- **Docker image**: ComfyUI core + handler (lightweight, ~5GB)
- **Network volume**: Models, custom nodes, LoRAs (loaded at runtime)
- **Handler**: Receives workflow JSON, runs ComfyUI, returns base64 outputs

## Setup

### 1. Deploy from RunPod Hub
Click the deploy badge above, or add this repo on RunPod Serverless.

### 2. Create network volumes
Create two volumes in the same region:
- `openclaw-image` (250GB) — for zimg image models
- `openclaw-video` (250GB) — for wan video models

### 3. Install models on volumes
Start a GPU pod with each volume attached, set your tokens, then run:
```bash
export HF_TOKEN=your_huggingface_token
export CIVITAI_TOKEN=your_civitai_token

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

### Submit a workflow
```bash
curl -X POST "https://api.runpod.ai/v2/{ENDPOINT_ID}/run" \
  -H "Authorization: Bearer {RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"input": {"workflow": {COMFYUI_WORKFLOW_JSON}}}'
```

### Check job status
```bash
curl "https://api.runpod.ai/v2/{ENDPOINT_ID}/status/{JOB_ID}" \
  -H "Authorization: Bearer {RUNPOD_API_KEY}"
```

### Upload input images
Include images in the input for img2img/video workflows:
```json
{
  "input": {
    "workflow": {...},
    "images": [
      {"name": "input.png", "image": "https://url-to-image.jpg"}
    ]
  }
}
```

### Transfer LoRA to volume
Upload a LoRA file from any URL to the network volume:
```bash
curl -X POST "https://api.runpod.ai/v2/{ENDPOINT_ID}/run" \
  -H "Authorization: Bearer {RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"input": {"action": "download_lora", "lora_url": "https://url-to-lora.safetensors", "dest_filename": "character-id.safetensors"}}'
```

## Supported Workflows

| Workflow | Type | Description |
|----------|------|-------------|
| zimg-txt2img | Image | Text-to-image with LoRA face consistency |
| zimg-img2img | Image | Edit/refine existing image |
| wan-i2v | Video | Image-to-video generation |
| wan-animate | Video | Character animation from reference motion |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `HF_TOKEN` | For setup | HuggingFace token (model downloads) |
| `CIVITAI_TOKEN` | For setup | CivitAI token (model downloads) |
| `COMFY_TIMEOUT` | No | Workflow timeout in seconds (default: 300) |
