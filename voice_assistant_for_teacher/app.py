"""
Voice-Enabled AI Teaching Assistant — Redesigned Streamlit UI.
Matches reference design: card-based layout, mic in input bar, grid quiz, 2-col explanation.
"""
from __future__ import annotations
import base64, hashlib, time
import streamlit as st

from classifier.groq_classifier import ClassifierError
from config.settings import settings
from image_generation.illustration import generate_illustration
from llms.base import ExplanationResult, GenerationError, QuizResult
from llms.gemini_llm import GeminiLLM
from router.task_router import RouterResult, TaskRouter
from stt.sarvam import STTError, SarvamSTT
from tts.elevenlabs import ElevenLabsTTS
from visuals import visual_router

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Voice Teaching Assistant", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

# ── Theme ─────────────────────────────────────────────────────────────────────
# Light mode only - dark theme removed
BG        = "#f4f3fb"
SURFACE   = "#ffffff"
SURF2     = "#f0edff"
TEXT      = "#1e1b3a"
TEXT2     = "#6e6a8a"
BORDER    = "#e5e2f3"
ACCENT    = "#6C5CE7"
ALIGHT    = "#a29bfe"
ABGD      = "rgba(108,92,231,0.06)"
UBGD      = "#6C5CE7"
UTXT      = "#ffffff"
CARD_BG   = "#ffffff"
INPUT_BG  = "#ffffff"
INPUT_BRD = "#e0ddf0"
SIDEBAR_BG= "#f9f8ff"
CARD_SHAD = "0 2px 12px rgba(108,92,231,.06)"

OK  = "#00b894"
ERR = "#d63031"
WARN= "#fdcb6e"

