"""Draw the deployed conversation pipeline as a reusable submission diagram."""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/submission/architecture.svg'
parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="610" viewBox="0 0 1440 610" role="img" aria-label="LingoLive deployed architecture: local context, authenticated Cloud Run relay, streaming transcription and two parallel Flash-Lite branches">
<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto-start-reverse"><path d="M0,0 L8,4 L0,8 Z" fill="#1a73e8"/></marker></defs>
<rect width="1440" height="610" fill="white"/>
<style>text{font-family:Arial,sans-serif;fill:#202124}.head{font-size:23px;font-weight:700}.body{font-size:19px}.small{font-size:17px;fill:#526477}.label{font-size:17px;font-weight:700;fill:#1a73e8}</style>''']

def box(x, y, w, h, title, lines, fill='#f1f6fd', color='#bdcfe8'):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="15" fill="{fill}" stroke="{color}" stroke-width="2"/>')
    parts.append(f'<text class="head" x="{x+20}" y="{y+32}">{escape(title)}</text>')
    for i, line in enumerate(lines):
        parts.append(f'<text class="body" x="{x+20}" y="{y+63+i*28}">{escape(line)}</text>')

def path(d, label=None, x=0, y=0, bidir=False):
    parts.append(f'<path d="{d}" fill="none" stroke="#1a73e8" stroke-width="3" marker-end="url(#arrow)"'+(' marker-start="url(#arrow)"' if bidir else '')+'/>')
    if label:
        parts.append(f'<text class="label" x="{x}" y="{y}" text-anchor="middle">{escape(label)}</text>')

parts.append('<rect x="870" y="110" width="550" height="370" rx="20" fill="#f3f9f3" stroke="#9dc4a5" stroke-width="2"/>')
parts.append('<text class="head" x="890" y="145">Google AI · Vertex AI</text>')
box(440, 12, 315, 84, 'Firebase Authentication', ['Verified Google sign-in'])
box(20, 140, 295, 287, 'Mobile / desktop web app', ['16 kHz microphone stream', 'Local turn / repeat routing', 'Goal + plan + recent turns', 'Relevant personal context', 'Reply cards + pronunciation', 'Tap words; review later'])
box(440, 140, 315, 287, 'Cloud Run · FastAPI', ['Secure session + validation', 'WebSocket speech relay', 'Durable usage reservation', 'Two concurrent AI tasks', 'Validate + merge JSON', 'Warm HTTP connections'])
box(895, 166, 500, 82, 'Gemini 3.5 Transcribe Live', ['Streaming multilingual speech → final text'], '#fff', '#9dc4a5')
box(965, 282, 430, 80, 'Flash-Lite · source branch', ['Meaning, words, memory suggestions'], '#fff', '#9dc4a5')
box(965, 384, 430, 80, 'Flash-Lite · reply branch', ['Three replies, readings, meanings'], '#fff', '#9dc4a5')
box(20, 492, 295, 104, 'Local learner memory', ['Saved lessons + editable notes', 'On return → place notes'])
box(440, 492, 315, 104, 'Private Cloud Storage', ['Atomic shared daily counters', '20 min audio / 100 lessons'])
box(895, 512, 500, 84, 'Secret Manager + runtime service account', ['Private signing secret; authenticated Google AI access'], '#f8f9fa', '#dadce0')
path('M597 96 V140')
path('M315 198 H440', 'PCM / text', 378, 179, True)
path('M755 207 H895', 'Live WS', 825, 189, True)
path('M315 350 H440', 'Context / result', 378, 330, True)
path('M755 350 H845 V322 H965')
path('M845 350 V424 H965')
parts.append('<circle cx="845" cy="350" r="6" fill="#1a73e8"/>')
parts.append('<text class="label" x="790" y="291">Parallel</text>')
parts.append('<text class="small" x="890" y="495">Parallel results merge and validate in Cloud Run.</text>')
path('M167 492 V427', bidir=True)
path('M597 492 V427', bidir=True)
parts.append('</svg>')
OUT.write_text('\n'.join(parts)+'\n')
print(OUT)
