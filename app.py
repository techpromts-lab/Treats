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
# INLINE SVG LOGO  (no file needed)
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
  <circle cx="102" cy="40" r="3.5" fill="#fbbf24"/>
  <circle cx="110" cy="52" r="2.5" fill="#fbbf24"/>
  <circle cx="96" cy="55" r="2" fill="#fbbf24"/>
</svg>"""

LOGO_URI = "data:image/svg+xml;base64," + base64.b64encode(LOGO_SVG.encode()).decode()


# ============================================================
# CUSTOM CSS
# ============================================================
def load_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        /* Hide Streamlit chrome (but keep sidebar toggle visible) */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        [data-testid="stToolbar"] { display: none; }
        [data-testid="stDecoration"] { display: none; }

        /* Header stays transparent but visible so mobile hamburger shows */
        header[data-testid="stHeader"] {
            background: transparent;
            height: auto;
            min-height: 48px;
        }

        /* ---------- SIDEBAR TOGGLE (HAMBURGER) ---------- */
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"] {
            display: flex !important;
            visibility: visible !important;
            color: #6c3ef5 !important;
            background: #ffffff !important;
            border: 1px solid #ede9fe !important;
            border-radius: 10px !important;
            padding: 8px !important;
            margin: 0 !important;
            position: fixed !important;
            top: 12px !important;
            left: 16px !important;
            width: 42px !important;
            height: 42px !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: 0 2px 10px rgba(108, 62, 245, 0.15) !important;
            transition: all 0.15s ease !important;
            z-index: 99999 !important;
        }
        [data-testid="collapsedControl"]:hover,
        [data-testid="stSidebarCollapsedControl"]:hover {
            background: #f5f3ff !important;
            border-color: #a855f7 !important;
            transform: scale(1.05);
        }
        [data-testid="collapsedControl"] svg,
        [data-testid="stSidebarCollapsedControl"] svg {
            color: #6c3ef5 !important;
            fill: #6c3ef5 !important;
            width: 20px !important;
            height: 20px !important;
        }

        .stApp {
            background: #ffffff;
            -webkit-overflow-scrolling: touch;
            overscroll-behavior-y: contain;
        }

        /* ============================================================
           MOBILE TOUCH FIX — prevent accidental text drag
           ============================================================ */
        * {
            -webkit-tap-highlight-color: transparent;
        }

        /* Disable selection on UI elements (not on text content) */
        button,
        .stButton,
        .stDownloadButton,
        label,
        h1, h2, h3, h4, h5, h6,
        .tool-header,
        .treats-brand,
        .sidebar-footer,
        .treats-hero,
        .starter-card,
        [data-testid="stSidebar"],
        [data-testid="stHeader"],
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"] {
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
            user-select: none;
            -webkit-touch-callout: none;
        }

        /* Keep text selectable where it matters */
        [data-testid="stChatMessage"],
        [data-testid="stChatMessage"] *,
        .stMarkdown,
        .stMarkdown *,
        .stTextArea textarea,
        .stTextInput input,
        pre, code, pre *, code * {
            -webkit-user-select: text;
            user-select: text;
        }

        /* Chat input: allow smooth typing on mobile */
        [data-testid="stChatInput"] textarea {
            touch-action: manipulation;
            -webkit-user-select: text;
            user-select: text;
        }

        /* Prevent horizontal scroll on mobile */
        html, body, .stApp {
            overflow-x: hidden;
            max-width: 100vw;
        }

        /* ---------- SIDEBAR ---------- */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #faf9ff 0%, #f5f3ff 100%);
            border-right: 1px solid #ede9fe;
            min-width: 270px !important;
            max-width: 270px !important;
        }
        [data-testid="stSidebar"] > div:first-child {
            padding: 1.5rem 0.85rem 1rem 0.85rem;
        }

        .treats-brand {
            padding: 4px 10px 24px 10px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .treats-brand img {
            width: 44px;
            height: 44px;
            filter: drop-shadow(0 4px 12px rgba(108, 62, 245, 0.25));
        }
        .treats-brand .name {
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #6c3ef5 0%, #a855f7 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        /* Radio group */
        [data-testid="stSidebar"] [data-testid="stRadio"] > div[role="radiogroup"] {
            gap: 3px !important;
            display: flex;
            flex-direction: column;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] {
            display: flex !important;
            align-items: center !important;
            gap: 12px !important;
            padding: 10px 14px !important;
            margin: 0 !important;
            border-radius: 10px !important;
            cursor: pointer !important;
            transition: all 0.15s ease !important;
            font-size: 14px !important;
            font-weight: 500 !important;
            color: #374151 !important;
            width: 100% !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            line-height: 1.3 !important;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover {
            background: #ffffff !important;
            border-color: #ede9fe !important;
            transform: translateX(2px);
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
            display: none !important;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]::before {
            content: '' !important;
            width: 20px !important;
            height: 20px !important;
            flex-shrink: 0 !important;
            background-repeat: no-repeat !important;
            background-position: center !important;
            background-size: 20px 20px !important;
            border-radius: 6px;
            padding: 4px;
            box-sizing: content-box;
        }

        /* Colored icons per tool */
        label[data-baseweb="radio"]:nth-of-type(1)::before {
            background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%236366f1' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'><path d='M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'/></svg>") !important;
            background-color: #eef2ff;
        }
        label[data-baseweb="radio"]:nth-of-type(2)::before {
            background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%233b82f6' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'><path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/><polyline points='14 2 14 8 20 8'/><line x1='9' y1='13' x2='15' y2='13'/><line x1='9' y1='17' x2='13' y2='17'/></svg>") !important;
            background-color: #dbeafe;
        }
        label[data-baseweb="radio"]:nth-of-type(3)::before {
            background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2310b981' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'><rect x='3' y='11' width='18' height='11' rx='2' ry='2'/><path d='M7 11V7a5 5 0 0 1 10 0v4'/></svg>") !important;
            background-color: #d1fae5;
        }
        label[data-baseweb="radio"]:nth-of-type(4)::before {
            background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23f97316' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'><polygon points='23 7 16 12 23 17 23 7'/><rect x='1' y='5' width='15' height='14' rx='2' ry='2'/></svg>") !important;
            background-color: #ffedd5;
        }
        label[data-baseweb="radio"]:nth-of-type(5)::before {
            background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ec4899' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'><polygon points='11 5 6 9 2 9 2 15 6 15 11 19 11 5'/><path d='M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07'/></svg>") !important;
            background-color: #fce7f3;
        }
        label[data-baseweb="radio"]:nth-of-type(6)::before {
            background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%238b5cf6' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'><rect x='3' y='3' width='18' height='18' rx='2' ry='2'/><circle cx='8.5' cy='8.5' r='1.5'/><polyline points='21 15 16 10 5 21'/></svg>") !important;
            background-color: #ede9fe;
        }

        /* Active item */
        label[data-baseweb="radio"]:has(input:checked) {
            background: #ffffff !important;
            border-color: #ddd6fe !important;
            font-weight: 700 !important;
            color: #1f2937 !important;
            box-shadow: 0 2px 8px rgba(108, 62, 245, 0.08);
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] > label:first-child {
            display: none !important;
        }

        .sidebar-footer {
            padding: 16px 14px;
            color: #8b8b9e;
            font-size: 12px;
            line-height: 1.6;
            border-top: 1px solid #ede9fe;
            margin-top: 24px;
        }
        .sidebar-footer strong {
            color: #6c3ef5;
            font-weight: 600;
        }

        /* ---------- MAIN CONTENT ---------- */
        .main .block-container,
        section.main > div.block-container {
            max-width: 780px;
            padding-top: 1.5rem;
            padding-bottom: 5rem;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
            margin: 0 auto;
        }

        /* ---------- TYPOGRAPHY ---------- */
        h1 {
            font-size: 30px !important;
            font-weight: 800 !important;
            letter-spacing: -0.03em !important;
            color: #111827 !important;
            margin-bottom: 0.4rem !important;
        }
        h2 {
            font-size: 22px !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
        }
        p, li, label, .stMarkdown {
            font-size: 15px;
            line-height: 1.65;
            color: #1f2937;
        }

        /* Colored tool headings */
        .tool-header {
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 6px;
            padding-bottom: 16px;
            border-bottom: 1px solid #f3f4f6;
        }
        .tool-header .icon {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .tool-header .icon svg {
            width: 22px;
            height: 22px;
        }
        .tool-header .title-block h1 {
            margin: 0 !important;
            font-size: 26px !important;
        }
        .tool-header .title-block p {
            margin: 2px 0 0 0 !important;
            color: #6b7280;
            font-size: 14px !important;
        }

        /* Per-tool color themes */
        .theme-chat   .icon { background: linear-gradient(135deg, #eef2ff, #e0e7ff); }
        .theme-cv     .icon { background: linear-gradient(135deg, #dbeafe, #bfdbfe); }
        .theme-pass   .icon { background: linear-gradient(135deg, #d1fae5, #a7f3d0); }
        .theme-video  .icon { background: linear-gradient(135deg, #ffedd5, #fed7aa); }
        .theme-tts    .icon { background: linear-gradient(135deg, #fce7f3, #fbcfe8); }
        .theme-photo  .icon { background: linear-gradient(135deg, #ede9fe, #ddd6fe); }

        /* ---------- BUTTONS ---------- */
        .stButton > button {
            background: #ffffff;
            color: #1f2937;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 8px 18px;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.15s ease;
            box-shadow: none;
        }
        .stButton > button:hover {
            background: #f9fafb;
            border-color: #d1d5db;
            color: #111827;
            transform: translateY(-1px);
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #6c3ef5 0%, #a855f7 100%);
            color: #ffffff;
            border: none;
            box-shadow: 0 4px 14px rgba(108, 62, 245, 0.3);
        }
        .stButton > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #5a2ee0 0%, #9333ea 100%);
            box-shadow: 0 6px 20px rgba(108, 62, 245, 0.4);
            transform: translateY(-1px);
        }
        .stDownloadButton > button {
            background: #ffffff;
            color: #1f2937;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 8px 18px;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.15s ease;
        }
        .stDownloadButton > button:hover {
            background: #f9fafb;
            border-color: #a855f7;
            color: #6c3ef5;
        }

        /* ---------- INPUTS ---------- */
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stSelectbox > div > div {
            border-radius: 10px !important;
            border-color: #e5e7eb !important;
            font-size: 14px !important;
            background: #ffffff !important;
            transition: all 0.15s ease !important;
        }
        .stTextInput input:focus,
        .stTextArea textarea:focus,
        .stNumberInput input:focus,
        .stSelectbox > div > div:focus-within {
            border-color: #a855f7 !important;
            box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.12) !important;
        }
        .stTextArea textarea {
            padding: 12px 14px !important;
            line-height: 1.6 !important;
        }

        /* ---------- FORM ---------- */
        [data-testid="stForm"] {
            border: 1px solid #f3f4f6;
            border-radius: 16px;
            padding: 22px 24px;
            background: linear-gradient(180deg, #fefeff 0%, #fafaff 100%);
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
        }

        /* ---------- CHAT MESSAGES ---------- */
        [data-testid="stChatMessage"] {
            background: transparent;
            padding: 20px 0;
            border-bottom: 1px solid #f3f4f6;
            border-radius: 0;
        }
        [data-testid="stChatMessage"]:last-child {
            border-bottom: none;
        }

        /* ---------- CHAT INPUT ---------- */
        [data-testid="stChatInput"] {
            border-radius: 14px;
            border: 1px solid #e5e7eb;
            background: #ffffff;
            box-shadow: 0 4px 16px rgba(108, 62, 245, 0.06);
            transition: all 0.15s ease;
        }
        [data-testid="stChatInput"]:focus-within {
            border-color: #a855f7;
            box-shadow: 0 4px 20px rgba(168, 85, 247, 0.15);
        }

        /* ---------- MISC ---------- */
        code {
            background: #faf5ff !important;
            color: #7c3aed !important;
            padding: 3px 8px !important;
            border-radius: 6px !important;
            font-size: 13px !important;
            font-weight: 600;
        }
        pre {
            background: #1e1b4b !important;
            border-radius: 14px !important;
        }
        [data-testid="stSlider"] [role="slider"] {
            background: #6c3ef5 !important;
        }
        [data-testid="stSlider"] [data-baseweb="slider"] div[role="progressbar"] {
            background: linear-gradient(90deg, #6c3ef5, #a855f7) !important;
        }
        hr { border-color: #f3f4f6; margin: 1.5rem 0; }
        .stCaption, [data-testid="stCaptionContainer"] {
            color: #6b7280;
            font-size: 13px;
        }

        /* ---------- HERO ---------- */
        .treats-hero {
            text-align: center;
            padding: 30px 20px 20px 20px;
        }
        .treats-hero .hero-logo {
            width: 120px;
            height: 120px;
            margin: 0 auto 16px auto;
            filter: drop-shadow(0 12px 32px rgba(108, 62, 245, 0.25));
            animation: float 3s ease-in-out infinite;
        }
        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-6px); }
        }
        .treats-hero h2 {
            font-size: 30px;
            font-weight: 800;
            color: #111827;
            margin: 0 0 10px 0;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #1f2937 0%, #6c3ef5 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .treats-hero p {
            color: #6b7280;
            font-size: 15px;
            margin: 0;
        }

        /* ---------- STARTER CARDS ---------- */
        .starter-card .stButton > button {
            width: 100%;
            text-align: left;
            padding: 16px 18px;
            height: auto;
            font-size: 13.5px;
            line-height: 1.5;
            color: #1f2937;
            background: linear-gradient(180deg, #ffffff 0%, #fafaff 100%);
            border: 1px solid #ede9fe;
            border-radius: 14px;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        .starter-card .stButton > button:hover {
            border-color: #a855f7;
            background: linear-gradient(180deg, #ffffff 0%, #f5f3ff 100%);
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(108, 62, 245, 0.12);
            color: #6c3ef5;
        }

        /* ---------- Expander ---------- */
        details {
            border: 1px solid #f3f4f6;
            border-radius: 12px;
            padding: 4px 14px;
            background: #fafafa;
        }
        details summary {
            font-weight: 600;
            font-size: 14px;
            color: #1f2937;
        }

        /* ---------- RESPONSIVE (mobile) ---------- */
        @media (max-width: 768px) {
            [data-testid="stSidebar"] {
                min-width: 82vw !important;
                max-width: 82vw !important;
            }

            /* Hamburger: push it more inside on mobile */
            [data-testid="collapsedControl"],
            [data-testid="stSidebarCollapsedControl"] {
                top: 14px !important;
                left: 20px !important;
                width: 44px !important;
                height: 44px !important;
                padding: 10px !important;
            }

            /* Zoom in: tighter padding, wider content */
            .main .block-container,
            section.main > div.block-container {
                padding-left: 0.75rem !important;
                padding-right: 0.75rem !important;
                padding-top: 0.75rem !important;
                padding-bottom: 3rem !important;
                max-width: 100% !important;
            }

            /* Tighter header on mobile */
            header[data-testid="stHeader"] {
                min-height: 40px;
            }

            /* Typography adjusts for zoomed-in feel */
            h1 { font-size: 22px !important; }
            h2 { font-size: 18px !important; }
            .tool-header { gap: 10px; padding-bottom: 12px; }
            .tool-header .icon { width: 38px; height: 38px; }
            .tool-header .icon svg { width: 18px; height: 18px; }
            .tool-header .title-block h1 { font-size: 19px !important; }
            .tool-header .title-block p { font-size: 12.5px !important; }

            .treats-hero { padding: 20px 8px 16px 8px; }
            .treats-hero h2 { font-size: 22px; }
            .treats-hero .hero-logo { width: 80px; height: 80px; }

            /* Buttons fill width nicely */
            .stButton > button,
            .stDownloadButton > button {
                font-size: 13px;
                padding: 10px 14px;
                border-radius: 10px;
            }

            /* Sidebar padding tighter */
            [data-testid="stSidebar"] > div:first-child {
                padding: 1rem 0.5rem 0.75rem 0.5rem !important;
            }
            .treats-brand { padding: 2px 6px 16px 6px; }
            .treats-brand img { width: 38px; height: 38px; }
            .treats-brand .name { font-size: 18px; }
            .sidebar-footer { padding: 12px 8px; font-size: 11px; }

            /* Chat messages tighter */
            [data-testid="stChatMessage"] {
                padding: 14px 0;
            }

            /* Forms fill screen */
            [data-testid="stForm"] {
                padding: 16px 14px;
                border-radius: 14px;
            }

            /* Radio items in sidebar tighter */
            [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] {
                padding: 9px 10px !important;
                font-size: 13.5px !important;
                gap: 10px !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)


load_css()


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
# SYSTEM PROMPT — Treats knows its own features
# ============================================================
TREATS_SYSTEM_PROMPT = """You are Treats, a helpful, general-purpose AI assistant built with Streamlit and Groq.