# ── Helpers ───────────────────────────────────────────────────────────────────
def _autoplay_audio(audio_bytes: bytes | None) -> None:
    if not audio_bytes: return
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(f'<audio autoplay style="display:none"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)

def _audio_player(audio_bytes: bytes | None, label: str = "") -> None:
    if not audio_bytes: return
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(f"""
    <div style="margin:8px 0;">
      {"<div style='font-size:11px;color:"+TEXT2+";font-weight:600;letter-spacing:.4px;text-transform:uppercase;margin-bottom:4px;'>"+label+"</div>" if label else ""}
      <audio controls style="width:100%;height:36px;border-radius:10px;">
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
      </audio>
    </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CSS — complete redesign matching reference mockup
# ═══════════════════════════════════════════════════════════════════════════════
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* ── Global ── */
*,body{{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif!important;}}
html,body,[data-testid="stAppViewContainer"],[data-testid="stApp"],.main .block-container{{
  background:{BG}!important;color:{TEXT}!important;}}
.block-container{{padding:0!important;padding-top:24px!important;max-width:100%!important;}}
header[data-testid="stHeader"]{{
  background:transparent!important;
  backdrop-filter:none!important;
  -webkit-backdrop-filter:none!important;
}}
/* Keep sidebar toggle visible but hide branding & deploy button */
footer,#MainMenu,.stDeployButton,div[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
header[data-testid="stHeader"] [data-testid="stToolbar"]{{display:none!important;}}

/* Hide raw material icon text that renders as 'keyboard_double_arrow_left/right' */
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button span,
[data-testid="collapsedControl"] button span,
[data-testid="stSidebarCollapsedControl"] button span{{
  font-size:0!important;
  overflow:hidden!important;
  width:0!important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button svg,
[data-testid="collapsedControl"] button svg,
[data-testid="stSidebarCollapsedControl"] button svg{{
  width:22px!important;height:22px!important;
  font-size:22px!important;
}}

/* Ensure sidebar expand button is always visible when collapsed */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"]{{
  display:flex!important;
  visibility:visible!important;
  opacity:1!important;
  position:fixed!important;
  top:12px!important;
  left:12px!important;
  z-index:99999!important;
  background:{ACCENT}!important;
  border:none!important;
  border-radius:12px!important;
  box-shadow:0 4px 16px rgba(108,92,231,.35)!important;
  padding:8px!important;
  width:auto!important;
  height:auto!important;
}}
[data-testid="collapsedControl"] button,
[data-testid="stSidebarCollapsedControl"] button{{
  color:#fff!important;
  background:transparent!important;
  border:none!important;
  cursor:pointer!important;
  padding:4px!important;
  width:28px!important;height:28px!important;
  display:flex!important;align-items:center!important;justify-content:center!important;
}}
[data-testid="collapsedControl"]:hover,
[data-testid="stSidebarCollapsedControl"]:hover{{
  background:#5b4ad4!important;
  box-shadow:0 6px 20px rgba(108,92,231,.45)!important;
  transform:scale(1.05);
}}

/* Sidebar close button (inside open sidebar) */
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"]{{
  display:flex!important;
  visibility:visible!important;
  opacity:1!important;
  position:absolute!important;
  top:8px!important;
  right:8px!important;
  z-index:1001!important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button{{
  background:{SURFACE}!important;
  border:1px solid {BORDER}!important;
  border-radius:8px!important;
  width:32px!important;height:32px!important;
  display:flex!important;align-items:center!important;justify-content:center!important;
  color:{ACCENT}!important;
  box-shadow:0 1px 6px rgba(0,0,0,.10)!important;
  cursor:pointer!important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button:hover{{
  background:{ABGD}!important;
  border-color:{ACCENT}!important;
}}
/* Sidebar close button styling */
[data-testid="stSidebar"] button[kind="header"]{{
  color:{TEXT}!important;
  opacity:.7;
}}
[data-testid="stSidebar"] button[kind="header"]:hover{{
  opacity:1;
  color:{ACCENT}!important;
}}

/* ── Scrollbar ── */
::-webkit-scrollbar{{width:5px;}}
::-webkit-scrollbar-track{{background:transparent;}}
::-webkit-scrollbar-thumb{{background:{BORDER};border-radius:3px;}}

/* ── Sidebar ── */
[data-testid="stSidebar"]{{background:{SIDEBAR_BG}!important;border-right:1px solid {BORDER}!important;
  transition:margin-left .25s ease, transform .25s ease!important;}}
[data-testid="stSidebar"] *{{color:{TEXT}!important;}}

/* Sidebar close button — make it prominent */
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"]{{
  display:flex!important;
  visibility:visible!important;
  opacity:1!important;
  position:absolute!important;
  top:10px!important;
  right:10px!important;
  z-index:1001!important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button{{
  background:{SURFACE}!important;
  border:1px solid {BORDER}!important;
  border-radius:8px!important;
  width:32px!important;height:32px!important;
  display:flex!important;align-items:center!important;justify-content:center!important;
  color:{ACCENT}!important;
  box-shadow:0 1px 4px rgba(0,0,0,.08)!important;
  cursor:pointer!important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button:hover{{
  background:{ABGD}!important;
  border-color:{ACCENT}!important;
}}

/* Custom sidebar toggle button in topbar */
.sidebar-toggle-btn{{
  width:38px;height:38px;border-radius:10px;
  background:{SURFACE};border:1px solid {BORDER};
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;font-size:18px;color:{ACCENT};
  transition:all .2s ease;
  box-shadow:0 1px 4px rgba(0,0,0,.06);
  flex-shrink:0;
}}
.sidebar-toggle-btn:hover{{
  background:{ABGD};border-color:{ACCENT};
  box-shadow:0 2px 8px rgba(108,92,231,.15);
}}

/* sidebar headers */
.sb-title{{font-size:17px;font-weight:800;color:{TEXT}!important;display:flex;align-items:center;gap:10px;margin-bottom:2px;}}
.sb-subtitle{{font-size:12px;color:{TEXT2}!important;font-weight:500;margin-bottom:4px;}}
.sb-section{{font-size:13px;font-weight:700;color:{ACCENT}!important;display:flex;align-items:center;gap:8px;margin:6px 0 4px;}}

/* sidebar radio */
[data-testid="stSidebar"] .stRadio label{{padding:6px 12px!important;border-radius:8px;transition:.15s;}}
[data-testid="stSidebar"] .stRadio label:hover{{background:{ABGD}!important;}}

/* sidebar slider */
[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] div{{color:{ACCENT}!important;}}

/* ── Top bar ── */
.topbar-wrap{{background:{SURFACE};border-bottom:1px solid {BORDER};padding:12px 28px;
  display:flex;align-items:center;justify-content:space-between;}}
.topbar-left{{display:flex;align-items:center;gap:14px;}}
.topbar-logo{{width:40px;height:40px;border-radius:13px;
  background:linear-gradient(135deg,{ACCENT},{ALIGHT});
  display:flex;align-items:center;justify-content:center;font-size:20px;color:#fff;
  box-shadow:0 3px 14px rgba(108,92,231,.28);}}
.topbar-title{{font-size:18px;font-weight:800;color:{TEXT};letter-spacing:-.3px;}}
.topbar-right{{display:flex;align-items:center;gap:10px;}}

/* ── Toggle switch ── */
.toggle-wrap{{display:flex;align-items:center;gap:8px;}}
.toggle-icon{{font-size:16px;}}

/* ── Chat area ── */
.chat-area{{max-width:960px;margin:0 auto;padding:20px 16px 180px;}}

/* ── User message ── */
.u-row{{display:flex;justify-content:flex-end;margin-bottom:16px;}}
.u-bubble{{max-width:65%;padding:12px 18px;border-radius:18px 18px 4px 18px;
  background:{UBGD};color:{UTXT};font-size:14px;line-height:1.6;font-weight:500;
  box-shadow:0 2px 10px rgba(108,92,231,.15);}}
.u-time{{font-size:10px;opacity:.55;text-align:right;margin-top:4px;}}

/* ── AI message card ── */
.ai-card{{background:{CARD_BG};border:1px solid {BORDER};border-radius:16px;
  padding:20px 24px;margin-bottom:16px;box-shadow:{CARD_SHAD};}}
.ai-header{{display:flex;align-items:center;gap:12px;margin-bottom:14px;}}
.ai-avatar{{width:36px;height:36px;border-radius:12px;flex-shrink:0;
  background:linear-gradient(135deg,{ACCENT},{ALIGHT});
  display:flex;align-items:center;justify-content:center;font-size:18px;color:#fff;}}
.ai-label{{font-size:15px;font-weight:700;color:{TEXT};}}
.ai-time{{font-size:11px;color:{TEXT2};font-weight:500;margin-top:1px;}}

/* ── Explanation text ── */
.expl-text{{font-size:14px;line-height:1.7;color:{TEXT};margin-bottom:12px;}}

/* ── Key points ── */
.kp-title{{font-size:13px;font-weight:700;color:{ACCENT};display:flex;align-items:center;gap:6px;
  margin-bottom:10px;letter-spacing:.3px;}}
.kp-item{{display:flex;gap:8px;font-size:13px;line-height:1.6;color:{TEXT};padding:4px 0;}}
.kp-bullet{{color:{ACCENT};font-weight:700;flex-shrink:0;margin-top:1px;}}

/* ── Quiz header ── */
.quiz-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;}}
.quiz-title{{font-size:15px;font-weight:700;color:{ACCENT};display:flex;align-items:center;gap:8px;}}

/* Fix expander arrow/title overlap */
[data-testid="stExpander"] details summary {{
  padding:14px 18px!important;
  gap:10px!important;
  overflow:hidden!important;
}}
[data-testid="stExpander"] details summary span {{
  overflow:hidden!important;
  text-overflow:ellipsis!important;
  white-space:nowrap!important;
}}
[data-testid="stExpander"] details summary svg {{
  flex-shrink:0!important;
  min-width:16px!important;
}}

/* ── Quiz grid ── */
.q-num{{font-weight:700;color:{ACCENT};font-size:13px;margin-bottom:4px;}}
.q-text{{font-size:12px;font-weight:600;color:{TEXT};line-height:1.45;margin-bottom:8px;
  min-height:48px;word-wrap:break-word;overflow-wrap:break-word;hyphens:auto;
  overflow:hidden;display:-webkit-box;-webkit-line-clamp:6;-webkit-box-orient:vertical;}}

/* Quiz column overflow fix */
[data-testid="stExpander"] [data-testid="column"] {{
  overflow:hidden!important;
  min-width:0!important;
}}
[data-testid="stExpander"] [data-testid="column"] .stRadio label {{
  white-space:normal!important;
  word-break:break-word!important;
}}
[data-testid="stExpander"] [data-testid="column"] .stRadio [data-testid="stMarkdownContainer"] p {{
  font-size:11.5px!important;
  word-break:break-word!important;
  overflow-wrap:break-word!important;
}}

/* ── Quiz results ── */
.result-card{{background:{CARD_BG};border:1px solid {BORDER};border-radius:14px;
  padding:18px 22px;margin-top:12px;box-shadow:{CARD_SHAD};}}
.result-title{{font-size:14px;font-weight:700;color:{ACCENT};margin-bottom:14px;
  display:flex;align-items:center;gap:6px;}}

/* score ring */
.score-ring{{width:90px;height:90px;border-radius:50%;display:flex;flex-direction:column;
  align-items:center;justify-content:center;margin:0 auto;}}
.score-big{{font-size:22px;font-weight:900;}}
.score-pct{{font-size:12px;font-weight:600;}}

/* stat pills */
.stat-row{{display:flex;gap:16px;margin-top:10px;justify-content:center;}}
.stat-item{{text-align:center;}}
.stat-val{{font-size:20px;font-weight:800;}}
.stat-lbl{{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-top:2px;}}

/* feedback card */
.feedback-card{{background:{ABGD};border:1px solid {BORDER};border-radius:12px;padding:14px 16px;}}
.feedback-title{{font-size:14px;font-weight:700;color:{TEXT};margin-bottom:4px;}}
.feedback-body{{font-size:12px;color:{TEXT2};line-height:1.5;}}
.rev-title{{font-size:12px;font-weight:700;color:{TEXT};margin:8px 0 4px;}}
.rev-tag{{display:inline-block;background:{ACCENT}15;color:{ACCENT};
  padding:4px 12px;border-radius:16px;font-size:11px;font-weight:600;margin:2px 4px 2px 0;
  border:1px solid {ACCENT}30;}}

/* answer line */
.ans-line{{font-size:12.5px;padding:3px 0;display:flex;align-items:center;gap:5px;}}
.ans-ok{{color:{OK};font-weight:600;}}
.ans-err{{color:{ERR};font-weight:600;}}

/* ── Generate Quiz button ── */
.gen-quiz-btn{{display:inline-flex;align-items:center;gap:6px;padding:8px 20px;
  border:1.5px solid {ACCENT};border-radius:10px;background:transparent;
  color:{ACCENT};font-size:13px;font-weight:600;cursor:pointer;transition:.2s;margin-top:8px;}}
.gen-quiz-btn:hover{{background:{ACCENT};color:#fff;}}

/* ── Bottom input bar — force light background ── */
[data-testid="stBottom"]{{
  background:{BG}!important;
  border-top:1px solid {BORDER}!important;
  padding:8px 0!important;
}}
[data-testid="stBottom"] > div,
[data-testid="stBottom"] > div > div,
[data-testid="stBottom"] > div > div > div{{
  background:transparent!important;
}}

/* ── Composer row (ChatGPT/WhatsApp style: mic | text field) ── */
.composer-wrap{{max-width:960px;margin:0 auto;padding:0 16px;}}
.composer-wrap [data-testid="column"]{{display:flex;align-items:center;}}

/* Mic toggle button inside the composer row — circular, inline, like WhatsApp */
div[data-testid="stBottom"] .stButton > button{{
  border-radius:50%!important;
  width:44px!important;height:44px!important;
  min-width:44px!important;
  padding:0!important;
  display:flex!important;align-items:center!important;justify-content:center!important;
  font-size:18px!important;
  background:{ACCENT}!important;
  color:#fff!important;
  border:none!important;
  box-shadow:0 2px 8px rgba(108,92,231,.25)!important;
  transition:all .2s ease!important;
}}
div[data-testid="stBottom"] .stButton > button:hover{{
  background:#5b4ad4!important;
  box-shadow:0 4px 14px rgba(108,92,231,.35)!important;
  transform:translateY(-1px)!important;
}}
/* Active/recording state: mic button turns red + pulses, becomes a stop icon */
div[data-testid="stBottom"] .stButton > button[kind="primary"]{{
  background:{ERR}!important;
  animation:pulse-record 1.4s ease-in-out infinite!important;
}}
@keyframes pulse-record{{
  0%{{box-shadow:0 0 0 0 rgba(214,48,49,.45);}}
  70%{{box-shadow:0 0 0 9px rgba(214,48,49,0);}}
  100%{{box-shadow:0 0 0 0 rgba(214,48,49,0);}}
}}

/* Inline recorder pop — appears directly beneath the composer, WhatsApp-style */
.recorder-pop{{max-width:960px;margin:8px auto 0;padding:10px 16px 4px;}}
.recorder-hint{{font-size:12.5px;color:{TEXT2};font-weight:500;padding:6px 2px;}}
[data-testid="stAudioInput"]{{
  border:1.5px solid {ACCENT}40!important;
  border-radius:14px!important;
  background:{SURFACE}!important;
  box-shadow:0 1px 8px rgba(108,92,231,.08)!important;
}}
[data-testid="stAudioInput"] button{{
  background:{ACCENT}!important;
  border:none!important;
  border-radius:10px!important;
  color:#fff!important;
  font-weight:600!important;
  box-shadow:0 2px 8px rgba(108,92,231,.2)!important;
  transition:all .2s ease!important;
}}
[data-testid="stAudioInput"] button:hover{{
  background:#5b4ad4!important;
  transform:translateY(-1px)!important;
}}
[data-testid="stAudioInput"] button[aria-pressed="true"]{{
  background:{ERR}!important;
  animation:pulse-record 1.4s ease-in-out infinite!important;
}}

[data-testid="stChatInput"]{{
  position:relative!important;
  border:1.5px solid {INPUT_BRD}!important;border-radius:22px!important;
  background:{INPUT_BG}!important;
  box-shadow:0 1px 8px rgba(108,92,231,.05)!important;
}}
[data-testid="stChatInput"]:focus-within{{
  border-color:{ACCENT}!important;
  box-shadow:0 0 0 3px rgba(108,92,231,.10)!important;
}}
[data-testid="stChatInput"] textarea{{
  color:{TEXT}!important;font-size:14px!important;font-weight:500!important;
  background:transparent!important;caret-color:{ACCENT}!important;
}}
[data-testid="stChatInput"] textarea::placeholder{{
  color:{TEXT2}!important;opacity:.55!important;
}}
/* send button */
[data-testid="stChatInput"] button{{
  background:{ACCENT}!important;border-radius:50%!important;
  color:#fff!important;border:none!important;
  box-shadow:0 2px 8px rgba(108,92,231,.25)!important;
  width:38px!important;height:38px!important;
}}
[data-testid="stChatInput"] button:hover{{
  background:#5b4ad4!important;
}}

/* ── Hide components.html iframe containers ── */
iframe[height="0"]{{display:none!important;pointer-events:none!important;}}
[data-testid="stHtml"]:has(iframe[height="0"]){{
  position:absolute!important;width:0!important;height:0!important;
  overflow:hidden!important;pointer-events:none!important;
}}

/* ── Streamlit widget overrides ── */
.stButton > button{{
  border-radius:10px!important;font-weight:600!important;font-size:13px!important;
  transition:.2s!important;font-family:'Inter',sans-serif!important;
}}
.stButton > button[kind="primary"]{{
  background:{ACCENT}!important;color:#fff!important;border:none!important;
  box-shadow:0 2px 10px rgba(108,92,231,.2)!important;
}}
.stButton > button[kind="primary"]:hover{{
  background:#5b4ad4!important;
  box-shadow:0 4px 16px rgba(108,92,231,.3)!important;
}}
.stButton > button:not([kind="primary"]){{
  background:transparent!important;color:{ACCENT}!important;
  border:1.5px solid {ACCENT}!important;
}}
.stButton > button:not([kind="primary"]):hover{{
  background:{ABGD}!important;
}}

/* containers */
div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"] > div{{
  border:1px solid {BORDER}!important;border-radius:14px!important;
  background:{CARD_BG}!important;
}}

/* radio in quiz */
.stRadio > div{{gap:2px!important;}}
.stRadio label{{padding:4px 8px!important;border-radius:8px!important;font-size:12.5px!important;
  transition:.15s!important;}}
.stRadio label:hover{{background:{ABGD}!important;}}
.stRadio [data-testid="stMarkdownContainer"] p{{font-size:12.5px!important;color:{TEXT}!important;}}

/* expander */
[data-testid="stExpander"]{{border:1px solid {BORDER}!important;border-radius:14px!important;
  background:{CARD_BG}!important;box-shadow:{CARD_SHAD};overflow:hidden;}}
[data-testid="stExpander"] summary{{font-weight:700!important;color:{ACCENT}!important;font-size:14px!important;}}
[data-testid="stExpander"] summary span{{color:{ACCENT}!important;}}

/* divider */
hr{{border-color:{BORDER}!important;margin:12px 0!important;}}

/* ── How-It-Works card ── */
.how-card{{background:{ABGD};border:1px solid {BORDER};border-radius:14px;padding:14px;margin-top:6px;}}
.how-step{{display:flex;align-items:center;gap:10px;padding:7px 0;font-size:12px;color:{TEXT};}}
.how-icon{{width:30px;height:30px;border-radius:10px;
  background:linear-gradient(135deg,{ACCENT},{ALIGHT});color:#fff;
  display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0;}}
.how-arr{{text-align:center;color:{ACCENT};font-size:12px;opacity:.4;margin:0;}}

/* ── Recording pipeline status bar ── */
.pipeline-bar{{display:flex;align-items:center;justify-content:center;gap:6px;
  padding:12px 20px;max-width:960px;margin:20px auto;background:{CARD_BG};
  border:1px solid {BORDER};border-radius:12px;box-shadow:{CARD_SHAD};
  position:relative;z-index:100;overflow:visible;}}
.pipe-step{{display:flex;align-items:center;gap:4px;font-size:12px;font-weight:600;
  color:{TEXT};overflow:visible;}}
.pipe-dot{{width:8px;height:8px;border-radius:50%;background:{TEXT2};opacity:.6;flex-shrink:0;}}
.pipe-dot.rec{{background:{ERR};animation:pulse 1.2s ease-in-out infinite;}}
.pipe-dot.done{{background:{OK};}}
.pipe-arrow{{color:{TEXT2};opacity:.4;font-size:12px;margin:0 4px;}}
@keyframes pulse{{0%{{opacity:.6;transform:scale(1)}}50%{{opacity:1;transform:scale(1.2)}}100%{{opacity:.6;transform:scale(1)}}}}

/* ── Footer ── */
.app-footer{{text-align:center;padding:8px;color:{TEXT2};font-size:11px;opacity:.5;font-weight:500;
  display:flex;align-items:center;justify-content:center;gap:4px;}}

/* ── Welcome ── */
.welcome-wrap{{text-align:center;padding:48px 20px 20px;max-width:700px;margin:0 auto;}}
.welcome-title{{font-size:28px;font-weight:900;letter-spacing:-.5px;
  background:linear-gradient(135deg,{ACCENT},{ALIGHT});-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;margin-bottom:8px;}}
.welcome-sub{{color:{TEXT2};font-size:14px;line-height:1.6;font-weight:500;}}
.try-label{{text-align:center;font-size:11px;font-weight:700;color:{TEXT2};
  letter-spacing:.6px;text-transform:uppercase;margin:24px 0 10px;}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ── Singletons ────────────────────────────────────────────────────────────────
@st.cache_resource
def get_router():  return TaskRouter()
@st.cache_resource
def get_stt():     return SarvamSTT()
@st.cache_resource
def get_tts():     return ElevenLabsTTS()
@st.cache_resource
def get_gemini():  return GeminiLLM()

router     = get_router()
stt        = get_stt()
tts_client = get_tts()
gemini_llm = get_gemini()

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {"messages": [], "last_audio_hash": None, "autoplay_idx": -1}.items():
    st.session_state.setdefault(k, v)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;padding:4px 0 0;">
      <div style="width:34px;height:34px;border-radius:11px;
        background:linear-gradient(135deg,{ACCENT},{ALIGHT});
        display:flex;align-items:center;justify-content:center;font-size:17px;color:#fff;">🎓</div>
      <div>
        <div class="sb-title" style="margin:0;">Voice Teaching Assistant</div>
        <div class="sb-subtitle">Learn Smarter. Anytime. Anywhere.</div>
      </div>
    </div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown(f'<div class="sb-section">⚙️ Smart Board Settings</div>', unsafe_allow_html=True)
    st.divider()

    st.markdown(f'<div class="sb-section">🌐 Language</div>', unsafe_allow_html=True)
    lang_choice = st.radio("Language", ["Hinglish", "English"], index=0, label_visibility="collapsed")
    lang_val = "hinglish" if lang_choice == "Hinglish" else "english"

    st.divider()
    st.markdown(f'<div class="sb-section">📝 Quiz Quantity</div>', unsafe_allow_html=True)
    n_quiz = st.slider("Quiz Quantity", 3, 20, 5, label_visibility="collapsed")
    st.caption(f"**{n_quiz} Questions**")

    st.divider()
    st.markdown(f'<div class="sb-section">ℹ️ How It Works</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="how-card">
      <div class="how-step"><div class="how-icon">🎤</div><div><b>Step 1</b><br/>Ask by voice or text</div></div>
      <div class="how-arr">↓</div>
      <div class="how-step"><div class="how-icon">🧠</div><div><b>Step 2</b><br/>AI understands the question</div></div>
      <div class="how-arr">↓</div>
      <div class="how-step"><div class="how-icon">📚</div><div><b>Step 3</b><br/>Generates explanation, visuals and quizzes</div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='flex:1;'></div>", unsafe_allow_html=True)
    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        for k in [k for k in st.session_state if k.startswith(("q_", "quiz_checked_", "result_audio_"))]:
            del st.session_state[k]
        st.session_state.messages = []
        st.session_state.autoplay_idx = -1
        st.rerun()

# ── Top bar ───────────────────────────────────────────────────────────────────
col_toggle, col_l, col_r = st.columns([0.5, 8.5, 1])
with col_toggle:
    # NOTE: this is a plain st.markdown HTML block, which renders directly in the
    # main app document (NOT inside a sandboxed iframe like components.html does).
    # That's why this script can actually reach and click Streamlit's real native
    # sidebar-collapse button — the previous components.html()-based toggle could
    # never work because CSS/JS inside that iframe is isolated from the parent page.
    st.markdown("""
    <button id="custom-sidebar-toggle" class="sidebar-toggle-btn" title="Toggle side panel" type="button">☰</button>
    <script>
    (function() {
      const btn = document.getElementById("custom-sidebar-toggle");
      if (!btn || btn.dataset.bound) return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", function() {
        const nativeBtn =
          document.querySelector('[data-testid="stSidebarCollapseButton"] button') ||
          document.querySelector('[data-testid="stSidebarCollapsedControl"] button') ||
          document.querySelector('[data-testid="collapsedControl"] button');
        if (nativeBtn) nativeBtn.click();
      });
    })();
    </script>
    """, unsafe_allow_html=True)
with col_l:
    st.markdown(f"""
    <div class="topbar-left" style="padding:10px 0;">
      <div class="topbar-logo">🎓</div>
      <div class="topbar-title">Voice Teaching Assistant</div>
    </div>""", unsafe_allow_html=True)
with col_r:
    pass  # Theme button removed - light mode only

st.markdown(f'<hr style="margin:0;border:none;border-top:1px solid {BORDER};">', unsafe_allow_html=True)

# ── Pipeline ──────────────────────────────────────────────────────────────────
def _tts(text: str) -> bytes | None:
    return tts_client.synthesize(text, voice_id=settings.elevenlabs_voice_id)

def _process_query(payload, source_type: str) -> None:
    ts = time.strftime("%I:%M %p")
    if source_type == "audio":
        try:
            query_text = stt.transcribe(payload).transcript
        except STTError as exc:
            st.session_state.messages += [
                {"role": "user",      "type": "text",  "content": "🎙️ *(voice message)*", "ts": ts},
                {"role": "assistant", "type": "error", "content": f"⚠️ {exc}", "ts": ts},
            ]
            return
    else:
        query_text = payload

    st.session_state.messages.append({"role": "user", "type": "text", "content": query_text, "ts": ts})

    try:
        result = router.handle_query(query_text, language=lang_val, num_quiz_questions=n_quiz)
    except (ClassifierError, GenerationError) as exc:
        st.session_state.messages.append({"role":"assistant","type":"error","content":f"⚠️ {exc}","ts":ts})
        return
    except Exception as exc:
        st.session_state.messages.append({"role":"assistant","type":"error","content":f"⚠️ Unexpected: {exc}","ts":ts})
        return

    ts2 = time.strftime("%I:%M %p")
    new_idx = len(st.session_state.messages)

    if isinstance(result.content, ExplanationResult):
        c = result.content
        audio = _tts(c.explanation)
        try:    illus = generate_illustration(c.title, gemini_llm)
        except: illus = None
        st.session_state.messages.append({
            "role":"assistant","type":"explanation",
            "result":result,"audio":audio,"illustration":illus,"ts":ts2,
        })
        st.session_state.autoplay_idx = new_idx

    elif isinstance(result.content, QuizResult):
        c = result.content
        # ★ Generate FULL audio for ALL quiz questions + options
        full_quiz_text = f"Quiz time! {c.title}. "
        for i, q in enumerate(c.questions):
            full_quiz_text += f"Question {i+1}. {q.question}. "
            for j, opt in enumerate(q.options):
                full_quiz_text += f"Option {chr(65+j)}, {opt}. "
        audio = _tts(full_quiz_text)
        st.session_state.messages.append({
            "role":"assistant","type":"quiz",
            "result":result,"audio":audio,"ts":ts2,
        })
        st.session_state.autoplay_idx = new_idx
    else:
        st.session_state.messages.append({
            "role":"assistant","type":"error",
            "content":"Unexpected response format.","ts":ts2,
        })

# ── Composer state ────────────────────────────────────────────────────────────
st.session_state.setdefault("_show_voice_section", False)

# ── Composer: WhatsApp/ChatGPT-style row — mic | text field | send ─────────────
st.markdown('<div class="composer-wrap">', unsafe_allow_html=True)

mic_col, field_col = st.columns([1, 15], gap="small")

with mic_col:
    mic_active = st.session_state._show_voice_section
    if st.button("⏹️" if mic_active else "🎤", key="composer_mic_btn",
                 help="Stop recording" if mic_active else "Record voice message",
                 type="primary" if mic_active else "secondary", use_container_width=True):
        st.session_state._show_voice_section = not st.session_state._show_voice_section
        st.rerun()

with field_col:
    chat_prompt = st.chat_input("Message Voice Teaching Assistant…", key="chat_input")

st.markdown('</div>', unsafe_allow_html=True)

# ── Inline voice recorder (WhatsApp-style: appears directly under the bar) ─────
if st.session_state._show_voice_section:
    st.markdown('<div class="recorder-pop">', unsafe_allow_html=True)
    rec_col1, rec_col2 = st.columns([10, 1])
    with rec_col1:
        st.markdown(f"""
        <div class="recorder-hint">🎙️ Tap below to record, speak your question, tap again to stop &amp; send</div>
        """, unsafe_allow_html=True)
    with rec_col2:
        if st.button("✕", key="close_recorder_btn", help="Close recorder"):
            st.session_state._show_voice_section = False
            st.rerun()

    audio_value = st.audio_input("Record your voice", key="voice_recorder", label_visibility="collapsed")

    if audio_value is not None:
        raw_audio = audio_value.getvalue()
        audio_hash = hashlib.md5(raw_audio).hexdigest()

        if audio_hash != st.session_state.last_audio_hash:
            st.session_state.last_audio_hash = audio_hash
            status_container = st.empty()
            status_container.info("🎙️ Processing your voice message...")
            try:
                _process_query(raw_audio, "audio")
                st.session_state._show_voice_section = False
                status_container.empty()
                st.rerun()
            except Exception as e:
                status_container.error(f"❌ Error processing audio: {str(e)}")
    st.markdown('</div>', unsafe_allow_html=True)

if chat_prompt:
    with st.spinner("🧠 Thinking..."):
        _process_query(chat_prompt, "text")
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# RENDER MESSAGES
# ══════════════════════════════════════════════════════════════════════════════
msgs = st.session_state.messages
autoplay_idx = st.session_state.get("autoplay_idx", -1)

if not msgs:
    # ── Welcome screen ──
    st.markdown(f"""
    <div class="welcome-wrap">
      <div class="welcome-title">👋 Welcome to Voice Teaching Assistant</div>
      <div class="welcome-sub">Ask any topic — I'll explain with visuals, audio &amp; quizzes!<br/>
      Type below or tap the 🎤 microphone to speak.</div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f'<div class="try-label">💡 Try asking</div>', unsafe_allow_html=True)
    examples = [
        "Photosynthesis kaise hoti hai?",
        "Compare mitosis aur meiosis",
        "Water cycle ka process samjhao",
        "Quiz banao fractions par",
    ]
    ec = st.columns(len(examples))
    for col, ex in zip(ec, examples):
        if col.button(ex, use_container_width=True):
            with st.spinner("🧠 Thinking..."):
                _process_query(ex, "text")
            st.rerun()

