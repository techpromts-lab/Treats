import streamlit as st
import requests
import json
import random
import asyncio
import io
import base64
from urllib.parse import quote
from datetime import datetime

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Treats",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CONSTANTS
# ============================================================
TOKEN_LIMIT = 5000  # free users

# ============================================================
# INLINE SVG LOGO
# ============================================================
LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">
  <defs>
    <linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#a855f7"/>
      <stop offset="100%" stop-color="#6c3ef5"/>
    </linearGradient>
    <linearGradient id="g2" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#312e81"/>
      <stop offset="100%" stop-color="#1e1b4b"/>
    </linearGradient>
  </defs>
  <ellipse cx="42" cy="22" rx="14" ry="10" fill="url(#g1)"/>
  <ellipse cx="78" cy="22" rx="14" ry="10" fill="url(#g1)"/>
  <ellipse cx="42" cy="22" rx="6" ry="4" fill="#fff"/>
  <ellipse cx="78" cy="22" rx="6" ry="4" fill="#fff"/>
  <circle cx="14" cy="70" r="12" fill="url(#g1)"/>
  <circle cx="106" cy="70" r="12" fill="url(#g1)"/>
  <rect x="20" y="35" width="80" height="70" rx="30" fill="#f5f3ff"/>
  <rect x="28" y="43" width="64" height="54" rx="24" fill="url(#g2)"/>
  <path d="M42 62 Q46 57 50 62" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/>
  <path d="M70 62 Q74 57 78 62" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/>
  <path d="M52 74 Q60 81 68 74" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/>
