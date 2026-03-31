#!/usr/bin/env python3
"""
ComfyUI Installer - FOR SKY WORKFLOWS

Force-reinstalls requirements for all problematic nodes to avoid conflicts.
"""

from __future__ import annotations

import os
import sys
import shutil
import subprocess
from pathlib import Path

COMFY = Path("/workspace/ComfyUI")
MODELS = COMFY / "models"
NODES = COMFY / "custom_nodes"


def die(msg: str, code: int = 1) -> None:
    print(f"❌ ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print("▶️  " + " ".join(cmd))
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=check)


def pip_install(args: list[str]) -> None:
    run([sys.executable, "-m", "pip", "install", *args], check=True)


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def rm_rf(p: Path) -> None:
    if p.is_symlink() or p.is_file():
        p.unlink(missing_ok=True)
    elif p.is_dir():
        shutil.rmtree(p, ignore_errors=True)


def hf_download(repo: str, file_path: str, local_dir: Path) -> None:
    """Download a file from HuggingFace."""
    run([
        "hf", "download", repo, file_path,
        "--local-dir", str(local_dir),
    ], check=True)


def install_node(repo: str, dir_name: str, force_reinstall: bool = False) -> None:
    """Clone a node repo and install its requirements."""
    dest = NODES / dir_name
    
    # Clone if doesn't exist
    if not dest.exists():
        print(f"⬇️  Cloning: {dir_name}")
        run(["git", "clone", "--depth", "1", repo, str(dest)], check=True)
    else:
        print(f"✅ Already exists: {dir_name}")
    
    # Install requirements
    req = dest / "requirements.txt"
    if req.exists():
        print(f"📦 Installing requirements for {dir_name}")
        args = ["-r", str(req), "--break-system-packages"]
        if force_reinstall:
            print(f"   🔧 Using --force-reinstall for {dir_name}")
            args.extend(["--force-reinstall", "--no-cache-dir"])
        pip_install(args)


def setup_environment_tokens() -> None:
    """Set up HF_TOKEN and CIVITAI_TOKEN in environment and bashrc."""
    print("🔑 Setting up environment tokens...\n")

    tokens = {
        "HF_TOKEN": os.environ.get("HF_TOKEN", ""),
        "CIVITAI_TOKEN": os.environ.get("CIVITAI_TOKEN", ""),
    }

    if not tokens["HF_TOKEN"]:
        die("HF_TOKEN env var is required. Set it before running: export HF_TOKEN=your_token")
    if not tokens["CIVITAI_TOKEN"]:
        print("⚠️  CIVITAI_TOKEN not set — CivitAI downloads will be skipped")

    bashrc = Path.home() / ".bashrc"

    for name, value in tokens.items():
        os.environ[name] = value
        export_line = f"export {name}='{value}'"
        # Append to bashrc if not already present
        already_set = False
        if bashrc.exists():
            content = bashrc.read_text()
            if export_line in content:
                already_set = True
        if not already_set:
            with open(bashrc, "a") as f:
                f.write(f"\n{export_line}\n")
        print(f"✅ {name} saved and active")

    print("✅ HF_TOKEN and CIVITAI_TOKEN saved and active\n")