else:
    st.markdown('<div class="chat-area">', unsafe_allow_html=True)

    for idx, msg in enumerate(msgs):
        ts = msg.get("ts", "")

        # ── USER MESSAGE ─────────────────────────────────────────────────
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="u-row">
              <div class="u-bubble">
                {msg["content"]}
                <div class="u-time">{ts} ✓</div>
              </div>
            </div>""", unsafe_allow_html=True)

        # ── ERROR ────────────────────────────────────────────────────────
        elif msg.get("type") == "error":
            st.markdown(f"""
            <div class="ai-card">
              <div class="ai-header">
                <div class="ai-avatar">🎓</div>
                <div><div class="ai-label">Assistant</div><div class="ai-time">{ts}</div></div>
              </div>
            </div>""", unsafe_allow_html=True)
            st.warning(msg["content"])

        # ── EXPLANATION ──────────────────────────────────────────────────
        elif msg.get("type") == "explanation":
            result: RouterResult = msg["result"]
            c: ExplanationResult = result.content

            if idx == autoplay_idx:
                _autoplay_audio(msg.get("audio"))
                st.session_state.autoplay_idx = -1

            # Card header
            st.markdown(f"""
            <div class="ai-card">
              <div class="ai-header">
                <div class="ai-avatar">🎓</div>
                <div><div class="ai-label">{c.title}</div></div>
              </div>
            </div>""", unsafe_allow_html=True)

            # ★ Two-column layout: explanation+diagram LEFT | audio+key-points RIGHT
            left_col, right_col = st.columns([3, 2])

            with left_col:
                st.markdown(f'<div class="expl-text">{c.explanation}</div>', unsafe_allow_html=True)

                # Diagram / visual
                if c.diagram and c.visual_type not in (None, "", "none"):
                    visual_router.render(c.visual_type, c.diagram)

                # Auto-illustration
                if msg.get("illustration"):
                    st.iframe(visual_router.wrap_svg_document(msg["illustration"]), height=260)

            with right_col:
                # Audio player
                if msg.get("audio"):
                    _audio_player(msg["audio"], "🔊 Audio Explanation")

                # Key points
                if c.key_points:
                    st.markdown(f'<div class="kp-title">🔑 Key Points</div>', unsafe_allow_html=True)
                    for pt in c.key_points:
                        st.markdown(f"""
                        <div class="kp-item">
                          <span class="kp-bullet">•</span>
                          <span>{pt}</span>
                        </div>""", unsafe_allow_html=True)

                st.markdown(f'<div class="ai-time" style="margin-top:12px;">{ts}</div>', unsafe_allow_html=True)

            # Generate Quiz button
            if st.button("📝 Generate Quiz", key=f"gen_quiz_{idx}", type="secondary"):
                with st.spinner("📝 Generating quiz..."):
                    try:
                        qr = router.handle_query(
                            f"Generate a quiz on: {c.title}",
                            language=lang_val, num_quiz_questions=n_quiz,
                        )
                        new_i = len(st.session_state.messages)
                        if isinstance(qr.content, QuizResult):
                            full_q_text = f"Quiz on {c.title}. "
                            for i, q in enumerate(qr.content.questions):
                                full_q_text += f"Question {i+1}. {q.question}. "
                                for j, opt in enumerate(q.options):
                                    full_q_text += f"Option {chr(65+j)}, {opt}. "
                            qa = _tts(full_q_text)
                            st.session_state.messages.append({
                                "role":"assistant","type":"quiz",
                                "result":qr,"audio":qa,"ts":time.strftime("%I:%M %p"),
                            })
                        else:
                            st.session_state.messages.append({
                                "role":"assistant","type":"explanation",
                                "result":qr,"audio":None,"illustration":None,
                                "ts":time.strftime("%I:%M %p"),
                            })
                            new_i = -1
                        st.session_state.autoplay_idx = new_i
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Quiz generation failed: {exc}")

            st.markdown(f'<hr style="border:none;border-top:1px solid {BORDER};margin:16px 0;">', unsafe_allow_html=True)

        # ── QUIZ ─────────────────────────────────────────────────────────
        elif msg.get("type") == "quiz":
            result = msg["result"]
            c: QuizResult = result.content

            if idx == autoplay_idx:
                _autoplay_audio(msg.get("audio"))
                st.session_state.autoplay_idx = -1

            # Quiz inside expander (collapsible like reference)
            with st.expander(f"📝 Quiz: {c.title} ({len(c.questions)} Questions)", expanded=True):

                # Replay quiz audio
                if msg.get("audio"):
                    _audio_player(msg["audio"], "🔊 Full quiz audio")

                # ★ Grid layout: questions in rows of up to 5
                num_per_row = min(len(c.questions), 5)
                for row_start in range(0, len(c.questions), num_per_row):
                    row_qs = c.questions[row_start:row_start + num_per_row]
                    cols = st.columns(len(row_qs))
                    for i, q in enumerate(row_qs):
                        qi = row_start + i
                        with cols[i]:
                            st.markdown(f'<div class="q-num">Q{qi+1}.</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="q-text">{q.question}</div>', unsafe_allow_html=True)
                            st.radio(
                                f"Q{qi+1}", q.options,
                                format_func=lambda x, opts=q.options: f"{chr(65 + opts.index(x))}. {x}",
                                key=f"q_{idx}_{qi}", index=None, label_visibility="collapsed",
                            )

                # Show Results button
                checked_key = f"quiz_checked_{idx}"
                st.session_state.setdefault(checked_key, False)

                if not st.session_state[checked_key]:
                    if st.button("📊 Show Results", key=f"check_{idx}", type="primary", use_container_width=True):
                        st.session_state[checked_key] = True
                        st.rerun()

            # ── Quiz Results ──────────────────────────────────────────────
            if st.session_state.get(f"quiz_checked_{idx}", False):
                score = 0
                total = len(c.questions)
                wrong_topics: list[str] = []
                wrong_qs: list[int] = []

                for qi, q in enumerate(c.questions):
                    sel = st.session_state.get(f"q_{idx}_{qi}")
                    if sel is not None and sel == q.answer:
                        score += 1
                    elif sel is not None:
                        wrong_topics.append(" ".join(q.question.split()[:3]))
                        wrong_qs.append(qi)
                    else:
                        wrong_qs.append(qi)

                pct = int(score / total * 100) if total else 0
                ring_col = OK if pct >= 70 else WARN if pct >= 40 else ERR

                if pct >= 80:
                    fb_emoji, fb_title, fb_body = "🎉", "Great Job!", "Keep it up! You understand the concept well."
                elif pct >= 60:
                    fb_emoji, fb_title, fb_body = "👍", "Good Job!", "A little more practice and you'll master it."
                else:
                    fb_emoji, fb_title, fb_body = "📖", "Keep Going!", "Review the topic carefully and try again."

                # Auto-play result summary
                result_audio_key = f"result_audio_{idx}"
                if result_audio_key not in st.session_state:
                    summary_text = f"Quiz results for {c.title}. You scored {score} out of {total}, that is {pct} percent. {fb_title}"
                    st.session_state[result_audio_key] = _tts(summary_text)
                _autoplay_audio(st.session_state.get(result_audio_key))

                with st.expander("📊 Quiz Results", expanded=True):
                    # Three-column layout matching reference
                    r1, r2, r3 = st.columns([1, 1, 1.2])

                    with r1:
                        # Score ring + stats
                        st.markdown(f"""
                        <div style="text-align:center;padding:8px 0;">
                          <div class="score-ring" style="border:6px solid {ring_col};box-shadow:0 0 20px {ring_col}22;">
                            <div class="score-big" style="color:{ring_col};">{score}/{total}</div>
                            <div class="score-pct" style="color:{ring_col};">{pct}%</div>
                          </div>
                          <div class="stat-row">
                            <div class="stat-item">
                              <div class="stat-val" style="color:{OK};">{score}</div>
                              <div class="stat-lbl" style="color:{TEXT2};">Correct</div>
                            </div>
                            <div class="stat-item">
                              <div class="stat-val" style="color:{ERR};">{total-score}</div>
                              <div class="stat-lbl" style="color:{TEXT2};">Incorrect</div>
                            </div>
                            <div class="stat-item">
                              <div class="stat-val" style="color:{ACCENT};">{pct}%</div>
                              <div class="stat-lbl" style="color:{TEXT2};">Score</div>
                            </div>
                          </div>
                        </div>""", unsafe_allow_html=True)

                    with r2:
                        # Individual question results
                        for qi, q in enumerate(c.questions):
                            sel = st.session_state.get(f"q_{idx}_{qi}")
                            if sel is None:
                                st.markdown(f'<div class="ans-line ans-err">Q{qi+1}. ⚠️ No answer</div>', unsafe_allow_html=True)
                            elif sel == q.answer:
                                st.markdown(f'<div class="ans-line ans-ok">Q{qi+1}. ✓ Correct</div>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<div class="ans-line ans-err">Q{qi+1}. ✗ Incorrect<br/><span style="font-size:11px;opacity:.7;">Correct Answer: {q.answer}</span></div>', unsafe_allow_html=True)
                                if " ".join(q.question.split()[:3]) not in wrong_topics:
                                    wrong_topics.append(" ".join(q.question.split()[:3]))

                    with r3:
                        # Feedback card
                        st.markdown(f"""
                        <div class="feedback-card">
                          <div class="feedback-title">{fb_emoji} {fb_title}</div>
                          <div class="feedback-body">{fb_body}</div>
                          {"<div class='rev-title'>Recommended Revision</div>" + "".join(f'<span class="rev-tag">{t}</span>' for t in wrong_topics) if wrong_topics else ""}
                        </div>""", unsafe_allow_html=True)

                    # Replay result audio
                    if st.session_state.get(result_audio_key):
                        _audio_player(st.session_state[result_audio_key], "🔊 Replay result summary")

            st.markdown(f'<hr style="border:none;border-top:1px solid {BORDER};margin:16px 0;">', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(f'<div class="app-footer">Made with ♡ love for learners</div>', unsafe_allow_html=True)