</svg>"""

LOGO_URI = "data:image/svg+xml;base64," + base64.b64encode(LOGO_SVG.encode()).decode()


# ============================================================
# SESSION STATE INIT
# ============================================================
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "tokens_used" not in st.session_state:
    st.session_state.tokens_used = 0
if "dev_mode" not in st.session_state:
    st.session_state.dev_mode = False
if "show_dev_input" not in st.session_state:
    st.session_state.show_dev_input = False


# ============================================================
# TOKEN HELPERS
# ============================================================
def tokens_remaining():
    if st.session_state.dev_mode:
        return None  # unlimited
    return max(0, TOKEN_LIMIT - st.session_state.tokens_used)


def can_send():
    if st.session_state.dev_mode:
        return True
    return st.session_state.tokens_used < TOKEN_LIMIT


def add_tokens(n):
    st.session_state.tokens_used += n


# ============================================================
# CUSTOM CSS
# ============================================================
def load_css(dark=False):
    if dark:
        bg = "#0d0d0d"; sidebar_bg_1 = "#161616"; sidebar_bg_2 = "#1a1a1a"
        surface = "#1a1a1a"; surface_2 = "#232323"
        border = "#2a2a2a"; border_soft = "#232323"
        text = "#ececec"; text_soft = "#a0a0a0"; text_muted = "#6b6b6b"
        hover = "#232323"; active = "#2d2d2d"
        btn_bg = "#1a1a1a"; btn_hover = "#232323"; btn_border = "#2a2a2a"
        chat_input_bg = "#1a1a1a"
    else:
        bg = "#ffffff"; sidebar_bg_1 = "#faf9ff"; sidebar_bg_2 = "#f5f3ff"
        surface = "#ffffff"; surface_2 = "#f7f7f8"
        border = "#ececec"; border_soft = "#f3f4f6"
        text = "#0d0d0d"; text_soft = "#6b7280"; text_muted = "#9ca3af"
        hover = "#ffffff"; active = "#ffffff"
        btn_bg = "#ffffff"; btn_hover = "#f9fafb"; btn_border = "#e5e7eb"
        chat_input_bg = "#ffffff"

    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"] {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}

        #MainMenu {{ visibility: hidden !important; }}
        footer {{ visibility: hidden !important; }}
        [data-testid="stDecoration"] {{ display: none !important; }}
        [data-testid="stStatusWidget"] {{ display: none !important; }}
        [data-testid="stAppDeployButton"] {{ display: none !important; }}
        [data-testid="stMainMenu"] {{ display: none !important; }}
        [data-testid="stToolbarActions"] {{ display: none !important; }}
        header[data-testid="stHeader"] {{ background: transparent !important; box-shadow: none !important; }}

        .stApp {{ background: {bg} !important; -webkit-overflow-scrolling: touch; overscroll-behavior-y: contain; }}

        @media (min-width: 769px) {{
            [data-testid="stSidebarCollapseButton"],
            [data-testid="stSidebarCollapsedControl"],
            [data-testid="collapsedControl"] {{
                display: none !important; visibility: hidden !important; pointer-events: none !important;
            }}
        }}
        @media (max-width: 768px) {{
            [data-testid="stSidebarCollapseButton"],
            [data-testid="stSidebarCollapsedControl"],
            [data-testid="collapsedControl"] {{
                display: flex !important; visibility: visible !important; opacity: 1 !important;
                color: #6c3ef5 !important; z-index: 999999 !important;
            }}
            [data-testid="stSidebarCollapseButton"] svg,
            [data-testid="stSidebarCollapsedControl"] svg,
            [data-testid="collapsedControl"] svg {{ color: #6c3ef5 !important; fill: #6c3ef5 !important; }}
        }}

        * {{ -webkit-tap-highlight-color: transparent; }}
        button, .stButton, .stDownloadButton, label,
        h1, h2, h3, h4, h5, h6,
        .tool-header, .treats-brand, .sidebar-footer, .treats-hero, [data-testid="stSidebar"] {{
            -webkit-user-select: none; -moz-user-select: none; user-select: none; -webkit-touch-callout: none;
        }}
        [data-testid="stChatMessage"], [data-testid="stChatMessage"] *,
        .stMarkdown, .stMarkdown *, .stTextArea textarea, .stTextInput input,
        pre, code, pre *, code * {{ -webkit-user-select: text; user-select: text; }}
        [data-testid="stChatInput"] textarea {{ touch-action: manipulation; }}
        html, body, .stApp {{ overflow-x: hidden; max-width: 100vw; }}

        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {sidebar_bg_1} 0%, {sidebar_bg_2} 100%) !important;
            border-right: 1px solid {border} !important;
            min-width: 280px !important; max-width: 280px !important;
        }}
        [data-testid="stSidebar"] > div:first-child {{ padding: 1.5rem 0.9rem 1rem 0.9rem; }}

        .treats-brand {{ padding: 4px 10px 22px 10px; display: flex; align-items: center; gap: 12px; }}
        .treats-brand img {{ width: 44px; height: 44px; filter: drop-shadow(0 4px 12px rgba(108, 62, 245, 0.25)); }}
        .treats-brand .name {{
            font-size: 20px; font-weight: 800; letter-spacing: -0.03em;
            background: linear-gradient(135deg, #6c3ef5 0%, #a855f7 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
        }}

        .sidebar-label {{
            font-size: 11px; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.08em; color: {text_muted};
            padding: 8px 14px 6px 14px; margin-top: 8px;
        }}

        [data-testid="stSidebar"] [data-testid="stRadio"] > div[role="radiogroup"] {{ gap: 3px !important; display: flex; flex-direction: column; }}

        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] {{
            display: flex !important; align-items: center !important; gap: 12px !important;
            padding: 10px 14px !important; margin: 0 !important; border-radius: 10px !important;
            cursor: pointer !important; transition: all 0.15s ease !important;
            font-size: 14px !important; font-weight: 500 !important; color: {text} !important;
            width: 100% !important; background: transparent !important; border: 1px solid transparent !important;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover {{ background: {hover} !important; border-color: {border} !important; }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {{ display: none !important; }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]::before {{
            content: '' !important; width: 20px !important; height: 20px !important; flex-shrink: 0 !important;
            background-repeat: no-repeat !important; background-position: center !important;
            background-size: 20px 20px !important; border-radius: 6px; padding: 4px; box-sizing: content-box;
        }}

        label[data-baseweb="radio"]:nth-of-type(1)::before {{ background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%236366f1' stroke-width='2.2'><path d='M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'/></svg>") !important; background-color: #eef2ff; }}
        label[data-baseweb="radio"]:nth-of-type(2)::before {{ background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%233b82f6' stroke-width='2.2'><path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/><polyline points='14 2 14 8 20 8'/></svg>") !important; background-color: #dbeafe; }}
        label[data-baseweb="radio"]:nth-of-type(3)::before {{ background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2310b981' stroke-width='2.2'><rect x='3' y='11' width='18' height='11' rx='2'/><path d='M7 11V7a5 5 0 0 1 10 0v4'/></svg>") !important; background-color: #d1fae5; }}
        label[data-baseweb="radio"]:nth-of-type(4)::before {{ background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23f97316' stroke-width='2.2'><polygon points='23 7 16 12 23 17 23 7'/><rect x='1' y='5' width='15' height='14' rx='2'/></svg>") !important; background-color: #ffedd5; }}
        label[data-baseweb="radio"]:nth-of-type(5)::before {{ background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ec4899' stroke-width='2.2'><polygon points='11 5 6 9 2 9 2 15 6 15 11 19 11 5'/></svg>") !important; background-color: #fce7f3; }}
        label[data-baseweb="radio"]:nth-of-type(6)::before {{ background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%238b5cf6' stroke-width='2.2'><rect x='3' y='3' width='18' height='18' rx='2'/><circle cx='8.5' cy='8.5' r='1.5'/><polyline points='21 15 16 10 5 21'/></svg>") !important; background-color: #ede9fe; }}

        label[data-baseweb="radio"]:has(input:checked) {{
            background: {active} !important; border-color: {border} !important;
            font-weight: 700 !important; color: {text} !important;
        }}

        [data-testid="stSidebar"] [data-testid="stRadio"] > label:first-child {{ display: none !important; }}

        [data-testid="stSidebar"] [data-testid="stSelectbox"] > label {{
            font-size: 11px !important; font-weight: 700 !important; text-transform: uppercase !important;
            letter-spacing: 0.08em !important; color: {text_muted} !important; padding-left: 2px !important;
        }}
        [data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {{
            background: {surface} !important; border: 1px solid {border} !important;
            border-radius: 10px !important; font-size: 13px !important; color: {text} !important;
        }}

        .sidebar-footer {{
            padding: 16px 14px; color: {text_soft}; font-size: 12px; line-height: 1.6;
            border-top: 1px solid {border}; margin-top: 20px;
        }}
        .sidebar-footer strong {{ color: #6c3ef5; font-weight: 600; }}

        /* Token usage panel */
        .token-panel {{
            background: {surface_2};
            border: 1px solid {border};
            border-radius: 10px;
            padding: 10px 14px;
            margin: 8px 0;
            font-size: 12px;
            color: {text_soft};
        }}
        .token-panel .row {{ display: flex; justify-content: space-between; margin: 4px 0; }}
        .token-panel .val {{ color: {text}; font-weight: 700; }}
        .token-panel .dev {{ color: #10b981; font-weight: 700; }}
        .token-panel .warn {{ color: #f59e0b; font-weight: 700; }}
        .token-panel .danger {{ color: #ef4444; font-weight: 700; }}

        /* Progress bar */
        .token-bar-wrap {{
            height: 6px;
            background: {border};
            border-radius: 3px;
            overflow: hidden;
            margin: 8px 0 4px 0;
        }}
        .token-bar-fill {{
            height: 100%;
            border-radius: 3px;
            transition: width 0.3s ease;
        }}

        section.main, [data-testid="stMain"] {{
            display: flex !important; flex-direction: column !important;
            align-items: center !important; width: 100% !important;
        }}

        section.main > div.block-container,
        [data-testid="stMain"] > div.block-container,
        .main .block-container {{
            width: 100% !important; max-width: 780px !important;
            margin-left: auto !important; margin-right: auto !important;
            padding: 1.5rem 1.5rem 5rem 1.5rem !important;
        }}

        [data-testid="stChatInput"], [data-testid="stChatInputContainer"],
        [data-testid="stBottomBlockContainer"] {{
            max-width: 780px !important; margin-left: auto !important; margin-right: auto !important;
            width: 100% !important; left: 0 !important; right: 0 !important; transform: none !important;
        }}
        [data-testid="stBottom"] {{
            width: 100% !important; left: 0 !important; right: 0 !important;
            display: flex !important; justify-content: center !important; background: {bg} !important;
        }}
        [data-testid="stBottom"] > div {{ width: 100% !important; max-width: 780px !important; margin: 0 auto !important; }}

        h1, h2, h3, h4, h5, h6 {{ color: {text} !important; }}
        h1 {{ font-size: 30px !important; font-weight: 800 !important; letter-spacing: -0.03em !important; margin-bottom: 0.4rem !important; }}
        h2 {{ font-size: 22px !important; font-weight: 700 !important; }}
        p, li, label, .stMarkdown {{ font-size: 15px; line-height: 1.65; color: {text} !important; }}

        .tool-header {{
            display: flex; align-items: center; gap: 14px; margin-bottom: 6px;
            padding-bottom: 16px; border-bottom: 1px solid {border_soft};
        }}
        .tool-header .icon {{
            width: 44px; height: 44px; border-radius: 12px;
            display: flex; align-items: center; justify-content: center; flex-shrink: 0;
        }}
        .tool-header .icon svg {{ width: 22px; height: 22px; }}
        .tool-header .title-block h1 {{ margin: 0 !important; font-size: 26px !important; }}
        .tool-header .title-block p {{ margin: 2px 0 0 0 !important; color: {text_soft} !important; font-size: 14px !important; }}

        .theme-chat .icon {{ background: linear-gradient(135deg, #eef2ff, #e0e7ff); }}
        .theme-cv .icon {{ background: linear-gradient(135deg, #dbeafe, #bfdbfe); }}
        .theme-pass .icon {{ background: linear-gradient(135deg, #d1fae5, #a7f3d0); }}
        .theme-video .icon {{ background: linear-gradient(135deg, #ffedd5, #fed7aa); }}
        .theme-tts .icon {{ background: linear-gradient(135deg, #fce7f3, #fbcfe8); }}
        .theme-photo .icon {{ background: linear-gradient(135deg, #ede9fe, #ddd6fe); }}

        .stButton > button {{
            background: {btn_bg}; color: {text}; border: 1px solid {btn_border};
            border-radius: 10px; padding: 8px 18px; font-weight: 600; font-size: 14px;
            transition: all 0.15s ease; box-shadow: none;
        }}
        .stButton > button:hover {{
            background: {btn_hover}; border-color: #a855f7;
            color: #6c3ef5; transform: translateY(-1px);
        }}
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, #6c3ef5 0%, #a855f7 100%);
            color: #ffffff; border: none; box-shadow: 0 4px 14px rgba(108, 62, 245, 0.3);
        }}
        .stButton > button[kind="primary"]:hover {{
            background: linear-gradient(135deg, #5a2ee0 0%, #9333ea 100%);
            box-shadow: 0 6px 20px rgba(108, 62, 245, 0.4); color: #ffffff;
        }}
        .stDownloadButton > button {{
            background: {btn_bg}; color: {text}; border: 1px solid {btn_border};
            border-radius: 10px; padding: 8px 18px; font-weight: 600; font-size: 14px;
        }}
        .stDownloadButton > button:hover {{ background: {btn_hover}; border-color: #a855f7; color: #6c3ef5; }}

        .stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox > div > div {{
            border-radius: 10px !important; border-color: {btn_border} !important;
            font-size: 14px !important; background: {surface} !important; color: {text} !important;
        }}
        .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {{
            border-color: #a855f7 !important; box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.12) !important;
        }}
        .stTextArea textarea {{ padding: 12px 14px !important; line-height: 1.6 !important; }}

        [data-testid="stForm"] {{
            border: 1px solid {border_soft}; border-radius: 16px;
            padding: 22px 24px; background: {surface}; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
        }}

        [data-testid="stChatMessage"] {{
            background: transparent !important; padding: 20px 0;
            border-bottom: 1px solid {border_soft}; border-radius: 0;
        }}
        [data-testid="stChatMessage"]:last-child {{ border-bottom: none; }}

        [data-testid="stChatInput"] {{
            border-radius: 14px; border: 1px solid {btn_border};
            background: {chat_input_bg}; box-shadow: 0 4px 16px rgba(108, 62, 245, 0.06);
        }}
        [data-testid="stChatInput"]:focus-within {{
            border-color: #a855f7; box-shadow: 0 4px 20px rgba(168, 85, 247, 0.15);
        }}

        code {{
            background: {surface_2} !important; color: #a855f7 !important;
            padding: 3px 8px !important; border-radius: 6px !important;
            font-size: 13px !important; font-weight: 600;
        }}
        pre {{ background: #1e1b4b !important; border-radius: 14px !important; }}
        hr {{ border-color: {border_soft}; margin: 1.5rem 0; }}
        .stCaption, [data-testid="stCaptionContainer"] {{ color: {text_soft}; font-size: 13px; }}

        .treats-hero {{
            display: flex !important; flex-direction: column !important;
            align-items: center !important; justify-content: center !important;
            min-height: 52vh !important; padding: 20px 16px !important;
        }}
        .treats-hero .hero-logo {{
            width: 160px !important; height: 160px !important; margin: 0 auto !important;
            filter: drop-shadow(0 14px 36px rgba(108, 62, 245, 0.22)) !important;
            animation: float 3s ease-in-out infinite;
        }}
        @keyframes float {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-6px); }}
        }}

        details {{
            border: 1px solid {border_soft}; border-radius: 12px;
            padding: 4px 14px; background: {surface_2};
        }}
        details summary {{ font-weight: 600; font-size: 14px; color: {text}; }}

        .token-badge {{
            display: inline-block; padding: 3px 9px; border-radius: 6px;
            font-size: 11px; font-weight: 600; background: {surface_2};
            color: {text_soft}; margin-top: 8px;
        }}

        @media (min-width: 769px) and (max-width: 1100px) {{
            section.main > div.block-container, .main .block-container {{ max-width: 680px !important; }}
            [data-testid="stChatInput"], [data-testid="stBottom"] > div {{ max-width: 680px !important; }}
            .treats-hero .hero-logo {{ width: 140px !important; height: 140px !important; }}
        }}

        @media (max-width: 768px) {{
            [data-testid="stSidebar"] {{ min-width: 82vw !important; max-width: 82vw !important; }}
            section.main > div.block-container, .main .block-container {{
                padding: 0.75rem 0.75rem 3rem 0.75rem !important; max-width: 100% !important;
            }}
            h1 {{ font-size: 22px !important; }}
            .tool-header .icon {{ width: 38px; height: 38px; }}
            .tool-header .title-block h1 {{ font-size: 19px !important; }}
            .treats-hero .hero-logo {{ width: 120px !important; height: 120px !important; }}
            .stButton > button, .stDownloadButton > button {{ font-size: 13px; padding: 10px 14px; }}
            [data-testid="stSidebar"] > div:first-child {{ padding: 1rem 0.5rem 0.75rem 0.5rem !important; }}
        }}
    </style>
    """, unsafe_allow_html=True)


