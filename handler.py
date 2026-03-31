"""
OpenClaw ComfyUI Worker — RunPod Serverless Handler

Receives ComfyUI workflow JSON, executes it, returns output images/videos.
Models + custom nodes loaded from network volume at /runpod-volume.

Supports:
- Standard workflow execution (image + video generation)
- LoRA download utility action (transfers LoRA from S3 to volume)
"""

import os
import sys
import json
import time
import uuid
import urllib.request
import runpod

# ComfyUI paths
COMFY_DIR = "/workspace/ComfyUI"
VOLUME_DIR = "/runpod-volume"
OUTPUT_DIR = f"{COMFY_DIR}/output"

sys.path.insert(0, COMFY_DIR)


def wait_for_comfyui(timeout=120):
    """Wait for ComfyUI server to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen("http://127.0.0.1:8188/system_stats")
            return True
        except Exception:
            time.sleep(2)
    return False


def start_comfyui():
    """Start ComfyUI server in the background."""
    import subprocess

    # Symlink volume models into ComfyUI if not already done
    comfy_models = f"{COMFY_DIR}/models"
    volume_models = f"{VOLUME_DIR}/ComfyUI/models"
    if os.path.exists(volume_models) and not os.path.islink(comfy_models):
        if os.path.exists(comfy_models):
            os.rename(comfy_models, f"{comfy_models}_bak")
        os.symlink(volume_models, comfy_models)

    # Symlink custom nodes from volume
    comfy_nodes = f"{COMFY_DIR}/custom_nodes"
    volume_nodes = f"{VOLUME_DIR}/ComfyUI/custom_nodes"
    if os.path.exists(volume_nodes) and not os.path.islink(comfy_nodes):
        if os.path.exists(comfy_nodes):
            os.rename(comfy_nodes, f"{comfy_nodes}_bak")
        os.symlink(volume_nodes, comfy_nodes)

    # Start ComfyUI
    subprocess.Popen(
        [sys.executable, "main.py", "--listen", "127.0.0.1", "--port", "8188", "--disable-auto-launch"],
        cwd=COMFY_DIR,
        stdout=open("/workspace/comfy.log", "w"),
        stderr=open("/workspace/comfy_err.log", "w"),
    )

    if not wait_for_comfyui():
        raise RuntimeError("ComfyUI failed to start within 120s")
    print("[Worker] ComfyUI server ready")


def queue_workflow(workflow):
    """Submit a workflow to ComfyUI's /prompt endpoint and wait for completion."""
    prompt_id = str(uuid.uuid4())
    payload = json.dumps({"prompt": workflow, "client_id": prompt_id}).encode()

    req = urllib.request.Request(
        "http://127.0.0.1:8188/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    actual_prompt_id = result.get("prompt_id", prompt_id)

    # Poll for completion
    timeout = int(os.environ.get("COMFY_TIMEOUT", "300"))
    start = time.time()
    while time.time() - start < timeout:
        try:
            history_req = urllib.request.Request(f"http://127.0.0.1:8188/history/{actual_prompt_id}")
            history_resp = urllib.request.urlopen(history_req)
            history = json.loads(history_resp.read())

            if actual_prompt_id in history:
                outputs = history[actual_prompt_id].get("outputs", {})
                if outputs:
                    return outputs
        except Exception:
            pass
        time.sleep(2)

    raise TimeoutError(f"Workflow execution timed out after {timeout}s")


def extract_output_files(outputs):
    """Extract image/video file paths from ComfyUI output."""
    files = []
    for node_id, node_output in outputs.items():
        for img in node_output.get("images", []):
            filename = img.get("filename", "")
            subfolder = img.get("subfolder", "")
            filepath = os.path.join(OUTPUT_DIR, subfolder, filename)
            if os.path.exists(filepath):
                files.append({"type": "image", "path": filepath, "filename": filename})

        for vid in node_output.get("gifs", []):
            filename = vid.get("filename", "")
            subfolder = vid.get("subfolder", "")
            filepath = os.path.join(OUTPUT_DIR, subfolder, filename)
            if os.path.exists(filepath):
                files.append({"type": "video", "path": filepath, "filename": filename})

    return files


def file_to_base64(filepath):
    """Read a file and return base64-encoded string."""
    import base64
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def handle_lora_download(job_input):
    """Utility action: download a LoRA from URL to the volume."""
    lora_url = job_input.get("lora_url")
    dest_filename = job_input.get("dest_filename")

    if not lora_url or not dest_filename:
        return {"error": "lora_url and dest_filename are required"}

    dest_dir = os.path.join(VOLUME_DIR, "ComfyUI", "models", "loras")
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, dest_filename)

    print(f"[Worker] Downloading LoRA to {dest_path}")
    urllib.request.urlretrieve(lora_url, dest_path)

    size = os.path.getsize(dest_path)
    print(f"[Worker] LoRA downloaded: {dest_filename} ({size} bytes)")
    return {"status": "ok", "dest": dest_path, "size": size}


# Global flag — start ComfyUI once on first job
_comfyui_started = False


def handler(job):
    """RunPod serverless handler.

    Args:
        job: Dict with 'id' and 'input' keys from RunPod SDK.
    """
    global _comfyui_started

    job_input = job["input"]

    # Health check — empty input returns status
    if not job_input or (not job_input.get("workflow") and not job_input.get("action")):
        return {"status": "ok", "message": "OpenClaw ComfyUI Worker ready", "comfyui_started": _comfyui_started}

    # Utility action: download LoRA
    if job_input.get("action") == "download_lora":
        return handle_lora_download(job_input)

    # Start ComfyUI on first real job
    if not _comfyui_started:
        start_comfyui()
        _comfyui_started = True

    # Extract workflow
    workflow = job_input.get("workflow")
    if not workflow:
        return {"error": "No workflow provided in input"}

    # Upload input images if provided
    images = job_input.get("images", [])
    for img_data in images:
        name = img_data.get("name", "input.png")
        image_url = img_data.get("image", "")

        if image_url.startswith("http"):
            input_dir = os.path.join(COMFY_DIR, "input")
            os.makedirs(input_dir, exist_ok=True)
            dest = os.path.join(input_dir, name)
            urllib.request.urlretrieve(image_url, dest)
            print(f"[Worker] Downloaded input image: {name}")

    # Execute workflow
    try:
        outputs = queue_workflow(workflow)
    except TimeoutError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Workflow execution failed: {str(e)}"}

    # Extract output files
    files = extract_output_files(outputs)
    if not files:
        return {"error": "No output files generated", "raw_outputs": str(outputs)}

    # Return outputs as base64
    result_images = []
    result_videos = []
    for f in files:
        encoded = file_to_base64(f["path"])
        if f["type"] == "image":
            result_images.append(encoded)
        else:
            result_videos.append(encoded)

    result = {}
    if result_images:
        result["images"] = result_images
    if result_videos:
        result["videos"] = result_videos
    result["file_count"] = len(files)

    return result


runpod.serverless.start({"handler": handler})
