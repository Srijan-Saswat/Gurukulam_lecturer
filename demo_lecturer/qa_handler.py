#!/usr/bin/env python3
"""
Interactive Q&A Handler for AI Lecture System
Uses Ollama (FREE local LLM) - No API costs!

Integrates with the existing lecture_generator.py and TTS pipeline.
"""

import json
import requests
import os
from pathlib import Path
from typing import Optional, Tuple
import logging

# Import TTS from the existing setup
try:
    from TTS.api import TTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("Warning: TTS not available. Audio responses will be disabled.")


class LectureQAHandler:
    """Handles question answering during lectures using free local Ollama LLM"""
    
    def __init__(self, model_name: str = "llama3.2:3b", ollama_url: str = "http://localhost:11434"):
        """
        Initialize the Q&A handler with Ollama
        
        Args:
            model_name: Ollama model to use (default: llama3.2:3b)
                       Options: llama3.2:3b, mistral:7b, phi3:mini
            ollama_url: Ollama server URL (default: localhost:11434)
        """
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.tts = None
        self.lecture_context = None
        self.config = self._load_config()
        self._setup_logging()
        
    def _load_config(self) -> dict:
        """Load configuration from project config.json"""
        config_path = Path("config.json")
        default_config = {
            "tts_model": "tts_models/en/ljspeech/vits",
            "temp_dir": "temp",
            "output_dir": "output"
        }
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def _setup_logging(self):
        """Configure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def check_ollama_status(self) -> Tuple[bool, str]:
        """Check if Ollama is running and the model is available"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                
                # Check for exact match or base model match
                model_base = self.model_name.split(':')[0]
                available_bases = [m.split(':')[0] for m in model_names]
                
                if self.model_name in model_names or model_base in available_bases:
                    return True, f"✅ Ollama running with model {self.model_name}"
                else:
                    available = ', '.join(model_names[:5]) if model_names else 'none'
                    return False, f"❌ Model {self.model_name} not found. Available: {available}. Run: ollama pull {self.model_name}"
            return False, "❌ Ollama responded but with an error"
        except requests.exceptions.ConnectionError:
            return False, "❌ Ollama is not running. Start it with: ollama serve"
        except Exception as e:
            return False, f"❌ Error checking Ollama: {str(e)}"
    
    def load_lecture_context(self, lecture_json_path: str) -> str:
        """Load lecture content for context-aware answers"""
        try:
            with open(lecture_json_path, 'r') as f:
                data = json.load(f)
            
            # Build context from all slides
            context = "Lecture content:\n"
            for i, slide in enumerate(data['slides'], 1):
                narration = slide.get('narration_text', slide.get('slide_text', ''))
                context += f"\nSlide {i}: {narration}\n"
            
            self.lecture_context = context
            self.logger.info(f"Loaded lecture context from {lecture_json_path}")
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to load lecture context: {e}")
            return ""
    
    def answer_question(self, question: str, current_slide: Optional[int] = None) -> str:
        """
        Generate answer to student question using Ollama
        
        Args:
            question: The student's question
            current_slide: Optional current slide number for context
            
        Returns:
            str: The AI teacher's answer
        """
        # Check Ollama status first
        status_ok, status_msg = self.check_ollama_status()
        if not status_ok:
            return f"Error: {status_msg}"
        
        # Build prompt with lecture context
        system_prompt = """You are an AI teacher giving a lecture. A student has asked a question.

Instructions:
- Provide a clear, concise answer based on the lecture content
- If the question relates to the lecture material, reference specific slides when helpful
- If the question is outside the lecture scope, politely acknowledge that and provide a brief, helpful response
- Keep answers to 2-3 sentences for natural spoken delivery
- Be friendly and encouraging"""

        lecture_info = self.lecture_context if self.lecture_context else "No lecture content loaded."
        slide_info = f"The student is currently on slide {current_slide}." if current_slide else ""

        user_prompt = f"""{lecture_info}

{slide_info}

Student question: {question}

Please provide a helpful answer:"""

        try:
            self.logger.info(f"Generating answer for: {question[:50]}...")
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": user_prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 256  # Limit response length for TTS
                    }
                },
                timeout=60  # Local models can take a moment on first load
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('response', 'No response generated')
                self.logger.info(f"Generated answer: {answer[:50]}...")
                return answer.strip()
            else:
                return f"Error: Ollama returned status {response.status_code}"
                
        except requests.exceptions.Timeout:
            return "Error: Request timed out. The model may be loading for the first time. Please try again."
        except Exception as e:
            self.logger.error(f"Error generating answer: {e}")
            return f"Error generating answer: {str(e)}"
    
    def generate_spoken_answer(self, answer_text: str, output_path: str = None) -> Optional[str]:
        """
        Convert answer text to speech using the existing TTS setup
        
        Args:
            answer_text: The text answer to convert
            output_path: Where to save the audio file (default: temp/qa_response.wav)
            
        Returns:
            str: Path to the generated audio file, or None if TTS unavailable
        """
        if not TTS_AVAILABLE:
            self.logger.warning("TTS not available, skipping audio generation")
            return None
            
        if output_path is None:
            output_path = os.path.join(self.config.get("temp_dir", "temp"), "qa_response.wav")
        
        try:
            if self.tts is None:
                self.logger.info("Initializing TTS for Q&A responses...")
                # Use VITS model for better quality (same as main lecture)
                tts_model = self.config.get("tts_model", "tts_models/en/ljspeech/vits")
                self.tts = TTS(model_name=tts_model, progress_bar=False)
            
            self.tts.tts_to_file(text=answer_text, file_path=output_path)
            self.logger.info(f"Generated audio response: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate audio: {e}")
            return None
    
    def ask_and_respond(self, question: str, current_slide: Optional[int] = None, 
                        generate_audio: bool = True) -> dict:
        """
        Complete Q&A flow: get answer and optionally generate audio
        
        Args:
            question: The student's question
            current_slide: Current slide number
            generate_audio: Whether to generate TTS audio
            
        Returns:
            dict with 'answer' (str) and 'audio_path' (str or None)
        """
        answer = self.answer_question(question, current_slide)
        
        audio_path = None
        if generate_audio and not answer.startswith("Error:"):
            audio_path = self.generate_spoken_answer(answer)
        
        return {
            "answer": answer,
            "audio_path": audio_path
        }


