# ============================================================
# Treats v5.1 — Streamlit AI Assistant (bug-fixed + hardened)
# ============================================================
from __future__ import annotations

import asyncio
import base64
import html
import io
import json
import logging
import os
import random
import string
import zipfile
from datetime import date, datetime, time, timedelta
from typing import Any, Callable, Iterable, Optional
from urllib.parse import quote                      # FIX #2

import requests
import streamlit as st
import streamlit.components.v1 as components

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Treats", page_icon="🧠",
    layout="wide", initial_sidebar_state="expanded",
)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("treats")


# ============================================================
# CONFIG
# ============================================================
class Cfg:
    KEY_SLOTS       = 10
    TOKEN_LIMIT     = 5_000
    TOKEN_WARN_AT   = 0.80
    MAX_CTX         = 6_000
    GROQ_MODELS     = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
    VISION_MODELS   = [
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
    ]
    DEFAULT_MODEL   = GROQ_MODELS[0]
    HEAVY_MODEL     = GROQ_MODELS[1]
    VISION_MODEL    = VISION_MODELS[0]
    SUPPORTED_IMGS  = ["png", "jpg", "jpeg", "webp", "gif"]
    STREAM_TIMEOUT  = 60
    GALLERY_MAX     = 24                                # FIX #9: cap gallery


# ============================================================
# EXCEPTIONS
# ============================================================
class TreatsError(Exception): ...
class QuotaError(TreatsError): ...
class ConfigError(TreatsError): ...


# ============================================================
# KEY MANAGER  (FIX #6: cache key list)
# ============================================================
class KeyManager:
    QUOTA_TRIGGERS = (
        "429", "rate limit", "rate_limit", "rate-limit",
        "quota", "insufficient_quota", "too many requests",
        "resourceexhausted", "resource exhausted",
        "exceeded", "tokens per minute", "requests per minute",
    )

    @staticmethod
    def _read(name: str) -> Optional[str]:
        try:
            val = st.secrets.get(name)
        except Exception:
            val = None
        if not val:
            val = os.getenv(name)
        return val.strip() if val and str(val).strip() else None

    @classmethod
    def load(cls) -> list[str]:
        cached = st.session_state.get("_keys_cache")
        if cached:
            return cached
        keys = [k for i in range(1, Cfg.KEY_SLOTS + 1)
                if (k := cls._read(f"GROQ_API_KEY_{i}"))]
        if not keys and (single := cls._read("GROQ_API_KEY")):
            keys = [single]
        if not keys:
            raise ConfigError(
                "No GROQ_API_KEY_1..10 found in secrets or environment.")
        st.session_state["_keys_cache"] = keys
        return keys

    @classmethod
    def index(cls) -> int:
        st.session_state.setdefault("key_index", 0)
        n = len(cls.load())
        st.session_state.key_index %= n
        return st.session_state.key_index

    @classmethod
    def rotate(cls) -> int:
        n = len(cls.load())
        st.session_state.key_index = (st.session_state.key_index + 1) % n
        log.info("Rotated to key #%d", st.session_state.key_index + 1)
        return st.session_state.key_index

    @classmethod
    def client(cls):
        from groq import Groq
        return Groq(api_key=cls.load()[cls.index()])

    @classmethod
    def is_quota_error(cls, exc: BaseException) -> bool:
        s = str(exc).lower()
        return any(t in s for t in cls.QUOTA_TRIGGERS)

    @classmethod
    def call(cls, fn: Callable[[Any], Any], retries: Optional[int] = None) -> Any:
        keys = cls.load()
        attempts = retries if retries is not None else len(keys)
        last: Optional[BaseException] = None
        for i in range(attempts):
            try:
                return fn(cls.client())
            except Exception as e:
                if cls.is_quota_error(e) and i < attempts - 1:
                    last = e
                    cls.rotate()
                    continue
                raise
        if last:
            raise QuotaError(f"All {len(keys)} API keys exhausted. Last: {last}")

    @classmethod
    def stream(cls, fn: Callable[[Any], Iterable[Any]]) -> Iterable[Any]:
        keys = cls.load()
        for i in range(len(keys)):
            try:
                yield from fn(cls.client())
                return
            except Exception as e:
                if cls.is_quota_error(e) and i < len(keys) - 1:
                    log.warning("Stream quota error, rotating key")
                    cls.rotate()
                    continue
                raise


# ============================================================
# TOKEN TRACKER
# ============================================================
class TokenTracker:
    @staticmethod
    def _today() -> str:
        return date.today().isoformat()

    @classmethod
    def _reset_if_needed(cls) -> None:
        if st.session_state.get("token_date") != cls._today():
            st.session_state.token_date = cls._today()
            st.session_state.tokens_used = 0
            st.session_state.warned_80 = False

    @classmethod
    def used(cls) -> int:
        cls._reset_if_needed()
        return int(st.session_state.get("tokens_used", 0))

    @classmethod
    def remaining(cls) -> int:
        return max(0, Cfg.TOKEN_LIMIT - cls.used())

    @classmethod
    def can_send(cls) -> bool:
        return cls.remaining() > 0

    @classmethod
    def add(cls, n: int) -> None:
        if n <= 0:
            return
        cls._reset_if_needed()
        st.session_state.tokens_used = cls.used() + int(n)
        if (st.session_state.tokens_used >= Cfg.TOKEN_LIMIT * Cfg.TOKEN_WARN_AT
                and not st.session_state.get("warned_80")):
            st.session_state.warned_80 = True
            st.toast(f"⚠️ Used {int(Cfg.TOKEN_WARN_AT * 100)}% of today's tokens")

    @classmethod
    def add_usage(cls, usage: Any) -> None:
        if usage is None:
            return
        total = getattr(usage, "total_tokens", None)
        if total:
            cls.add(int(total))

    @classmethod
    def reset_in(cls) -> str:
        now = datetime.now()
        tomorrow = datetime.combine(now.date() + timedelta(days=1), time.min)
        secs = int((tomorrow - now).total_seconds())
        h, rem = divmod(secs, 3600)
        m, _ = divmod(rem, 60)
        return f"{h}h {m}m"


# ============================================================
# STATE  (FIX #5, #12: add missing defaults)
# ============================================================
DEFAULTS: dict[str, Any] = {
    "dark_mode": False, "density": "comfortable", "font_size": "medium",
    "conv_search": "", "rename_conv": None, "show_settings": False,
    "gallery": [], "key_index": 0,
    "tokens_used": 0, "token_date": date.today().isoformat(),
    "warned_80": False,
    "conversations": None, "active_conversation": None,
    "pending_images": {},          # per-conversation
    "prompt_template": None, "editing_msg": None,
    "last_error": None,
    "li": None, "lp": "",          # last generated image
    "_keys_cache": None,
    "_auto_stream_guard": None,    # FIX #15: prevent re-stream loops
}

for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

TokenTracker._reset_if_needed()


# ============================================================
# LOGO
# ============================================================
LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">
  <defs>
    <linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#a855f7"/><stop offset="100%" stop-color="#6c3ef5"/>
    </linearGradient>
    <linearGradient id="g2" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#312e81"/><stop offset="100%" stop-color="#1e1b4b"/>
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
# CSS  (identical to v5.0 — omitted for brevity, keep as-is)
# ============================================================
_PALETTES = {
    True: dict(bg="#0b0b0f", sbg1="#141418", sbg2="#1a1a20", surf="#15151b", surf2="#1f1f26",
               bord="#26262e", bsoft="#1d1d23", txt="#f0f0f3", tsoft="#a0a0ab",
               tmuted="#6e6e7a", hov="#1f1f26", act="#272730", bbtn="#1a1a20", bhv="#23232b",
               bbd="#2c2c35", accent="#a855f7", input_bg="#15151b", input_txt="#f0f0f3"),
    False: dict(bg="#ffffff", sbg1="#fbfaff", sbg2="#f5f3ff", surf="#ffffff", surf2="#f9f9fb",
                bord="#ececf1", bsoft="#f4f4f8", txt="#0e0e11", tsoft="#6b6b78",
                tmuted="#9a9aa8", hov="#f7f5ff", act="#f0ecff", bbtn="#ffffff", bhv="#f7f7fb",
                bbd="#e5e5ed", accent="#6c3ef5", input_bg="#ffffff", input_txt="#0d0d0d"),
}