load_css(dark=st.session_state.dark_mode)


# ============================================================
# ERROR
# ============================================================
class TreatsError(Exception):
    pass


# ============================================================
# GROQ CLIENT
# ============================================================
@st.cache_resource(show_spinner=False)
def get_client():
    from groq import Groq
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key:
        raise TreatsError("GROQ_API_KEY not found in secrets.")
    return Groq(api_key=api_key)


AVAILABLE_MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]

# ============================================================
# SYSTEM PROMPTS
# ============================================================
TREATS_SYSTEM_PROMPT = """You are Treats, a helpful, general-purpose AI assistant built with Streamlit and Groq.
You are friendly, concise, and always ready to help with anything the user asks.
Never use emojis unless the user uses them first."""

TITLE_PROMPT = """Based on this first message, generate a short title (3-5 words max).
Return ONLY the title, no quotes, no punctuation at the end.

User message: {message}"""


# ============================================================
# TRIM HISTORY
# ============================================================
MAX_CONTEXT_TOKENS = 6000


def trim_history(messages, max_tokens=MAX_CONTEXT_TOKENS):
    total = 0
    trimmed = []
    for msg in reversed(messages):
        tokens = len(msg["content"]) // 4
        if total + tokens > max_tokens:
            break
        trimmed.insert(0, msg)
        total += tokens
    while trimmed and trimmed[0]["role"] == "assistant":
        trimmed.pop(0)
    return trimmed