def main() -> None:
    print("🎨 ComfyUI Bulletproof Installer\n")

    # =========================================================================
    # ENVIRONMENT TOKENS (run first)
    # =========================================================================
    setup_environment_tokens()

    # Validate directories
    if not COMFY.exists():
        die(f"ComfyUI not found at {COMFY}")
    if not MODELS.exists():
        die(f"Models dir not found at {MODELS}")
    if not NODES.exists():
        die(f"Custom nodes dir not found at {NODES}")

    # Install HuggingFace CLI
    print("🔧 Installing huggingface-cli...")
    pip_install(["-U", "huggingface_hub[cli]", "--break-system-packages"])
    
    # Verify it's installed
    if shutil.which("hf") is None:
        die("hf command not found after installation. Try: pip install huggingface_hub[cli]")

    # =========================================================================
    # MODELS
    # =========================================================================
    print("\n🚀 Downloading models...\n")

    # FLUX 2 Klein 9B FP8
    print("⬇️  FLUX 2 Klein 9B FP8")
    ensure_dir(MODELS / "diffusion_models")
    hf_download("black-forest-labs/FLUX.2-klein-9b-fp8", 
                "flux-2-klein-9b-fp8.safetensors", 
                MODELS / "diffusion_models")

    # Qwen 3 4B
    print("⬇️  Qwen 3 4B")
    ensure_dir(MODELS / "text_encoders")
    hf_download("Comfy-Org/flux2-klein-4B", 
                "split_files/text_encoders/qwen_3_4b.safetensors", 
                MODELS)
    src = MODELS / "split_files" / "text_encoders" / "qwen_3_4b.safetensors"
    if src.exists():
        shutil.move(str(src), str(MODELS / "text_encoders" / "qwen_3_4b.safetensors"))
        rm_rf(MODELS / "split_files")

    # Qwen 3 8B FP8
    print("⬇️  Qwen 3 8B FP8")
    hf_download("Comfy-Org/vae-text-encorder-for-flux-klein-9b", 
                "split_files/text_encoders/qwen_3_8b_fp8mixed.safetensors", 
                MODELS)
    src = MODELS / "split_files" / "text_encoders" / "qwen_3_8b_fp8mixed.safetensors"
    if src.exists():
        shutil.move(str(src), str(MODELS / "text_encoders" / "qwen_3_8b_fp8mixed.safetensors"))
        rm_rf(MODELS / "split_files")

    # CLIP Vision
    print("⬇️  CLIP Vision")
    ensure_dir(MODELS / "clip_vision")
    hf_download("h94/IP-Adapter", 
                "models/image_encoder/model.safetensors", 
                MODELS)
    src = MODELS / "models" / "image_encoder" / "model.safetensors"
    if src.exists():
        shutil.move(str(src), str(MODELS / "clip_vision" / "clip_vision_h.safetensors"))
        rm_rf(MODELS / "models")

    # Z-Image Turbo
    print("⬇️  Z-Image Turbo")
    hf_download("Comfy-Org/z_image_turbo", 
                "split_files/diffusion_models/z_image_turbo_bf16.safetensors", 
                MODELS)
    src = MODELS / "split_files" / "diffusion_models" / "z_image_turbo_bf16.safetensors"
    if src.exists():
        shutil.move(str(src), str(MODELS / "diffusion_models" / "z_image_turbo_bf16.safetensors"))
        rm_rf(MODELS / "split_files")

    # Z-Image VAE
    print("⬇️  Z-Image VAE")
    ensure_dir(MODELS / "vae")
    hf_download("Comfy-Org/z_image_turbo", 
                "split_files/vae/ae.safetensors", 
                MODELS)
    src = MODELS / "split_files" / "vae" / "ae.safetensors"
    if src.exists():
        shutil.move(str(src), str(MODELS / "vae" / "ae.safetensors"))
        rm_rf(MODELS / "split_files")

    # SD VAE
    print("⬇️  SD VAE")
    hf_download("stabilityai/sd-vae-ft-ema", 
                "diffusion_pytorch_model.safetensors", 
                MODELS / "vae")
    src = MODELS / "vae" / "diffusion_pytorch_model.safetensors"
    if src.exists():
        dest = MODELS / "vae" / "ema_vae_fp16.safetensors"
        if dest.exists():
            dest.unlink()
        shutil.move(str(src), str(dest))

    # FLUX 2 VAE
    print("⬇️  FLUX 2 VAE")
    hf_download("Comfy-Org/flux2-dev", 
                "split_files/vae/flux2-vae.safetensors", 
                MODELS)
    src = MODELS / "split_files" / "vae" / "flux2-vae.safetensors"
    if src.exists():
        shutil.move(str(src), str(MODELS / "vae" / "flux2-vae.safetensors"))
        rm_rf(MODELS / "split_files")

    # BFS Best Face Swap LoRA
    print("⬇️  BFS Best Face Swap LoRA")
    ensure_dir(MODELS / "loras")
    hf_download("Alissonerdx/BFS-Best-Face-Swap",
                "bfs_head_v1_flux-klein_9b_step3500_rank128.safetensors",
                MODELS / "loras")

    # =========================================================================
    # ADDITIONAL MODELS
    # =========================================================================

    # Nipples YOLO detection model
    print("⬇️  Nipples YOLOv8s detection model")
    yolo_bbox_dir = MODELS / "ultralytics" / "bbox"
    ensure_dir(yolo_bbox_dir)
    nipples_yolo = yolo_bbox_dir / "nipples_yolov8s.pt"
    if not nipples_yolo.exists():
        run([
            "curl", "-L",
            "-o", str(nipples_yolo),
            "https://huggingface.co/ashllay/YOLO_Models/resolve/e07b01219ff1807e1885015f439d788b038f49bd/bbox/nipples_yolov8s.pt",
        ], check=True)
    else:
        print("✅ nipples_yolov8s.pt already exists")

    # SeedVR2 upscaler models
    print("⬇️  SeedVR2 upscaler models")
    seedvr2_dir = MODELS / "SEEDVR2"
    ensure_dir(seedvr2_dir)
    seedvr2_3b = seedvr2_dir / "seedvr2_ema_3b_fp16.safetensors"
    if not seedvr2_3b.exists():
        run([
            "curl", "-L",
            "-o", str(seedvr2_3b),
            "https://huggingface.co/numz/SeedVR2_comfyUI/resolve/main/seedvr2_ema_3b_fp16.safetensors",
        ], check=True)
    else:
        print("✅ seedvr2_ema_3b_fp16.safetensors already exists")

    seedvr2_7b = seedvr2_dir / "seedvr2_ema_7b_fp16.safetensors"
    if not seedvr2_7b.exists():
        run([
            "curl", "-L",
            "-o", str(seedvr2_7b),
            "https://huggingface.co/numz/SeedVR2_comfyUI/resolve/main/seedvr2_ema_7b_fp16.safetensors",
        ], check=True)
    else:
        print("✅ seedvr2_ema_7b_fp16.safetensors already exists")

    # CyberRealisticPony checkpoint
    print("⬇️  CyberRealisticPony V14.1 FP16")
    ensure_dir(MODELS / "checkpoints")
    cyber_pony = MODELS / "checkpoints" / "CyberRealisticPony_V14.1_FP16.safetensors"
    if not cyber_pony.exists():
        run([
            "curl", "-L",
            "-o", str(cyber_pony),
            "https://huggingface.co/cyberdelia/CyberRealisticPony/resolve/main/CyberRealisticPony_V14.1_FP16.safetensors",
        ], check=True)
    else:
        print("✅ CyberRealisticPony_V14.1_FP16.safetensors already exists")

    print("\n✅ All models downloaded\n")

    # =========================================================================
    # CUSTOM NODES
    # =========================================================================
    print("🔌 Installing custom nodes...\n")

    os.environ["GIT_TERMINAL_PROMPT"] = "0"

    # NODES WITH FORCE-REINSTALL (problematic ones that need clean installs)
    problematic_nodes = [
        ("https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler.git", "ComfyUI-SeedVR2_VideoUpscaler"),
        ("https://github.com/1038lab/ComfyUI-QwenVL.git", "ComfyUI-QwenVL"),
        ("https://github.com/IuvenisSapiens/ComfyUI_Qwen3-VL-Instruct.git", "ComfyUI_Qwen3-VL-Instruct"),
        ("https://github.com/MaraScott/ComfyUI_MaraScott_Nodes.git", "ComfyUI_MaraScott_Nodes"),
    ]

    # REGULAR NODES (install normally)
    regular_nodes = [
        ("https://github.com/Lightricks/ComfyUI-LTXVideo.git", "ComfyUI-LTXVideo"),
        ("https://github.com/kijai/ComfyUI-segment-anything-2.git", "ComfyUI-segment-anything-2"),
        ("https://github.com/omar92/ComfyUI-QualityOfLifeSuit_Omar92.git", "ComfyUI-QualityOfLifeSuit_Omar92"),
        ("https://github.com/MixLabPro/comfyui-mixlab-nodes.git", "comfyui-mixlab-nodes"),
        ("https://github.com/BadCafeCode/masquerade-nodes-comfyui.git", "masquerade-nodes-comfyui"),
        ("https://github.com/lquesada/ComfyUI-Inpaint-CropAndStitch.git", "ComfyUI-Inpaint-CropAndStitch"),
        ("https://github.com/WASasquatch/was-node-suite-comfyui.git", "was-node-suite-comfyui"),
        ("https://github.com/1038lab/ComfyUI-RMBG.git", "ComfyUI-RMBG"),
        ("https://github.com/rgthree/rgthree-comfy.git", "rgthree-comfy"),
        ("https://github.com/kijai/ComfyUI-KJNodes.git", "ComfyUI-KJNodes"),
        ("https://github.com/chflame163/ComfyUI_LayerStyle.git", "ComfyUI_LayerStyle"),
        ("https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes.git", "ComfyUI_Comfyroll_CustomNodes"),
        ("https://github.com/ltdrdata/ComfyUI-Impact-Pack.git", "ComfyUI-Impact-Pack"),
        ("https://github.com/yolain/ComfyUI-Easy-Use.git", "ComfyUI-Easy-Use"),
        ("https://github.com/pythongosssss/ComfyUI-Custom-Scripts.git", "ComfyUI-Custom-Scripts"),
        ("https://github.com/TinyTerra/ComfyUI_tinyterraNodes.git", "ComfyUI_tinyterraNodes"),
        ("https://github.com/giriss/comfy-image-saver.git", "comfy-image-saver"),
    ]

    # Install problematic nodes with force-reinstall
    print("🔧 Installing problematic nodes with force-reinstall...\n")
    for repo, dir_name in problematic_nodes:
        try:
            install_node(repo, dir_name, force_reinstall=True)
        except Exception as e:
            print(f"⚠️  Failed to install {dir_name}: {e}")
            print("   Continuing with other nodes...")

    # Install regular nodes normally
    print("\n📦 Installing regular nodes...\n")
    for repo, dir_name in regular_nodes:
        try:
            install_node(repo, dir_name, force_reinstall=False)
        except Exception as e:
            print(f"⚠️  Failed to install {dir_name}: {e}")
            print("   Continuing with other nodes...")

    
    # =========================================================================
    # IMPACT PACK + SUBPACK (Flux2 cloth remover fix)
    # =========================================================================
    print("\n🧩 Ensuring Impact Pack + Impact Subpack are installed...\n")

    impact_pack = NODES / "ComfyUI-Impact-Pack"
    impact_subpack = NODES / "ComfyUI-Impact-Subpack"

    # Impact Pack (may already exist from regular_nodes list)
    if not impact_pack.exists():
        print("⬇️  Cloning Impact Pack")
        run(["git", "clone", "--depth", "1", "https://github.com/ltdrdata/ComfyUI-Impact-Pack.git", str(impact_pack)], check=True)
    else:
        print("✅ Impact Pack already exists")

    req = impact_pack / "requirements.txt"
    if req.exists():
        print("📦 Installing Impact Pack requirements")
        pip_install(["-r", str(req), "--break-system-packages"])

    # Impact Subpack (required dependency)
    if not impact_subpack.exists():
        print("⬇️  Cloning Impact Subpack (required)")
        run(["git", "clone", "--depth", "1", "https://github.com/ltdrdata/ComfyUI-Impact-Subpack.git", str(impact_subpack)], check=True)
    else:
        print("✅ Impact Subpack already exists")

    req = impact_subpack / "requirements.txt"
    if req.exists():
        print("📦 Installing Impact Subpack requirements")
        pip_install(["-r", str(req), "--break-system-packages"])

    # Run Impact Pack installer (registers components)
    installer = impact_pack / "install.py"
    if installer.exists():
        print("🛠️  Running Impact Pack install.py")
        run([sys.executable, str(installer)], cwd=impact_pack, check=True)
    else:
        print("⚠️  Impact Pack install.py not found; skipping installer")

    # Sanity check import (catches broken installs early)
    print("🔎 Import check: Impact Pack nodes")
    run([sys.executable, "-c", "import sys; sys.path.insert(0,'custom_nodes/ComfyUI-Impact-Pack'); import nodes"], cwd=COMFY, check=False)

    # =========================================================================
    # IMPACT MODEL DEPENDENCY: Segment Anything (SAM) weights
    # =========================================================================
    print("\n🧠 Ensuring SAM ViT-H is present for Impact Pack...\n")
    sams_dir = MODELS / "sams"
    ensure_dir(sams_dir)
    sam_file = sams_dir / "sam_vit_h_4b8939.pth"
    if not sam_file.exists():
        print("⬇️  Downloading SAM ViT-H (sam_vit_h_4b8939.pth)")
        run([
            "curl", "-L",
            "-o", str(sam_file),
            "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth",
        ], check=True)
    else:
        print("✅ SAM ViT-H already exists")

    # =========================================================================
    # OPTIONAL: CivitAI model download (requires CIVITAI_TOKEN)
    # =========================================================================
    print("\n🧪 Optional: CivitAI checkpoint download (requires CIVITAI_TOKEN)\n")
    civitai_token = os.environ.get("CIVITAI_TOKEN", "").strip()
    if civitai_token:
        ckpt_dir = MODELS / "checkpoints"
        ensure_dir(ckpt_dir)
        biglust = ckpt_dir / "bigLust_v16.safetensors"
        if not biglust.exists():
            print("⬇️  Downloading bigLust_v16.safetensors from CivitAI")
            run([
                "curl", "-L",
                "-H", f"Authorization: Bearer {civitai_token}",
                "-o", str(biglust),
                "https://civitai.com/api/download/models/1081768",
            ], check=True)
        else:
            print("✅ bigLust_v16.safetensors already exists")
    else:
        print("⚠️  CIVITAI_TOKEN not set; skipping bigLust_v16.safetensors download")

    # =========================================================================
    # LAST INSTALL: RES4LYF (installed last to avoid dependency conflicts)
    # =========================================================================
    print("\n🔬 Installing RES4LYF (last, to avoid dependency conflicts)...\n")
    try:
        install_node("https://github.com/ClownsharkBatwing/RES4LYF", "RES4LYF")
    except Exception as e:
        print(f"⚠️  Failed to install RES4LYF: {e}")
        print("   Continuing...")

    print("\n✅ All custom nodes installed")

    # =========================================================================
    # LAST DOWNLOAD: LustifySDXL Endgame checkpoint (installed last)
    # =========================================================================
    print("\n🔞 Downloading LustifySDXL ENDGAME checkpoint (last)...\n")
    civitai_token = os.environ.get("CIVITAI_TOKEN", "").strip()
    if civitai_token:
        ckpt_dir = MODELS / "checkpoints"
        ensure_dir(ckpt_dir)
        lustify = ckpt_dir / "lustifySDXLNSFW_endgame.safetensors"
        if not lustify.exists():
            print("⬇️  Downloading lustifySDXLNSFW_endgame.safetensors from CivitAI")
            run([
                "curl", "-L",
                "-H", f"Authorization: Bearer {civitai_token}",
                "-o", str(lustify),
                "https://civitai.com/api/download/models/1094291",
            ], check=True)
        else:
            print("✅ lustifySDXLNSFW_endgame.safetensors already exists")
    else:
        print("⚠️  CIVITAI_TOKEN not set; skipping lustifySDXLNSFW_endgame.safetensors download")

    print("\n" + "="*60)
    print("🎉 Installation Complete!")
    print("="*60)
    print("\n📋 Next steps:")
    print("  1. Restart ComfyUI")
    print("  2. All workflows should work")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Installation interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Installation failed: {e}", file=sys.stderr)
        sys.exit(1)