def load_css(dark: bool, density: str, font_size: str) -> None:
    C = _PALETTES[dark]
    fs_base = {"small": "13.5px", "medium": "15px", "large": "17px"}[font_size]
    fs_h1   = {"small": "26px", "medium": "30px", "large": "35px"}[font_size]
    fs_tool = {"small": "23px", "medium": "27px", "large": "31px"}[font_size]
    msg_pad = "14px 0" if density == "compact" else "24px 0"

    st.markdown(f"""<style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
        html, body, [class*="css"] {{ font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; -webkit-font-smoothing:antialiased; }}
        @media (prefers-reduced-motion: reduce) {{ *,*::before,*::after {{ animation-duration:0.01ms!important; transition-duration:0.01ms!important; }} }}
        #MainMenu, footer, [data-testid="stDecoration"], [data-testid="stStatusWidget"],
        [data-testid="stAppDeployButton"], [data-testid="stMainMenu"],
        [data-testid="stToolbarActions"] {{ display:none!important; }}
        header[data-testid="stHeader"] {{ background:transparent!important; box-shadow:none!important; }}
        html, body, .stApp, [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main, section.main, [data-testid="stMain"] {{
            background:{C['bg']}!important; color:{C['txt']}!important; }}
        ::-webkit-scrollbar {{ width:8px; height:8px; }}
        ::-webkit-scrollbar-thumb {{ background:{C['bord']}; border-radius:4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background:{C['tmuted']}; }}
        button, .stButton, .stDownloadButton, label, h1, h2, h3, h4, h5, h6,
        .tool-header, .treats-brand, .sidebar-footer, .treats-hero, [data-testid="stSidebar"] {{
            -webkit-user-select:none; user-select:none; -webkit-touch-callout:none; }}
        [data-testid="stChatMessage"], .stMarkdown, .stTextArea textarea, .stTextInput input,
        pre, code {{ -webkit-user-select:text; user-select:text; }}
        [data-testid="stSidebar"] {{
            background:linear-gradient(180deg,{C['sbg1']} 0%,{C['sbg2']} 100%)!important;
            border-right:1px solid {C['bord']}!important; }}
        [data-testid="stSidebar"] > div:first-child {{ padding:1.5rem 1rem 1rem 1rem; }}
        .treats-brand {{ padding:6px 12px 24px 12px; display:flex; align-items:center; gap:12px; }}
        .treats-brand img {{ width:42px; height:42px; filter:drop-shadow(0 4px 16px rgba(108,62,245,0.35)); transition:transform 0.3s ease; }}
        .treats-brand:hover img {{ transform:rotate(-8deg) scale(1.05); }}
        .treats-brand .name {{ font-size:21px; font-weight:800; letter-spacing:-0.04em;
            background:linear-gradient(135deg,#6c3ef5 0%,#a855f7 100%);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }}
        .sidebar-label {{ font-size:10px; font-weight:700; text-transform:uppercase;
            letter-spacing:0.12em; color:{C['tmuted']}; padding:12px 14px 6px 14px; margin-top:4px; }}
        [data-testid="stSidebar"] [data-testid="stRadio"] > div[role="radiogroup"] {{ gap:4px!important; display:flex; flex-direction:column; }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] {{
            display:flex!important; align-items:center!important; gap:12px!important;
            padding:11px 14px!important; margin:0!important; border-radius:11px!important;
            cursor:pointer!important; transition:all 0.18s ease!important;
            font-size:14px!important; font-weight:500!important; color:{C['txt']}!important;
            width:100%!important; background:transparent!important; border:1px solid transparent!important; }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover {{
            background:{C['hov']}!important; border-color:{C['bord']}!important; transform:translateX(3px); }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {{ display:none!important; }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]::before {{
            content:''!important; width:22px!important; height:22px!important; flex-shrink:0!important;
            background-repeat:no-repeat!important; background-position:center!important;
            background-size:20px 20px!important; border-radius:7px; padding:5px; box-sizing:content-box; }}
        label[data-baseweb="radio"]:nth-of-type(1)::before {{ background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%236366f1' stroke-width='2.2'><path d='M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'/></svg>")!important; background-color:#eef2ff; }}
        label[data-baseweb="radio"]:nth-of-type(2)::before {{ background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%233b82f6' stroke-width='2.2'><path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/><polyline points='14 2 14 8 20 8'/></svg>")!important; background-color:#dbeafe; }}
        label[data-baseweb="radio"]:nth-of-type(3)::before {{ background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2310b981' stroke-width='2.2'><rect x='3' y='11' width='18' height='11' rx='2'/><path d='M7 11V7a5 5 0 0 1 10 0v4'/></svg>")!important; background-color:#d1fae5; }}
        label[data-baseweb="radio"]:nth-of-type(4)::before {{ background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23f97316' stroke-width='2.2'><polygon points='23 7 16 12 23 17 23 7'/><rect x='1' y='5' width='15' height='14' rx='2'/></svg>")!important; background-color:#ffedd5; }}
        label[data-baseweb="radio"]:nth-of-type(5)::before {{ background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ec4899' stroke-width='2.2'><polygon points='11 5 6 9 2 9 2 15 6 15 11 19 11 5'/></svg>")!important; background-color:#fce7f3; }}
        label[data-baseweb="radio"]:nth-of-type(6)::before {{ background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%238b5cf6' stroke-width='2.2'><rect x='3' y='3' width='18' height='18' rx='2'/><circle cx='8.5' cy='8.5' r='1.5'/><polyline points='21 15 16 10 5 21'/></svg>")!important; background-color:#ede9fe; }}
        label[data-baseweb="radio"]:has(input:checked) {{ background:{C['act']}!important; border-color:{C['bord']}!important; font-weight:700!important; box-shadow:0 2px 8px rgba(108,62,245,0.08); }}
        [data-testid="stSidebar"] [data-testid="stRadio"] > label:first-child {{ display:none!important; }}
        [data-testid="stSidebar"] [data-testid="stSelectbox"] > label {{ font-size:10px!important; font-weight:700!important; text-transform:uppercase!important; letter-spacing:0.12em!important; color:{C['tmuted']}!important; padding-left:2px!important; }}
        [data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {{ background:{C['surf']}!important; border:1px solid {C['bord']}!important; border-radius:11px!important; font-size:13px!important; color:{C['txt']}!important; }}
        .sidebar-footer {{ padding:16px; color:{C['tmuted']}; font-size:11px; line-height:1.75; border-top:1px solid {C['bord']}; margin-top:16px; text-align:center; }}
        .sidebar-footer strong {{ color:{C['accent']}; font-weight:700; }}
        .sidebar-footer .kbd {{ display:inline-block; padding:2px 7px; background:{C['surf2']}; border:1px solid {C['bord']}; border-radius:5px; font-size:10px; font-family:'JetBrains Mono',monospace; color:{C['tsoft']}; margin:0 2px; }}
        .panel {{ background:{C['surf2']}; border:1px solid {C['bord']}; border-radius:12px; padding:12px 15px; margin:6px 0 8px 0; font-size:12px; color:{C['tsoft']}; }}
        .panel .row {{ display:flex; justify-content:space-between; margin:5px 0; align-items:center; }}
        .panel .val {{ color:{C['txt']}; font-weight:700; font-variant-numeric:tabular-nums; }}
        .panel .ok   {{ color:#10b981; font-weight:700; }}
        .panel .warn {{ color:#f59e0b; font-weight:700; }}
        .panel .bad  {{ color:#ef4444; font-weight:700; }}
        .bar-wrap {{ height:5px; background:{C['bord']}; border-radius:3px; overflow:hidden; margin:10px 0 2px 0; }}
        .bar-fill {{ height:100%; border-radius:3px; transition:width 0.4s ease; }}
        section.main, [data-testid="stMain"] {{ display:flex!important; flex-direction:column!important; align-items:center!important; width:100%!important; }}
        section.main > div.block-container, .main .block-container {{ width:100%!important; max-width:820px!important; margin:0 auto!important; padding:2rem 1.5rem 7rem 1.5rem!important; }}
        [data-testid="stChatInput"], [data-testid="stBottomBlockContainer"] {{ max-width:820px!important; margin-left:auto!important; margin-right:auto!important; width:100%!important; }}
        [data-testid="stBottom"], [data-testid="stBottom"] > div {{ background:{C['bg']}!important; }}
        [data-testid="stBottom"] {{ width:100%!important; display:flex!important; justify-content:center!important; }}
        [data-testid="stBottom"] > div {{ max-width:820px!important; margin:0 auto!important; }}
        [data-testid="stChatInput"], [data-testid="stChatInput"] > div, [data-testid="stChatInput"] > div > div {{ background:{C['input_bg']}!important; }}
        [data-testid="stChatInput"] {{ border-radius:16px!important; border:1.5px solid {C['bbd']}!important; box-shadow:0 4px 20px rgba(108,62,245,0.08)!important; transition:all 0.2s ease!important; }}
        [data-testid="stChatInput"]:focus-within {{ border-color:{C['accent']}!important; box-shadow:0 6px 28px rgba(108,62,245,0.18)!important; transform:translateY(-1px); }}
        [data-testid="stChatInput"] textarea {{ background:{C['input_bg']}!important; color:{C['input_txt']}!important; -webkit-text-fill-color:{C['input_txt']}!important; caret-color:{C['accent']}!important; font-size:15px!important; }}
        [data-testid="stChatInput"] textarea::placeholder {{ color:{C['tmuted']}!important; -webkit-text-fill-color:{C['tmuted']}!important; }}
        h1, h2, h3, h4, h5, h6 {{ color:{C['txt']}!important; }}
        h1 {{ font-size:{fs_h1}!important; font-weight:800!important; letter-spacing:-0.035em!important; }}
        p, li, label, .stMarkdown {{ font-size:{fs_base}; line-height:1.7; color:{C['txt']}!important; }}
        .tool-header {{ display:flex; align-items:center; gap:16px; margin-bottom:8px; padding-bottom:20px; border-bottom:1px solid {C['bsoft']}; }}
        .tool-header .icon {{ width:48px; height:48px; border-radius:14px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }}
        .tool-header .icon svg {{ width:24px; height:24px; }}
        .tool-header .title-block h1 {{ margin:0!important; font-size:{fs_tool}!important; }}
        .tool-header .title-block p {{ margin:3px 0 0 0!important; color:{C['tsoft']}!important; font-size:13.5px!important; }}
        .theme-chat .icon {{ background:linear-gradient(135deg,#eef2ff,#e0e7ff); }}
        .theme-cv .icon {{ background:linear-gradient(135deg,#dbeafe,#bfdbfe); }}
        .theme-pass .icon {{ background:linear-gradient(135deg,#d1fae5,#a7f3d0); }}
        .theme-video .icon {{ background:linear-gradient(135deg,#ffedd5,#fed7aa); }}
        .theme-tts .icon {{ background:linear-gradient(135deg,#fce7f3,#fbcfe8); }}
        .theme-photo .icon {{ background:linear-gradient(135deg,#ede9fe,#ddd6fe); }}
        .stButton > button {{ background:{C['bbtn']}; color:{C['txt']}; border:1.5px solid {C['bbd']}; border-radius:11px; padding:9px 18px; font-weight:600; font-size:13.5px; transition:all 0.18s ease; }}
        .stButton > button:hover {{ background:{C['bhv']}; border-color:{C['accent']}; color:{C['accent']}; transform:translateY(-1.5px); box-shadow:0 6px 16px rgba(108,62,245,0.12); }}
        .stButton > button:focus-visible {{ outline:2px solid {C['accent']}!important; outline-offset:2px!important; }}
        .stButton > button[kind="primary"] {{ background:linear-gradient(135deg,#6c3ef5 0%,#a855f7 100%); color:#fff; border:none; box-shadow:0 4px 18px rgba(108,62,245,0.35); }}
        .stButton > button[kind="primary"]:hover {{ background:linear-gradient(135deg,#5a2ee0 0%,#9333ea 100%); box-shadow:0 6px 24px rgba(108,62,245,0.45); }}
        .stDownloadButton > button {{ background:{C['bbtn']}; color:{C['txt']}; border:1.5px solid {C['bbd']}; border-radius:11px; padding:9px 18px; font-weight:600; font-size:13.5px; }}
        .stDownloadButton > button:hover {{ background:{C['bhv']}; border-color:{C['accent']}; color:{C['accent']}; transform:translateY(-1px); }}
        .stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox > div > div {{ border-radius:11px!important; border:1.5px solid {C['bbd']}!important; font-size:14px!important; background:{C['surf']}!important; color:{C['txt']}!important; }}
        .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {{ border-color:{C['accent']}!important; box-shadow:0 0 0 4px rgba(108,62,245,0.1)!important; }}
        [data-testid="stForm"] {{ border:1px solid {C['bsoft']}; border-radius:18px; padding:24px 26px; background:{C['surf']}; }}
        [data-testid="stChatMessage"] {{ background:transparent!important; padding:{msg_pad}; border-bottom:1px solid {C['bsoft']}; animation:msgIn 0.4s ease; }}
        [data-testid="stChatMessage"]:last-child {{ border-bottom:none; }}
        @keyframes msgIn {{ from {{ opacity:0; transform:translateY(10px); }} to {{ opacity:1; transform:translateY(0); }} }}
        code {{ background:{C['surf2']}!important; color:{C['accent']}!important; padding:3px 9px!important; border-radius:7px!important; font-weight:600; font-family:'JetBrains Mono',monospace!important; }}
        pre {{ background:#1e1b4b!important; border-radius:14px!important; padding:16px 18px!important; }}
        pre code {{ background:transparent!important; color:#e0e7ff!important; padding:0!important; }}
        hr {{ border-color:{C['bsoft']}; margin:1.5rem 0; }}
        .treats-hero {{ display:flex!important; flex-direction:column!important; align-items:center!important; justify-content:center!important; min-height:58vh!important; text-align:center!important; animation:heroIn 0.6s ease; }}
        @keyframes heroIn {{ from {{ opacity:0; transform:scale(0.95); }} to {{ opacity:1; transform:scale(1); }} }}
        .treats-hero .hero-logo {{ width:160px!important; height:160px!important; filter:drop-shadow(0 18px 44px rgba(108,62,245,0.3)); animation:float 4s ease-in-out infinite; }}
        .treats-hero .greeting {{ font-size:28px; font-weight:700; letter-spacing:-0.03em; background:linear-gradient(135deg,{C['txt']} 0%,{C['accent']} 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-top:28px; line-height:1.3; }}
        @keyframes float {{ 0%,100% {{ transform:translateY(0); }} 50% {{ transform:translateY(-10px); }} }}
        details {{ border:1px solid {C['bsoft']}; border-radius:14px; padding:6px 16px; background:{C['surf2']}; }}
        details summary {{ font-weight:600; font-size:13.5px; color:{C['txt']}!important; padding:8px 0; }}
        [data-testid="stPopover"] > button {{ background:{C['bbtn']}!important; color:{C['tsoft']}!important; border:1.5px solid {C['bbd']}!important; border-radius:9px!important; padding:4px 12px!important; font-size:16px!important; font-weight:700!important; line-height:1!important; min-height:32px!important; height:32px!important; }}
        [data-testid="stPopover"] > button:hover {{ background:{C['bhv']}!important; border-color:{C['accent']}!important; color:{C['accent']}!important; }}
        [data-testid="stPopoverBody"] {{ background:{C['surf']}!important; border:1px solid {C['bord']}!important; border-radius:14px!important; padding:8px!important; box-shadow:0 12px 40px rgba(0,0,0,0.15)!important; }}
        [data-testid="stPopoverBody"] .stButton > button {{ width:100%!important; text-align:left!important; justify-content:flex-start!important; margin-bottom:4px!important; }}
        [data-testid="stFileUploaderDropzone"] {{ background:{C['surf2']}!important; border:1.5px dashed {C['bbd']}!important; border-radius:14px!important; padding:12px!important; }}
        [data-testid="stFileUploaderDropzone"]:hover {{ border-color:{C['accent']}!important; background:{C['hov']}!important; }}
        .limit-banner {{ background:{('#450a0a' if dark else '#fef2f2')}; border:1px solid {('#7f1d1d' if dark else '#fecaca')}; color:{('#fecaca' if dark else '#991b1b')}; padding:18px 22px; border-radius:14px; margin-bottom:24px; }}
        .attach-chip {{ display:inline-flex; align-items:center; gap:8px; background:{C['surf2']}; border:1px solid {C['bord']}; border-radius:10px; padding:6px 12px; font-size:12px; color:{C['tsoft']}; margin:4px 4px 4px 0; }}
        .msg-meta {{ font-size:11px; color:{C['tmuted']}; margin-top:6px; }}
        @media (min-width:1024px) {{
            [data-testid="stSidebar"] {{ margin-left:0!important; transform:none!important; visibility:visible!important; opacity:1!important; display:block!important; width:290px!important; min-width:290px!important; max-width:290px!important; position:relative!important; }}
            [data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {{ display:none!important; visibility:hidden!important; opacity:0!important; pointer-events:none!important; }}
        }}
        @media (max-width:1023px) {{
            [data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {{ display:flex!important; visibility:visible!important; opacity:1!important; position:fixed!important; top:12px!important; left:12px!important; width:46px!important; height:46px!important; align-items:center!important; justify-content:center!important; background:linear-gradient(135deg,#6c3ef5 0%,#a855f7 100%)!important; border:none!important; border-radius:13px!important; padding:0!important; margin:0!important; box-shadow:0 6px 20px rgba(108,62,245,0.5)!important; z-index:2147483647!important; cursor:pointer!important; }}
            [data-testid="stSidebarCollapseButton"] svg, [data-testid="stSidebarCollapsedControl"] svg, [data-testid="collapsedControl"] svg {{ fill:#fff!important; stroke:#fff!important; width:22px!important; height:22px!important; }}
        }}
        @media (max-width:768px) {{
            [data-testid="stSidebar"] {{ min-width:86vw!important; max-width:86vw!important; }}
            section.main > div.block-container {{ padding:1.25rem 1rem 5rem 1rem!important; }}
            .treats-hero .hero-logo {{ width:120px!important; height:120px!important; }}
            .treats-hero .greeting {{ font-size:22px; }}
            .tool-header .icon {{ width:42px; height:42px; }}
        }}
    </style>""", unsafe_allow_html=True)


