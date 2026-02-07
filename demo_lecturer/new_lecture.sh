#!/usr/bin/env bash
# ============================================================
# AI Lecture Generator - Process New Presentation
# Usage: ./new_lecture.sh "YourSlides.pdf"
# ============================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}   🎓 AI Lecture Generator - Processing New Slides${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

cd "$(dirname "$0")"

if [ -z "$1" ]; then
    echo -e "${RED}❌ Error: Please provide a presentation file${NC}"
    echo ""
    echo "Usage: ./new_lecture.sh \"YourSlides.pdf\""
    exit 1
fi

INPUT_FILE="$1"

if [ ! -f "$INPUT_FILE" ]; then
    echo -e "${RED}❌ Error: File not found: $INPUT_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}📄 Processing: $INPUT_FILE${NC}"
echo ""

# source lecture_env/bin/activate

# Step 0: Clear old files
echo -e "${YELLOW}Step 0/5: Clearing old files...${NC}"
rm -f temp/audio_slide_*.wav temp/qa_response.wav 2>/dev/null
rm -f slides/slide_*.png 2>/dev/null
rm -f *_lecture.json 2>/dev/null
rm -f output/subtitle_data_synced.js output/lecture_subtitles.srt 2>/dev/null
echo -e "${GREEN}✅ Cleared${NC}"
echo ""

# Step 1: Extract slides
echo -e "${YELLOW}Step 1/5: Extracting slides...${NC}"
python slide_extractor_with_images.py "$INPUT_FILE"
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to extract slides${NC}"
    exit 1
fi

LECTURE_JSON=$(ls -t *_lecture.json 2>/dev/null | head -1)
if [ -z "$LECTURE_JSON" ]; then
    echo -e "${RED}❌ No lecture JSON created${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Extracted: $LECTURE_JSON${NC}"
echo ""

# Step 2: Generate audio
echo -e "${YELLOW}Step 2/5: Generating audio (may take a few minutes)...${NC}"
python lecture_generator.py "$LECTURE_JSON"
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to generate audio${NC}"
    exit 1
fi

AUDIO_COUNT=$(ls -1 temp/audio_slide_*.wav 2>/dev/null | wc -l | tr -d ' ')
if [ "$AUDIO_COUNT" -eq 0 ]; then
    echo -e "${RED}❌ No audio generated${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Generated $AUDIO_COUNT audio files${NC}"
echo ""

# Step 3: Sync subtitles
echo -e "${YELLOW}Step 3/5: Syncing subtitles...${NC}"
python sync_subtitles.py
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to sync subtitles${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Subtitles synced${NC}"
echo ""

# Step 4: Generate player
echo -e "${YELLOW}Step 4/5: Generating web player...${NC}"
python generate_player.py
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to generate player${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Player generated${NC}"
echo ""

# Step 5: Summary
echo -e "${YELLOW}Step 5/5: Verifying...${NC}"
SLIDES=$(ls -1 slides/slide_*.png 2>/dev/null | wc -l | tr -d ' ')
AUDIO=$(ls -1 temp/audio_slide_*.wav 2>/dev/null | wc -l | tr -d ' ')
echo "   📊 Slides: $SLIDES"
echo "   🔊 Audio: $AUDIO"
echo ""

echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 Done! Run ./start_lecture.sh to view${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