You are friendly, concise, and always ready to help with anything the user asks — writing, coding, learning, brainstorming, analysis, translation, and more.

## Your Features

Treats is a multi-tool AI assistant. You know exactly what you can do, and you should tell users about these features when they ask "what can you do" or "what are your features":

1. **Chat** — The conversation you're having right now. Supports streaming responses, temperature control (0.0–1.5), two AI models (gpt-oss-20b for speed, gpt-oss-120b for quality), regenerate responses, copy, and export conversations as Markdown or JSON.

2. **CV Builder** — Generates professional CVs in seconds. Supports English and Arabic, three tones (Professional, Concise, Academic), and exports as Markdown or Text.

3. **Password Generator** — Creates strong, secure passwords. Customizable length (8–64 characters), with optional numbers and symbols.

4. **Video Script** — Generates complete video scripts with scene-by-scene storyboards. Choose duration, style (Educational, Promotional, Storytelling, Entertainment), language, and platform (YouTube, TikTok, Instagram, LinkedIn).

5. **Text to Speech** — Converts text into natural-sounding speech. Multiple voices in English and Arabic, with controls for rate, pitch, and volume. Download as MP3.

6. **Image Generator** — Creates images from text descriptions. Free, no API key required. Multiple models, aspect ratios, seeds for reproducible results, and auto-enhance option.