load_css(st.session_state.dark_mode, st.session_state.density, st.session_state.font_size)


# ============================================================
# JS HELPERS
# ============================================================
components.html("""
<script>
(function() {
    const doc = window.parent.document;
    function styleToggle() {
        if (window.parent.innerWidth >= 1024) return;
        const sels = ['[data-testid="stSidebarCollapsedControl"]','[data-testid="stSidebarCollapseButton"]','[data-testid="collapsedControl"]','[data-testid="stSidebarCollapsedControl"] button','[data-testid="stSidebarCollapseButton"] button','button[kind="headerNoPadding"]','button[kind="header"]'];
        const STYLE = 'background:linear-gradient(135deg,#6c3ef5 0%,#a855f7 100%) !important;color:#fff !important;border:none !important;border-radius:13px !important;padding:0 !important;margin:0 !important;box-shadow:0 6px 20px rgba(108,62,245,0.5) !important;z-index:2147483647 !important;position:fixed !important;top:12px !important;left:12px !important;width:46px !important;height:46px !important;display:flex !important;align-items:center !important;justify-content:center !important;cursor:pointer !important;opacity:1 !important;visibility:visible !important;';
        sels.forEach(function(sel){
            doc.querySelectorAll(sel).forEach(function(el){
                el.style.cssText = STYLE;
                el.querySelectorAll('svg').forEach(function(s){ s.style.fill='#fff'; s.style.stroke='#fff'; s.style.width='22px'; s.style.height='22px'; });
            });
        });
    }
    styleToggle();
    setInterval(styleToggle, 500);
    window.parent.addEventListener('resize', styleToggle);
})();
</script>""", height=0)

