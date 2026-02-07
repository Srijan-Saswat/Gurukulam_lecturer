#!/usr/bin/env python3
"""
Slide Extractor - Improved text joining for natural TTS
"""
from pathlib import Path
import json
import fitz  # PyMuPDF
import re

class SlideExtractorWithImages:
    def __init__(self, output_image_dir='slides'):
        self.output_image_dir = Path(output_image_dir)
        self.output_image_dir.mkdir(exist_ok=True)
        
    def process_file(self, file_path: str):
        file_path = Path(file_path)
        if file_path.suffix.lower() == '.pdf':
            return self._process_pdf(file_path)
        elif file_path.suffix.lower() in ['.pptx', '.ppt']:
            return self._process_powerpoint(file_path)
        else:
            raise ValueError(f"Unsupported: {file_path.suffix}")
    
    def _process_pdf(self, pdf_path: Path):
        doc = fitz.open(pdf_path)
        slides_data = []
        
        for old_img in self.output_image_dir.glob("slide_*.png"):
            old_img.unlink()
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            text_blocks = []
            for block in blocks:
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        line_text = ""
                        line_size = 12
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                line_text += text + " "
                                line_size = span.get("size", 12)
                        line_text = line_text.strip()
                        if line_text:
                            bbox = line["bbox"]
                            text_blocks.append({
                                'text': line_text,
                                'x': bbox[0],
                                'y': bbox[1],
                                'size': line_size,
                                'height': bbox[3] - bbox[1]
                            })
            
            # Sort by position
            if text_blocks:
                avg_size = sum(b['size'] for b in text_blocks) / len(text_blocks)
                headers = sorted([b for b in text_blocks if b['size'] > avg_size * 1.1], key=lambda b: b['y'])
                body = sorted([b for b in text_blocks if b['size'] <= avg_size * 1.1], key=lambda b: (b['x'] // 150, b['y']))
                sorted_blocks = headers + body
            else:
                sorted_blocks = []
            
            # Process with IMPROVED joining
            slide_text = self._join_text_naturally(sorted_blocks)
            
            # Save image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image_path = self.output_image_dir / f"slide_{page_num + 1}.png"
            pix.save(str(image_path))
            
            narration = self._create_narration(slide_text, page_num + 1)
            slides_data.append({
                "image_path": f"slides/slide_{page_num + 1}.png",
                "slide_text": slide_text,
                "narration_text": narration
            })
            print(f"  Slide {page_num + 1}: {len(slide_text)} chars")
        
        doc.close()
        
        json_file = f"{pdf_path.stem}_lecture.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({"slides": slides_data}, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Extracted {len(slides_data)} slides")
        print(f"📁 Images: {self.output_image_dir}")
        print(f"📝 JSON: {json_file}")
        return json_file
    
    def _join_text_naturally(self, text_blocks):
        """
        Join text blocks into natural flowing sentences.
        KEY FIX: Don't add periods between lines that are part of the same title/header.
        """
        if not text_blocks:
            return ""
        
        # First, clean all text and collect
        cleaned_texts = []
        for block in text_blocks:
            text = self._remove_bullets(block['text'])
            if text:
                cleaned_texts.append({
                    'text': text,
                    'size': block['size'],
                    'y': block['y']
                })
        
        if not cleaned_texts:
            return ""
        
        # Group text by font size (headers vs body)
        avg_size = sum(t['size'] for t in cleaned_texts) / len(cleaned_texts)
        
        result_parts = []
        current_group = []
        current_is_header = None
        
        for item in cleaned_texts:
            is_header = item['size'] > avg_size * 1.1
            text = item['text']
            
            # Check if text ends with sentence punctuation
            ends_sentence = text.rstrip().endswith(('.', '!', '?', ':'))
            
            if current_is_header is None:
                current_is_header = is_header
                current_group.append(text)
            elif is_header == current_is_header and not ends_sentence:
                # Same type, no sentence end - join with space (NOT period)
                current_group.append(text)
            else:
                # Different type or sentence ended - flush current group
                joined = ' '.join(current_group)
                if joined and not joined.rstrip().endswith(('.', '!', '?', ':')):
                    joined += '.'
                result_parts.append(joined)
                current_group = [text]
                current_is_header = is_header
        
        # Don't forget last group
        if current_group:
            joined = ' '.join(current_group)
            if joined and not joined.rstrip().endswith(('.', '!', '?', ':')):
                joined += '.'
            result_parts.append(joined)
        
        # Join all parts
        result = ' '.join(result_parts)
        return self._fix_spacing(result)
    
    def _remove_bullets(self, text):
        bullets = '•◦▪▫●○■□◆◇⬤⚫►▸▹⦿⦾⬛⬜🔘⚪⭕🔴🟠🟡🟢🔵🟣◯'
        for b in bullets:
            text = text.replace(b, '')
        text = re.sub(r'^[-–—*]\s*', '', text)
        text = re.sub(r'^\d+[.)]\s*', '', text)
        return text.strip()
    
    def _fix_spacing(self, text):
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        text = re.sub(r',([A-Za-z])', r', \1', text)
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r'\.\s*,', ',', text)  # Fix ". ," -> ","
        return text.strip()
    
    def _process_powerpoint(self, pptx_path: Path):
        import subprocess
        pdf_path = pptx_path.with_suffix('.pdf')
        subprocess.run([
            'soffice', '--headless', '--convert-to', 'pdf',
            '--outdir', str(pptx_path.parent), str(pptx_path)
        ], capture_output=True, timeout=60)
        if pdf_path.exists():
            return self._process_pdf(pdf_path)
        raise Exception("PDF conversion failed")
    
    def _create_narration(self, slide_text: str, slide_number: int) -> str:
        if not slide_text.strip():
            return f"This is slide {slide_number}."
        narration = slide_text.strip()
        if not narration.endswith(('.', '!', '?')):
            narration += '.'
        if slide_number == 1:
            return f"Welcome to today's presentation. {narration}"
        return f"Moving on to slide {slide_number}. {narration}"

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python slide_extractor_with_images.py presentation.pdf")
        sys.exit(1)
    extractor = SlideExtractorWithImages()
    extractor.process_file(sys.argv[1])
