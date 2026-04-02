#!/bin/bash
set -e

COMFY="/workspace/ComfyUI"

echo "[Start] OpenClaw ComfyUI Worker (self-contained)"

# Models are baked into the image — no volume needed.
# LoRAs from S3 are downloaded per-job by the handler's download_lora action.

# Start handler
echo "[Start] Launching handler..."
exec python -u /workspace/handler.py