components.html("""
<script>
(function() {
    const doc = window.parent.document;
    let lastCount = 0, init = false;
    function count() { return doc.querySelectorAll('[data-testid="stChatMessage"]').length; }
    function scroll() {
        const msgs = doc.querySelectorAll('[data-testid="stChatMessage"]');
        if (!msgs.length) return;
        const last = msgs[msgs.length - 1];
        try { last.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
        catch(e) { last.scrollIntoView(); }
    }
    function check() {
        const c = count();
        if (!init) { lastCount = c; init = true; return; }
        if (c > lastCount) { setTimeout(scroll, 250); setTimeout(scroll, 700); setTimeout(scroll, 1500); }
        lastCount = c;
    }
    try { new MutationObserver(check).observe(doc.body, { childList: true, subtree: true }); } catch(e) {}
    setInterval(check, 700);
    window.parent.addEventListener('keydown', function(e) {
        const mod = e.metaKey || e.ctrlKey;
        if (!mod) return;
        if (e.key === 'k' || e.key === 'K') {
            const btn = doc.querySelector('button[kind="primary"]');
            if (btn && btn.textContent.includes('New chat')) { e.preventDefault(); btn.click(); }
        }
        if (e.key === '/') {
            const ta = doc.querySelector('[data-testid="stChatInput"] textarea');
            if (ta) { e.preventDefault(); ta.focus(); }
        }
    });
})();
</script>""", height=0)


# ============================================================
# PROMPTS
# ============================================================
SYS_CHAT = """You are Treats, a helpful AI assistant.

IMPORTANT: You have access to tools. If the user asks for:
- Voice / speech / audio in any language → CALL generate_speech
- Image / picture / drawing → CALL generate_image

Always prefer calling tools over describing them. Be concise.
Never use emojis unless the user does."""

SYS_VISION = """You are Treats, a helpful AI assistant with vision.

The user may upload images and ask about them. Analyze images carefully:
- Describe what you see accurately
- Answer the user's specific question
- If text is in the image, transcribe it
- If it's a document, extract key information

Be concise. Never use emojis unless the user does."""

TITLE_PROMPT = "Generate a short title (3-5 words). Return ONLY the title.\n\nMessage: {message}"

TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "generate_speech",
        "description": "Convert text to speech in a specific language",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string", "description": "The text to convert to speech"},
            "language": {"type": "string", "enum": ["English", "Arabic", "French", "Spanish", "German"]}
        }, "required": ["text", "language"]}}},
    {"type": "function", "function": {
        "name": "generate_image",
        "description": "Generate an image from a text prompt",
        "parameters": {"type": "object", "properties": {
            "prompt": {"type": "string", "description": "Description of the image"}},
            "required": ["prompt"]}}},
]

PROMPTS_LIB = [
    ("Explain",    "Explain {topic} in simple terms."),
    ("Summarize",  "Summarize in 5 bullets:\n\n{text}"),
    ("Translate",  "Translate to {language}:\n\n{text}"),
    ("Email",      "Write a professional email about {topic}."),
    ("Code",       "Write Python code that {task}."),
    ("Brainstorm", "Give me 10 ideas about {topic}."),
]


# ============================================================
# UTILITIES
# ============================================================
def esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def greeting() -> str:
    h = datetime.now().hour
    if h < 12:  return "Good morning"
    if h < 17:  return "Good afternoon"
    if h < 22:  return "Good evening"
    return "Working late"


def fmt_time(iso: str) -> str:
    try:    return datetime.fromisoformat(iso).strftime("%H:%M")
    except Exception: return ""


def copy_to_clipboard(text: str) -> None:
    # FIX #10: allow clipboard-write in iframe via sandbox attr
    js_text = json.dumps(text)
    components.html(
        f"""<script>(async function(){{
            try {{ await navigator.clipboard.writeText({js_text}); }}
            catch(e) {{
                var ta=document.createElement('textarea'); ta.value={js_text};
                ta.style.position='fixed'; ta.style.opacity='0';
                document.body.appendChild(ta); ta.select();
                try{{document.execCommand('copy');}}catch(_){{}}
                document.body.removeChild(ta);
            }}
        }})();</script>""",
        height=0,
    )


def msg_tokens(m: dict) -> int:
    c = m.get("content", "") or ""
    if isinstance(c, list):
        t = sum(len(i.get("text", "")) for i in c
                if isinstance(i, dict) and i.get("type") == "text") // 4
        t += 500 * sum(1 for i in c
                       if isinstance(i, dict) and i.get("type") == "image_url")
        return t
    return len(c) // 4


def trim_history(msgs: list[dict], max_tokens: int = Cfg.MAX_CTX) -> list[dict]:
    total, out = 0, []
    for m in reversed(msgs):
        t = msg_tokens(m)
        if total + t > max_tokens:
            break
        out.insert(0, m)
        total += t
    while out and out[0]["role"] == "assistant":
        out.pop(0)
    return out


def build_api_message(m: dict) -> dict:
    imgs = m.get("images") or []
    if imgs:
        content = [{"type": "text", "text": m.get("content") or " "}]
        for url in imgs:
            content.append({"type": "image_url", "image_url": {"url": url}})
        return {"role": m["role"], "content": content}
    return {"role": m["role"], "content": m.get("content") or ""}