def count_tokens(text):
    return max(1, len(text) // 4)


# ============================================================
# CONVERSATION MANAGEMENT
# ============================================================
def init_conversations():
    if "conversations" not in st.session_state:
        st.session_state.conversations = {
            "default": {
                "id": "default", "title": "New chat",
                "messages": [], "created": datetime.now().isoformat(),
            }
        }
        st.session_state.active_conversation = "default"


def get_active_messages():
    init_conversations()
    return st.session_state.conversations[st.session_state.active_conversation]["messages"]


def set_active_messages(msgs):
    st.session_state.conversations[st.session_state.active_conversation]["messages"] = msgs


def new_conversation():
    init_conversations()
    new_id = f"conv_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    st.session_state.conversations[new_id] = {
        "id": new_id, "title": "New chat",
        "messages": [], "created": datetime.now().isoformat(),
    }
    st.session_state.active_conversation = new_id


def delete_conversation(cid):
    if cid in st.session_state.conversations:
        del st.session_state.conversations[cid]
    if st.session_state.active_conversation == cid:
        keys = list(st.session_state.conversations.keys())
        st.session_state.active_conversation = keys[0] if keys else None
    if not st.session_state.conversations:
        new_conversation()


def auto_title(message):
    try:
        client = get_client()
        resp = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": TITLE_PROMPT.format(message=message[:300])}],
            temperature=0.3, max_tokens=20,
        )
        title = resp.choices[0].message.content.strip().strip('"').strip("'")
        add_tokens(resp.usage.total_tokens if resp.usage else 20)
        return title[:40] if title else "New chat"
    except Exception:
        return message[:30] + ("..." if len(message) > 30 else "")


