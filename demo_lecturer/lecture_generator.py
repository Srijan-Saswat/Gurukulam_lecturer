#!/usr/bin/env python3
import os, json, re, logging
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass
import torch
from gtts import gTTS
import subprocess
import librosa
import pysrt
import nltk

# Setup NLTK safely
for pkg in ['punkt', 'punkt_tab']:
    try:
        nltk.download(pkg, quiet=True)
    except:
        pass

@dataclass
class SlideContent:
    slide_number: int
    image_path: str
    narration_text: str
    duration: float = 0.0
    start_time: float = 0.0

@dataclass
class SubtitleSegment:
    text: str
    start_time: float
    end_time: float

class TextPreprocessor:
    """Full text preprocessing for natural TTS output"""
    
    @staticmethod
    def clean_for_tts(text):
        if not text:
            return ""
        
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Smart line break handling - join mid-sentence breaks
        lines = text.split('\n')
        processed = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if processed:
                prev = processed[-1]
                # Only keep separate if previous ended with sentence punctuation
                if prev.endswith(('.', '!', '?', ':')):
                    processed.append(line)
                else:
                    # Join mid-sentence line breaks
                    processed[-1] = prev + ' ' + line
            else:
                processed.append(line)
        text = ' '.join(processed)
        
        # Fix spacing after punctuation
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        text = re.sub(r',([A-Za-z])', r', \1', text)
        
        # Fix concatenated words (camelCase accidents)
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        text = re.sub(r'([a-z])(\d)', r'\1 \2', text)
        text = re.sub(r'(\d)([a-z])', r'\1 \2', text)
        
        # Handle dashes - convert to commas for natural pauses
        text = text.replace('—', ', ')
        text = text.replace('–', ', ')
        text = text.replace(' - ', ', ')
        
        # Expand abbreviations for better pronunciation
        abbreviations = {
            'Dr.': 'Doctor',
            'Mr.': 'Mister', 
            'Mrs.': 'Misses',
            'Ms.': 'Miss',
            'Prof.': 'Professor',
            'vs.': 'versus',
            'etc.': 'etcetera',
            'e.g.': 'for example',
            'i.e.': 'that is',
            'w/': 'with',
            'w/o': 'without',
            'govt.': 'government',
            'dept.': 'department',
            'approx.': 'approximately',
            'min.': 'minutes',
            'max.': 'maximum',
            'avg.': 'average',
        }
        for abbr, full in abbreviations.items():
            text = text.replace(abbr, full)
        
        # Handle ordinals
        text = re.sub(r'\b1st\b', 'first', text, flags=re.IGNORECASE)
        text = re.sub(r'\b2nd\b', 'second', text, flags=re.IGNORECASE)
        text = re.sub(r'\b3rd\b', 'third', text, flags=re.IGNORECASE)
        text = re.sub(r'\b4th\b', 'fourth', text, flags=re.IGNORECASE)
        text = re.sub(r'\b5th\b', 'fifth', text, flags=re.IGNORECASE)
        
        # Handle common tech/acronym pronunciations
        text = re.sub(r'\bAI\b', 'A.I.', text)
        text = re.sub(r'\bAPI\b', 'A.P.I.', text)
        text = re.sub(r'\bUI\b', 'U.I.', text)
        text = re.sub(r'\bURL\b', 'U.R.L.', text)
        text = re.sub(r'\bPDF\b', 'P.D.F.', text)
        text = re.sub(r'\bTTS\b', 'text to speech', text)
        text = re.sub(r'\bLLM\b', 'large language model', text)
        
        # Clean up multiple spaces and periods
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r',{2,}', ',', text)
        
        text = text.strip()
        
        # Ensure proper ending punctuation
        if text and text[-1] not in '.!?':
            text += '.'
        
        return text
    
    @staticmethod
    def split_into_sentences(text):
        try:
            sentences = nltk.sent_tokenize(text)
        except:
            sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

