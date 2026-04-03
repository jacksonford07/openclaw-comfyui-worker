#!/bin/bash
set -e

VOLUME="/runpod-volume"
COMFY="/workspace/ComfyUI"

echo "[Start] OpenClaw ComfyUI Worker"

# Symlink models from volume
if [ -d "$VOLUME/ComfyUI/models" ] && [ ! -L "$COMFY/models" ]; then
    rm -rf "$COMFY/models"
    ln -s "$VOLUME/ComfyUI/models" "$COMFY/models"
fi

# Symlink custom nodes from volume
if [ -d "$VOLUME/ComfyUI/custom_nodes" ] && [ ! -L "$COMFY/custom_nodes" ]; then
    rm -rf "$COMFY/custom_nodes"
    ln -s "$VOLUME/ComfyUI/custom_nodes" "$COMFY/custom_nodes"
fi

echo "[Start] Launching handler..."
exec python -u /workspace/handler.py