# =============================================================================
# Flask API Server for Web Player Integration
# =============================================================================

def create_qa_server(handler: LectureQAHandler, port: int = 5001):
    """Create a simple Flask server for the web player to call"""
    try:
        from flask import Flask, request, jsonify, send_file
        from flask_cors import CORS
    except ImportError:
        print("Flask not installed. Run: pip install flask flask-cors")
        return None
    
    app = Flask(__name__)
    CORS(app)  # Allow cross-origin requests from the web player
    
    @app.route('/api/ask', methods=['POST'])
    def ask_question():
        data = request.json
        question = data.get('question', '')
        current_slide = data.get('current_slide')
        generate_audio = data.get('generate_audio', True)
        
        if not question:
            return jsonify({"error": "No question provided"}), 400
        
        result = handler.ask_and_respond(question, current_slide, generate_audio)
        
        response = {
            "answer": result["answer"],
            "has_audio": result["audio_path"] is not None
        }
        
        return jsonify(response)
    
    @app.route('/api/audio', methods=['GET'])
    def get_audio():
        audio_path = os.path.join(handler.config.get("temp_dir", "temp"), "qa_response.wav")
        if os.path.exists(audio_path):
            return send_file(audio_path, mimetype='audio/wav')
        return jsonify({"error": "No audio available"}), 404
    
    @app.route('/api/status', methods=['GET'])
    def get_status():
        status_ok, status_msg = handler.check_ollama_status()
        return jsonify({
            "ollama_running": status_ok,
            "message": status_msg,
            "model": handler.model_name
        })
    
    return app


# =============================================================================
# CLI Testing Functions
# =============================================================================