class LectureTTSGenerator:
    def __init__(self, config_path="config.json"):
        self.config = {
            "tts_model": "tts_models/en/ljspeech/vits",
            "output_dir": "output",
            "slides_dir": "slides", 
            "temp_dir": "temp"
        }
        if os.path.exists(config_path):
            with open(config_path) as f:
                self.config.update(json.load(f))
        for d in ["output_dir", "slides_dir", "temp_dir"]:
            Path(self.config[d]).mkdir(exist_ok=True)
        self.tts_model = None
        self.slides = []
        self.subtitles = []
        self.preprocessor = TextPreprocessor()
        logging.basicConfig(level=logging.INFO, format='%(message)s')
        self.logger = logging.getLogger(__name__)
        
    def tts_to_wav(self, text: str, wav_path: str):
        """TTS via gTTS (mp3) -> wav using ffmpeg (keeps rest of pipeline unchanged)."""
        text = text.strip()
        if not text:
            raise ValueError("Empty text for TTS")

        mp3_path = os.path.splitext(wav_path)[0] + ".mp3"

        # gTTS needs internet access
        tts = gTTS(text=text, lang="en")
        tts.save(mp3_path)

        # Convert to wav: 22.05kHz mono to match your earlier pipeline
        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, "-ar", "22050", "-ac", "1", wav_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        

    def initialize_tts(self):
        self.logger.info("Using gTTS (Google Text-to-Speech) + ffmpeg for audio generation")
        self.tts_model = "gTTS"


    def load_slides_content(self, content_file):
        with open(content_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.slides = []
        for i, s in enumerate(data.get("slides", [])):
            raw = s.get("narration_text", s.get("slide_text", ""))
            clean = self.preprocessor.clean_for_tts(raw)
            self.slides.append(SlideContent(i+1, s.get("image_path", ""), clean))
        self.logger.info(f"Loaded {len(self.slides)} slides")

    def generate_audio_segments(self):
        if not self.tts_model:
            self.initialize_tts()
        audio_files = []
        cumulative = 0.0
        for slide in self.slides:
            if not slide.narration_text.strip():
                self.logger.info(f"  ⚠ Slide {slide.slide_number}: no text, skipping")
                continue
            path = os.path.join(self.config["temp_dir"], f"audio_slide_{slide.slide_number}.wav")
            self.logger.info(f"  Generating slide {slide.slide_number}...")
            self.tts_to_wav(slide.narration_text, path)
            audio, sr = librosa.load(path)
            slide.duration = len(audio) / sr
            slide.start_time = cumulative
            cumulative += slide.duration
            audio_files.append(path)
            self.logger.info(f"  ✓ Slide {slide.slide_number}: {slide.duration:.1f}s")
        return audio_files

    def generate_subtitles(self):
        self.subtitles = []
        for slide in self.slides:
            if not slide.narration_text.strip() or slide.duration == 0:
                continue
            sentences = self.preprocessor.split_into_sentences(slide.narration_text)
            if not sentences:
                continue
            dur = slide.duration / len(sentences)
            for i, sent in enumerate(sentences):
                start = slide.start_time + i * dur
                end = slide.start_time + (i + 1) * dur
                self.subtitles.append(SubtitleSegment(sent, start, end))

    def create_srt_file(self, path):
        items = []
        for i, s in enumerate(self.subtitles):
            start = pysrt.SubRipTime.from_ordinal(int(s.start_time * 1000))
            end = pysrt.SubRipTime.from_ordinal(int(s.end_time * 1000))
            items.append(pysrt.SubRipItem(i + 1, start, end, s.text))
        pysrt.SubRipFile(items).save(path, encoding='utf-8')
        self.logger.info(f"Subtitles saved: {path}")

    def generate_lecture(self, content_file):
        self.logger.info("=" * 50)
        self.logger.info(f"Processing: {content_file}")
        self.logger.info("=" * 50)
        self.load_slides_content(content_file)
        if not self.slides:
            raise ValueError("No slides found!")
        audio_files = self.generate_audio_segments()
        if not audio_files:
            raise ValueError("No audio generated!")
        self.generate_subtitles()
        srt = os.path.join(self.config["output_dir"], "lecture_subtitles.srt")
        self.create_srt_file(srt)
        self.logger.info("=" * 50)
        self.logger.info(f"✅ Complete! {len(audio_files)} audio files, {len(self.subtitles)} subtitles")
        return audio_files, srt

def find_latest_json():
    files = list(Path('.').glob('*_lecture.json'))
    return max(files, key=os.path.getmtime) if files else None

if __name__ == "__main__":
    import sys
    f = sys.argv[1] if len(sys.argv) > 1 else find_latest_json()
    if not f:
        print("❌ No *_lecture.json found!")
        sys.exit(1)
    print(f"📄 Processing: {f}")
    gen = LectureTTSGenerator()
    try:
        audio, srt = gen.generate_lecture(str(f))
        print(f"\n✅ Generated {len(audio)} audio files")
        print(f"📁 Audio: {gen.config['temp_dir']}/")
        print(f"📝 Subtitles: {srt}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
