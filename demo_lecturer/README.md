# 🎓 AI Lecture Generator

**Transform static presentations into interactive AI-narrated lectures with Q&A**

Convert PDF slides into engaging narrated lectures with synchronized subtitles and an AI-powered Q&A feature.

---

## Features

- **Automatic Slide Extraction** - Extracts text and images from PDF/PPTX
- **Neural Text-to-Speech** - Natural narration using Coqui TTS (VITS model)
- **Synchronized Subtitles** - Auto-generated with precise timing
- **Interactive Web Player** - HTML5 player with slide navigation
- **AI Q&A System** - Students can pause and ask questions (powered by Ollama/Llama 3.2)
- **100% Local & Free** - No cloud APIs, no costs, full privacy

---

## Quick Start

```bash
# Process a presentation
./new_lecture.sh "YourSlides.pdf"

# Start the lecture player
./start_lecture.sh
```

---

## Installation

### Prerequisites
- macOS or Linux
- Python 3.9+
- 4GB+ RAM

### Step 1: Setup Environment

```bash
# Clone and enter directory
cd ~/Desktop/ai-lecture-generator

# Create virtual environment
python3 -m venv lecture_env
source lecture_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Install Ollama (for Q&A feature)

**macOS:** Download from https://ollama.com/download/mac

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Step 3: Download AI Model

```bash
ollama pull llama3.2:3b
```

### Step 4: Make Scripts Executable

```bash
chmod +x new_lecture.sh start_lecture.sh stop_lecture.sh
```

---

## Usage

### Process a New Presentation
```bash
./new_lecture.sh "presentation.pdf"
```

This will:
1. Extract slides and images
2. Generate AI narration
3. Create synchronized subtitles
4. Build the web player

### Start the Lecture Player
```bash
./start_lecture.sh
```

Opens browser automatically with your lecture.

### Stop All Servers
```bash
./stop_lecture.sh
```

---

## Using the Player

| Action | How |
|--------|-----|
| Play/Pause | Click audio controls |
| Navigate | Use slide buttons |
| Ask Question | Click "✋ Raise Hand" |
| Resume | Click "Resume Lecture" |

---

## Project Structure

```
ai-lecture-generator/
├── lecture_generator.py      # TTS audio generation
├── slide_extractor_with_images.py  # Slide extraction
├── sync_subtitles.py         # Subtitle synchronization
├── generate_player.py        # Web player generator
├── qa_handler.py             # AI Q&A system
├── new_lecture.sh            # One-command processing
├── start_lecture.sh          # Start servers
├── stop_lecture.sh           # Stop servers
├── config.json               # Configuration
└── requirements.txt          # Dependencies
```

### Generated at Runtime (not in repo)
- `slides/` - Extracted slide images
- `temp/` - Audio files
- `output/` - Web player files
- `*_lecture.json` - Slide content data

---

## Configuration

Edit `config.json` to customize:

```json
{
  "tts_model": "tts_models/en/ljspeech/vits",
  "output_dir": "output",
  "slides_dir": "slides",
  "temp_dir": "temp"
}
```

---

## Troubleshooting

### "Ollama not responding"
```bash
# macOS: Open Ollama app (🦙 in menu bar)
# Linux: Run `ollama serve`
```

### "No audio generated"
```bash
python lecture_generator.py YourFile_lecture.json
```

### "Port already in use"
```bash
./stop_lecture.sh
./start_lecture.sh
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| TTS Engine | Coqui TTS (VITS) |
| LLM | Ollama + Llama 3.2 |
| PDF Processing | PyMuPDF |
| Audio Analysis | Librosa |
| Web Server | Flask |
| Frontend | HTML5 + JavaScript |

---

## Future Improvements

- [ ] Voice cloning from reference audio
- [ ] Multiple language support
- [ ] Avatar/talking head integration
- [ ] Export to video (MP4)
- [ ] Mobile-responsive design

---

## Author

**Kylie Noa Pele**  
GurukulamAI Intern  
December 2025
https://www.linkedin.com/in/kyliepele/
criispy@berkeley.edu

---

## Acknowledgments

- [Coqui TTS](https://github.com/coqui-ai/TTS) - Open-source text-to-speech
- [Ollama](https://ollama.com) - Local LLM runtime
- [Meta AI](https://ai.meta.com) - Llama 3.2 model

---

*Made with ❤️ for accessible education*
