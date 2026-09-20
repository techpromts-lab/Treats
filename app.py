import streamlit as st
import requests
import json
import random
import asyncio
import io
from urllib.parse import quote
from datetime import datetime

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Treats",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CUSTOM CSS  —  ChatGPT-inspired professional UI
# ============================================================
def load_css():
    st.markdown("""
    <style>
        /* ---------- Fonts ---------- */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        /* ---------- Hide Streamlit branding ---------- */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        header[data-testid="stHeader"] {
            background: transparent;
            height: 0;
        }
        [data-testid="stToolbar"] { display: none; }
        [data-testid="stDecoration"] { display: none; }

        /* ---------- App background ---------- */
        .stApp {
            background: #ffffff;
        }

        /* ---------- Sidebar ---------- */
        [data-testid="stSidebar"] {
            background: #f9f9f9;
            border-right: 1px solid #ececec;
        }
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem;
        }

        /* Sidebar brand */
        .treats-brand {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 14px 20px 14px;
            font-size: 18px;
            font-weight: 600;
            color: #0d0d0d;
            letter-spacing: -0.01em;
        }
        .treats-brand .dot {
            width: 26px;
            height: 26px;
            background: #10a37f;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 700;
            font-size: 13px;
        }

        /* Sidebar nav buttons (radio) */
        [data-testid="stSidebar"] [role="radiogroup"] {
            gap: 2px;
        }
        [data-testid="stSidebar"] [role="radiogroup"] > label {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.12s ease;
            font-size: 14px;
            color: #0d0d0d;
            margin: 0;
        }
        [data-testid="stSidebar"] [role="radiogroup"] > label:hover {
            background: #ececec;
        }
        [data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {
            display: none; /* hide default radio circle */
        }
        [data-testid="stSidebar"] [role="radiogroup"] > label[data-checked="true"],
        [data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
            background: #e8e8e8;
            font-weight: 500;
        }

        /* ---------- Main content: ChatGPT-like centering ---------- */
        .main .block-container,
        section.main > div.block-container {
            max-width: 820px;
            padding-top: 2rem;
            padding-bottom: 6rem;
            margin: 0 auto;
        }

        /* ---------- Typography ---------- */
        h1 {
            font-size: 28px !important;
            font-weight: 600 !important;
            letter-spacing: -0.02em !important;
            color: #0d0d0d !important;
            margin-bottom: 1.2rem !important;
        }
        h2 {
            font-size: 22px !important;
            font-weight: 600 !important;
            letter-spacing: -0.01em !important;
        }
        h3 {
            font-size: 17px !important;
            font-weight: 600 !important;
        }
        p, li, label, .stMarkdown {
            font-size: 15px;
            line-height: 1.65;
            color: #0d0d0d;
        }

        /* ---------- Buttons ---------- */
        .stButton > button {
            background: #ffffff;
            color: #0d0d0d;
            border: 1px solid #d9d9e3;
            border-radius: 10px;
            padding: 8px 16px;
            font-weight: 500;
            font-size: 14px;
            transition: all 0.12s ease;
            box-shadow: none;
        }
        .stButton > button:hover {
            background: #f7f7f8;
            border-color: #b4b4bb;
            color: #0d0d0d;
        }
        .stButton > button[kind="primary"] {
            background: #0d0d0d;
            color: #ffffff;
            border: 1px solid #0d0d0d;
        }
        .stButton > button[kind="primary"]:hover {
            background: #2d2d2d;
            border-color: #2d2d2d;
        }
        .stDownloadButton > button {
            background: #ffffff;
            color: #0d0d0d;
            border: 1px solid #d9d9e3;
            border-radius: 10px;
            padding: 8px 16px;
            font-weight: 500;
            font-size: 14px;
        }
        .stDownloadButton > button:hover {
            background: #f7f7f8;
            border-color: #b4b4bb;
        }

        /* ---------- Inputs ---------- */
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stSelectbox > div > div {
            border-radius: 10px !important;
            border-color: #d9d9e3 !important;
            font-size: 14px !important;
            background: #ffffff !important;
        }
        .stTextInput input:focus,
        .stTextArea textarea:focus,
        .stNumberInput input:focus {
            border-color: #10a37f !important;
            box-shadow: 0 0 0 2px rgba(16, 163, 127, 0.15) !important;
        }
        .stTextArea textarea {
            padding: 12px 14px !important;
            line-height: 1.6 !important;
        }

        /* ---------- Form ---------- */
        [data-testid="stForm"] {
            border: 1px solid #ececec;
            border-radius: 14px;
            padding: 20px 22px;
            background: #fafafa;
        }

        /* ---------- Chat messages (ChatGPT style) ---------- */
        [data-testid="stChatMessage"] {
            background: transparent;
            padding: 20px 0;
            border-bottom: 1px solid #f0f0f0;
            border-radius: 0;
        }
        [data-testid="stChatMessage"]:last-child {
            border-bottom: none;
        }
        [data-testid="stChatMessage"] [data-testid="stChatMessageAvatarUser"],
        [data-testid="stChatMessage"] [data-testid="stChatMessageAvatarAssistant"] {
            background: #0d0d0d;
            color: white;
        }

        /* ---------- Chat input (bottom) ---------- */
        [data-testid="stChatInput"] {
            border-radius: 14px;
            border: 1px solid #d9d9e3;
            background: #ffffff;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }
        [data-testid="stChatInput"]:focus-within {
            border-color: #10a37f;
            box-shadow: 0 0 0 3px rgba(16, 163, 127, 0.12);
        }

        /* ---------- Expander ---------- */
        .streamlit-expanderHeader {
            font-size: 14px;
            font-weight: 500;
        }
        details {
            border: 1px solid #ececec;
            border-radius: 10px;
            padding: 4px 12px;
        }

        /* ---------- Code blocks ---------- */
        code {
            background: #f7f7f8 !important;
            color: #d6336c !important;
            padding: 2px 6px !important;
            border-radius: 4px !important;
            font-size: 13px !important;
        }
        pre {
            background: #0d0d0d !important;
            border-radius: 12px !important;
        }

        /* ---------- Slider ---------- */
        [data-testid="stSlider"] [role="slider"] {
            background: #10a37f !important;
        }

        /* ---------- Tabs ---------- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            border-bottom: 1px solid #ececec;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 14px;
            font-weight: 500;
            padding: 10px 16px;
            color: #6e6e80;
        }
        .stTabs [aria-selected="true"] {
            color: #0d0d0d !important;
        }

        /* ---------- Dividers ---------- */
        hr {
            border-color: #ececec;
            margin: 1.5rem 0;
        }

        /* ---------- Caption ---------- */
        .stCaption, [data-testid="stCaptionContainer"] {
            color: #6e6e80;
            font-size: 13px;
        }

        /* ---------- Toast ---------- */
        [data-testid="stToast"] {
            border-radius: 10px;
        }

        /* ---------- Hide the empty sidebar collapse button styling ---------- */
        [data-testid="collapsedControl"] {
            color: #0d0d0d;
        }

        /* ---------- Empty-state hero ---------- */
        .treats-hero {
            text-align: center;
            padding: 60px 20px 40px 20px;
        }
        .treats-hero .logo {
            width: 52px;
            height: 52px;
            background: #10a37f;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 700;
            font-size: 22px;
            margin-bottom: 18px;
        }
        .treats-hero h2 {
            font-size: 26px;
            font-weight: 600;
            color: #0d0d0d;
            margin: 0 0 8px 0;
            letter-spacing: -0.02em;
        }
        .treats-hero p {
            color: #6e6e80;
            font-size: 15px;
            margin: 0;
        }

        /* ---------- Starter cards ---------- */
        .starter-card .stButton > button {
            width: 100%;
            text-align: left;
            padding: 14px 16px;
            height: auto;
            font-size: 13.5px;
            line-height: 1.5;
            color: #0d0d0d;
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
    while trimmed and trimmed[0]["role"] != "user":
        trimmed.pop(0)
    return trimmed


# ============================================================
# POLLINATIONS — IMAGE GENERATION
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
            models = ["flux", "turbo", "flux-realism"]
        models = [str(m) for m in models if m]
        return models if models else ["flux", "turbo"]
    except Exception:
        return ["flux", "turbo", "flux-realism", "flux-anime", "flux-3d"]


def generate_image(prompt: str, width: int = 1024, height: int = 1024,
                   model: str = "flux", seed: int = None,
                   enhance: bool = True, nologo: bool = True) -> bytes:
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
# SIDEBAR NAVIGATION
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
        '<div class="treats-brand">'
        '<span class="dot">T</span>'
        '<span>Treats</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    choice_label = st.radio(
        "Navigation",
        list(TOOLS.keys()),
        label_visibility="collapsed",
        key="nav",
    )
    tool = TOOLS[choice_label]

    st.markdown("<div style='height: 40vh'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='padding: 0 14px; color: #6e6e80; font-size: 12px;'>"
        "Treats v2.0<br>Powered by Groq</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# TOOL: CHAT
# ============================================================
def render_chat():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Top controls (only when conversation exists)
    if st.session_state.messages:
        c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
        with c1:
            model = st.selectbox(
                "Model",
                AVAILABLE_MODELS,
                key="model",
                label_visibility="collapsed",
            )
        with c2:
            temp = st.slider(
                "Temperature",
                0.0, 1.5, 0.7, 0.1,
                key="temp",
                label_visibility="collapsed",
            )
        with c3:
            if st.button("New chat", key="new_conv", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        with c4:
            if st.button("Export", key="export_btn", use_container_width=True):
                st.session_state.show_export = not st.session_state.get("show_export", False)
        st.markdown("---")
    else:
        model = "openai/gpt-oss-120b"
        temp = 0.7

    # Empty state — hero
    if not st.session_state.messages:
        st.markdown(
            '<div class="treats-hero">'
            '<div class="logo">T</div>'
            '<h2>How can I help you today?</h2>'
            '<p>Ask anything. Treats is here to assist.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)

        starters = [
            "Explain vector databases in simple terms.",
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

    # Render messages
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

    # Export panel
    if st.session_state.get("show_export") and st.session_state.messages:
        with st.expander("Export conversation", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                md = "\n\n".join(
                    f"**{m['role'].capitalize()}:** {m['content']}"
                    for m in st.session_state.messages
                )
                st.download_button(
                    "Download Markdown",
                    data=md,
                    file_name=f"treats_chat_{datetime.now():%Y%m%d_%H%M}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with col2:
                st.download_button(
                    "Download JSON",
                    data=json.dumps(st.session_state.messages, ensure_ascii=False, indent=2),
                    file_name=f"treats_chat_{datetime.now():%Y%m%d_%H%M}.json",
                    mime="application/json",
                    use_container_width=True,
                )

    # Input
    prompt = st.chat_input("Message Treats...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    # Generate response
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        try:
            client = get_client()
            history = trim_history(st.session_state.messages)
            stream = client.chat.completions.create(
                model=model,
                messages=history,
                temperature=temp,
                stream=True,
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
    st.title("CV Builder")
    st.caption("Generate a professional CV in seconds.")

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

    st.title("Password Generator")
    st.caption("Create strong, secure passwords.")

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
    st.title("Video Script")
    st.caption("Generate scripts with scene-by-scene storyboards.")

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
    st.title("Text to Speech")
    st.caption("Convert text into natural-sounding speech.")

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
    st.title("Image Generator")
    st.caption("Create images from text descriptions. Free, no API key required.")

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
                mime="image/png",
                use_container_width=True,
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