def test_ollama_connection():
    """Test that Ollama is properly set up"""
    print("=" * 60)
    print("Testing Ollama Connection...")
    print("=" * 60)
    
    handler = LectureQAHandler()
    status_ok, status_msg = handler.check_ollama_status()
    print(status_msg)
    
    if not status_ok:
        print("\n📋 To fix this:")
        print("1. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh")
        print("2. Start Ollama: ollama serve")
        print("3. Pull a model: ollama pull llama3.2:3b")
    
    return status_ok


def test_with_lecture():
    """Test Q&A with actual lecture content"""
    print("\n" + "=" * 60)
    print("Testing Q&A with Lecture Content...")
    print("=" * 60)
    
    handler = LectureQAHandler()
    
    # Try to load the most recent lecture JSON
    lecture_files = list(Path('.').glob('*_lecture.json'))
    if lecture_files:
        lecture_file = max(lecture_files, key=os.path.getmtime)
        print(f"Loading lecture: {lecture_file}")
        handler.load_lecture_context(str(lecture_file))
    else:
        print("No lecture JSON found, using test content...")
        handler.lecture_context = """Lecture content:
        
Slide 1: Introduction to Machine Learning. Machine learning is a subset of AI.

Slide 2: Types of Machine Learning: supervised, unsupervised, and reinforcement learning.

Slide 3: Applications include image recognition, natural language processing, and robotics."""
    
    # Test question
    question = "What are the types of machine learning?"
    print(f"\nQuestion: {question}")
    print("\nGenerating answer...")
    
    answer = handler.answer_question(question, current_slide=2)
    print(f"\nAI Teacher: {answer}")
    
    return answer


def interactive_mode():
    """Interactive Q&A testing"""
    print("\n" + "=" * 60)
    print("Interactive Q&A Mode")
    print("Type 'quit' to exit, 'audio' to toggle audio responses")
    print("=" * 60)
    
    handler = LectureQAHandler()
    generate_audio = False  # Start with audio off for faster testing
    
    # Load lecture content
    lecture_files = list(Path('.').glob('*_lecture.json'))
    if lecture_files:
        lecture_file = max(lecture_files, key=os.path.getmtime)
        handler.load_lecture_context(str(lecture_file))
        print(f"✅ Loaded: {lecture_file}")
    
    while True:
        question = input("\n❓ Your question: ").strip()
        
        if question.lower() == 'quit':
            print("Goodbye!")
            break
        elif question.lower() == 'audio':
            generate_audio = not generate_audio
            print(f"Audio responses: {'ON' if generate_audio else 'OFF'}")
            continue
        elif not question:
            continue
        
        print("🤔 Thinking...")
        result = handler.ask_and_respond(question, generate_audio=generate_audio)
        print(f"\n🎓 AI Teacher: {result['answer']}")
        
        if result['audio_path']:
            print(f"🔊 Audio saved to: {result['audio_path']}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--interactive":
            interactive_mode()
        elif sys.argv[1] == "--server":
            # Start the API server
            handler = LectureQAHandler()
            
            # Load lecture content
            lecture_files = list(Path('.').glob('*_lecture.json'))
            if lecture_files:
                lecture_file = max(lecture_files, key=os.path.getmtime)
                handler.load_lecture_context(str(lecture_file))
            
            app = create_qa_server(handler)
            if app:
                print("Starting Q&A API server on http://localhost:5001")
                app.run(host='0.0.0.0', port=5001, debug=False)
        elif sys.argv[1] == "--test":
            if test_ollama_connection():
                test_with_lecture()
    else:
        # Default: run connection test
        print("AI Lecture Q&A Handler")
        print("=" * 60)
        print("Usage:")
        print("  python qa_handler.py           # Test Ollama connection")
        print("  python qa_handler.py --test    # Test with lecture content")
        print("  python qa_handler.py --interactive  # Interactive Q&A mode")
        print("  python qa_handler.py --server  # Start API server for web player")
        print("=" * 60)
        test_ollama_connection()
