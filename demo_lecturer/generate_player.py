#!/usr/bin/env python3
"""
AI Lecture Player Generator - With Interactive Q&A Feature
Generates HTML player with synchronized subtitles AND Q&A capability
"""

import json
from pathlib import Path
import os
import time

# Get timestamp for cache busting
cache_buster = str(int(time.time()))

# Find the most recent lecture JSON
lecture_files = list(Path(".").glob("*_lecture.json"))
if not lecture_files:
    print("❌ No lecture JSON found!")
    raise SystemExit(1)

lecture_file = max(lecture_files, key=os.path.getmtime)
print(f"📄 Using: {lecture_file}")

with open(lecture_file, "r") as f:
    data = json.load(f)

slides = data["slides"]
num_slides = len(slides)

# Load subtitle data if available
subtitle_js = "const subtitleData = {};"
subtitle_file = Path("output/subtitle_data_synced.js")
if subtitle_file.exists():
    with open(subtitle_file, "r") as f:
        subtitle_js = f.read()
    print("✅ Loaded synchronized subtitle data")
else:
    print("⚠️  No subtitle data found, using empty subtitles")

# Build the lecture context for inline Q&A (fallback if server not running)
lecture_context_js = "const lectureContext = " + json.dumps(
    [
        {"slide": i + 1, "text": slide.get("narration_text", slide.get("slide_text", ""))}
        for i, slide in enumerate(slides)
    ]
) + ";"