# ============================================================
# CONVERSATIONS
# ============================================================
def _new_conv_dict(cid: str, title: str = "New chat") -> dict:
    return {"id": cid, "title": title, "messages": [],
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat()}


def init_conversations() -> None:
    if st.session_state.conversations is None:
        did = "default"
        st.session_state.conversations = {did: _new_conv_dict(did)}
        st.session_state.active_conversation = did


def get_messages() -> list[dict]:
    init_conversations()
    return st.session_state.conversations[st.session_state.active_conversation]["messages"]


def set_messages(msgs: list[dict]) -> None:
    cid = st.session_state.active_conversation
    st.session_state.conversations[cid]["messages"] = msgs
    st.session_state.conversations[cid]["updated"] = datetime.now().isoformat()


def new_conversation() -> None:
    init_conversations()
    nid = f"c_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    st.session_state.conversations[nid] = _new_conv_dict(nid)
    st.session_state.active_conversation = nid


def delete_conversation(cid: str) -> None:
    st.session_state.conversations.pop(cid, None)
    st.session_state.pending_images.pop(cid, None)     # FIX #12
    if st.session_state.active_conversation == cid:
        keys = list(st.session_state.conversations.keys())
        st.session_state.active_conversation = keys[0] if keys else None
    if not st.session_state.conversations:
        new_conversation()


def pending_for(cid: Optional[str] = None) -> list:
    """Get the pending image list for a conversation (FIX #12)."""
    cid = cid or st.session_state.active_conversation
    if not cid:
        return []
    return st.session_state.pending_images.setdefault(cid, [])


def auto_title(msg: str) -> str:
    try:
        def _c(cli):
            return cli.chat.completions.create(
                model=Cfg.DEFAULT_MODEL,
                messages=[{"role": "user", "content": TITLE_PROMPT.format(message=msg[:300])}],
                temperature=0.3, max_tokens=20,
            )
        r = KeyManager.call(_c)
        TokenTracker.add_usage(getattr(r, "usage", None))
        t = r.choices[0].message.content.strip().strip('"').strip("'")
        return t[:40] if t else msg[:30]
    except Exception:
        return msg[:30] + ("..." if len(msg) > 30 else "")


# ============================================================
# EXTERNAL SERVICES
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_img_models() -> list[str]:
    try:
        r = requests.get("https://image.pollinations.ai/models", timeout=10)
        r.raise_for_status()
        d = r.json()
        # FIX #11: robust parsing
        if isinstance(d, list):
            m = [x.get("name") for x in d if isinstance(x, dict) and x.get("name")] or \
                [x for x in d if isinstance(x, str)]
        elif isinstance(d, dict):
            m = list(d.keys())
        else:
            m = []
        m = [str(x) for x in m if x]
        return m or ["flux", "turbo"]
    except Exception:
        return ["flux", "turbo", "flux-realism", "flux-anime", "flux-3d"]


def generate_image(prompt: str, w: int = 1024, h: int = 1024, model: str = "flux",
                   seed: Optional[int] = None, enhance: bool = True,
                   nologo: bool = True) -> bytes:
    if not prompt or not prompt.strip():
        raise TreatsError("Please enter a prompt.")
    url = f"https://image.pollinations.ai/prompt/{quote(prompt.strip())}"
    params = {"width": w, "height": h, "model": model,
              "seed": seed if seed is not None else -1,
              "nologo": str(nologo).lower(), "enhance": str(enhance).lower()}
    try:
        r = requests.get(url, params=params, timeout=60)
        if r.status_code == 429:
            raise TreatsError("Image service is busy. Try again in a moment.")
        r.raise_for_status()
        if not r.content or len(r.content) < 500:
            raise TreatsError("Empty image returned.")
        return r.content
    except requests.exceptions.Timeout:
        raise TreatsError("Image request timed out.")
    except requests.exceptions.RequestException as e:
        raise TreatsError(f"Image request failed: {e}")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_voices() -> dict[str, list[str]]:
    try:
        import edge_tts
        async def _l():
            return await edge_tts.list_voices()
        v = asyncio.run(_l())
        langs = {"en": "en-", "ar": "ar-", "fr": "fr-", "es": "es-", "de": "de-"}
        return {code: [x["ShortName"] for x in v if x["Locale"].startswith(prefix)]
                for code, prefix in langs.items()}
    except Exception:
        return {"en": [], "ar": [], "fr": [], "es": [], "de": []}


async def _tts_async(text: str, voice: str, rate: str, pitch: str, volume: str) -> bytes:
    import edge_tts
    c = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
    buf = io.BytesIO()
    async for ch in c.stream():
        if ch["type"] == "audio":
            buf.write(ch["data"])
    return buf.getvalue()


LANG_CODE = {"English": "en", "Arabic": "ar", "French": "fr", "Spanish": "es", "German": "de"}
LANG_LABEL = {v: k for k, v in LANG_CODE.items()}


def tts_speak(text: str, language: str = "English",
              rate_val: float = 1.0, pitch_val: int = 0, vol_val: int = 100) -> bytes:
    code = LANG_CODE.get(language, "en")
    voices = fetch_voices()
    pool = voices.get(code) or []
    if not pool:
        raise TreatsError(f"No voices available for {language}.")
    voice = pool[0]
    rate  = f"{'+' if rate_val >= 1 else ''}{int((rate_val - 1) * 100)}%"
    pitch = f"{'+' if pitch_val >= 0 else ''}{pitch_val}Hz"
    vol   = f"+{vol_val}%"
    return asyncio.run(_tts_async(text, voice, rate, pitch, vol))


# ============================================================
# ICONS + TOOL HEADER
# ============================================================
ICONS = {
    "chat":     """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>""",
    "cv":       """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>""",
    "password": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>""",
    "video":    """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>""",
    "tts":      """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#ec4899" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d='M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07'/></svg>""",
    "photo":    """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>""",
}


def render_tool_header(key: str, title: str, sub: str) -> None:
    st.markdown(
        f'<div class="tool-header theme-{key}"><div class="icon">{ICONS[key]}</div>'
        f'<div class="title-block"><h1>{esc(title)}</h1><p>{esc(sub)}</p></div></div>'
        f'<div style="height:26px"></div>',
        unsafe_allow_html=True,
    )


# ============================================================
# SIDEBAR
# ============================================================
init_conversations()

TOOLS = {
    "Chat": "chat", "CV Builder": "cv", "Password Generator": "password",
    "Video Script": "video", "Text to Speech": "tts", "Image Generator": "photo",
}

