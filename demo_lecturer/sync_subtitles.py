#!/usr/bin/env python3
"""
Parse existing SRT file and organize subtitle data by slide with proper timing
"""
import re
import json
from pathlib import Path
import librosa

def get_audio_durations():
    """Get actual duration of each audio file"""
    durations = {}
    temp_dir = Path('temp')
    
    for audio_file in sorted(temp_dir.glob('audio_slide_*.wav')):
        slide_num = int(re.search(r'slide_(\d+)', audio_file.name).group(1))
        audio_data, sample_rate = librosa.load(str(audio_file))
        duration = len(audio_data) / sample_rate
        durations[slide_num] = duration
    
    return durations

def parse_srt_file(srt_path, audio_durations):
    """Parse SRT and assign subtitles to correct slides based on timing"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\s*\n', content.strip())
    
    # Calculate cumulative time boundaries for each slide
    slide_boundaries = {}
    cumulative_time = 0
    for slide_num in sorted(audio_durations.keys()):
        slide_boundaries[slide_num] = {
            'start': cumulative_time,
            'end': cumulative_time + audio_durations[slide_num]
        }
        cumulative_time += audio_durations[slide_num]
    
    print("Slide boundaries:")
    for slide_num, bounds in slide_boundaries.items():
        print(f"  Slide {slide_num}: {bounds['start']:.1f}s - {bounds['end']:.1f}s")
    
    # Parse all subtitles
    all_subtitles = []
    for block in blocks:
        if not block.strip():
            continue
        
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        
        timing_match = re.search(
            r'(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})',
            lines[1]
        )
        
        if not timing_match:
            continue
        
        start_h, start_m, start_s, start_ms = map(int, timing_match.groups()[:4])
        end_h, end_m, end_s, end_ms = map(int, timing_match.groups()[4:])
        
        start_time = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000
        end_time = end_h * 3600 + end_m * 60 + end_s + end_ms / 1000
        
        text = ' '.join(lines[2:])
        
        all_subtitles.append({
            'start': start_time,
            'end': end_time,
            'text': text
        })
    
    # Assign subtitles to slides and adjust timing to be relative
    subtitles_by_slide = {}
    
    for sub in all_subtitles:
        # Find which slide this subtitle belongs to
        for slide_num, bounds in slide_boundaries.items():
            if bounds['start'] <= sub['start'] < bounds['end']:
                if slide_num not in subtitles_by_slide:
                    subtitles_by_slide[slide_num] = []
                
                # Make timing relative to slide start
                subtitles_by_slide[slide_num].append({
                    'start': sub['start'] - bounds['start'],
                    'end': sub['end'] - bounds['start'],
                    'text': sub['text']
                })
                break
    
    return subtitles_by_slide

# Get audio durations
try:
    audio_durations = get_audio_durations()
    print(f"Found {len(audio_durations)} audio files")
except Exception as e:
    print(f"Error getting audio durations: {e}")
    exit(1)

# Read and parse SRT
srt_file = 'output/lecture_subtitles.srt'
if Path(srt_file).exists():
    subtitles = parse_srt_file(srt_file, audio_durations)
    
    # Save as JavaScript
    with open('output/subtitle_data_synced.js', 'w') as f:
        f.write('const subtitleData = ')
        f.write(json.dumps(subtitles, indent=2))
        f.write(';')
    
    print(f"\n✅ Parsed subtitle segments:")
    for slide_num, subs in sorted(subtitles.items()):
        print(f"  Slide {slide_num}: {len(subs)} subtitle segments")
        # Show first 3 subtitles as preview
        for sub in subs[:3]:
            print(f"    {sub['start']:.1f}s-{sub['end']:.1f}s: {sub['text'][:50]}...")
    
    print(f"\n📁 Saved to: output/subtitle_data_synced.js")
else:
    print(f"❌ No subtitle file found at {srt_file}")
