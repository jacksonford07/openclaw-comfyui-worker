# ============================
# AUTO-SET HF + CIVITAI TOKENS
# ============================

import os
from pathlib import Path

HF_TOKEN_VALUE = "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"
CIVITAI_TOKEN_VALUE = "768747f7e04aac897ecee0b854bd37e5"

bashrc_path = Path.home() / ".bashrc"

def append_if_missing(line: str):
    if bashrc_path.exists():
        content = bashrc_path.read_text()
        if line not in content:
            with bashrc_path.open("a") as f:
                f.write(f"\n{line}\n")
    else:
        with bashrc_path.open("w") as f:
            f.write(f"{line}\n")

# Export for current session
os.environ["HF_TOKEN"] = HF_TOKEN_VALUE
os.environ["HUGGINGFACE_HUB_TOKEN"] = HF_TOKEN_VALUE
os.environ["CIVITAI_TOKEN"] = CIVITAI_TOKEN_VALUE

# Persist in ~/.bashrc
append_if_missing(f"export HF_TOKEN='{HF_TOKEN_VALUE}'")
append_if_missing(f"export HUGGINGFACE_HUB_TOKEN='{HF_TOKEN_VALUE}'")
append_if_missing(f"export CIVITAI_TOKEN='{CIVITAI_TOKEN_VALUE}'")

print("✅ HF_TOKEN saved and active")
print("✅ CIVITAI_TOKEN saved and active")
print("✅ Tokens persisted to ~/.bashrc")

import os
import sys
import shutil
import subprocess
import re
import urllib.request
from pathlib import Path

# ============================
# STYLING
# ============================
R  = "[0m"
B  = "[1m"
GR = "[38;5;22m"
BL = "[38;5;54m"

def banner():
    print(f"""
{BL}{B}╔══════════════════════════════════════════════════════════════╗
║             SKY WORKFLOWS — WAN ANIMATE INSTALLER           ║
║                      ComfyUI Setup Script                    ║
╚══════════════════════════════════════════════════════════════╝{R}
""")

def section(title: str):
    pad = (60 - len(title) - 2) // 2
    print(f"\n{BL}{B}{'─' * pad} {title} {'─' * pad}{R}\n")

def done():
    print(f"""
{GR}{B}╔══════════════════════════════════════════════════════════════╗
║                  INSTALLATION COMPLETE                       ║
║              Restart ComfyUI to apply changes                ║
╚══════════════════════════════════════════════════════════════╝{R}
""")

# ============================
# CONFIG
# ============================
COMFY = Path(os.environ.get("COMFY_PATH", "/workspace/ComfyUI")).resolve()
MODELS = COMFY / "models"
NODES = COMFY / "custom_nodes"

HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()
CIVITAI_TOKEN = os.environ.get("CIVITAI_TOKEN", "").strip()

# ============================
# UTILS
# ============================
def run(cmd, cwd=None, check=True, env=None):
    print(f"\n$ {' '.join(map(str, cmd))}")
    return subprocess.run(
        list(map(str, cmd)),
        cwd=str(cwd) if cwd else None,
        check=check,
        env=env
    )

def pip_install(args):
    run([sys.executable, "-m", "pip", "install", *args])

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def safe_move(src: Path, dst: Path):
    if not src.exists():
        return
    ensure_dir(dst.parent)
    if dst.exists():
        dst.unlink(missing_ok=True)
    shutil.move(str(src), str(dst))

def rm_rf(p: Path):
    if p.is_file() or p.is_symlink():
        p.unlink(missing_ok=True)
    elif p.is_dir():
        shutil.rmtree(p, ignore_errors=True)

def git_clone_or_pull(url: str, folder_name: str):
    ensure_dir(NODES)
    dst = NODES / folder_name
    if not dst.exists():
        run(["git", "clone", "--depth", "1", url, str(dst)])
    else:
        run(["git", "fetch", "--all", "--prune"], cwd=dst)
        run(["git", "reset", "--hard", "origin/HEAD"], cwd=dst)

    req = dst / "requirements.txt"
    if req.exists():
        pip_install(["-r", str(req), "--break-system-packages"])

def hf_download(repo_id: str, file_path: str, out_dir: Path):
    ensure_dir(out_dir)
    env = os.environ.copy()
    if HF_TOKEN:
        env["HF_TOKEN"] = HF_TOKEN
        # some setups use HF_TOKEN, others use HUGGINGFACE_HUB_TOKEN
        env["HUGGINGFACE_HUB_TOKEN"] = HF_TOKEN
    run(["hf", "download", repo_id, file_path, "--local-dir", str(out_dir)], env=env)