When users ask about your capabilities, present these features clearly and help them decide what to use. Be warm but professional. Never use emojis in your responses unless the user uses them first."""


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
        }
    except Exception:
        return {"en": [], "ar": []}


async def _tts_generate(text, voice, rate, pitch, volume):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


# ============================================================
# TOOL HEADER HELPER
# ============================================================
TOOL_ICONS = {
    "chat": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>""",
    "cv": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="13" y2="17"/></svg>""",
    "password": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>""",
    "video": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>""",
    "tts": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#ec4899" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>""",
    "photo": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>""",
}


def render_tool_header(theme_key, title, subtitle):
    st.markdown(
        f'<div class="tool-header theme-{theme_key}">'
        f'<div class="icon">{TOOL_ICONS[theme_key]}</div>'
        f'<div class="title-block">'
        f'<h1>{title}</h1>'
        f'<p>{subtitle}</p>'
        f'</div>'
        f'</div>'
        f'<div style="height: 24px"></div>',
        unsafe_allow_html=True,
    )


# ============================================================
# SIDEBAR
# ============================================================
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

    choice_label = st.radio(
        "Navigation",
        list(TOOLS.keys()),
        label_visibility="collapsed",
        key="nav",
    )
    tool = TOOLS[choice_label]

    st.markdown(
        '<div class="sidebar-footer">'
        '<strong>Treats v2.0</strong><br>'
        'Powered by Groq'
        '</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# TOOL: CHAT
# ============================================================
def render_chat():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if st.session_state.messages:
        render_tool_header("chat", "Chat", "Conversation with AI")
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            model = st.selectbox("Model", AVAILABLE_MODELS, key="model")
        with c2:
            temp = st.slider("Temperature", 0.0, 1.5, 0.7, 0.1, key="temp")
        with c3:
            st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
            if st.button("New chat", key="new_conv", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        st.markdown("---")
    else:
        model = "openai/gpt-oss-120b"
        temp = 0.7

    if not st.session_state.messages:
        st.markdown(
            f'<div class="treats-hero">'
            f'<img src="{LOGO_URI}" class="hero-logo" alt="Treats">'
            f'<h2>How can I help you today?</h2>'
            f'<p>Ask anything. Treats is here to assist.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)

        starters = [
            "What can you do?",
            "Write a professional email requesting time off.",
            "Give me 5 ideas for a Streamlit project.",
        ]
        cols = st.columns(3)
        for c, s in zip(cols, starters):
            with c:
                st.markdown('<div class="starter-card">', unsafe_allow_html=True)
                if st.button(s, key=f"starter_{s[:14]}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": s})
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and i == len(st.session_state.messages) - 1:
                cols = st.columns([1, 1, 8])
                with cols[0]:
                    if st.button("Copy", key=f"copy_{i}"):
                        st.toast("Select and copy the text above.")
                with cols[1]:
                    if st.button("Retry", key=f"regen_{i}"):
                        st.session_state.messages = st.session_state.messages[:i]
                        st.rerun()

    if st.session_state.messages:
        with st.expander("Export conversation"):
            col1, col2 = st.columns(2)
            with col1:
                md = "\n\n".join(f"**{m['role'].capitalize()}:** {m['content']}" for m in st.session_state.messages)
                st.download_button(
                    "Download Markdown", data=md,
                    file_name=f"treats_chat_{datetime.now():%Y%m%d_%H%M}.md",
                    mime="text/markdown", use_container_width=True,
                )
            with col2:
                st.download_button(
                    "Download JSON",
                    data=json.dumps(st.session_state.messages, ensure_ascii=False, indent=2),
                    file_name=f"treats_chat_{datetime.now():%Y%m%d_%H%M}.json",
                    mime="application/json", use_container_width=True,
                )

    prompt = st.chat_input("Message Treats...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        try:
            client = get_client()
            full_messages = [{"role": "system", "content": TREATS_SYSTEM_PROMPT}] + st.session_state.messages
            history = trim_history(full_messages)
            stream = client.chat.completions.create(
                model=model, messages=history, temperature=temp, stream=True,
            )
            with st.chat_message("assistant"):
                placeholder = st.empty()
                full = ""
                for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    full += delta
                    placeholder.markdown(full + "▌")
                placeholder.markdown(full)
            st.session_state.messages.append({"role": "assistant", "content": full})
            st.rerun()
        except TreatsError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Unexpected error: {e}")


# ============================================================
# TOOL: CV BUILDER
# ============================================================
def render_cv():
    render_tool_header("cv", "CV Builder", "Generate a professional CV in seconds")

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
                )
            cv_text = resp.choices[0].message.content
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
# TOOL: PASSWORD GENERATOR
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
    if use_numbers:
        chars += string.digits
    if use_symbols:
        chars += "!@#$%^&*()-_=+"

    if st.button("Generate Password", type="primary", use_container_width=True):
        pwd = "".join(random.choice(chars) for _ in range(length))
        st.code(pwd, language=None)
        st.download_button("Download", pwd, "password.txt", use_container_width=True)


# ============================================================
# TOOL: VIDEO SCRIPT
# ============================================================
def render_video():
    render_tool_header("video", "Video Script", "Generate scripts with scene-by-scene storyboards")

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
Break into scenes with a storyboard (timestamp, visual, narration)."""
            with st.spinner("Generating..."):
                resp = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                )
            script = resp.choices[0].message.content
            st.markdown("---")
            st.markdown(script)
            st.download_button("Download Markdown", script, "script.md", "text/markdown", use_container_width=True)
        except TreatsError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Error: {e}")