# Logo paths (HTML is inside output/, so use ../ to reach project root assets/)
EROS_LOGO_SRC = "../assets/eros_now.png"
IMMERSO_LOGO_SRC = "../assets/immerso_ai.jpg"

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AI Lecture Player with Q&A</title>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        h1 {{
            text-align: center;
            color: #667eea;
            margin-bottom: 30px;
        }}

        /* ===== Header with logos (UPDATED) ===== */
        .title-row {{
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            align-items: center;
            margin-bottom: 30px; /* matches previous h1 margin-bottom */

            /* pull outward so logos sit near container corners (but still inside white frame) */
            margin-left: -16px;
            margin-right: -16px;
        }}
        .title-row h1 {{
            margin: 0; /* we moved spacing to .title-row */
            text-align: center;
        }}
        .brand-logo {{
            height: 68px; /* enlarged */
            width: auto;
            object-fit: contain;
        }}
        .logo-left {{
            justify-self: start;
        }}
        .logo-right {{
            justify-self: end;
        }}
        @media (max-width: 640px) {{
            .title-row {{
                margin-left: 0;
                margin-right: 0;
            }}
            .brand-logo {{
                height: 44px;
            }}
        }}
        /* ===== End Header with logos ===== */

        .success-banner {{
            background: #4caf50;
            color: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 20px;
        }}
        .presentation-view {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 30px;
            margin: 30px 0;
        }}
        .slide-display {{
            background: #f8f9ff;
            border-radius: 12px;
            padding: 20px;
            border: 2px solid #667eea;
        }}
        .slide-display img {{
            width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .controls-panel {{
            background: #f8f9ff;
            border-radius: 12px;
            padding: 20px;
        }}

        /* Avatar panel (SadTalker video) */
        .avatar-panel {{
            width: 100%;
            max-width: 320px;
            margin: 0 auto 16px auto;
            background: #111;
            border-radius: 12px;
            overflow: hidden;
            border: 2px solid #222;
        }}
        .avatar-panel video {{
            width: 100%;
            height: auto;
            display: block;
        }}

        .subtitle-box {{
            background: #1a1a1a;
            color: white;
            padding: 20px;
            border-radius: 8px;
            min-height: 80px;
            margin: 20px 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1em;
            text-align: center;
            line-height: 1.5;
        }}
        audio {{
            width: 100%;
            margin: 20px 0;
        }}
        .slide-nav {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
            gap: 10px;
            margin-top: 20px;
        }}
        .slide-btn {{
            padding: 12px;
            border: 2px solid #667eea;
            background: white;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }}
        .slide-btn:hover {{
            background: #f0f2ff;
        }}
        .slide-btn.active {{
            background: #667eea;
            color: white;
        }}

        /* Q&A Section Styles */
        .qa-section {{
            margin-top: 30px;
            padding-top: 30px;
            border-top: 2px solid #e0e0e0;
        }}
        .qa-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
        }}
        .qa-header h2 {{
            color: #667eea;
            margin: 0;
        }}
        .raise-hand-btn {{
            background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 25px;
            font-size: 1.1em;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(255, 152, 0, 0.4);
        }}
        .raise-hand-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(255, 152, 0, 0.5);
        }}
        .raise-hand-btn.active {{
            background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
            box-shadow: 0 4px 15px rgba(244, 67, 54, 0.4);
        }}
        .raise-hand-btn .emoji {{
            font-size: 1.3em;
        }}

        .qa-panel {{
            display: none;
            background: #f8f9ff;
            border-radius: 12px;
            padding: 20px;
            margin-top: 20px;
            border: 2px solid #667eea;
        }}
        .qa-panel.visible {{
            display: block;
            animation: slideIn 0.3s ease;
        }}
        @keyframes slideIn {{
            from {{ opacity: 0; transform: translateY(-10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .qa-input-group {{
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }}
        .qa-input {{
            flex: 1;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.3s;
        }}
        .qa-input:focus {{
            outline: none;
            border-color: #667eea;
        }}
        .qa-submit {{
            background: #667eea;
            color: white;
            border: none;
            padding: 15px 25px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }}
        .qa-submit:hover {{
            background: #5568d3;
        }}
        .qa-submit:disabled {{
            background: #ccc;
            cursor: not-allowed;
        }}

        .qa-response {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-top: 15px;
            border-left: 4px solid #667eea;
        }}
        .qa-response.loading {{
            color: #666;
            font-style: italic;
        }}
        .qa-response .teacher-label {{
            color: #667eea;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        .qa-response .answer-text {{
            line-height: 1.6;
        }}
        .qa-response audio {{
            margin-top: 15px;
        }}

        .qa-status {{
            font-size: 0.9em;
            color: #666;
            margin-top: 10px;
        }}
        .qa-status.error {{
            color: #f44336;
        }}
        .qa-status.success {{
            color: #4caf50;
        }}

        .resume-btn {{
            background: #4caf50;
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 15px;
            display: none;
        }}
        .resume-btn.visible {{
            display: inline-block;
        }}

        /* Paused state indicator */
        .paused-indicator {{
            display: none;
            background: #ff9800;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            text-align: center;
            margin: 10px 0;
            font-weight: 600;
        }}
        .paused-indicator.visible {{
            display: block;
        }}
    </style>
</head>
<body>
    <div class="container">

        <!-- Title row with logos (CHANGED from single h1 ONLY) -->
        <div class="title-row">
            <img class="brand-logo logo-left" src="{EROS_LOGO_SRC}?v={cache_buster}" alt="Eros Now Logo">  
            <h1>🎓 Gurukulam AI</h1>
            <img class="brand-logo logo-right" src="{IMMERSO_LOGO_SRC}?v={cache_buster}" alt="Immerso.ai Logo">
        </div>

        <div class="success-banner">
            ✅ "{lecture_file.stem.replace('_lecture', '')}" - {num_slides} slides with synchronized subtitles & interactive Q&A
        </div>

        <div class="presentation-view">
            <div class="slide-display">
                <h2 id="slideTitle">Slide 1</h2>
                <img id="slideImage" src="../slides/slide_1.png?v={cache_buster}" alt="Slide 1">
                <div class="paused-indicator" id="pausedIndicator">
                    ⏸️ Lecture paused - Ask your question below
                </div>
            </div>

            <div class="controls-panel">
                <div class="avatar-panel">
                    <video
                        id="avatarVideo"
                        src="avatar_slide_01.mp4?v={cache_buster}"
                        muted
                        playsinline
                        preload="auto"
                        style="pointer-events:none;background:#000;border-radius:10px;width:100%;"
                    ></video>
                </div>

                <h3>👩‍🏫 Avatar</h3>
                <hr style="margin:16px 0;">

                <h3>🔊 Audio Controls</h3>
                <audio id="mainAudio" controls preload="none">
                    <source src="../temp/audio_slide_1.wav?v={cache_buster}" type="audio/wav">
                </audio>

                <div class="subtitle-box" id="subtitles">
                    Press play to start the lecture
                </div>

                <div class="slide-nav" id="slideNav">
"""

for i in range(1, num_slides + 1):
    active = "active" if i == 1 else ""
    html += f'                    <button class="slide-btn {active}" onclick="loadSlide({i})">Slide {i}</button>\n'

html += f"""                </div>
            </div>
        </div>

        <!-- Q&A Section -->
        <div class="qa-section">
            <div class="qa-header">
                <h2>💬 Have a Question?</h2>
                <button class="raise-hand-btn" id="raiseHandBtn" onclick="toggleQA()">
                    <span class="emoji">✋</span>
                    <span id="raiseHandText">Raise Hand</span>
                </button>
            </div>

            <div class="qa-panel" id="qaPanel">
                <div class="qa-input-group">
                    <input type="text" class="qa-input" id="questionInput"
                           placeholder="Type your question here..."
                           onkeypress="if(event.key==='Enter') askQuestion()">
                    <button class="qa-submit" id="askBtn" onclick="askQuestion()">Ask</button>
                </div>

                <div class="qa-response" id="qaResponse" style="display: none;">
                    <div class="teacher-label">🎓 AI Teacher:</div>
                    <div class="answer-text" id="answerText"></div>
                    <audio id="answerAudio" controls style="display: none;"></audio>
                </div>

                <div class="qa-status" id="qaStatus"></div>

                <button class="resume-btn" id="resumeBtn" onclick="resumeLecture()">
                    ▶️ I'm satisfied - Resume Lecture
                </button>
            </div>
        </div>
    </div>

    <script>
        // Subtitle data
        {subtitle_js}

        // Lecture context for Q&A
        {lecture_context_js}

        const CACHE_BUSTER = '{cache_buster}';
        const QA_SERVER = 'http://localhost:5001';  // Q&A API server

        let currentSlide = 1;
        let isQAMode = false;
        let wasPlaying = false;

        // =====================
        // Avatar + Audio Sync
        // =====================
        const avatar = document.getElementById("avatarVideo");
        const audioEl = document.getElementById("mainAudio");

        function waitCanPlay(el) {{
            return new Promise((resolve) => {{
                if (!el) return resolve();
                if (el.readyState >= 3) return resolve(); // HAVE_FUTURE_DATA+
                const done = () => {{
                    el.removeEventListener("canplay", done);
                    el.removeEventListener("canplaythrough", done);
                    resolve();
                }};
                el.addEventListener("canplay", done, {{ once: true }});
                el.addEventListener("canplaythrough", done, {{ once: true }});
            }});
        }}

        function setAvatarForSlide(slideIndex) {{
            const v = document.getElementById("avatarVideo");
            if (!v) return;

            const s = String(slideIndex).padStart(2, '0');
            v.pause();
            v.src = `avatar_slide_${{s}}.mp4?v=${{Date.now()}}`;
            v.load();
            v.currentTime = 0;
        }}

        // When user plays/pauses audio manually, follow it (best-effort).
        if (avatar && audioEl) {{
            audioEl.addEventListener("play", async function () {{
                // try to align + start video once it can play
                await waitCanPlay(avatar);
                avatar.currentTime = audioEl.currentTime;
                avatar.play().catch(()=>{{}});
            }});
            audioEl.addEventListener("pause", function () {{
                avatar.pause();
            }});
            audioEl.addEventListener("ended", function () {{
                avatar.pause();
            }});

            // drift correction (keeps lips tight)
            audioEl.addEventListener("timeupdate", function () {{
                if (!avatar || avatar.paused) return;
                const drift = Math.abs(avatar.currentTime - audioEl.currentTime);
                if (drift > 0.08) {{
                    avatar.currentTime = audioEl.currentTime;
                }}
            }});
        }}

        // Hide avatar panel if mp4 missing / fails to load
        const avatarPanel = document.querySelector(".avatar-panel");
        if (avatar && avatarPanel) {{
            avatar.addEventListener("error", function () {{
                avatarPanel.style.display = "none";
            }});
        }}

        // =====================
        // Slide Navigation
        // =====================
        async function loadSlide(slideNum, autoPlay = false) {{
            currentSlide = slideNum;

            document.querySelectorAll('.slide-btn').forEach((btn, i) => {{
                btn.classList.toggle('active', i + 1 === slideNum);
            }});

            document.getElementById('slideTitle').textContent = `Slide ${{slideNum}}`;
            document.getElementById('slideImage').src = `../slides/slide_${{slideNum}}.png?v=${{CACHE_BUSTER}}`;

            const audio = document.getElementById('mainAudio');
            const v = document.getElementById('avatarVideo');

            // Load avatar FIRST (so it buffers earlier than audio)
            setAvatarForSlide(slideNum);

            // Load audio
            audio.src = `../temp/audio_slide_${{slideNum}}.wav?v=${{CACHE_BUSTER}}`;
            audio.load();

            document.getElementById('subtitles').textContent = 'Press play to hear narration';

            if (autoPlay) {{
                // Wait for both to be ready, then start together.
                await Promise.all([waitCanPlay(audio), waitCanPlay(v)]);

                audio.currentTime = 0;
                if (v) v.currentTime = 0;

                // Play audio first, then align+play avatar.
                await audio.play();
                if (v) {{
                    v.currentTime = audio.currentTime;
                    await v.play().catch(()=>{{}});
                }}
            }}
        }}

        // =====================
        // Subtitle Updates
        // =====================
        document.getElementById('mainAudio').addEventListener('timeupdate', function() {{
            const currentTime = this.currentTime;
            const subtitleDisplay = document.getElementById('subtitles');
            const slideSubtitles = subtitleData[currentSlide] || [];

            const currentSubtitle = slideSubtitles.find(sub =>
                currentTime >= sub.start && currentTime <= sub.end
            );

            if (currentSubtitle) {{
                subtitleDisplay.textContent = currentSubtitle.text;
                subtitleDisplay.style.background = '#1a1a1a';
            }} else if (currentTime > 0) {{
                subtitleDisplay.textContent = '...';
                subtitleDisplay.style.background = '#333';
            }}
        }});

        // Auto-advance slides (FIXED: autoplay waits for avatar+audio readiness)
        document.getElementById('mainAudio').addEventListener('ended', async function() {{
            if (currentSlide < {num_slides} && !isQAMode) {{
                // Keep a tiny gap between slides (reduce if you want)
                await new Promise(r => setTimeout(r, 250));
                await loadSlide(currentSlide + 1, true);
            }} else if (currentSlide >= {num_slides}) {{
                document.getElementById('subtitles').textContent = '🎉 Lecture complete!';
            }}
        }});

        // =====================
        // Q&A Functions
        // =====================
        function toggleQA() {{
            isQAMode = !isQAMode;
            const panel = document.getElementById('qaPanel');
            const btn = document.getElementById('raiseHandBtn');
            const btnText = document.getElementById('raiseHandText');
            const pausedIndicator = document.getElementById('pausedIndicator');
            const audio = document.getElementById('mainAudio');

            if (isQAMode) {{
                // Pause the lecture
                wasPlaying = !audio.paused;
                audio.pause();

                // Show Q&A panel
                panel.classList.add('visible');
                btn.classList.add('active');
                btnText.textContent = 'Lower Hand';
                pausedIndicator.classList.add('visible');

                // Focus on input
                document.getElementById('questionInput').focus();
            }} else {{
                // Hide Q&A panel
                panel.classList.remove('visible');
                btn.classList.remove('active');
                btnText.textContent = 'Raise Hand';
                pausedIndicator.classList.remove('visible');

                // Resume if was playing
                if (wasPlaying) {{
                    audio.play();
                }}
            }}
        }}

        async function askQuestion() {{
            const input = document.getElementById('questionInput');
            const question = input.value.trim();

            if (!question) return;

            const askBtn = document.getElementById('askBtn');
            const responseDiv = document.getElementById('qaResponse');
            const answerText = document.getElementById('answerText');
            const answerAudio = document.getElementById('answerAudio');
            const statusDiv = document.getElementById('qaStatus');
            const resumeBtn = document.getElementById('resumeBtn');

            // Show loading state
            askBtn.disabled = true;
            askBtn.textContent = 'Thinking...';
            responseDiv.style.display = 'block';
            responseDiv.classList.add('loading');
            answerText.textContent = '🤔 The AI teacher is thinking...';
            answerAudio.style.display = 'none';
            statusDiv.textContent = '';

            try {{
                // Try to use the API server first
                const response = await fetch(`${{QA_SERVER}}/api/ask`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        question: question,
                        current_slide: currentSlide,
                        generate_audio: true
                    }})
                }});

                if (response.ok) {{
                    const data = await response.json();
                    answerText.textContent = data.answer;

                    if (data.has_audio) {{
                        answerAudio.src = `${{QA_SERVER}}/api/audio?t=${{Date.now()}}`;
                        answerAudio.style.display = 'block';
                        answerAudio.play();
                    }}

                    statusDiv.textContent = '✅ Answer generated using local AI';
                    statusDiv.className = 'qa-status success';
                }} else {{
                    throw new Error('Server error');
                }}
            }} catch (error) {{
                // Fallback: provide a simple response
                console.log('Q&A server not available, using fallback');

                const slideContext = lectureContext.find(s => s.slide === currentSlide);
                const contextText = slideContext ? slideContext.text : '';

                answerText.textContent =
                    `I'd be happy to help! You asked about "${{question}}" while on slide ${{currentSlide}}. ` +
                    `This slide covers: "${{contextText.substring(0, 100)}}..." ` +
                    `For a full AI-powered answer, please start the Q&A server with: python qa_handler.py --server`;

                statusDiv.innerHTML = '⚠️ Q&A server not running. Start with: <code>python qa_handler.py --server</code>';
                statusDiv.className = 'qa-status error';
            }}

            // Reset UI
            responseDiv.classList.remove('loading');
            askBtn.disabled = false;
            askBtn.textContent = 'Ask';
            resumeBtn.classList.add('visible');
            input.value = '';
        }}

        function resumeLecture() {{
            toggleQA();  // This will close Q&A and resume if was playing
            document.getElementById('resumeBtn').classList.remove('visible');
            document.getElementById('qaResponse').style.display = 'none';
        }}

        // Check Q&A server status on load
        async function checkQAServer() {{
            try {{
                const response = await fetch(`${{QA_SERVER}}/api/status`);
                if (response.ok) {{
                    const data = await response.json();
                    console.log('Q&A Server status:', data);
                }}
            }} catch (e) {{
                console.log('Q&A server not running. Start with: python qa_handler.py --server');
            }}
        }}

        // Initialize
        setAvatarForSlide(currentSlide);
        checkQAServer();
        console.log('Lecture Player initialized with Q&A support');
        console.log('Subtitle data loaded:', Object.keys(subtitleData).length, 'slides');
    </script>
</body>
</html>"""

# Write the player file
output_path = "output/dynamic_player.html"
with open(output_path, "w") as f:
    f.write(html)

print("✅ Generated dynamic player with Q&A feature")
print(f"📊 Slides: {num_slides}")
print(f"📁 Output: {output_path}")
print()
print("To use Q&A feature:")
print("1. Start Ollama: ollama serve")
print("2. Start Q&A server: python qa_handler.py --server")
print("3. Open the player: http://localhost:8000/output/dynamic_player.html")
