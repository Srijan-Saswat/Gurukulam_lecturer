#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

import torch
from gfpgan import GFPGANer


def run(cmd):
    print("🟦", " ".join(cmd))
    subprocess.run(cmd, check=True)


def get_video_info(video_path: str):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return fps, nframes


def extract_frames(video_path: str, frames_dir: Path):
    frames_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # frame is BGR
        out = frames_dir / f"{idx:06d}.png"
        cv2.imwrite(str(out), frame)
        idx += 1

    cap.release()
    return idx


def enhance_frames_gfpgan(frames_dir: Path, out_dir: Path, gfpgan_weights: Path, upscale: int = 2):
    out_dir.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"✅ Using device: {device}")

    if not gfpgan_weights.exists():
        raise FileNotFoundError(f"GFPGAN weights not found: {gfpgan_weights}")

    # For GFPGAN v1.4:
    restorer = GFPGANer(
        model_path=str(gfpgan_weights),
        upscale=upscale,
        arch="clean",
        channel_multiplier=2,
        bg_upsampler=None,
        device=device,
    )

    frames = sorted(frames_dir.glob("*.png"))
    if not frames:
        raise RuntimeError(f"No frames found in: {frames_dir}")

    for fp in tqdm(frames, desc="GFPGAN enhancing"):
        img = cv2.imread(str(fp), cv2.IMREAD_COLOR)
        if img is None:
            raise RuntimeError(f"Failed to read: {fp}")

        # enhance expects BGR numpy
        try:
            _, _, restored = restorer.enhance(img, has_aligned=False, only_center_face=False, paste_back=True)
        except Exception as e:
            # If a frame fails, fall back to original
            print(f"⚠️ GFPGAN failed on {fp.name}: {e}  -> using original frame")
            restored = img

        cv2.imwrite(str(out_dir / fp.name), restored)


def rebuild_video_with_audio(enhanced_dir: Path, src_video: str, out_video: str, fps: float):
    # Use source video as audio reference to keep sync
    # -shortest ensures we don't go longer than audio
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-framerate", str(fps),
        "-i", str(enhanced_dir / "%06d.png"),
        "-i", src_video,
        "-map", "0:v:0",
        "-map", "1:a:0?",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-shortest",
        out_video
    ])


def main():
    if len(sys.argv) != 3:
        print("Usage: python enhance_avatar_gfpgan.py <input.mp4> <output.mp4>")
        sys.exit(1)

    in_mp4 = sys.argv[1]
    out_mp4 = sys.argv[2]

    if not os.path.exists(in_mp4):
        print(f"❌ Input not found: {in_mp4}")
        sys.exit(1)

    fps, nframes = get_video_info(in_mp4)
    print(f"✅ Input FPS={fps:.3f}, frames={nframes}")

    work = Path("output/_gfpgan_work")
    frames_dir = work / "frames"
    enhanced_dir = work / "enhanced"

    # Clean work dir
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)

    extracted = extract_frames(in_mp4, frames_dir)
    print(f"✅ Extracted {extracted} frames -> {frames_dir}")

    # IMPORTANT: your weights are here (based on your find output)
    weights = Path("./gfpgan/weights/GFPGANv1.4.pth")
    print(f"✅ Using GFPGAN weights: {weights}")

    enhance_frames_gfpgan(frames_dir, enhanced_dir, weights, upscale=2)
    print(f"✅ Enhanced frames -> {enhanced_dir}")

    rebuild_video_with_audio(enhanced_dir, in_mp4, out_mp4, fps)
    print(f"✅ Wrote enhanced video: {out_mp4}")


if __name__ == "__main__":
    main()