# ============================================================
# TOOL: TEXT TO SPEECH
# ============================================================
def render_tts():
    render_tool_header("tts", "Text to Speech", "Convert text into natural-sounding speech")

    voices = fetch_available_voice_ids()
    lang_choice = st.radio("Language", ["English", "Arabic"], horizontal=True)
    voice_pool = voices["en"] if lang_choice == "English" else voices["ar"]

    if not voice_pool:
        st.warning("No voices available right now. Please try again later.")
        return

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
# TOOL: IMAGE GENERATOR
# ============================================================
def render_photo():
    render_tool_header("photo", "Image Generator", "Create images from text descriptions — free, no API key")

    with st.spinner("Loading models..."):
        models = fetch_image_models()

    prompt = st.text_area(
        "Prompt",
        placeholder="A cat sipping coffee in a Parisian cafe, cinematic lighting, 4K",
        height=110,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        model = st.selectbox("Model", models, key="photo_model")
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
                    model=model, seed=use_seed, enhance=enhance,
                )
            st.session_state["last_image"] = img_bytes
            st.session_state["last_prompt"] = prompt
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
                            width=w, height=h, model=model,
                            seed=new_seed, enhance=enhance,
                        )
                    st.session_state["last_image"] = img_bytes
                    st.rerun()
                except TreatsError as e:
                    st.error(str(e))


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