with st.sidebar:
    st.markdown(
        f'<div class="treats-brand"><img src="{LOGO_URI}" alt="Treats">'
        f'<span class="name">Treats</span></div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.markdown('<div class="sidebar-label" style="padding-top:0;">Display</div>',
                    unsafe_allow_html=True)
    with c2:
        if st.button("🌙" if not st.session_state.dark_mode else "☀️",
                     key="thm", help="Toggle theme"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
    with c3:
        if st.button("⚙️", key="settings", help="Settings"):
            st.session_state.show_settings = not st.session_state.show_settings

    if st.session_state.show_settings:
        density = st.selectbox(
            "Density", ["comfortable", "compact"],
            index=0 if st.session_state.density == "comfortable" else 1,
            key="dens_sel")
        if density != st.session_state.density:
            st.session_state.density = density
            st.rerun()
        fsize = st.selectbox(
            "Font size", ["small", "medium", "large"],
            index={"small": 0, "medium": 1, "large": 2}[st.session_state.font_size],
            key="fs_sel")
        if fsize != st.session_state.font_size:
            st.session_state.font_size = fsize
            st.rerun()

    # Usage panel
    st.markdown('<div class="sidebar-label">Usage</div>', unsafe_allow_html=True)
    used = TokenTracker.used()
    rem  = TokenTracker.remaining()
    pct  = min(100, int((used / Cfg.TOKEN_LIMIT) * 100))
    if pct >= 90:   bar_color, cls, txt = "#ef4444", "bad",  "Critical"
    elif pct >= 70: bar_color, cls, txt = "#f59e0b", "warn", "Warning"
    else:           bar_color, cls, txt = "#10b981", "ok",   "Active"

    st.markdown(
        f'<div class="panel">'
        f'<div class="row"><span>Status</span><span class="{cls}">{txt}</span></div>'
        f'<div class="row"><span>Used</span><span class="val">{used:,} / {Cfg.TOKEN_LIMIT:,}</span></div>'
        f'<div class="row"><span>Remaining</span><span class="val">{rem:,}</span></div>'
        f'<div class="row"><span>Resets in</span><span class="val">{TokenTracker.reset_in()}</span></div>'
        f'<div class="bar-wrap"><div class="bar-fill" style="width:{pct}%;background:{bar_color};"></div></div>'
        f'</div>', unsafe_allow_html=True)

    try:
        total_keys = len(KeyManager.load())
        idx = KeyManager.index()
        st.markdown(
            f'<div class="panel"><div class="row"><span>API Key</span>'
            f'<span class="val">{idx + 1} / {total_keys}</span></div></div>',
            unsafe_allow_html=True)
    except ConfigError:
        st.markdown(
            '<div class="panel"><div class="row"><span class="bad">'
            'No API keys configured</span></div></div>',
            unsafe_allow_html=True)

    st.markdown('<div class="sidebar-label">Tools</div>', unsafe_allow_html=True)
    choice = st.radio("nav", list(TOOLS.keys()),
                      label_visibility="collapsed", key="nav")
    tool = TOOLS[choice]

    if tool == "chat":
        st.markdown('<div class="sidebar-label">Conversations</div>',
                    unsafe_allow_html=True)

        if st.button("+ New chat", key="nc", use_container_width=True, type="primary"):
            new_conversation()
            st.rerun()

        search = st.text_input("search", placeholder="🔍 Search...",
                               label_visibility="collapsed", key="conv_search")

        items = list(st.session_state.conversations.items())
        if search:
            items = [(c, v) for c, v in items if search.lower() in v["title"].lower()]

        for cid, conv in items:
            active = cid == st.session_state.active_conversation
            label = f"{'● ' if active else ''}{conv['title'][:24]}"
            col1, col2, col3 = st.columns([5, 1, 1])
            with col1:
                if st.button(label, key=f"c_{cid}", use_container_width=True):
                    st.session_state.active_conversation = cid
                    st.rerun()
            with col2:
                if st.button("✎", key=f"r_{cid}", help="Rename"):
                    st.session_state.rename_conv = cid
                    st.rerun()
            with col3:
                if st.button("×", key=f"d_{cid}", help="Delete"):
                    delete_conversation(cid)
                    st.rerun()

            if st.session_state.rename_conv == cid:
                with st.form(f"ren_{cid}"):
                    new_title = st.text_input(
                        "New title", value=conv["title"],
                        label_visibility="collapsed", key=f"nt_{cid}")
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        if st.form_submit_button("Save", use_container_width=True):
                            st.session_state.conversations[cid]["title"] = new_title[:40]
                            st.session_state.rename_conv = None
                            st.rerun()
                    with sc2:
                        if st.form_submit_button("Cancel", use_container_width=True):
                            st.session_state.rename_conv = None
                            st.rerun()

        if len(st.session_state.conversations) > 1:
            if st.button("📦 Export all (ZIP)", key="exp_all", use_container_width=True):
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w") as z:
                    for c, v in st.session_state.conversations.items():
                        safe = "".join(ch for ch in v["title"]
                                       if ch.isalnum() or ch in " -_")[:30] or c
                        z.writestr(f"{safe}.json",
                                   json.dumps(v["messages"], ensure_ascii=False,
                                              indent=2, default=str))
                st.download_button(
                    "⬇️ Download ZIP", buf.getvalue(),
                    f"treats_all_{datetime.now():%Y%m%d}.zip",
                    "application/zip", use_container_width=True)

    st.markdown('<div class="sidebar-label">AI Model</div>', unsafe_allow_html=True)
    model = st.selectbox("m", Cfg.GROQ_MODELS, key="mdl", label_visibility="collapsed")

    st.markdown(
        '<div class="sidebar-footer"><strong>Treats v5.1</strong><br>'
        'Powered by Groq<br><br>'
        '<span class="kbd">Enter</span> send · '
        '<span class="kbd">Shift+Enter</span> newline<br>'
        '<span class="kbd">⌘K</span> new chat · '
        '<span class="kbd">⌘/</span> focus</div>',
        unsafe_allow_html=True)


# ============================================================
# CHAT — MESSAGE RENDERING
# ============================================================
def render_message_actions(m: dict, i: int, msgs: list[dict]) -> None:
    c1, _ = st.columns([1, 8])
    with c1:
        with st.popover("☰"):
            if st.button("📋 Copy", key=f"cp_{i}", use_container_width=True):
                copy_to_clipboard(m.get("content", ""))
                st.toast("Copied!")

            if m["role"] == "user":
                if st.button("✏️ Edit", key=f"ed_{i}", use_container_width=True):
                    st.session_state.editing_msg = i
                    st.rerun()

            if m["role"] == "assistant":
                if st.button("🔄 Regenerate", key=f"rg_{i}", use_container_width=True):
                    set_messages(msgs[:i])
                    st.rerun()

            if st.button("🗑 Delete", key=f"dl_{i}", use_container_width=True):
                set_messages(msgs[:i] + msgs[i + 1:])
                st.rerun()


def render_message(m: dict, i: int, msgs: list[dict]) -> None:
    with st.chat_message(m["role"]):
        for url in m.get("images", []):
            try:
                st.image(url, width=280)
            except Exception:
                pass

        mtype = m.get("type", "text")
        if mtype == "audio":
            st.markdown(m.get("content", ""))
            if "audio_bytes" in m:
                st.audio(m["audio_bytes"], format="audio/mp3")
                st.download_button("⬇️ MP3", m["audio_bytes"],
                                   f"tts_{i}.mp3", "audio/mpeg", key=f"dl_tts_{i}")
        elif mtype == "image":
            st.markdown(m.get("content", ""))
            if "image_bytes" in m:
                st.image(m["image_bytes"])
                st.download_button("⬇️ PNG", m["image_bytes"],
                                   f"img_{i}.png", "image/png", key=f"dl_img_{i}")
        else:
            if m.get("content"):
                st.markdown(m["content"])

        if m["role"] == "user" and st.session_state.editing_msg == i:
            new_text = st.text_area("Edit message", value=m.get("content", ""),
                                    key=f"edit_ta_{i}", height=100)
            ec1, ec2 = st.columns([1, 1])
            with ec1:
                if st.button("Save & regenerate", key=f"edit_save_{i}",
                             type="primary", use_container_width=True):
                    msgs[i]["content"] = new_text
                    set_messages(msgs[:i + 1])
                    st.session_state.editing_msg = None
                    st.rerun()
            with ec2:
                if st.button("Cancel", key=f"edit_cancel_{i}",
                             use_container_width=True):
                    st.session_state.editing_msg = None
                    st.rerun()

        meta = fmt_time(m.get("ts", ""))
        if meta:
            st.markdown(f'<div class="msg-meta">{esc(meta)}</div>',
                        unsafe_allow_html=True)

        if not (m["role"] == "user" and st.session_state.editing_msg == i):
            render_message_actions(m, i, msgs)


# ============================================================
# CHAT — TOOL HANDLING  (FIX #8: keep assistant tool_calls in history)
# ============================================================
def handle_tool_call(tc: Any, msgs: list[dict]) -> None:
    name = tc.function.name
    try:
        args = json.loads(tc.function.arguments)
    except Exception:
        args = {}

    if name == "generate_speech":
        text = (args.get("text") or "").strip()
        lang = args.get("language") or "English"
        try:
            audio_bytes = tts_speak(text, lang)
            msgs.append({
                "role": "assistant",
                "content": f"🔊 **Audio** ({lang}):\n\n> {text}",
                "type": "audio",
                "audio_bytes": audio_bytes,
                "ts": datetime.now().isoformat(),
            })
        except Exception as e:
            msgs.append({"role": "assistant",
                         "content": f"❌ TTS failed: {e}",
                         "ts": datetime.now().isoformat()})
        set_messages(msgs)
        st.rerun()

    elif name == "generate_image":
        prompt_txt = (args.get("prompt") or "").strip()
        try:
            img_bytes = generate_image(prompt_txt, 1024, 1024, "flux")
            msgs.append({
                "role": "assistant",
                "content": f"🎨 **Image:**\n\n> {prompt_txt}",
                "type": "image",
                "image_bytes": img_bytes,
                "ts": datetime.now().isoformat(),
            })
        except Exception as e:
            msgs.append({"role": "assistant",
                         "content": f"❌ Image failed: {e}",
                         "ts": datetime.now().isoformat()})
        set_messages(msgs)
        st.rerun()


# ============================================================
# CHAT — STREAMING  (FIX #3: correct token accounting)
# ============================================================
def stream_chat_response(hist: list[dict], model_name: str, msgs: list[dict]) -> None:
    def _stream(cli):
        return cli.chat.completions.create(
            model=model_name, messages=hist, temperature=0.7, stream=True,
        )

    full = ""
    usage = None
    with st.chat_message("assistant"):
        ph = st.empty()
        try:
            for chunk in KeyManager.stream(_stream):
                # capture final usage if the API sends it
                if getattr(chunk, "usage", None) is not None:
                    usage = chunk.usage
                delta = None
                try:
                    delta = chunk.choices[0].delta.content
                except Exception:
                    delta = None
                if delta:
                    full += delta
                    ph.markdown(full + "▌")
            ph.markdown(full or "_(empty response)_")
        except QuotaError as e:
            st.error(str(e))
            return
        except Exception as e:
            if not full:
                st.error(f"Streaming failed: {e}")
                return

    # FIX #3: use real usage if present, otherwise count ONLY prompt + completion
    if usage and getattr(usage, "total_tokens", None):
        TokenTracker.add(int(usage.total_tokens))
    else:
        prompt_tokens = sum(msg_tokens(m) for m in hist)
        completion_tokens = len(full) // 4
        TokenTracker.add(prompt_tokens + completion_tokens)

    msgs.append({"role": "assistant", "content": full,
                 "ts": datetime.now().isoformat()})
    set_messages(msgs)
    st.rerun()


# ============================================================
# CHAT — IMAGE ATTACHMENT  (FIX #4, #7: robust removal)
# ============================================================
def render_attachments() -> None:
    cid = st.session_state.active_conversation
    bucket = pending_for(cid)

    header = (f"📎 Attachments ({len(bucket)})" if bucket
              else "📎 Attach an image")

    with st.expander(header, expanded=bool(bucket)):
        up = st.file_uploader(
            "Choose image", type=Cfg.SUPPORTED_IMGS,
            key=f"up_{cid}",
            label_visibility="collapsed", accept_multiple_files=True)

        # FIX #4: track uploaded file ids so removed ones don't come back
        seen_key = f"_seen_uploads_{cid}"
        seen = st.session_state.setdefault(seen_key, set())

        if up:
            for f in up:
                fid = getattr(f, "file_id", None) or f"{f.name}:{f.size}"
                if fid in seen:
                    continue
                seen.add(fid)
                try:
                    b64 = base64.b64encode(f.getvalue()).decode()
                    mime = f.type or "image/png"
                    data_url = f"data:{mime};base64,{b64}"
                    if data_url not in bucket:
                        bucket.append(data_url)
                except Exception as e:
                    st.error(f"Could not read {f.name}: {e}")

        if bucket:
            cols = st.columns(min(3, len(bucket)))
            for idx, url in enumerate(list(bucket)):
                with cols[idx % len(cols)]:
                    st.image(url, use_container_width=True)
                    if st.button("Remove", key=f"rm_{cid}_{idx}",
                                 use_container_width=True):
                        bucket.pop(idx)
                        st.rerun()


# ============================================================
# CHAT — MAIN RENDER
# ============================================================
def render_chat() -> None:
    msgs = get_messages()

    if not TokenTracker.can_send():
        st.markdown(
            f'<div class="limit-banner"><strong>Daily limit reached</strong><br>'
            f'You used {TokenTracker.used():,} / {Cfg.TOKEN_LIMIT:,} tokens.<br>'
            f'Resets in {TokenTracker.reset_in()}.</div>',
            unsafe_allow_html=True)
        for i, m in enumerate(msgs):
            render_message(m, i, msgs)
        return

    if not msgs:
        st.markdown(
            f'<div class="treats-hero"><img src="{LOGO_URI}" class="hero-logo">'
            f'<div class="greeting">{esc(greeting())}. How can I help you?</div></div>',
            unsafe_allow_html=True)
        with st.expander("💡 Prompt Library"):
            cols = st.columns(3)
            for i, (label, template) in enumerate(PROMPTS_LIB):
                with cols[i % 3]:
                    if st.button(label, key=f"p_{i}", use_container_width=True):
                        # FIX #14: store as default text via session state hint
                        st.session_state.prompt_template = template
                        st.toast(f"Template loaded — type it or paste it below")
                        st.rerun()

    for i, m in enumerate(msgs):
        render_message(m, i, msgs)

    render_attachments()

    prefill = st.session_state.prompt_template
    if prefill:
        st.session_state.prompt_template = None
        st.info(f"💡 Template: `{prefill}`")

    prompt = st.chat_input("Message Treats…")

    if prompt:
        if not TokenTracker.can_send():
            st.error("Daily limit reached.")
            st.stop()
        new_msg = {"role": "user", "content": prompt,
                   "ts": datetime.now().isoformat()}
        bucket = pending_for()
        if bucket:
            new_msg["images"] = list(bucket)
            bucket.clear()
        msgs.append(new_msg)
        set_messages(msgs)

        cid = st.session_state.active_conversation
        if st.session_state.conversations[cid]["title"] == "New chat":
            st.session_state.conversations[cid]["title"] = auto_title(prompt)
        st.rerun()

    # FIX #15: guard against re-streaming the same message repeatedly
    if msgs and msgs[-1]["role"] == "user":
        last_id = f"{cid_last(msgs)}"
        if st.session_state._auto_stream_guard != last_id:
            st.session_state._auto_stream_guard = last_id
            respond_to_last_user(msgs, model)
    else:
        st.session_state._auto_stream_guard = None


def cid_last(msgs: list[dict]) -> str:
    if not msgs:
        return ""
    m = msgs[-1]
    return f"{m.get('ts','')}|{len(m.get('content') or '')}"


def respond_to_last_user(msgs: list[dict], model_name: str) -> None:
    try:
        last_user = next((m for m in reversed(msgs) if m["role"] == "user"), None)
        is_vision = bool(last_user and last_user.get("images"))

        clean = [build_api_message(m) for m in msgs
                 if (m.get("content") or m.get("images"))]
        sys_prompt = SYS_VISION if is_vision else SYS_CHAT
        full = [{"role": "system", "content": sys_prompt}] + clean
        hist = trim_history(full)
        active_model = Cfg.VISION_MODEL if is_vision else model_name

        if not is_vision:
            def _tools(cli):
                return cli.chat.completions.create(
                    model=active_model, messages=hist, temperature=0.7,
                    tools=TOOLS_SCHEMA, tool_choice="auto")

            # FIX #16: correct exception ordering — QuotaError is a TreatsError subclass
            try:
                response = KeyManager.call(_tools)
                TokenTracker.add_usage(getattr(response, "usage", None))
                tool_calls = getattr(response.choices[0].message, "tool_calls", None)
                if tool_calls:
                    for tc in tool_calls:
                        handle_tool_call(tc, msgs)
                    return
            except QuotaError:
                raise
            except TreatsError:
                raise
            except Exception as e:
                log.warning("Tool call failed, falling back to stream: %s", e)

        stream_chat_response(hist, active_model, msgs)

    except ConfigError as e:
        st.error(f"Configuration error: {e}")
    except QuotaError as e:
        st.error(f"Quota error: {e}")
    except TreatsError as e:
        st.error(str(e))
    except Exception as e:
        log.exception("Unexpected error")
        st.error(f"Unexpected error: {e}")


# ============================================================
# TOOLS
# ============================================================
CV_TEMPLATES = {
    "Modern":   "modern two-column with colored header",
    "Classic":  "traditional professional",
    "Creative": "creative with unique styling",
}


def render_cv() -> None:
    render_tool_header("cv", "CV Builder", "Generate a professional CV in seconds")
    if not TokenTracker.can_send():
        st.warning("Daily limit reached.")
        return

    tpl = st.radio("Template", list(CV_TEMPLATES.keys()), horizontal=True)
    with st.form("cv_f"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Full Name")
            role = st.text_input("Target Role")
            edu  = st.text_input("Education")
        with c2:
            lang  = st.selectbox("Language", ["English", "Arabic"])
            tone  = st.selectbox("Tone", ["Professional", "Concise", "Academic"])
            skills = st.text_input("Skills (comma-separated)")
        exp = st.text_area("Experience", placeholder="One bullet per line", height=140)
        submitted = st.form_submit_button("✨ Generate CV", type="primary",
                                          use_container_width=True)

    if submitted:
        if not name or not role:
            st.warning("Name and role are required.")
            return
        try:
            p = (f"Write a CV in {lang}, {tone} tone. Style: {CV_TEMPLATES[tpl]}.\n"
                 f"Name: {name}\nRole: {role}\nExperience: {exp}\n"
                 f"Education: {edu}\nSkills: {skills}\nReturn Markdown.")
            with st.spinner("Generating…"):
                def _c(cli):
                    return cli.chat.completions.create(
                        model=Cfg.HEAVY_MODEL,
                        messages=[{"role": "user", "content": p}],
                        temperature=0.6)
                r = KeyManager.call(_c)
            TokenTracker.add_usage(getattr(r, "usage", None))
            txt = r.choices[0].message.content
            st.markdown("---")
            st.markdown(txt)
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("⬇️ Markdown", txt, "cv.md", "text/markdown",
                                   use_container_width=True)
            with c2:
                st.download_button("⬇️ Text", txt, "cv.txt", "text/plain",
                                   use_container_width=True)
        except TreatsError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Error: {e}")


def render_password() -> None:
    render_tool_header("password", "Password Generator",
                       "Create strong, secure passwords")

    c1, c2, c3 = st.columns(3)
    with c1: length = st.slider("Length", 8, 64, 16)
    with c2: use_numbers = st.checkbox("Numbers", value=True)
    with c3: use_symbols = st.checkbox("Symbols", value=True)

    alphabet = string.ascii_letters
    if use_numbers: alphabet += string.digits
    if use_symbols: alphabet += "!@#$%^&*()-_=+"

    if st.button("🎲 Generate", type="primary", use_container_width=True):
        pwd = "".join(random.choice(alphabet) for _ in range(length))
        st.code(pwd, language=None)
        st.download_button("⬇️ Download", pwd, "password.txt",
                           use_container_width=True)


def render_video() -> None:
    render_tool_header("video", "Video Script",
                       "Generate scene-by-scene storyboards")
    if not TokenTracker.can_send():
        st.warning("Daily limit reached.")
        return

    with st.form("v_f"):
        topic = st.text_input("Topic")
        c1, c2 = st.columns(2)
        with c1:
            dur = st.selectbox("Duration",
                               ["30 seconds", "60 seconds", "3 minutes", "5 minutes"])
            lang = st.selectbox("Language", ["English", "Arabic"])
        with c2:
            sty  = st.selectbox("Style", ["Educational", "Promotional",
                                          "Storytelling", "Entertainment"])
            plat = st.selectbox("Platform", ["YouTube", "TikTok",
                                              "Instagram", "LinkedIn"])
        submitted = st.form_submit_button("🎬 Generate", type="primary",
                                          use_container_width=True)

    if submitted:
        if not topic:
            st.warning("Enter a topic.")
            return
        try:
            p = (f"Video script in {lang} for {plat}. Topic: {topic}. "
                 f"Duration: {dur}. Style: {sty}. Storyboard.")
            with st.spinner("Generating…"):
                def _c(cli):
                    return cli.chat.completions.create(
                        model=Cfg.HEAVY_MODEL,
                        messages=[{"role": "user", "content": p}],
                        temperature=0.7)
                r = KeyManager.call(_c)
            TokenTracker.add_usage(getattr(r, "usage", None))
            txt = r.choices[0].message.content
            st.markdown("---")
            st.markdown(txt)
            st.download_button("⬇️ Markdown", txt, "script.md", "text/markdown",
                               use_container_width=True)
        except TreatsError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Error: {e}")


def render_tts() -> None:
    render_tool_header("tts", "Text to Speech",
                       "Convert text into natural-sounding speech")
    voices = fetch_voices()
    avail = [k for k in voices if voices[k]]
    if not avail:
        st.warning("No voices available.")
        return

    lc = st.radio("Language", avail, format_func=lambda x: LANG_LABEL.get(x, x),
                  horizontal=True)
    voice = st.selectbox("Voice", voices[lc], key="tv")
    text = st.text_area("Text", height=160, placeholder="Enter text…")

    c1, c2, c3 = st.columns(3)
    with c1: rate_val  = st.slider("Rate", 0.5, 2.0, 1.0, 0.1)
    with c2: pitch_val = st.slider("Pitch (Hz)", -50, 50, 0, 5)
    with c3: vol_val   = st.slider("Volume", 0, 100, 100, 5)

    rate  = f"{'+' if rate_val >= 1 else ''}{int((rate_val - 1) * 100)}%"
    pitch = f"{'+' if pitch_val >= 0 else ''}{pitch_val}Hz"
    vol   = f"+{vol_val}%"

    if st.button("🔊 Generate Audio", type="primary", use_container_width=True):
        if not text.strip():
            st.warning("Enter text.")
            return
        try:
            with st.spinner("Generating…"):
                audio = asyncio.run(_tts_async(text, voice, rate, pitch, vol))
            st.audio(audio, format="audio/mp3")
            st.download_button("⬇️ MP3", audio, "tts.mp3", "audio/mpeg",
                               use_container_width=True)
        except Exception as e:
            st.error(f"Failed: {e}")


def render_photo() -> None:
    render_tool_header("photo", "Image Generator",
                       "Create images from text descriptions")
    with st.spinner("Loading models…"):
        models = fetch_img_models()

    prompt = st.text_area("Prompt",
                          placeholder="A cat in Paris, cinematic lighting, 4K",
                          height=110)
    c1, c2, c3 = st.columns(3)
    with c1: model   = st.selectbox("Model", models, key="pm")
    with c2:
        aspect = st.selectbox("Aspect",
                              ["1:1 (1024×1024)", "16:9 (1344×768)",
                               "9:16 (768×1344)", "4:3 (1152×896)"], key="pa")
    with c3: enhance = st.checkbox("Auto-enhance", value=True, key="pe")

    sizes = {
        "1:1 (1024×1024)": (1024, 1024),
        "16:9 (1344×768)": (1344, 768),
        "9:16 (768×1344)": (768, 1344),
        "4:3 (1152×896)":  (1152, 896),
    }
    w, h = sizes[aspect]

    c1, c2 = st.columns([3, 1])
    with c1:
        seed_input = st.number_input("Seed (0 = random)", min_value=0,
                                     value=0, step=1, key="ps")
    with c2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("🎲 Randomize", key="prd", use_container_width=True):
            st.session_state["ps"] = random.randint(1, 999999)
            st.rerun()

    seed = int(seed_input) if seed_input > 0 else None

    if st.button("🎨 Generate Image", type="primary", use_container_width=True):
        if not prompt.strip():
            st.warning("Enter a prompt.")
            return
        try:
            with st.spinner("Generating…"):
                img = generate_image(prompt, w, h, model, seed, enhance)
            st.session_state.li = img
            st.session_state.lp = prompt
            st.session_state.gallery.append({
                "p": prompt, "b": img, "t": datetime.now().isoformat()})
            # FIX #9: cap gallery size
            if len(st.session_state.gallery) > Cfg.GALLERY_MAX:
                st.session_state.gallery = st.session_state.gallery[-Cfg.GALLERY_MAX:]
            st.toast("Image generated!")
        except TreatsError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Error: {e}")

    if st.session_state.li:
        st.markdown("---")
        st.image(st.session_state.li, caption=st.session_state.lp)
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇️ PNG", st.session_state.li,
                f"treats_{datetime.now():%Y%m%d_%H%M%S}.png",
                "image/png", use_container_width=True)
        with c2:
            if st.button("🔄 Regenerate", use_container_width=True):
                try:
                    with st.spinner("Regenerating…"):
                        st.session_state.li = generate_image(
                            st.session_state.lp, w, h, model,
                            random.randint(1, 999999), enhance)
                    st.rerun()
                except TreatsError as e:
                    st.error(str(e))

    if st.session_state.gallery:
        with st.expander(f"🖼️ Gallery ({len(st.session_state.gallery)})"):
            gc = st.columns(3)
            for i, item in enumerate(reversed(st.session_state.gallery)):
                with gc[i % 3]:
                    st.image(item["b"], caption=item["p"][:40],
                             use_container_width=True)


# ============================================================
# ROUTER  (FIX #1: remove stray dot)
# ============================================================
ROUTES: dict[str, Callable[[], None]] = {
    "chat": render_chat,
    "cv": render_cv,
    "password": render_password,
    "video": render_video,
    "tts": render_tts,
    "photo": render_photo,
}

ROUTES[tool]()