def civitai_download(model_version_id: str, out_path: Path):
    if not CIVITAI_TOKEN:
        print("⚠️ CIVITAI_TOKEN not set; skipping CivitAI download.")
        return
    ensure_dir(out_path.parent)
    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"↪ Existing partial/full file found, attempting resume: {out_path}")
    run([
        "curl",
        "--http1.1",
        "-L",
        "-C", "-",
        "--retry", "20",
        "--retry-all-errors",
        "--retry-delay", "5",
        "-H", f"Authorization: Bearer {CIVITAI_TOKEN}",
        "-o", str(out_path),
        f"https://civitai.com/api/download/models/{model_version_id}"
    ])

# ============================
# STABLE TORCH + SAGEATTENTION
# ============================
def install_torch_and_sageattention():
    """
    Installs stable torch cu128 + sageattention.
    Using stable (not nightly) to avoid driver compatibility issues.
    """
    print("\n⚡ Installing stable PyTorch (cu128) + SageAttention\n")

    # Install stable torch cu128
    pip_install([
        "-U",
        "torch", "torchvision", "torchaudio",
        "--index-url", "https://download.pytorch.org/whl/cu128",
        "--break-system-packages"
    ])

    # Install SageAttention
    run([sys.executable, "-m", "pip", "uninstall", "-y", "sageattention"], check=False)
    pip_install(["-U", "sageattention", "--break-system-packages"])

    # Sanity print
    subprocess.run([sys.executable, "-c",
                    "import torch; import sageattention; "
                    "print('torch', torch.__version__); "
                    "print('sageattention ok')"],
                   check=True)

