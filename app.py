import streamlit as st
import requests
import json
import random
import asyncio
import io
import base64
import zipfile
import streamlit.components.v1 as components
from urllib.parse import quote
from datetime import datetime, date

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Treats",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

TOKEN_LIMIT = 5000
TOKEN_WARN_AT = 0.8

# ============================================================
# LOGO
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
# SESSION STATE
# ============================================================
defaults = {
    "dark_mode": False,
    "tokens_used": 0,
    "token_date": date.today().isoformat(),
    "dev_mode": False,
    "show_dev_input": False,
    "density": "comfortable",
    "font_size": "medium",
    "conv_search": "",
    "rename_conv": None,
    "warned_80": False,
    "show_settings": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# DAILY RESET
# ============================================================
def check_daily_reset():
    today = date.today().isoformat()
    if st.session_state.token_date != today:
        st.session_state.token_date = today
        st.session_state.tokens_used = 0
        st.session_state.warned_80 = False

check_daily_reset()

# ============================================================
# TOKEN HELPERS
# ============================================================
def is_unlimited(): return st.session_state.dev_mode
def can_send():
    if is_unlimited(): return True
    return st.session_state.tokens_used < TOKEN_LIMIT
def add_tokens(n):
    if not is_unlimited():
        st.session_state.tokens_used += n
        if (st.session_state.tokens_used >= TOKEN_LIMIT * TOKEN_WARN_AT
                and not st.session_state.warned_80):
            st.session_state.warned_80 = True
            st.toast(f"⚠️ You've used {int(TOKEN_WARN_AT*100)}% of your daily tokens", icon="⚠️")

# ============================================================
# CSS
# ============================================================
def load_css(dark=False, density="comfortable", font_size="medium"):
    if dark:
        bg="#0d0d0d"; sbg1="#161616"; sbg2="#1a1a1a"; surf="#1a1a1a"; surf2="#232323"
        bord="#2a2a2a"; bsoft="#232323"; txt="#ececec"; tsoft="#a0a0a0"; tmuted="#6b6b6b"
        hov="#232323"; act="#2d2d2d"; bbtn="#1a1a1a"; bhv="#232323"; bbd="#2a2a2a"; cib="#1a1a1a"
    else:
        bg="#ffffff"; sbg1="#faf9ff"; sbg2="#f5f3ff"; surf="#ffffff"; surf2="#f7f7f8"
        bord="#ececec"; bsoft="#f3f4f6"; txt="#0d0d0d"; tsoft="#6b7280"; tmuted="#9ca3af"
        hov="#ffffff"; act="#ffffff"; bbtn="#ffffff"; bhv="#f9fafb"; bbd="#e5e7eb"; cib="#ffffff"

    fs_base = {"small": "13px", "medium": "15px", "large": "17px"}[font_size]
    fs_h1 = {"small": "26px", "medium": "30px", "large": "34px"}[font_size]
    fs_tool = {"small": "22px", "medium": "26px", "large": "30px"}[font_size]
    msg_pad = "12px 0" if density == "compact" else "22px 0"

    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"] {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}

        #MainMenu, footer, [data-testid="stDecoration"], [data-testid="stStatusWidget"],
        [data-testid="stAppDeployButton"], [data-testid="stMainMenu"],
        [data-testid="stToolbarActions"] {{ display: none !important; }}
        header[data-testid="stHeader"] {{ background: transparent !important; box-shadow: none !important; }}

        html, body, .stApp, [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main, section.main, [data-testid="stMain"] {{
            background: {bg} !important; color: {txt} !important;
        }}

        * {{ -webkit-tap-highlight-color: transparent; }}
        button, .stButton, .stDownloadButton, label, h1,h2,h3,h4,h5,h6,
        .tool-header, .treats-brand, .sidebar-footer, .treats-hero, [data-testid="stSidebar"] {{
            -webkit-user-select: none; user-select: none; -webkit-touch-callout: none;
        }}
        [data-testid="stChatMessage"], .stMarkdown, .stTextArea textarea, .stTextInput input,
        pre, code {{ -webkit-user-select: text; user-select: text; }}

        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {sbg1} 0%, {sbg2} 100%) !important;
            border-right: 1px solid {bord} !important;
            min-width: 290px !important; max-width: 290px !important;
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
            font-size: 10px; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.1em; color: {tmuted}; padding: 10px 14px 6px 14px; margin-top: 6px;
        }}

        [data-testid="stSidebar"] [data-testid="stRadio"] > div[role="radiogroup"] {{ gap: 3px !important; display: flex; flex-direction: column; }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] {{
            display: flex !important; align-items: center !important; gap: 12px !important;
            padding: 10px 14px !important; margin: 0 !important; border-radius: 10px !important;
            cursor: pointer !important; transition: all 0.15s ease !important;
            font-size: 14px !important; font-weight: 500 !important; color: {txt} !important;
            width: 100% !important; background: transparent !important; border: 1px solid transparent !important;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover {{ background: {hov} !important; border-color: {bord} !important; transform: translateX(2px); }}
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
        label[data-baseweb="radio"]:has(input:checked) {{ background: {act} !important; border-color: {bord} !important; font-weight: 700 !important; }}
        [data-testid="stSidebar"] [data-testid="stRadio"] > label:first-child {{ display: none !important; }}

        [data-testid="stSidebar"] [data-testid="stSelectbox"] > label {{
            font-size: 10px !important; font-weight: 700 !important; text-transform: uppercase !important;
            letter-spacing: 0.1em !important; color: {tmuted} !important; padding-left: 2px !important;
        }}
        [data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {{
            background: {surf} !important; border: 1px solid {bord} !important;
            border-radius: 10px !important; font-size: 13px !important; color: {txt} !important;
        }}

        .sidebar-footer {{
            padding: 14px; color: {tmuted}; font-size: 11px; line-height: 1.7;
            border-top: 1px solid {bord}; margin-top: 16px;
        }}
        .sidebar-footer strong {{ color: #6c3ef5; font-weight: 600; }}
        .sidebar-footer .kbd {{
            display: inline-block; padding: 1px 6px; background: {surf2};
            border: 1px solid {bord}; border-radius: 4px; font-size: 10px;
            font-family: monospace; color: {tsoft}; margin: 0 2px;
        }}

        .token-panel {{
            background: {surf2}; border: 1px solid {bord};
            border-radius: 10px; padding: 10px 14px; margin: 6px 0; font-size: 12px; color: {tsoft};
        }}
        .token-panel .row {{ display: flex; justify-content: space-between; margin: 4px 0; }}
        .token-panel .val {{ color: {txt}; font-weight: 700; }}
        .token-panel .dev {{ color: #10b981; font-weight: 700; }}
        .token-panel .warn {{ color: #f59e0b; font-weight: 700; }}
        .token-panel .danger {{ color: #ef4444; font-weight: 700; }}
        .token-bar-wrap {{ height: 6px; background: {bord}; border-radius: 3px; overflow: hidden; margin: 8px 0 4px 0; }}
        .token-bar-fill {{ height: 100%; border-radius: 3px; transition: width 0.3s; }}

        section.main, [data-testid="stMain"] {{
            display: flex !important; flex-direction: column !important;
            align-items: center !important; width: 100% !important;
        }}
        section.main > div.block-container, .main .block-container {{
            width: 100% !important; max-width: 800px !important;
            margin: 0 auto !important; padding: 1.5rem 1.5rem 5rem 1.5rem !important;
        }}

        [data-testid="stChatInput"], [data-testid="stBottomBlockContainer"] {{
            max-width: 800px !important; margin-left: auto !important; margin-right: auto !important;
            width: 100% !important; left: 0 !important; right: 0 !important;
        }}
        [data-testid="stBottom"], [data-testid="stBottom"] > div {{ background: {bg} !important; }}
        [data-testid="stBottom"] {{ width: 100% !important; display: flex !important; justify-content: center !important; }}
        [data-testid="stBottom"] > div {{ max-width: 800px !important; margin: 0 auto !important; }}

        [data-testid="stChatInput"] {{
            border-radius: 14px !important; border: 1px solid {bbd} !important;
            background: {cib} !important; box-shadow: 0 4px 16px rgba(108, 62, 245, 0.06) !important;
            transition: all 0.2s ease !important;
        }}
        [data-testid="stChatInput"]:focus-within {{
            border-color: #a855f7 !important;
            box-shadow: 0 4px 20px rgba(168, 85, 247, 0.15) !important;
        }}
        [data-testid="stChatInput"] textarea {{ background: transparent !important; color: {txt} !important; }}
        [data-testid="stChatInput"] textarea::placeholder {{ color: {tsoft} !important; }}

        h1, h2, h3, h4, h5, h6 {{ color: {txt} !important; }}
        h1 {{ font-size: {fs_h1} !important; font-weight: 800 !important; letter-spacing: -0.03em !important; }}
        p, li, label, .stMarkdown {{ font-size: {fs_base}; line-height: 1.65; color: {txt} !important; }}

        .tool-header {{
            display: flex; align-items: center; gap: 14px; margin-bottom: 6px;
            padding-bottom: 16px; border-bottom: 1px solid {bsoft};
        }}
        .tool-header .icon {{
            width: 44px; height: 44px; border-radius: 12px;
            display: flex; align-items: center; justify-content: center; flex-shrink: 0;
        }}
        .tool-header .icon svg {{ width: 22px; height: 22px; }}
        .tool-header .title-block h1 {{ margin: 0 !important; font-size: {fs_tool} !important; }}
        .tool-header .title-block p {{ margin: 2px 0 0 0 !important; color: {tsoft} !important; font-size: 13px !important; }}

        .theme-chat .icon {{ background: linear-gradient(135deg, #eef2ff, #e0e7ff); }}
        .theme-cv .icon {{ background: linear-gradient(135deg, #dbeafe, #bfdbfe); }}
        .theme-pass .icon {{ background: linear-gradient(135deg, #d1fae5, #a7f3d0); }}
        .theme-video .icon {{ background: linear-gradient(135deg, #ffedd5, #fed7aa); }}
        .theme-tts .icon {{ background: linear-gradient(135deg, #fce7f3, #fbcfe8); }}
        .theme-photo .icon {{ background: linear-gradient(135deg, #ede9fe, #ddd6fe); }}

        .stButton > button {{
            background: {bbtn}; color: {txt}; border: 1px solid {bbd};
            border-radius: 10px; padding: 8px 16px; font-weight: 600; font-size: 13px;
            transition: all 0.15s ease;
        }}
        .stButton > button:hover {{
            background: {bhv}; border-color: #a855f7; color: #6c3ef5;
            transform: translateY(-1px); box-shadow: 0 2px 8px rgba(108, 62, 245, 0.1);
        }}
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, #6c3ef5 0%, #a855f7 100%);
            color: #ffffff; border: none;
            box-shadow: 0 4px 14px rgba(108, 62, 245, 0.3);
        }}
        .stButton > button[kind="primary"]:hover {{
            background: linear-gradient(135deg, #5a2ee0 0%, #9333ea 100%);
            box-shadow: 0 6px 20px rgba(108, 62, 245, 0.4); color: #ffffff;
        }}
        .stDownloadButton > button {{
            background: {bbtn}; color: {txt}; border: 1px solid {bbd};
            border-radius: 10px; padding: 8px 16px; font-weight: 600; font-size: 13px;
        }}
        .stDownloadButton > button:hover {{ background: {bhv}; border-color: #a855f7; color: #6c3ef5; }}

        .stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox > div > div {{
            border-radius: 10px !important; border-color: {bbd} !important;
            font-size: 14px !important; background: {surf} !important; color: {txt} !important;
        }}
        .stTextInput input:focus, .stTextArea textarea:focus {{
            border-color: #a855f7 !important; box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.12) !important;
        }}

        [data-testid="stForm"] {{
            border: 1px solid {bsoft}; border-radius: 16px;
            padding: 22px 24px; background: {surf};
        }}

        [data-testid="stChatMessage"] {{
            background: transparent !important; padding: {msg_pad};
            border-bottom: 1px solid {bsoft}; border-radius: 0;
            animation: fadeIn 0.3s ease;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(6px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        [data-testid="stChatMessage"]:last-child {{ border-bottom: none; }}

        code {{ background: {surf2} !important; color: #a855f7 !important; padding: 3px 8px !important; border-radius: 6px !important; font-weight: 600; }}
        pre {{ background: #1e1b4b !important; border-radius: 14px !important; }}
        hr {{ border-color: {bsoft}; }}

        .treats-hero {{
            display: flex !important; flex-direction: column !important;
            align-items: center !important; justify-content: center !important;
            min-height: 55vh !important; text-align: center !important;
        }}
        .treats-hero .hero-logo {{
            width: 160px !important; height: 160px !important;
            filter: drop-shadow(0 14px 36px rgba(108, 62, 245, 0.22));
            animation: float 3s ease-in-out infinite;
        }}
        .treats-hero .greeting {{
            font-size: 26px; font-weight: 700; letter-spacing: -0.02em;
            background: linear-gradient(135deg, #1f2937 0%, #6c3ef5 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-top: 24px; color: {txt};
        }}
        @keyframes float {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-8px); }}
        }}

        details {{ border: 1px solid {bsoft}; border-radius: 12px; padding: 4px 14px; background: {surf2}; }}
        details summary {{ font-weight: 600; font-size: 13px; color: {txt} !important; }}

        .token-badge {{
            display: inline-block; padding: 2px 8px; border-radius: 6px;
            font-size: 10px; font-weight: 600; background: {surf2}; color: {tsoft};
            margin-right: 6px;
        }}
        .time-badge {{
            display: inline-block; font-size: 10px; color: {tmuted};
            margin-left: 4px;
        }}

        .empty-state {{
            text-align: center; padding: 40px 20px; color: {tsoft};
            border: 2px dashed {bord}; border-radius: 16px; margin: 20px 0;
        }}
        .empty-state .icon {{ font-size: 42px; margin-bottom: 10px; opacity: 0.6; }}
        .empty-state .title {{ font-size: 16px; font-weight: 600; color: {txt}; margin-bottom: 6px; }}
        .empty-state .desc {{ font-size: 13px; }}

        @media (max-width: 768px) {{
            [data-testid="stSidebar"] {{ min-width: 84vw !important; max-width: 84vw !important; }}
            .main .block-container {{ padding: 0.75rem !important; }}
            .treats-hero .hero-logo {{ width: 120px !important; height: 120px !important; }}
        }}
    </style>
    """, unsafe_allow_html=True)

load_css(
    dark=st.session_state.dark_mode,
    density=st.session_state.density,
    font_size=st.session_state.font_size,
)

# ============================================================
# INJECT JS — Force style on sidebar toggle button
# ============================================================
components.html("""
<script>
(function() {
    const doc = window.parent.document;

    function styleToggle() {
        const selectors = [
            '[data-testid="stSidebarCollapsedControl"]',
            '[data-testid="stSidebarCollapseButton"]',
            '[data-testid="collapsedControl"]',
            'button[kind="headerNoPadding"]',
            'button[kind="header"]'
        ];

        const STYLE = 'background:#6c3ef5 !important;' +
                      'background-color:#6c3ef5 !important;' +
                      'background-image:none !important;' +
                      'color:#ffffff !important;' +
                      'border:none !important;' +
                      'border-radius:12px !important;' +
                      'padding:10px !important;' +
                      'margin:12px !important;' +
                      'box-shadow:0 4px 16px rgba(108,62,245,0.5) !important;' +
                      'z-index:2147483647 !important;' +
                      'position:fixed !important;' +
                      'top:8px !important;' +
                      'left:8px !important;' +
                      'width:44px !important;' +
                      'height:44px !important;' +
                      'display:flex !important;' +
                      'align-items:center !important;' +
                      'justify-content:center !important;' +
                      'cursor:pointer !important;' +
                      'opacity:1 !important;' +
                      'visibility:visible !important;';

        selectors.forEach(function(sel) {
            doc.querySelectorAll(sel).forEach(function(el) {
                el.style.cssText = STYLE;
                const btn = el.querySelector('button') || el;
                if (btn && btn !== el) btn.style.cssText = STYLE;
                el.querySelectorAll('svg').forEach(function(svg) {
                    svg.style.fill = '#ffffff';
                    svg.style.color = '#ffffff';
                    svg.style.stroke = '#ffffff';
                    svg.style.width = '22px';
                    svg.style.height = '22px';
                });
                el.querySelectorAll('span').forEach(function(sp) {
                    sp.style.color = '#ffffff';
                });
            });
        });
    }

    styleToggle();
    setInterval(styleToggle, 400);
    try {
        const observer = new MutationObserver(styleToggle);
        observer.observe(doc.body, { childList: true, subtree: true });
    } catch(e) {}
})();
</script>
""", height=0)

# ============================================================
# ERROR + GROQ
# ============================================================
class TreatsError(Exception): pass

@st.cache_resource(show_spinner=False)
def get_client():
    from groq import Groq
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key: raise TreatsError("GROQ_API_KEY not found in secrets.")
    return Groq(api_key=api_key)

AVAILABLE_MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]

SYS_PROMPT = """You are Treats, a helpful, general-purpose AI assistant.
Friendly, concise, and professional. Never use emojis unless the user uses them first."""

TITLE_PROMPT = """Generate a short title (3-5 words). Return ONLY the title.

Message: {message}"""

# ============================================================
# HELPERS
# ============================================================
MAX_CTX = 6000

def trim_history(msgs, max_tokens=MAX_CTX):
    total = 0; out = []
    for m in reversed(msgs):
        t = len(m["content"]) // 4
        if total + t > max_tokens: break
        out.insert(0, m); total += t
    while out and out[0]["role"] == "assistant": out.pop(0)
    return out

def count_tokens(txt): return max(1, len(txt) // 4)
def count_words(txt): return len(txt.split())

def get_greeting():
    h = datetime.now().hour
    if h < 12: return "Good morning"
    elif h < 17: return "Good afternoon"
    else: return "Good evening"

def fmt_time(iso):
    try: return datetime.fromisoformat(iso).strftime("%H:%M")
    except: return ""

def copy_to_clipboard(text, key):
    js_text = json.dumps(text)
    components.html(f"""
    <script>
    (function() {{
        var ta = document.createElement('textarea');
        ta.value = {js_text};
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        try {{ document.execCommand('copy'); }} catch(e) {{}}
        document.body.removeChild(ta);
    }})();
    </script>
    """, height=0)

# ============================================================
# CONVERSATIONS
# ============================================================
def init_convs():
    if "conversations" not in st.session_state:
        st.session_state.conversations = {
            "default": {"id":"default","title":"New chat","messages":[],
                        "created": datetime.now().isoformat()}
        }
        st.session_state.active_conversation = "default"

def get_msgs():
    init_convs()
    return st.session_state.conversations[st.session_state.active_conversation]["messages"]

def set_msgs(msgs):
    st.session_state.conversations[st.session_state.active_conversation]["messages"] = msgs

def new_conv():
    init_convs()
    nid = f"c_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    st.session_state.conversations[nid] = {
        "id":nid,"title":"New chat","messages":[],
        "created": datetime.now().isoformat()
    }
    st.session_state.active_conversation = nid

def del_conv(cid):
    if cid in st.session_state.conversations:
        del st.session_state.conversations[cid]
    if st.session_state.active_conversation == cid:
        keys = list(st.session_state.conversations.keys())
        st.session_state.active_conversation = keys[0] if keys else None
    if not st.session_state.conversations: new_conv()

def dup_conv(cid):
    if cid in st.session_state.conversations:
        src = st.session_state.conversations[cid]
        nid = f"c_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        st.session_state.conversations[nid] = {
            "id":nid,
            "title": src["title"] + " (copy)",
            "messages": [dict(m) for m in src["messages"]],
            "created": datetime.now().isoformat()
        }
        st.session_state.active_conversation = nid

def auto_title(msg):
    try:
        c = get_client()
        r = c.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role":"user","content":TITLE_PROMPT.format(message=msg[:300])}],
            temperature=0.3, max_tokens=20,
        )
        t = r.choices[0].message.content.strip().strip('"').strip("'")
        return t[:40] if t else msg[:30]
    except:
        return msg[:30] + ("..." if len(msg) > 30 else "")

# ============================================================
# IMAGE
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_img_models():
    try:
        r = requests.get("https://image.pollinations.ai/models", timeout=10)
        r.raise_for_status(); d = r.json()
        if isinstance(d, list):
            m = [x.get("name") or x for x in d] if d and isinstance(d[0], dict) else d
        elif isinstance(d, dict): m = list(d.keys())
        else: m = ["flux","turbo"]
        m = [str(x) for x in m if x]
        return m if m else ["flux","turbo"]
    except: return ["flux","turbo","flux-realism","flux-anime","flux-3d"]

def gen_image(prompt, w=1024, h=1024, model="flux", seed=None, enhance=True, nologo=True):
    if not prompt or not prompt.strip(): raise TreatsError("Please enter a prompt.")
    url = f"https://image.pollinations.ai/prompt/{quote(prompt.strip())}"
    p = {"width":w,"height":h,"model":model,
         "seed":seed if seed is not None else -1,
         "nologo":str(nologo).lower(),"enhance":str(enhance).lower()}
    try:
        r = requests.get(url, params=p, timeout=60)
        if r.status_code == 429: raise TreatsError("Service is busy.")
        r.raise_for_status()
        if not r.content or len(r.content) < 500: raise TreatsError("Empty image.")
        return r.content
    except requests.exceptions.Timeout: raise TreatsError("Request timed out.")
    except requests.exceptions.RequestException as e: raise TreatsError(f"Failed: {e}")

# ============================================================
# TTS
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_voices():
    try:
        import edge_tts
        async def _l(): return await edge_tts.list_voices()
        v = asyncio.run(_l())
        return {
            "en":[x["ShortName"] for x in v if x["Locale"].startswith("en-")],
            "ar":[x["ShortName"] for x in v if x["Locale"].startswith("ar-")],
            "fr":[x["ShortName"] for x in v if x["Locale"].startswith("fr-")],
            "es":[x["ShortName"] for x in v if x["Locale"].startswith("es-")],
            "de":[x["ShortName"] for x in v if x["Locale"].startswith("de-")],
        }
    except: return {"en":[],"ar":[],"fr":[],"es":[],"de":[]}

async def _tts(text, voice, rate, pitch, volume):
    import edge_tts
    c = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
    buf = io.BytesIO()
    async for ch in c.stream():
        if ch["type"] == "audio": buf.write(ch["data"])
    return buf.getvalue()

# ============================================================
# TOOL ICONS
# ============================================================
ICONS = {
    "chat": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>""",
    "cv": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>""",
    "password": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>""",
    "video": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2.2"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>""",
    "tts": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#ec4899" stroke-width="2.2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d='M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07'/></svg>""",
    "photo": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2.2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>""",
}

def tool_header(k, title, sub):
    st.markdown(
        f'<div class="tool-header theme-{k}"><div class="icon">{ICONS[k]}</div>'
        f'<div class="title-block"><h1>{title}</h1><p>{sub}</p></div></div>'
        f'<div style="height:24px"></div>', unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
init_convs()

TOOLS = {
    "Chat":"chat","CV Builder":"cv","Password Generator":"password",
    "Video Script":"video","Text to Speech":"tts","Image Generator":"photo",
}

with st.sidebar:
    st.markdown(
        f'<div class="treats-brand"><img src="{LOGO_URI}" alt="Treats">'
        f'<span class="name">Treats</span></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.markdown('<div class="sidebar-label" style="padding-top:0;">Display</div>', unsafe_allow_html=True)
    with c2:
        if st.button("🌙" if not st.session_state.dark_mode else "☀️", key="thm", help="Toggle theme"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
    with c3:
        if st.button("⚙️", key="settings", help="Settings"):
            st.session_state.show_settings = not st.session_state.get("show_settings", False)

    if st.session_state.get("show_settings", False):
        density = st.selectbox("Density", ["comfortable","compact"],
                                index=0 if st.session_state.density=="comfortable" else 1,
                                key="dens_sel")
        if density != st.session_state.density:
            st.session_state.density = density; st.rerun()
        fsize = st.selectbox("Font size", ["small","medium","large"],
                              index={"small":0,"medium":1,"large":2}[st.session_state.font_size],
                              key="fs_sel")
        if fsize != st.session_state.font_size:
            st.session_state.font_size = fsize; st.rerun()

    st.markdown('<div class="sidebar-label">Usage</div>', unsafe_allow_html=True)
    if is_unlimited():
        st.markdown(
            f'<div class="token-panel"><div class="row"><span>Status</span><span class="dev">Developer</span></div>'
            f'<div class="row"><span>Limit</span><span class="dev">Unlimited</span></div>'
            f'<div class="row"><span>Used</span><span class="val">{st.session_state.tokens_used:,}</span></div></div>',
            unsafe_allow_html=True)
    else:
        used = st.session_state.tokens_used
        rem = max(0, TOKEN_LIMIT - used)
        pct = min(100, int((used / TOKEN_LIMIT) * 100))
        if pct >= 90: bc, sc, stt = "#ef4444","danger","Critical"
        elif pct >= 70: bc, sc, stt = "#f59e0b","warn","Warning"
        else: bc, sc, stt = "#10b981","dev","Active"
        st.markdown(
            f'<div class="token-panel"><div class="row"><span>Status</span><span class="{sc}">{stt}</span></div>'
            f'<div class="row"><span>Used</span><span class="val">{used:,} / {TOKEN_LIMIT:,}</span></div>'
            f'<div class="row"><span>Remaining</span><span class="val">{rem:,}</span></div>'
            f'<div class="token-bar-wrap"><div class="token-bar-fill" style="width:{pct}%;background:{bc};"></div></div></div>',
            unsafe_allow_html=True)

    st.markdown('<div class="sidebar-label">Tools</div>', unsafe_allow_html=True)
    choice = st.radio("nav", list(TOOLS.keys()), label_visibility="collapsed", key="nav")
    tool = TOOLS[choice]

    if tool == "chat":
        st.markdown('<div class="sidebar-label">Conversations</div>', unsafe_allow_html=True)
        if st.button("+ New chat", key="nc", use_container_width=True):
            new_conv(); st.rerun()

        search = st.text_input("search", placeholder="🔍 Search...",
                                label_visibility="collapsed", key="conv_search")

        items = list(st.session_state.conversations.items())
        if search:
            items = [(c, v) for c, v in items if search.lower() in v["title"].lower()]

        for cid, conv in items:
            act = cid == st.session_state.active_conversation
            lbl = f"{'● ' if act else ''}{conv['title'][:24]}"
            col1, col2, col3 = st.columns([5, 1, 1])
            with col1:
                if st.button(lbl, key=f"c_{cid}", use_container_width=True):
                    st.session_state.active_conversation = cid; st.rerun()
            with col2:
                if st.button("✎", key=f"r_{cid}", help="Rename"):
                    st.session_state.rename_conv = cid; st.rerun()
            with col3:
                if st.button("×", key=f"d_{cid}", help="Delete"):
                    del_conv(cid); st.rerun()

            if st.session_state.rename_conv == cid:
                with st.form(f"ren_{cid}"):
                    new_title = st.text_input("New title", value=conv["title"],
                                                label_visibility="collapsed",
                                                key=f"nt_{cid}")
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        if st.form_submit_button("Save", use_container_width=True):
                            st.session_state.conversations[cid]["title"] = new_title[:40]
                            st.session_state.rename_conv = None; st.rerun()
                    with sc2:
                        if st.form_submit_button("Cancel", use_container_width=True):
                            st.session_state.rename_conv = None; st.rerun()

        if len(st.session_state.conversations) > 1:
            if st.button("📦 Export all (ZIP)", key="exp_all", use_container_width=True):
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w") as z:
                    for c, v in st.session_state.conversations.items():
                        safe = "".join(ch for ch in v["title"] if ch.isalnum() or ch in " -_")[:30]
                        z.writestr(f"{safe or c}.json",
                                    json.dumps(v["messages"], ensure_ascii=False, indent=2))
                st.download_button("⬇️ Download ZIP", buf.getvalue(),
                                    f"treats_all_{datetime.now():%Y%m%d}.zip",
                                    "application/zip", use_container_width=True)

    st.markdown('<div class="sidebar-label">AI Model</div>', unsafe_allow_html=True)
    model = st.selectbox("m", AVAILABLE_MODELS, key="mdl", label_visibility="collapsed")

    dev_label = "🔓 Dev: ON" if st.session_state.dev_mode else "Developer"
    if st.button(dev_label, key="dev_btn", use_container_width=True):
        if st.session_state.dev_mode:
            st.session_state.dev_mode = False
            st.session_state.show_dev_input = False; st.rerun()
        else:
            st.session_state.show_dev_input = not st.session_state.show_dev_input; st.rerun()

    if st.session_state.show_dev_input and not st.session_state.dev_mode:
        with st.form("dev_f", clear_on_submit=True):
            pwd = st.text_input("p", type="password", placeholder="Password",
                                 label_visibility="collapsed")
            if st.form_submit_button("Unlock", use_container_width=True):
                if pwd == st.secrets.get("DEV_PASSWORD", ""):
                    st.session_state.dev_mode = True
                    st.session_state.show_dev_input = False
                    st.toast("Developer mode enabled", icon="✅"); st.rerun()
                else: st.error("Wrong password")

    st.markdown(
        '<div class="sidebar-footer">'
        '<strong>Treats v3.0</strong><br>'
        'Powered by Groq<br><br>'
        '<span class="kbd">Enter</span> send · '
        '<span class="kbd">Shift+Enter</span> new line'
        '</div>', unsafe_allow_html=True)

# ============================================================
# CHAT
# ============================================================
PROMPTS = [
    ("Explain","Explain {topic} in simple terms."),
    ("Summarize","Summarize in 5 bullets:\n\n{text}"),
    ("Translate","Translate to {language}:\n\n{text}"),
    ("Email","Write a professional email about {topic}."),
    ("Code","Write Python code that {task}."),
    ("Brainstorm","Give me 10 ideas about {topic}."),
]

def render_chat():
    msgs = get_msgs()

    if not can_send():
        st.markdown(
            '<div style="background:#fef2f2;border:1px solid #fecaca;color:#991b1b;'
            'padding:16px 20px;border-radius:12px;margin-bottom:20px;">'
            f'<strong>Daily limit reached</strong><br>'
            f'You used {st.session_state.tokens_used:,} / {TOKEN_LIMIT:,} tokens.<br>'
            'Resets tomorrow at midnight.</div>', unsafe_allow_html=True)
        for m in msgs:
            with st.chat_message(m["role"]): st.markdown(m["content"])
        return

    if not msgs:
        st.markdown(
            f'<div class="treats-hero">'
            f'<img src="{LOGO_URI}" class="hero-logo">'
            f'<div class="greeting">{get_greeting()}. How can I help you?</div>'
            f'</div>', unsafe_allow_html=True)

        with st.expander("💡 Prompt Library"):
            cols = st.columns(3)
            for i, (l, t) in enumerate(PROMPTS):
                with cols[i % 3]:
                    if st.button(l, key=f"p_{i}", use_container_width=True):
                        st.session_state.pl_template = t; st.rerun()

    for i, m in enumerate(msgs):
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

            if m["role"] == "assistant":
                ts = fmt_time(m.get("ts", ""))
                tok = count_tokens(m["content"])
                wc = count_words(m["content"])
                st.markdown(
                    f'<span class="token-badge">{tok} tokens</span>'
                    f'<span class="token-badge">{wc} words</span>'
                    f'<span class="time-badge">{ts}</span>',
                    unsafe_allow_html=True)

                c1, c2, c3, _ = st.columns([1, 1, 1, 7])
                with c1:
                    if st.button("📋 Copy", key=f"cp_{i}"):
                        copy_to_clipboard(m["content"], f"cp_{i}")
                        st.toast("Copied!", icon="✅")
                with c2:
                    if i == len(msgs) - 1:
                        if st.button("🔄 Retry", key=f"rg_{i}"):
                            set_msgs(msgs[:i]); st.rerun()
                with c3:
                    if st.button("🗑", key=f"dl_{i}", help="Delete"):
                        new_msgs = msgs[:i] + msgs[i+1:]
                        set_msgs(new_msgs); st.rerun()

    if msgs:
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if st.button("New chat", key="nci", use_container_width=True):
                new_conv(); st.rerun()
        with c2:
            if st.button("Duplicate", key="dup", use_container_width=True):
                dup_conv(st.session_state.active_conversation); st.rerun()
        with c3:
            with st.expander("Export"):
                a, b = st.columns(2)
                with a:
                    md = "\n\n".join(f"**{m['role']}:** {m['content']}" for m in msgs)
                    st.download_button("MD", md,
                        f"treats_{datetime.now():%Y%m%d}.md",
                        "text/markdown", use_container_width=True)
                with b:
                    st.download_button("JSON",
                        json.dumps(msgs, ensure_ascii=False, indent=2),
                        f"treats_{datetime.now():%Y%m%d}.json",
                        "application/json", use_container_width=True)

    prompt = st.chat_input("Message Treats...")
    if prompt:
        if not can_send(): st.error("Limit reached."); st.stop()
        msgs.append({"role":"user","content":prompt,"ts": datetime.now().isoformat()})
        set_msgs(msgs)
        cid = st.session_state.active_conversation
        if st.session_state.conversations[cid]["title"] == "New chat":
            st.session_state.conversations[cid]["title"] = auto_title(prompt)
        st.rerun()

    if msgs and msgs[-1]["role"] == "user":
        try:
            client = get_client()
            clean_msgs = [{"role": m["role"], "content": m["content"]} for m in msgs]
            full = [{"role":"system","content":SYS_PROMPT}] + clean_msgs
            hist = trim_history(full)

            stream = client.chat.completions.create(
                model=model,
                messages=hist,
                temperature=0.7,
                stream=True,
            )

            with st.chat_message("assistant"):
                ph = st.empty()
                full_txt = ""
                for ch in stream:
                    if ch.choices and ch.choices[0].delta.content:
                        full_txt += ch.choices[0].delta.content
                        ph.markdown(full_txt + "▌")
                ph.markdown(full_txt)

            total_t = sum(count_tokens(m["content"]) for m in hist) + count_tokens(full_txt)
            add_tokens(total_t)

            msgs.append({"role":"assistant","content":full_txt,"ts": datetime.now().isoformat()})
            set_msgs(msgs)
            st.rerun()
        except TreatsError as e: st.error(str(e))
        except Exception as e: st.error(f"Error: {e}")

# ============================================================
# CV
# ============================================================
CV_TPL = {
    "Modern":"modern two-column with colored header",
    "Classic":"traditional professional",
    "Creative":"creative with unique styling",
}

def render_cv():
    tool_header("cv","CV Builder","Generate a professional CV in seconds")
    if not can_send(): st.warning("Limit reached."); return

    tpl = st.radio("Template", list(CV_TPL.keys()), horizontal=True)
    with st.form("cv_f"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Full Name")
            role = st.text_input("Target Role")
            edu = st.text_input("Education")
        with c2:
            lang = st.selectbox("Language",["English","Arabic"])
            tone = st.selectbox("Tone",["Professional","Concise","Academic"])
            skills = st.text_input("Skills (comma-separated)")
        exp = st.text_area("Experience", placeholder="One bullet per line", height=140)
        sub = st.form_submit_button("✨ Generate CV", type="primary", use_container_width=True)

    if sub:
        if not name or not role: st.warning("Name and role required."); return
        try:
            client = get_client()
            p = f"Write a CV in {lang}, {tone} tone. Style: {CV_TPL[tpl]}.\nName:{name}\nRole:{role}\nExperience:{exp}\nEducation:{edu}\nSkills:{skills}\nMarkdown."
            with st.spinner("Generating..."):
                r = client.chat.completions.create(model="openai/gpt-oss-120b",
                    messages=[{"role":"user","content":p}], temperature=0.6)
            txt = r.choices[0].message.content
            if r.usage: add_tokens(r.usage.total_tokens)
            st.markdown("---"); st.markdown(txt)
            c1, c2 = st.columns(2)
            with c1: st.download_button("⬇️ Markdown", txt, "cv.md", "text/markdown", use_container_width=True)
            with c2: st.download_button("⬇️ Text", txt, "cv.txt", "text/plain", use_container_width=True)
        except Exception as e: st.error(f"Error: {e}")

# ============================================================
# PASSWORD
# ============================================================
def render_password():
    import string
    tool_header("password","Password Generator","Create strong, secure passwords")
    c1, c2, c3 = st.columns(3)
    with c1: ln = st.slider("Length", 8, 64, 16)
    with c2: un = st.checkbox("Numbers", value=True)
    with c3: us = st.checkbox("Symbols", value=True)
    ch = string.ascii_letters
    if un: ch += string.digits
    if us: ch += "!@#$%^&*()-_=+"
    if st.button("🎲 Generate", type="primary", use_container_width=True):
        pwd = "".join(random.choice(ch) for _ in range(ln))
        st.code(pwd, language=None)
        st.download_button("⬇️ Download", pwd, "password.txt", use_container_width=True)

# ============================================================
# VIDEO
# ============================================================
def render_video():
    tool_header("video","Video Script","Generate scene-by-scene storyboards")
    if not can_send(): st.warning("Limit reached."); return
    with st.form("v_f"):
        topic = st.text_input("Topic")
        c1, c2 = st.columns(2)
        with c1:
            dur = st.selectbox("Duration",["30 seconds","60 seconds","3 minutes","5 minutes"])
            lang = st.selectbox("Language",["English","Arabic"])
        with c2:
            sty = st.selectbox("Style",["Educational","Promotional","Storytelling","Entertainment"])
            plat = st.selectbox("Platform",["YouTube","TikTok","Instagram","LinkedIn"])
        sub = st.form_submit_button("🎬 Generate", type="primary", use_container_width=True)
    if sub:
        if not topic: st.warning("Enter a topic."); return
        try:
            client = get_client()
            p = f"Video script in {lang} for {plat}. Topic:{topic}. Duration:{dur}. Style:{sty}. Storyboard."
            with st.spinner("Generating..."):
                r = client.chat.completions.create(model="openai/gpt-oss-120b",
                    messages=[{"role":"user","content":p}], temperature=0.7)
            s = r.choices[0].message.content
            if r.usage: add_tokens(r.usage.total_tokens)
            st.markdown("---"); st.markdown(s)
            st.download_button("⬇️ Markdown", s, "script.md", "text/markdown", use_container_width=True)
        except Exception as e: st.error(f"Error: {e}")

# ============================================================
# TTS
# ============================================================
LBL = {"en":"English","ar":"Arabic","fr":"French","es":"Spanish","de":"German"}

def render_tts():
    tool_header("tts","Text to Speech","Convert text into natural-sounding speech")
    voices = fetch_voices()
    avail = [k for k in voices if voices[k]]
    if not avail: st.warning("No voices."); return
    lc = st.radio("Language", avail, format_func=lambda x: LBL.get(x,x), horizontal=True)
    voice = st.selectbox("Voice", voices[lc], key="tv")
    text = st.text_area("Text", height=160, placeholder="Enter text...")
    c1, c2, c3 = st.columns(3)
    with c1: rv = st.slider("Rate", 0.5, 2.0, 1.0, 0.1)
    with c2: pv = st.slider("Pitch (Hz)", -50, 50, 0, 5)
    with c3: vv = st.slider("Volume", 0, 100, 100, 5)
    rate = f"{'+' if rv >= 1 else ''}{int((rv-1)*100)}%"
    pitch = f"{'+' if pv >= 0 else ''}{pv}Hz"
    vol = f"+{vv}%"
    if st.button("🔊 Generate Audio", type="primary", use_container_width=True):
        if not text.strip(): st.warning("Enter text."); return
        try:
            with st.spinner("Generating..."):
                a = asyncio.run(_tts(text, voice, rate, pitch, vol))
            st.audio(a, format="audio/mp3")
            st.download_button("⬇️ MP3", a, "tts.mp3", "audio/mpeg", use_container_width=True)
        except Exception as e: st.error(f"Failed: {e}")

# ============================================================
# IMAGE
# ============================================================
def render_photo():
    tool_header("photo","Image Generator","Create images from text descriptions")
    if "gallery" not in st.session_state: st.session_state.gallery = []
    with st.spinner("Loading models..."): models = fetch_img_models()
    pr = st.text_area("Prompt", placeholder="A cat in Paris, cinematic lighting, 4K", height=110)
    c1, c2, c3 = st.columns(3)
    with c1: m = st.selectbox("Model", models, key="pm")
    with c2: asp = st.selectbox("Aspect",
        ["1:1 (1024×1024)","16:9 (1344×768)","9:16 (768×1344)","4:3 (1152×896)"], key="pa")
    with c3: enh = st.checkbox("Auto-enhance", value=True, key="pe")
    d = {"1:1 (1024×1024)":(1024,1024),"16:9 (1344×768)":(1344,768),
         "9:16 (768×1344)":(768,1344),"4:3 (1152×896)":(1152,896)}
    w, h = d[asp]
    c1, c2 = st.columns([3,1])
    with c1: sd = st.number_input("Seed (0 = random)", min_value=0, value=0, step=1, key="ps")
    with c2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("🎲 Randomize", key="prd", use_container_width=True):
            st.session_state["ps"] = random.randint(1,999999); st.rerun()
    seed = int(sd) if sd > 0 else None
    if st.button("🎨 Generate Image", type="primary", use_container_width=True):
        if not pr.strip(): st.warning("Enter a prompt."); return
        try:
            with st.spinner("Generating..."):
                img = gen_image(pr, w, h, m, seed, enh)
            st.session_state.li = img; st.session_state.lp = pr
            st.session_state.gallery.append({"p":pr,"b":img,"t":datetime.now().isoformat()})
            st.toast("Image generated!", icon="🎨")
        except TreatsError as e: st.error(str(e))
        except Exception as e: st.error(f"Error: {e}")
    if "li" in st.session_state:
        st.markdown("---")
        st.image(st.session_state.li, caption=st.session_state.get("lp",""))
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("⬇️ PNG", st.session_state.li,
                f"treats_{datetime.now():%Y%m%d_%H%M%S}.png",
                "image/png", use_container_width=True)
        with c2:
            if st.button("🔄 Regenerate", use_container_width=True):
                try:
                    with st.spinner("Regenerating..."):
                        img = gen_image(st.session_state.lp, w, h, m,
                                        random.randint(1,999999), enh)
                    st.session_state.li = img; st.rerun()
                except TreatsError as e: st.error(str(e))
    if st.session_state.gallery:
        with st.expander(f"🖼️ Gallery ({len(st.session_state.gallery)})"):
            gc = st.columns(3)
            for i, it in enumerate(reversed(st.session_state.gallery)):
                with gc[i % 3]: st.image(it["b"], caption=it["p"][:40], use_container_width=True)

# ============================================================
# ROUTER
# ============================================================
if tool == "chat": render_chat()
elif tool == "cv": render_cv()
elif tool == "password": render_password()
elif tool == "video": render_video()
elif tool == "tts": render_tts()
elif tool == "photo": render_photo()
