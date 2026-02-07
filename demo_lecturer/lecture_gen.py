#!/usr/bin/env python3
"""
AI Lecture Generator - Generates TTS audio and subtitles
Improved text preprocessing for natural speech flow
"""

import os
import json
import re
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass
import logging

import torch
from TTS.api import TTS
import librosa
import pysrt

# Handle NLTK imports with proper error handling
import nltk

def setup_nltk():
    """Download required NLTK data if not present"""
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        print("Downloading NLTK punkt tokenizer...")
        nltk.download('punkt', quiet=True)
    
    # Try punkt_tab but don't fail if it doesn't exist
    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        try:
            nltk.download('punkt_tab', quiet=True)
        except:
            pass  # punkt_tab may not exist in all NLTK versions

setup_nltk()


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
    """Preprocess text for natural TTS output"""
    
    @staticmethod
    def clean_for_tts(text: str) -> str:
        """
        Clean text to prevent unnatural pauses in TTS.
        Removes mid-sentence line breaks while preserving sentence structure.
        """
        if not text:
            return ""
        
        # Step 1: Normalize whitespace and line breaks
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Step 2: Handle line breaks intelligently
        lines = text.split('\n')
        processed_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            if processed_lines:
                prev_line = processed_lines[-1]
                # If previous line ended with sentence punctuation, keep separate
                if prev_line.endswith(('.', '!', '?', ':')):
                    processed_lines.append(line)
                else:
                    # Join with previous line (mid-sentence break)
                    processed_lines[-1] = prev_line + ' ' + line
            else:
                processed_lines.append(line)
        
        text = ' '.join(processed_lines)
        
        # Step 3: Fix common spacing issues
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        text = re.sub(r'\,([A-Za-z])', r', \1', text)
        
        # Step 4: Fix concatenated words
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        # Step 5: Normalize multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Step 6: Handle dashes - convert to commas for natural pauses
        text = text.replace('—', ', ')
        text = text.replace('–', ', ')
        
        # Step 7: Expand common abbreviations
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
        }
        for abbr, full in abbreviations.items():
            text = text.replace(abbr, full)
        
        # Step 8: Handle ordinals
        text = re.sub(r'\b1st\b', 'first', text, flags=re.IGNORECASE)
        text = re.sub(r'\b2nd\b', 'second', text, flags=re.IGNORECASE)
        text = re.sub(r'\b3rd\b', 'third', text, flags=re.IGNORECASE)
        
        # Step 9: Final cleanup
        text = text.strip()
        if text and text[-1] not in '.!?':
            text += '.'
        
        return text
    
    @staticmethod
    def split_into_sentences(text: str) -> List[str]:
        """Split text into sentences for subtitle timing"""
        try:
            sentences = nltk.sent_tokenize(text)
        except Exception:
            # Fallback: split on sentence-ending punctuation
            sentences = re.split(r'(?<=[.!?])\s+', text)
        
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences


class LectureTTSGenerator:
    """Main class for generating lecture audio with TTS"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.tts_model = None
        self.slides: List[SlideContent] = []
        self.subtitles: List[SubtitleSegment] = []
        self.preprocessor = TextPreprocessor()
        self._setup_logging()
        
    def _load_config(self, config_path: str) -> dict:
        default_config = {
            "tts_model": "tts_models/en/ljspeech/vits",
            "output_dir": "output",
            "slides_dir": "slides",
            "temp_dir": "temp",
        }
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        for dir_key in ["output_dir", "slides_dir", "temp_dir"]:
            Path(default_config[dir_key]).mkdir(parents=True, exist_ok=True)
        
        return default_config
    
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('lecture_generator.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def initialize_tts(self):
        """Initialize TTS model"""
        self.logger.info(f"Initializing TTS model: {self.config['tts_model']}")
        self.tts_model = TTS(model_name=self.config["tts_model"], progress_bar=False)
        self.logger.info("TTS model loaded successfully")
    
    def load_slides_content(self, content_file: str):
        """Load slides and narration content from file"""
        with open(content_file, 'r', encoding='utf-8') as f:
            content_data = json.load(f)
        
        self.slides = []
        for i, slide_data in enumerate(content_data.get("slides", [])):
            raw_narration = slide_data.get("narration_text", slide_data.get("slide_text", ""))
            
            # Preprocess for natural TTS
            clean_narration = self.preprocessor.clean_for_tts(raw_narration)
            
            slide = SlideContent(
                slide_number=i + 1,
                image_path=slide_data.get("image_path", f"slides/slide_{i+1}.png"),
                narration_text=clean_narration
            )
            self.slides.append(slide)
        
        self.logger.info(f"Loaded {len(self.slides)} slides from {content_file}")
    
    def generate_audio_segments(self) -> List[str]:
        """Generate TTS audio for each slide"""
        if not self.tts_model:
            self.initialize_tts()
        
        audio_files = []
        cumulative_time = 0.0
        
        for slide in self.slides:
            self.logger.info(f"Generating audio for slide {slide.slide_number}/{len(self.slides)}")
            
            if not slide.narration_text.strip():
                self.logger.warning(f"  Slide {slide.slide_number} has no narration, skipping")
                continue
            
            audio_path = os.path.join(
                self.config["temp_dir"],
                f"audio_slide_{slide.slide_number}.wav"
            )
            
            self.tts_model.tts_to_file(
                text=slide.narration_text,
                file_path=audio_path
            )
            
            audio_data, sample_rate = librosa.load(audio_path)
            slide.duration = len(audio_data) / sample_rate
            slide.start_time = cumulative_time
            cumulative_time += slide.duration
            
            audio_files.append(audio_path)
            self.logger.info(f"  ✓ Slide {slide.slide_number}: {slide.duration:.1f}s")
        
        return audio_files
    
    def generate_subtitles(self):
        """Generate subtitle segments with timing"""
        self.subtitles = []
        
        for slide in self.slides:
            if not slide.narration_text.strip() or slide.duration == 0:
                continue
            
            sentences = self.preprocessor.split_into_sentences(slide.narration_text)
            
            if not sentences:
                continue
            
            sentence_duration = slide.duration / len(sentences)
            
            for i, sentence in enumerate(sentences):
                start_time = slide.start_time + (i * sentence_duration)
                end_time = start_time + sentence_duration
                
                self.subtitles.append(SubtitleSegment(
                    text=sentence.strip(),
                    start_time=start_time,
                    end_time=end_time
                ))
    
    def create_srt_file(self, output_path: str):
        """Create SRT subtitle file"""
        srt_items = []
        
        for i, subtitle in enumerate(self.subtitles, 1):
            start_time = pysrt.SubRipTime.from_ordinal(int(subtitle.start_time * 1000))
            end_time = pysrt.SubRipTime.from_ordinal(int(subtitle.end_time * 1000))
            
            srt_items.append(pysrt.SubRipItem(
                index=i,
                start=start_time,
                end=end_time,
                text=subtitle.text
            ))
        
        pysrt.SubRipFile(srt_items).save(output_path, encoding='utf-8')
        self.logger.info(f"Subtitles saved to {output_path}")
    
    def generate_lecture(self, content_file: str) -> Tuple[List[str], str]:
        """Main method to generate complete lecture"""
        self.logger.info("=" * 60)
        self.logger.info(f"Processing: {content_file}")
        self.logger.info("=" * 60)
        
        self.load_slides_content(content_file)
        
        if not self.slides:
            raise ValueError("No slides found in content file")
        
        audio_files = self.generate_audio_segments()
        
        if not audio_files:
            raise ValueError("No audio files were generated")
        
        self.generate_subtitles()
        
        srt_path = os.path.join(self.config["output_dir"], "lecture_subtitles.srt")
        self.create_srt_file(srt_path)
        
        self.logger.info("=" * 60)
        self.logger.info(f"✅ Lecture generation complete!")
        self.logger.info(f"   Audio files: {len(audio_files)}")
        self.logger.info(f"   Subtitle segments: {len(self.subtitles)}")
        self.logger.info("=" * 60)
        
        return audio_files, srt_path


def find_latest_lecture_json():
    """Find the most recently modified *_lecture.json file"""
    lecture_files = list(Path('.').glob('*_lecture.json'))
    return max(lecture_files, key=os.path.getmtime) if lecture_files else None


if __name__ == "__main__":
    import sys
    
    content_file = sys.argv[1] if len(sys.argv) > 1 else find_latest_lecture_json()
    
    if not content_file:
        print("❌ No *_lecture.json found!")
        print("   Run slide_extractor_with_images.py first.")
        sys.exit(1)
    
    print(f"📄 Processing: {content_file}")
    
    generator = LectureTTSGenerator()
    
    try:
        audio_files, srt_path = generator.generate_lecture(str(content_file))
        print(f"\n✅ Generated {len(audio_files)} audio files")
        print(f"📁 Audio saved to: {generator.config['temp_dir']}/")
        print(f"📝 Subtitles saved to: {srt_path}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
