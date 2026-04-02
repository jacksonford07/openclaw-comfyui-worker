#!/bin/bash
set -e

VOLUME="/runpod-volume"
COMFY="/workspace/ComfyUI"

echo "[Start] OpenClaw ComfyUI Worker"

# Symlink models from volume
if [ -d "$VOLUME/ComfyUI/models" ] && [ ! -L "$COMFY/models" ]; then
    echo "[Start] Symlinking models from volume..."
    rm -rf "$COMFY/models"
    ln -s "$VOLUME/ComfyUI/models" "$COMFY/models"
fi

# Symlink custom nodes from volume
if [ -d "$VOLUME/ComfyUI/custom_nodes" ] && [ ! -L "$COMFY/custom_nodes" ]; then
    echo "[Start] Symlinking custom nodes from volume..."
    rm -rf "$COMFY/custom_nodes"
    ln -s "$VOLUME/ComfyUI/custom_nodes" "$COMFY/custom_nodes"
fi

# Install known problematic packages before custom node deps
echo "[Start] Installing known dependencies..."
pip install -q -U kernels 2>/dev/null || true

# Install custom node dependencies
if [ -d "$COMFY/custom_nodes" ]; then
    echo "[Start] Installing custom node dependencies..."
    for req in "$COMFY/custom_nodes"/*/requirements.txt; do
        [ -f "$req" ] || continue
        node_name=$(basename "$(dirname "$req")")
        echo "[Start] Installing deps for $node_name"
        pip install -q -r "$req" 2>/dev/null || true
    done
    for script in "$COMFY/custom_nodes"/*/install.py; do
        [ -f "$script" ] || continue
        node_name=$(basename "$(dirname "$script")")
        echo "[Start] Running install.py for $node_name"
        (cd "$(dirname "$script")" && python3 "$script" 2>/dev/null) || true
    done
    echo "[Start] Custom node deps installed"
fi

# Start handler
echo "[Start] Launching handler..."
exec python -u /workspace/handler.py