# ============================
# MAIN
# ============================
def main():
    banner()

    if not COMFY.exists():
        raise SystemExit(f"❌ ComfyUI not found at {COMFY}")

    ensure_dir(MODELS)
    ensure_dir(NODES)

    section("STEP 1 — CORE DEPENDENCIES")
    pip_install(["-U", "pip", "--break-system-packages"])
    pip_install(["-U", "huggingface_hub[cli]", "onnxruntime-gpu", "opencv-python-headless", "--break-system-packages"])

    section("STEP 2 — PYTORCH / SAGEATTENTION")
    install_torch_and_sageattention()

    section("STEP 3 — CUSTOM NODES")
    repos = [
        ("https://github.com/kijai/ComfyUI-WanVideoWrapper.git", "ComfyUI-WanVideoWrapper"),
        ("https://github.com/kijai/ComfyUI-WanAnimatePreprocess.git", "ComfyUI-WanAnimatePreprocess"),
        ("https://github.com/kijai/ComfyUI-KJNodes.git", "ComfyUI-KJNodes"),
        ("https://github.com/yolain/ComfyUI-Easy-Use.git", "ComfyUI-Easy-Use"),
        ("https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git", "ComfyUI-VideoHelperSuite"),
        ("https://github.com/9nate-drake/Comfyui-SecNodes.git", "Comfyui-SecNodes"),
        ("https://github.com/rgthree/rgthree-comfy.git", "rgthree-comfy"),
        ("https://github.com/chflame163/ComfyUI_LayerStyle.git", "ComfyUI_LayerStyle"),
        ("https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes.git", "ComfyUI_Comfyroll_CustomNodes"),
        ("https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git", "ComfyUI-Frame-Interpolation"),
        ("https://github.com/jamesWalker55/comfyui-various.git", "comfyui-various"),
    ]
    for url, name in repos:
        git_clone_or_pull(url, name)

    section("STEP 4 — RIFE FRAME INTERPOLATION MODEL")
    # ---- RIFE frame interpolation model
    # All original GitHub Release mirrors are 404. These HuggingFace mirrors are verified active.
    # Pre-downloading here means the node never attempts the broken runtime auto-download.
    rife_dir = NODES / "ComfyUI-Frame-Interpolation/ckpts/rife"
    rife_model = rife_dir / "rife49.pth"
    if not rife_model.exists():
        ensure_dir(rife_dir)
        print("\n⬇️  Downloading rife49.pth from HuggingFace...")
        rife_mirrors = [
            "https://huggingface.co/VMTamashii/rife49/resolve/main/rife49.pth",
            "https://huggingface.co/Isi99999/Frame_Interpolation_Models/resolve/main/rife49.pth",
            "https://huggingface.co/MachineDelusions/RIFE/resolve/main/rife49.pth",
            "https://huggingface.co/hfmaster/models-moved/resolve/main/rife/rife49.pth",
        ]
        for mirror in rife_mirrors:
            if rife_model.exists():
                break
            print(f"  Trying: {mirror}")
            run(["wget", "--tries=3", "--timeout=60", "-O", str(rife_model), mirror], check=False)
            # wget writes a partial file on failure — remove it so exists() check stays reliable
            if rife_model.exists() and rife_model.stat().st_size < 1_000_000:
                rife_model.unlink()
        if rife_model.exists():
            print("✅ rife49.pth downloaded successfully")
        else:
            print("⚠️  rife49.pth could not be downloaded from any mirror.\n"
                  "    Place it manually at:\n"
                  f"    {rife_model}")
    else:
        print("✅ rife49.pth already present — skipping")

    section("STEP 5 — DIFFUSION MODELS & TEXT ENCODERS")
    # ---- Model folders
    for d in ["diffusion_models", "text_encoders", "vae", "clip_vision", "detection", "loras", "sams", "controlnet"]:
        ensure_dir(MODELS / d)
    ensure_dir(MODELS / "diffusion_models/Wan22Animate")

    # ---- WAN core (Comfy-Org repackaged)
    hf_download(
        "Comfy-Org/Wan_2.2_ComfyUI_Repackaged",
        "split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp16.safetensors",
        MODELS
    )
    safe_move(
        MODELS / "split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp16.safetensors",
        MODELS / "diffusion_models/wan2.2_i2v_low_noise_14B_fp16.safetensors"
    )
    rm_rf(MODELS / "split_files")

    hf_download(
        "Comfy-Org/Wan_2.2_ComfyUI_Repackaged",
        "split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        MODELS
    )
    safe_move(
        MODELS / "split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        MODELS / "text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"
    )
    rm_rf(MODELS / "split_files")

    # Extra encoder (bf16) used by some workflows
    hf_download("Kijai/WanVideo_comfy", "umt5-xxl-enc-bf16.safetensors", MODELS / "text_encoders")

    # Fully uncensored UMT5-XXL text encoder (11.4 GB)
    uncensored_encoder = MODELS / "text_encoders/models_t5_umt5-xxl-enc-bf16_fully_uncensored.safetensors"
    if not uncensored_encoder.exists():
        try:
            run([
                "wget", "-O", str(uncensored_encoder),
                "https://huggingface.co/eddy1111111/Wan_toolkit/resolve/main/models_t5_umt5-xxl-enc-bf16_fully_uncensored.safetensors"
            ], check=False)
            # If first download failed, try alternative mirror
            if not uncensored_encoder.exists():
                run([
                    "wget", "-O", str(uncensored_encoder),
                    "https://huggingface.co/henterchan/models_t5_umt5-xxl-enc-bf16_fully_uncensored/resolve/main/models_t5_umt5-xxl-enc-bf16_fully_uncensored.safetensors"
                ])
        except Exception as e:
            print(f"⚠️ Could not download uncensored encoder: {e}")


    # WAN Animate fp8 scaled model (Kijai)
    hf_download(
        "Kijai/WanVideo_comfy_fp8_scaled",
        "Wan22Animate/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors",
        MODELS / "diffusion_models"
    )

    # Uni3C ControlNet (Camera Movement)
    hf_download("Kijai/WanVideo_comfy", "Wan21_Uni3C_controlnet_fp16.safetensors", MODELS / "controlnet")

    # VAE
    hf_download("DeepBeepMeep/Wan2.1", "Wan2.1_VAE.safetensors", MODELS / "vae")
    safe_move(MODELS / "vae/Wan2.1_VAE.safetensors", MODELS / "vae/Wan2_1_VAE_bf16.safetensors")

    # WAN 2.1 VAE (Comfy-Org repackaged)
    hf_download(
        "Comfy-Org/Wan_2.2_ComfyUI_Repackaged",
        "split_files/vae/wan_2.1_vae.safetensors",
        MODELS
    )
    safe_move(
        MODELS / "split_files/vae/wan_2.1_vae.safetensors",
        MODELS / "vae/wan_2.1_vae.safetensors"
    )
    rm_rf(MODELS / "split_files")

    # CLIP Vision
    clip_vision_path = MODELS / "clip_vision/clip_vision_h.safetensors"
    if not clip_vision_path.exists():
        run([
            "wget", "-O", str(clip_vision_path),
            "https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors"
        ])

    # Detection models
    hf_download(
        "Wan-AI/Wan2.2-Animate-14B",
        "process_checkpoint/det/yolov10m.onnx",
        MODELS / "detection"
    )
    safe_move(
        MODELS / "detection/process_checkpoint/det/yolov10m.onnx",
        MODELS / "detection/yolov10m.onnx"
    )
    rm_rf(MODELS / "detection/process_checkpoint")

    hf_download(
        "JunkyByte/easy_ViTPose",
        "onnx/wholebody/vitpose-l-wholebody.onnx",
        MODELS / "detection"
    )
    # keep the downloaded structure but also copy a flat version
    src_vitpose = MODELS / "detection/onnx/wholebody/vitpose-l-wholebody.onnx"
    if src_vitpose.exists():
        shutil.copy2(src_vitpose, MODELS / "detection/vitpose-l-wholebody.onnx")

    section("STEP 6 — CIVITAI MODELS")
    # ---- SmoothMix (optional)
    civitai_download("2260110", MODELS / "diffusion_models/smoothMixWan22I2V14B_i2vHigh.safetensors")
    civitai_download("2259006", MODELS / "diffusion_models/smoothMixWan22I2V14B_i2vV20Low.safetensors")

    section("STEP 7 — SAM & LoRAs")
    # ---- SeC model
    hf_download("VeryAladeen/Sec-4B", "SeC-4B-fp16.safetensors", MODELS / "sams")

    # ---- WAN toolkit LoRAs (these must exist for your workflow dropdowns)
    for f in [
        "lightx2v_elite_it2v_animate_face.safetensors",
        "WAN22_MoCap_fullbodyCOPY_ED.safetensors",
        "Wan2.2-Fun-A14B-InP-Fusion-Elite.safetensors",
        "FullDynamic_Ultimate_Fusion_Elite.safetensors",
    ]:
        hf_download("eddy1111111/Wan_toolkit", f, MODELS / "loras")

    # ---- Additional LoRAs
    loras_to_download = [
        # LightX2V I2V 14B 480p Step Distill LoRAs (different ranks)
        ("Kijai/WanVideo_comfy", "Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank32_bf16.safetensors"),
        ("Kijai/WanVideo_comfy", "Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors"),
        ("Kijai/WanVideo_comfy", "Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank128_bf16.safetensors"),
    ]
    
    for repo, file_path in loras_to_download:
        try:
            hf_download(repo, file_path, MODELS / "loras")
        except Exception as e:
            print(f"⚠️ Could not download {file_path}: {e}")
    
    # WanVideo Running I2V LoRA
    lora_file = MODELS / "loras/P001-SideSex-Wan-i2v-v10-000010_converted.safetensors"
    if not lora_file.exists():
        try:
            run([
                "wget", "-O", str(lora_file),
                "https://huggingface.co/Serenak/chilloutmix/resolve/main/P001-SideSex-Wan-i2v-v10-000010_converted.safetensors"
            ], check=False)
        except Exception as e:
            print(f"⚠️ Could not download WanVideo Running I2V LoRA: {e}")
    
    # M4CROM4STI4 Physics LoRAs
    physics_loras = [
        ("https://huggingface.co/Market5/M4CROM4STI4-Huge_Natural_Breasts_Physics/resolve/main/wan-m4crom4sti4-i2v-106epo-k3nk.safetensors", 
         "wan-m4crom4sti4-i2v-106epo-k3nk.safetensors"),
        ("https://huggingface.co/Socialsparks/Wan2.2-lora/resolve/main/wan22-m4crom4sti4-i2v-20epoc-high-k3nk.safetensors",
         "wan22-m4crom4sti4-i2v-20epoc-high-k3nk.safetensors"),
    ]
    
    for url, filename in physics_loras:
        lora_path = MODELS / f"loras/{filename}"
        if not lora_path.exists():
            try:
                run(["wget", "-O", str(lora_path), url], check=False)
            except Exception as e:
                print(f"⚠️ Could not download {filename}: {e}")

    # ---- Run WAN I2V LoRA
    civitai_download("1723090", MODELS / "loras/run_wan_i2v_14b.safetensors")

    # ---- Detailz LoRA
    civitai_download("1565668", MODELS / "loras/civitai_1565668.safetensors")

    # ---- Wan22 Remix T2V/I2V High V2.1 (installed last)
    civitai_download("2567309", MODELS / "diffusion_models/wan22RemixT2VI2V_i2vHighV21.safetensors")

    done()

if __name__ == "__main__":
    main()
