#!/usr/bin/env bash
set -euo pipefail

# Always run relative to THIS script's folder
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p temp output

echo "🔹 Checking slide audio files..."
shopt -s nullglob
WAVS=(temp/audio_slide_*.wav)
shopt -u nullglob

if [ ${#WAVS[@]} -eq 0 ]; then
  echo "❌ No slide wavs found at: $SCRIPT_DIR/temp/audio_slide_*.wav"
  echo "   Run your lecture generation first (creates temp/audio_slide_1.wav etc.)"
  exit 1
fi
echo "✅ Found ${#WAVS[@]} slide wavs."

echo "🔹 Building temp/concat_list.txt..."
(
  cd temp
  ls -1 audio_slide_*.wav | sort -V | sed "s|^|file '|; s|$|'|" > concat_list.txt
)

echo "🔹 Building temp/full_lecture.wav..."
ffmpeg -y -hide_banner -loglevel error \
  -f concat -safe 0 -i temp/concat_list.txt \
  -acodec pcm_s16le -ar 44100 temp/full_lecture.wav
echo "✅ Built: temp/full_lecture.wav"

# -----------------------------
# SadTalker Avatar Generation
# -----------------------------
# ✅ CHANGE AVATAR HERE
FACE_IMG="assets/lady.png"
FACE_IMG_JPG="assets/lady.jpg"

SADTALKER_DIR="SadTalker"
OUT_DIR="output/sadtalker_out"

if [ ! -f "$FACE_IMG" ]; then
  echo "❌ Missing face image: $FACE_IMG"
  exit 1
fi

# Convert PNG -> JPG (SadTalker is sometimes picky with PNG)
echo "🔹 Preparing avatar image..."
python - <<PY
from PIL import Image
img = Image.open("$FACE_IMG").convert("RGB")
img.save("$FACE_IMG_JPG", quality=95)
print("✅ wrote $FACE_IMG_JPG")
PY

if [ ! -d "$SADTALKER_DIR" ]; then
  echo "❌ SadTalker folder not found: $SADTALKER_DIR"
  exit 1
fi

mkdir -p "$OUT_DIR"

echo "🔹 Running SadTalker..."
python "$SADTALKER_DIR/inference.py" \
  --driven_audio temp/full_lecture.wav \
  --source_image "$FACE_IMG_JPG" \
  --result_dir "$OUT_DIR" \
  --preprocess resize \
  --still \
  --enhancer none \
  --background_enhancer none

echo "🔹 Locating newest SadTalker mp4..."
LATEST_MP4="$(find "$OUT_DIR" -type f -name "*.mp4" | sort | tail -n 1)"

if [ -z "${LATEST_MP4:-}" ] || [ ! -f "$LATEST_MP4" ]; then
  echo "❌ SadTalker did not produce an mp4."
  exit 1
fi

cp -f "$LATEST_MP4" output/sadtalker_avatar_raw.mp4
echo "✅ Raw avatar: output/sadtalker_avatar_raw.mp4"

# -----------------------------
# Optional: Enhance (GFPGAN) -> final output/sadtalker_avatar.mp4
# -----------------------------
if [ -f "enhance_avatar_gfpgan.py" ]; then
  echo "🔹 Enhancing with GFPGAN..."
  python enhance_avatar_gfpgan.py output/sadtalker_avatar_raw.mp4 output/sadtalker_avatar.mp4
  echo "✅ Enhanced avatar: output/sadtalker_avatar.mp4"
else
  # fallback to raw if enhancer script not present
  cp -f output/sadtalker_avatar_raw.mp4 output/sadtalker_avatar.mp4
  echo "✅ Final avatar (no enhancement): output/sadtalker_avatar.mp4"
fi
