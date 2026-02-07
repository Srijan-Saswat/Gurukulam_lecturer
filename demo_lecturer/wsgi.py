import os
from pathlib import Path

from qa_handler import LectureQAHandler, create_qa_server

# Ollama configuration
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")

# Initialize handler
handler = LectureQAHandler(
    model_name=MODEL_NAME,
    ollama_url=OLLAMA_URL
)

# Load latest lecture JSON automatically
lecture_files = list(Path(".").glob("*_lecture.json"))
if lecture_files:
    lecture_file = max(lecture_files, key=lambda p: p.stat().st_mtime)
    handler.load_lecture_context(str(lecture_file))

# IMPORTANT: expose Flask app for Gunicorn
app = create_qa_server(handler)

