#!/bin/bash
set -e

VOLUME="/runpod-volume"
COMFY="/workspace/ComfyUI"

echo "[Start] OpenClaw ComfyUI Worker"

# Symlink models from volume (if volume exists)
if [ -d "$VOLUME/ComfyUI/models" ] && [ ! -L "$COMFY/models" ]; then
    echo "[Start] Symlinking models from volume..."
    rm -rf "$COMFY/models"
    ln -s "$VOLUME/ComfyUI/models" "$COMFY/models"
fi

# Symlink custom nodes from volume (if volume exists)
if [ -d "$VOLUME/ComfyUI/custom_nodes" ] && [ ! -L "$COMFY/custom_nodes" ]; then
    echo "[Start] Symlinking custom nodes from volume..."
    rm -rf "$COMFY/custom_nodes"
    ln -s "$VOLUME/ComfyUI/custom_nodes" "$COMFY/custom_nodes"
fi

# No dep installs — everything is baked into the image or on the volume.
# Go straight to handler.
echo "[Start] Launching handler..."
exec python -u /workspace/handler.py