# ============================================================
# IMAGE GENERATION
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_image_models():
    try:
        r = requests.get("https://image.pollinations.ai/models", timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            models = [m.get("name") or m for m in data] if data and isinstance(data[0], dict) else data
        elif isinstance(data, dict):
            models = list(data.keys())
        else:
            models = ["flux", "turbo"]
        models = [str(m) for m in models if m]
        return models if models else ["flux", "turbo"]
    except Exception:
        return ["flux", "turbo", "flux-realism", "flux-anime", "flux-3d"]


def generate_image(prompt, width=1024, height=1024, model="flux", seed=None, enhance=True, nologo=True):
    if not prompt or not prompt.strip():
        raise TreatsError("Please enter an image prompt.")
    encoded = quote(prompt.strip())
    url = f"https://image.pollinations.ai/prompt/{encoded}"
    params = {
        "width": width, "height": height, "model": model,
        "seed": seed if seed is not None else -1,
        "nologo": str(nologo).lower(),
        "enhance": str(enhance).lower(),
    }
    try:
        r = requests.get(url, params=params, timeout=60)
        if r.status_code == 429:
            raise TreatsError("Service is busy. Please try again shortly.")
        r.raise_for_status()
        if not r.content or len(r.content) < 500:
            raise TreatsError("Image came back empty. Try a different prompt.")
        return r.content
    except requests.exceptions.Timeout:
        raise TreatsError("Request timed out. Try a simpler prompt.")
    except requests.exceptions.RequestException as e:
        raise TreatsError(f"Failed to reach image service: {e}")


# ============================================================
# TTS
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_available_voice_ids():
    try:
        import edge_tts
        async def _list():
            return await edge_tts.list_voices()
        voices = asyncio.run(_list())
        return {
            "en": [v["ShortName"] for v in voices if v["Locale"].startswith("en-")],
            "ar": [v["ShortName"] for v in voices if v["Locale"].startswith("ar-")],
            "fr": [v["ShortName"] for v in voices if v["Locale"].startswith("fr-")],
            "es": [v["ShortName"] for v in voices if v["Locale"].startswith("es-")],
            "de": [v["ShortName"] for v in voices if v["Locale"].startswith("de-")],
        }
    except Exception:
        return {"en": [], "ar": [], "fr": [], "es": [], "de": []}


async def _tts_generate(text, voice, rate, pitch, volume):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


# ============================================================
# TOOL ICONS
# ============================================================
TOOL_ICONS = {
    "chat": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>""",
    "cv": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="13" y2="17"/></svg>""",
    "password": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>""",
    "video": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>""",
    "tts": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#ec4899" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d='M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07'/></svg>""",
    "photo": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>""",
}


def render_tool_header(theme_key, title, subtitle):
    st.markdown(
        f'<div class="tool-header theme-{theme_key}">'
        f'<div class="icon">{TOOL_ICONS[theme_key]}</div>'
        f'<div class="title-block"><h1>{title}</h1><p>{subtitle}</p></div>'
        f'</div><div style="height: 24px"></div>',
        unsafe_allow_html=True,
    )


# ============================================================
# SIDEBAR
# ============================================================
init_conversations()

TOOLS = {
    "Chat": "chat",
    "CV Builder": "cv",
    "Password Generator": "password",
    "Video Script": "video",
    "Text to Speech": "tts",
    "Image Generator": "photo",
}

with st.sidebar:
    st.markdown(
        f'<div class="treats-brand">'
        f'<img src="{LOGO_URI}" alt="Treats">'
        f'<span class="name">Treats</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Theme toggle
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown('<div class="sidebar-label" style="padding-top:0;">Theme</div>', unsafe_allow_html=True)
    with c2:
        dark_icon = "🌙" if not st.session_state.dark_mode else "☀️"
        if st.button(dark_icon, key="theme_toggle"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    # TOKEN USAGE PANEL
    st.markdown('<div class="sidebar-label">Usage</div>', unsafe_allow_html=True)

    if st.session_state.dev_mode:
        st.markdown(
            '<div class="token-panel">'
            '<div class="row"><span>Status</span><span class="dev">Developer</span></div>'
            '<div class="row"><span>Limit</span><span class="dev">Unlimited</span></div>'
            f'<div class="row"><span>Used</span><span class="val">{st.session_state.tokens_used:,}</span></div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        used = st.session_state.tokens_used
        remaining = max(0, TOKEN_LIMIT - used)
        pct = min(100, int((used / TOKEN_LIMIT) * 100)) if TOKEN_LIMIT else 0

        if pct >= 90:
            bar_color = "#ef4444"
            status_class = "danger"
            status_text = "Critical"
        elif pct >= 70:
            bar_color = "#f59e0b"
            status_class = "warn"
            status_text = "Warning"
        else:
            bar_color = "#10b981"
            status_class = "dev"
            status_text = "Active"

        st.markdown(
            f'<div class="token-panel">'
            f'<div class="row"><span>Status</span><span class="{status_class}">{status_text}</span></div>'
            f'<div class="row"><span>Used</span><span class="val">{used:,} / {TOKEN_LIMIT:,}</span></div>'
            f'<div class="row"><span>Remaining</span><span class="val">{remaining:,}</span></div>'
            f'<div class="token-bar-wrap"><div class="token-bar-fill" style="width: {pct}%; background: {bar_color};"></div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Tools
    st.markdown('<div class="sidebar-label">Tools</div>', unsafe_allow_html=True)
    choice_label = st.radio(
        "Navigation", list(TOOLS.keys()),
        label_visibility="collapsed", key="nav",
    )
    tool = TOOLS[choice_label]

    # Conversations (Chat only)
    if tool == "chat":
        st.markdown('<div class="sidebar-label">Conversations</div>', unsafe_allow_html=True)
        if st.button("+ New chat", key="new_conv_btn", use_container_width=True):
            new_conversation()
            st.rerun()

        for cid, conv in list(st.session_state.conversations.items()):
            is_active = cid == st.session_state.active_conversation
            label = f"{'● ' if is_active else ''}{conv['title'][:26]}"
            col1, col2 = st.columns([5, 1])
            with col1:
                if st.button(label, key=f"conv_{cid}", use_container_width=True):
                    st.session_state.active_conversation = cid
                    st.rerun()
            with col2:
                if st.button("×", key=f"del_{cid}"):
                    delete_conversation(cid)
                    st.rerun()

    # Model
    st.markdown('<div class="sidebar-label">AI Model</div>', unsafe_allow_html=True)
    model = st.selectbox(
        "AI Model", AVAILABLE_MODELS,
        key="model", label_visibility="collapsed",
    )

    # ---- DEVELOPER BUTTON ----
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    dev_label = "🔓 Developer Mode: ON" if st.session_state.dev_mode else "Developer"
    if st.button(dev_label, key="dev_btn", use_container_width=True):
        if st.session_state.dev_mode:
            st.session_state.dev_mode = False
            st.session_state.show_dev_input = False
            st.rerun()
        else:
            st.session_state.show_dev_input = not st.session_state.show_dev_input
            st.rerun()

    if st.session_state.show_dev_input and not st.session_state.dev_mode:
        with st.form("dev_form", clear_on_submit=True):
            pwd = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Enter developer password")
            submit = st.form_submit_button("Unlock", use_container_width=True)
            if submit:
                correct = st.secrets.get("DEV_PASSWORD", "")
                if correct and pwd == correct:
                    st.session_state.dev_mode = True
                    st.session_state.show_dev_input = False
                    st.toast("Developer mode enabled — unlimited tokens", icon="✅")
                    st.rerun()
                else:
                    st.error("Wrong password")

    # Footer
    st.markdown(
        '<div class="sidebar-footer">'
        '<strong>Treats v2.2</strong><br>'
        'Powered by Groq'
        '</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# TOOL: CHAT
# ============================================================
PROMPT_LIBRARY = [
    ("Explain", "Explain {topic} in simple terms with examples."),
    ("Summarize", "Summarize this in 5 bullet points:\n\n{text}"),
    ("Translate", "Translate this to {language}:\n\n{text}"),
    ("Email", "Write a professional email about {topic}."),
    ("Code", "Write clean Python code that {task}."),
    ("Brainstorm", "Give me 10 creative ideas about {topic}."),
]


def render_chat():
    messages = get_active_messages()

    # Check limit
    if not can_send():
        st.markdown(
            '<div style="background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; '
            'padding: 16px 20px; border-radius: 12px; margin-bottom: 20px;">'
            '<strong>Token limit reached</strong><br>'
            f'You have used {st.session_state.tokens_used:,} of {TOKEN_LIMIT:,} tokens.<br>'
            'Start a new session to reset, or contact the developer for unlimited access.'
            '</div>',
            unsafe_allow_html=True,
        )
        if messages:
            for i, msg in enumerate(messages):
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        return

    if not messages:
        st.markdown(
            f'<div class="treats-hero">'
            f'<img src="{LOGO_URI}" class="hero-logo" alt="Treats">'
            f'</div>',
            unsafe_allow_html=True,
        )

    if not messages:
        with st.expander("Prompt Library"):
            cols = st.columns(3)
            for i, (label, template) in enumerate(PROMPT_LIBRARY):
                with cols[i % 3]:
                    if st.button(label, key=f"pl_{i}", use_container_width=True):
                        st.session_state.pl_template = template
                        st.rerun()

    for i, msg in enumerate(messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                tokens = count_tokens(msg["content"])
                st.markdown(
                    f'<div class="token-badge">{tokens} tokens</div>',
                    unsafe_allow_html=True,
                )
                if i == len(messages) - 1:
                    cols = st.columns([1, 1, 8])
                    with cols[0]:
                        if st.button("Copy", key=f"copy_{i}"):
                            st.session_state[f"show_copy_{i}"] = not st.session_state.get(f"show_copy_{i}", False)
                    with cols[1]:
                        if st.button("Retry", key=f"regen_{i}"):
                            new_msgs = messages[:i]
                            set_active_messages(new_msgs)
                            st.rerun()

                if st.session_state.get(f"show_copy_{i}", False):
                    st.code(msg["content"], language=None)

    if messages:
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("New chat", key="new_chat_inline", use_container_width=True):
                new_conversation()
                st.rerun()
        with c2:
            with st.expander("Export"):
                col1, col2 = st.columns(2)
                with col1:
                    md = "\n\n".join(f"**{m['role'].capitalize()}:** {m['content']}" for m in messages)
                    st.download_button(
                        "Markdown", data=md,
                        file_name=f"treats_chat_{datetime.now():%Y%m%d_%H%M}.md",
                        mime="text/markdown", use_container_width=True,
                    )
                with col2:
                    st.download_button(
                        "JSON",
                        data=json.dumps(messages, ensure_ascii=False, indent=2),
                        file_name=f"treats_chat_{datetime.now():%Y%m%d_%H%M}.json",
                        mime="application/json", use_container_width=True,
                    )

    prompt = st.chat_input("Message Treats...")
    if prompt:
        if not can_send():
            st.error("Token limit reached.")
            st.stop()
        messages.append({"role": "user", "content": prompt})
        set_active_messages(messages)
        cid = st.session_state.active_conversation
        if st.session_state.conversations[cid]["title"] == "New chat":
            st.session_state.conversations[cid]["title"] = auto_title(prompt)
        st.rerun()

    if messages and messages[-1]["role"] == "user":
        try:
            client = get_client()
            full_messages = [{"role": "system", "content": TREATS_SYSTEM_PROMPT}] + messages
            history = trim_history(full_messages)
            stream = client.chat.completions.create(
                model=model,
                messages=history,
                temperature=0.7,
                stream=True,
                stream_options={"include_usage": True},
            )
            with st.chat_message("assistant"):
                placeholder = st.empty()
                full = ""
                total_tokens = 0
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        delta = chunk.choices[0].delta.content
                        full += delta
                        placeholder.markdown(full + "▌")
                    if hasattr(chunk, "usage") and chunk.usage:
                        total_tokens = chunk.usage.total_tokens
                placeholder.markdown(full)

            if total_tokens == 0:
                # Fallback estimate
                total_tokens = sum(count_tokens(m["content"]) for m in history) + count_tokens(full)
            add_tokens(total_tokens)

            messages.append({"role": "assistant", "content": full})
            set_active_messages(messages)
            st.rerun()
        except TreatsError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Unexpected error: {e}")


# ============================================================
# TOOL: CV BUILDER
# ============================================================
CV_TEMPLATES = {
    "Modern": "Use a modern layout with a colored header, clean two-column layout, and contemporary typography.",
    "Classic": "Use a traditional professional layout with clear sections, simple typography, and formal structure.",
    "Creative": "Use a creative layout with unique section styling, elegant typography, and distinctive visual elements.",
}


def render_cv():
    render_tool_header("cv", "CV Builder", "Generate a professional CV in seconds")

    if not can_send():
        st.warning("Token limit reached. Cannot generate more content.")
        return

    template = st.radio("Template", list(CV_TEMPLATES.keys()), horizontal=True)

    with st.form("cv_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name")
            role = st.text_input("Target Role")
            edu = st.text_input("Education")
        with col2:
            lang = st.selectbox("Language", ["English", "Arabic"])
            tone = st.selectbox("Tone", ["Professional", "Concise", "Academic"])
            skills = st.text_input("Skills (comma-separated)")

        exp = st.text_area("Experience", placeholder="One bullet per line", height=140)
        submitted = st.form_submit_button("Generate CV", type="primary", use_container_width=True)

    if submitted:
        if not name or not role:
            st.warning("Name and role are required.")
            return
        try:
            client = get_client()
            prompt = f"""Write a professional CV in {lang} with a {tone} tone.
Style: {CV_TEMPLATES[template]}
Name: {name}
Role: {role}
Experience: {exp}
Education: {edu}
Skills: {skills}
Format in clean Markdown with clear headings."""
            with st.spinner("Generating..."):
                resp = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.6,
                    stream_options={"include_usage": True},
                )
            cv_text = resp.choices[0].message.content
            if resp.usage:
                add_tokens(resp.usage.total_tokens)
            st.markdown("---")
            st.markdown(cv_text)
            col1, col2 = st.columns(2)
            with col1:
                st.download_button("Download Markdown", cv_text, "cv.md", "text/markdown", use_container_width=True)
            with col2:
                st.download_button("Download Text", cv_text, "cv.txt", "text/plain", use_container_width=True)
        except TreatsError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Error: {e}")


# ============================================================
# TOOL: PASSWORD GENERATOR (no tokens used)
# ============================================================
def render_password():
    import string
    render_tool_header("password", "Password Generator", "Create strong, secure passwords")

    col1, col2, col3 = st.columns(3)
    with col1:
        length = st.slider("Length", 8, 64, 16)
    with col2:
        use_numbers = st.checkbox("Include numbers", value=True)
    with col3:
        use_symbols = st.checkbox("Include symbols", value=True)

    chars = string.ascii_letters
    if use_numbers: chars += string.digits
    if use_symbols: chars += "!@#$%^&*()-_=+"

    if st.button("Generate Password", type="primary", use_container_width=True):
        pwd = "".join(random.choice(chars) for _ in range(length))
        st.code(pwd, language=None)
        st.download_button("Download", pwd, "password.txt", use_container_width=True)


# ============================================================
# TOOL: VIDEO SCRIPT
# ============================================================
def render_video():
    render_tool_header("video", "Video Script", "Generate scripts with scene-by-scene storyboards")

    if not can_send():
        st.warning("Token limit reached.")
        return

    with st.form("video_form"):
        topic = st.text_input("Topic")
        col1, col2 = st.columns(2)
        with col1:
            duration = st.selectbox("Duration", ["30 seconds", "60 seconds", "3 minutes", "5 minutes"])
            lang = st.selectbox("Language", ["English", "Arabic"])
        with col2:
            style = st.selectbox("Style", ["Educational", "Promotional", "Storytelling", "Entertainment"])
            platform = st.selectbox("Platform", ["YouTube", "TikTok", "Instagram", "LinkedIn"])
        submitted = st.form_submit_button("Generate Script", type="primary", use_container_width=True)

    if submitted:
        if not topic:
            st.warning("Please enter a topic.")
            return
        try:
            client = get_client()
            prompt = f"""Write a video script in {lang} for {platform}.
Topic: {topic}
Duration: {duration}
Style: {style}
Break into scenes with a storyboard."""
            with st.spinner("Generating..."):
                resp = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                )
            script = resp.choices[0].message.content
            if resp.usage:
                add_tokens(resp.usage.total_tokens)
            st.markdown("---")
            st.markdown(script)
            st.download_button("Download Markdown", script, "script.md", "text/markdown", use_container_width=True)
        except TreatsError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Error: {e}")


# ============================================================
# TOOL: TEXT TO SPEECH (no tokens used)
# ============================================================
LANG_LABELS = {"en": "English", "ar": "Arabic", "fr": "French", "es": "Spanish", "de": "German"}


def render_tts():
    render_tool_header("tts", "Text to Speech", "Convert text into natural-sounding speech")

    voices = fetch_available_voice_ids()
    avail = [k for k in voices.keys() if voices[k]]

    if not avail:
        st.warning("No voices available right now.")
        return

    lang_choice = st.radio(
        "Language", avail,
        format_func=lambda x: LANG_LABELS.get(x, x),
        horizontal=True,
    )
    voice_pool = voices[lang_choice]

    voice = st.selectbox("Voice", voice_pool, key="tts_voice")
    text = st.text_area("Text", height=160, placeholder="Enter the text to convert...")

    col1, col2, col3 = st.columns(3)
    with col1:
        rate_val = st.slider("Rate", 0.5, 2.0, 1.0, 0.1)
    with col2:
        pitch_val = st.slider("Pitch (Hz)", -50, 50, 0, 5)
    with col3:
        vol_val = st.slider("Volume", 0, 100, 100, 5)

    rate = f"{'+' if rate_val >= 1 else ''}{int((rate_val - 1) * 100)}%"
    pitch = f"{'+' if pitch_val >= 0 else ''}{pitch_val}Hz"
    volume = f"+{vol_val}%"

    if st.button("Generate Audio", type="primary", use_container_width=True):
        if not text.strip():
            st.warning("Please enter some text.")
            return
        try:
            with st.spinner("Generating..."):
                audio = asyncio.run(_tts_generate(text, voice, rate, pitch, volume))
            st.audio(audio, format="audio/mp3")
            st.download_button("Download MP3", audio, "treats_tts.mp3", "audio/mpeg", use_container_width=True)
        except Exception as e:
            st.error(f"Generation failed: {e}")


# ============================================================
# TOOL: IMAGE GENERATOR (no tokens used)
# ============================================================
def render_photo():
    render_tool_header("photo", "Image Generator", "Create images from text descriptions")

    if "image_gallery" not in st.session_state:
        st.session_state.image_gallery = []

    with st.spinner("Loading models..."):
        models = fetch_image_models()

    prompt = st.text_area(
        "Prompt",
        placeholder="A cat sipping coffee in a Parisian cafe, cinematic lighting, 4K",
        height=110,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        model_img = st.selectbox("Model", models, key="photo_model")
    with col2:
        aspect = st.selectbox(
            "Aspect Ratio",
            ["1:1 (1024×1024)", "16:9 (1344×768)", "9:16 (768×1344)", "4:3 (1152×896)"],
            key="photo_aspect",
        )
    with col3:
        enhance = st.checkbox("Auto-enhance prompt", value=True, key="photo_enhance")

    dims = {
        "1:1 (1024×1024)": (1024, 1024),
        "16:9 (1344×768)": (1344, 768),
        "9:16 (768×1344)": (768, 1344),
        "4:3 (1152×896)": (1152, 896),
    }
    w, h = dims[aspect]

    col1, col2 = st.columns([3, 1])
    with col1:
        seed = st.number_input("Seed (0 = random)", min_value=0, value=0, step=1, key="photo_seed")
    with col2:
        st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
        if st.button("Randomize", key="photo_random", use_container_width=True):
            st.session_state["photo_seed"] = random.randint(1, 999999)
            st.rerun()

    use_seed = int(seed) if seed > 0 else None

    if st.button("Generate Image", type="primary", use_container_width=True):
        if not prompt.strip():
            st.warning("Please enter an image prompt.")
            return
        try:
            with st.spinner("Generating image..."):
                img_bytes = generate_image(
                    prompt=prompt, width=w, height=h,
                    model=model_img, seed=use_seed, enhance=enhance,
                )
            st.session_state["last_image"] = img_bytes
            st.session_state["last_prompt"] = prompt
            st.session_state.image_gallery.append({"prompt": prompt, "bytes": img_bytes, "time": datetime.now().isoformat()})
        except TreatsError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Unexpected error: {e}")

    if "last_image" in st.session_state:
        st.markdown("---")
        st.image(st.session_state["last_image"], caption=st.session_state.get("last_prompt", ""))
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download PNG",
                data=st.session_state["last_image"],
                file_name=f"treats_photo_{datetime.now():%Y%m%d_%H%M%S}.png",
                mime="image/png", use_container_width=True,
            )
        with col2:
            if st.button("Regenerate", key="photo_regen", use_container_width=True):
                new_seed = random.randint(1, 999999)
                try:
                    with st.spinner("Regenerating..."):
                        img_bytes = generate_image(
                            prompt=st.session_state["last_prompt"],
                            width=w, height=h, model=model_img,
                            seed=new_seed, enhance=enhance,
                        )
                    st.session_state["last_image"] = img_bytes
                    st.rerun()
                except TreatsError as e:
                    st.error(str(e))

    if st.session_state.image_gallery:
        with st.expander(f"Gallery ({len(st.session_state.image_gallery)})"):
            gcols = st.columns(3)
            for idx, item in enumerate(reversed(st.session_state.image_gallery)):
                with gcols[idx % 3]:
                    st.image(item["bytes"], caption=item["prompt"][:40], use_container_width=True)


# ============================================================
# ROUTER
# ============================================================
if tool == "chat":
    render_chat()
elif tool == "cv":
    render_cv()
elif tool == "password":
    render_password()
elif tool == "video":
    render_video()
elif tool == "tts":
    render_tts()
elif tool == "photo":
    render_photo()
