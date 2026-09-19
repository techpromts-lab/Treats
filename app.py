import json
import secrets as pysecrets
import string
from datetime import datetime

import streamlit as st
from groq import Groq

# ============================================================
# TREATS AI ASSISTANT
# ============================================================
# Version: 1.2.0
# Platform: Streamlit
# AI Provider: Groq
# Tools: Chat, CV Generator, Password Generator, Video Script
# ============================================================

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Treats AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# APPLICATION CONSTANTS
# ============================================================
APP_NAME = "Treats"
APP_VERSION = "1.2.0"

DEFAULT_MODEL = "openai/gpt-oss-20b"
AVAILABLE_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
]
DEFAULT_TEMPERATURE = 0.7
MAX_CONTEXT_TOKENS = 6000
REQUEST_TIMEOUT = 60  # seconds

# Free usage limits per tool (ignored for owner)
FREE_LIMITS = {
    "cv": 1,
    "password": 5,
    "video": 1,
}

TOOL_CHAT = "💬 Chat"
TOOL_CV = "📄 CV Generator"
TOOL_PASSWORD = "🔐 Password Generator"
TOOL_VIDEO = "🎬 Video Generator"
ALL_TOOLS = [TOOL_CHAT, TOOL_CV, TOOL_PASSWORD, TOOL_VIDEO]

SYSTEM_PROMPT = """
You are Treats, a helpful, intelligent, friendly, and reliable AI assistant.
Your goals are:
1. Understand what the user is asking.
2. Give clear and useful answers.
3. Be accurate and honest.
4. Do not invent facts when you are uncertain.
5. Explain complicated subjects simply when appropriate.
6. Help with writing, coding, brainstorming, learning, planning,
   analysis, and everyday questions.
7. Maintain context throughout the current conversation.
8. Follow the user's language.
9. If the user writes Arabic, respond naturally in Arabic.
10. If the user writes English, respond naturally in English.
11. Be concise when the question is simple.
12. Give more detailed explanations when the task requires them.
13. Never claim to have performed an action that you did not perform.
14. Clearly distinguish facts, assumptions, and suggestions.
15. Treat the user respectfully.

You are Treats.
You are designed as a general-purpose AI assistant and should be
structured so that future versions can add tools, memory, files,
web access, personalization, voice, and other capabilities.
"""

STARTER_PROMPTS = [
    {
        "label": "💡 Brainstorm an idea",
        "prompt": (
            "Help me brainstorm a new product idea. "
            "Give me several practical ideas and explain "
            "how each one could work."
        ),
    },
    {
        "label": "💻 Help me code",
        "prompt": (
            "Help me build a Python application. "
            "Ask me the important questions first and "
            "then propose a clean architecture."
        ),
    },
    {
        "label": "📚 Explain something",
        "prompt": (
            "Teach me an interesting subject in a simple "
            "but detailed way."
        ),
    },
]


# ============================================================
# CUSTOM EXCEPTION
# ============================================================
class TreatsError(Exception):
    """User-facing error raised when generation fails.
    These errors are NOT stored in the conversation history."""
    pass


# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown(
    """
    <style>
    .treats-header {
        padding: 12px 0 20px 0;
        border-bottom: 1px solid #eeeeee;
        margin-bottom: 20px;
    }
    .treats-logo {
        font-size: 32px;
        font-weight: 800;
        letter-spacing: -1px;
        margin: 0;
    }
    .treats-subtitle {
        color: #777777;
        font-size: 14px;
        margin-top: 3px;
    }
    section[data-testid="stSidebar"] {
        border-right: 1px solid #eeeeee;
    }
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
    }
    div[data-testid="stChatInput"] {
        border-radius: 14px;
    }
    .status-text {
        color: #777777;
        font-size: 13px;
    }
    .welcome-box {
        padding: 50px 20px;
        text-align: center;
        border: 1px solid #eeeeee;
        border-radius: 18px;
        margin-top: 40px;
    }
    .welcome-title {
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 8px;
    }
    .welcome-description {
        color: #777777;
        font-size: 16px;
    }
    .owner-badge {
        display: inline-block;
        padding: 4px 10px;
        background: #FFF3CD;
        color: #8A6D3B;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# GROQ CLIENT (cached across reruns)
# ============================================================
@st.cache_resource(show_spinner=False)
def get_client():
    """Return a cached Groq client, or None if no key is configured."""
    try:
        key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        return None
    if not key or not key.strip():
        return None
    try:
        return Groq(api_key=key.strip())
    except Exception:
        return None


def has_api_key() -> bool:
    """Check whether GROQ_API_KEY is configured."""
    try:
        key = st.secrets.get("GROQ_API_KEY", "")
        return bool(key and key.strip())
    except Exception:
        return False


# ============================================================
# SESSION STATE
# ============================================================
def initialize_session():
    defaults = {
        "messages": [],
        "model": DEFAULT_MODEL,
        "temperature": DEFAULT_TEMPERATURE,
        "pending": False,
        "selected_tool": TOOL_CHAT,
        "is_owner": False,
        "used_cv": 0,
        "used_password": 0,
        "used_video": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_session()


# ============================================================
# CHAT HELPERS
# ============================================================
def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token."""
    return max(1, len(text or "") // 4)


def trim_history(messages, max_tokens=MAX_CONTEXT_TOKENS):
    """Keep the most recent messages within a token budget,
    ensuring the result starts with a user message."""
    total = 0
    kept = []
    for msg in reversed(messages):
        tokens = estimate_tokens(msg.get("content", ""))
        if total + tokens > max_tokens:
            break
        kept.insert(0, msg)
        total += tokens
    while kept and kept[0].get("role") != "user":
        kept.pop(0)
    return kept


def build_messages():
    conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
    conversation.extend(trim_history(st.session_state.messages))
    return conversation


def format_error(error: Exception) -> str:
    text = str(error).lower()
    if "rate_limit" in text or "429" in text:
        return ("Treats has temporarily reached the API rate limit. "
                "Please wait a moment and try again.")
    if "authentication" in text or "api key" in text or "401" in text:
        return ("Treats could not authenticate with the AI service. "
                "Please check the Groq API key in Streamlit Secrets.")
    if "timeout" in text or "timed out" in text:
        return "The request took too long. Please try again."
    if "model" in text and ("not found" in text or "unavailable" in text):
        return ("The selected AI model is currently unavailable. "
                "Please choose a different model.")
    return f"Treats encountered an unexpected error: {error}"


def stream_assistant_reply():
    """Generator that yields text chunks from Groq.
    Raises TreatsError on failure."""
    client = get_client()
    if client is None:
        raise TreatsError(
            "Treats is not connected to the AI service yet. "
            "Please configure the GROQ_API_KEY secret in Streamlit."
        )

    conversation = build_messages()
    try:
        stream = client.chat.completions.create(
            model=st.session_state.model,
            messages=conversation,
            temperature=st.session_state.temperature,
            max_completion_tokens=4096,
            stream=True,
            timeout=REQUEST_TIMEOUT,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                yield content
    except Exception as error:
        raise TreatsError(format_error(error)) from error


def clear_conversation():
    st.session_state.messages = []
    st.session_state.pending = False


def regenerate_last():
    """Remove the last assistant message so it can be regenerated."""
    if (st.session_state.messages
            and st.session_state.messages[-1]["role"] == "assistant"):
        st.session_state.messages.pop()


def export_markdown() -> str:
    lines = [
        f"# {APP_NAME} — Conversation",
        f"_Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        f"_Model: {st.session_state.model}_",
        f"_Temperature: {st.session_state.temperature}_",
        "",
    ]
    for msg in st.session_state.messages:
        role = "You" if msg["role"] == "user" else APP_NAME
        lines.append(f"### {role}")
        lines.append(msg.get("content", ""))
        lines.append("")
    return "\n".join(lines)


def export_json() -> str:
    payload = {
        "app": APP_NAME,
        "version": APP_VERSION,
        "exported_at": datetime.now().isoformat(),
        "model": st.session_state.model,
        "temperature": st.session_state.temperature,
        "messages": st.session_state.messages,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ============================================================
# OWNER ACCESS + USAGE LIMITS
# ============================================================
def check_owner_password(password: str) -> bool:
    """Return True if password matches OWNER_PASSWORD in secrets."""
    try:
        correct = st.secrets.get("OWNER_PASSWORD", "")
        return bool(correct) and password == correct
    except Exception:
        return False


def is_owner() -> bool:
    return st.session_state.get("is_owner", False)


def remaining_uses(tool_key: str):
    """Return remaining free uses, or ∞ for owner."""
    if is_owner():
        return "∞"
    used = st.session_state.get(f"used_{tool_key}", 0)
    limit = FREE_LIMITS.get(tool_key, 0)
    return max(0, limit - used)


def consume_use(tool_key: str) -> bool:
    """Try to consume one use of a tool. Return True if allowed."""
    if is_owner():
        return True
    used = st.session_state.get(f"used_{tool_key}", 0)
    limit = FREE_LIMITS.get(tool_key, 0)
    if used >= limit:
        return False
    st.session_state[f"used_{tool_key}"] = used + 1
    return True


def show_limit_reached(tool_name: str) -> None:
    st.warning(
        f"⚠️ You've used all your free **{tool_name}** requests."
    )
    st.info(
        "💡 **To continue:**\n"
        "- Upgrade to premium (coming soon), or\n"
        "- Use the **🔑 Owner access** panel in the sidebar."
    )


# ============================================================
# TOOL 1: CV GENERATOR
# ============================================================
def render_cv_generator():
    st.markdown("## 📄 CV Generator")
    st.caption(
        f"Free uses left: **{remaining_uses('cv')}**"
        + ("  ·  👑 Owner mode (unlimited)" if is_owner() else "")
    )

    if remaining_uses("cv") == 0 and not is_owner():
        show_limit_reached("CV Generator")
        return

    with st.form("cv_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            full_name = st.text_input(
                "Full name *", placeholder="e.g. Mohammad Ahmad"
            )
        with col_b:
            target_role = st.text_input(
                "Target role", placeholder="e.g. Software Engineer"
            )

        experience = st.text_area(
            "Describe your experience *",
            height=200,
            placeholder=(
                "Write freely in any language. Example:\n"
                "I'm a software engineer with 5 years of experience "
                "in Python and AWS. I worked at Company X for 3 years "
                "where I led a team of 4. Before that, I worked at..."
            ),
        )

        col_c, col_d = st.columns(2)
        with col_c:
            cv_language = st.selectbox("CV language", ["English", "Arabic"])
        with col_d:
            tone = st.selectbox(
                "Tone", ["Professional", "Concise", "Academic"]
            )

        submitted = st.form_submit_button(
            "✨ Generate CV", use_container_width=True
        )

    if not submitted:
        return

    if not full_name.strip() or not experience.strip():
        st.error("Please fill in your name and experience.")
        return

    client = get_client()
    if client is None:
        st.error("AI service not configured.")
        return

    if not consume_use("cv"):
        show_limit_reached("CV Generator")
        return

    cv_prompt = f"""
    Create a professional CV in {cv_language} based on the information below.
    Tone: {tone}.

    Full name: {full_name}
    Target role: {target_role or "(not specified)"}
    Experience (raw input): {experience}

    Output in clean Markdown with these sections:
    # Full Name
    ## Professional Summary  (2-4 sentences)
    ## Work Experience  (company, role, dates, 3-5 bullet achievements)
    ## Education
    ## Skills  (as a comma-separated list)
    ## Languages

    Rules:
    - Do NOT invent facts. If a section has no info, either omit it or keep it minimal.
    - Convert vague descriptions into concrete bullet points.
    - Use strong action verbs.
    - Keep it ATS-friendly (no tables, no images).
    """

    with st.spinner("Generating your CV..."):
        try:
            response = client.chat.completions.create(
                model=st.session_state.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": cv_prompt},
                ],
                temperature=0.5,
                max_completion_tokens=2048,
                timeout=REQUEST_TIMEOUT,
            )
            cv_text = response.choices[0].message.content
        except Exception as error:
            st.error(format_error(error))
            return

    st.divider()
    st.markdown(cv_text)
    st.divider()

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    st.download_button(
        "⬇ Download CV (Markdown)",
        data=cv_text,
        file_name=f"cv_{stamp}.md",
        mime="text/markdown",
        use_container_width=True,
    )


# ============================================================
# TOOL 2: PASSWORD GENERATOR
# ============================================================
def render_password_generator():
    st.markdown("## 🔐 Password Generator")
    st.caption(
        f"Free uses left: **{remaining_uses('password')}**"
        + ("  ·  👑 Owner mode (unlimited)" if is_owner() else "")
    )

    if remaining_uses("password") == 0 and not is_owner():
        show_limit_reached("Password Generator")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        length = st.slider("Length", 8, 64, 16)
    with col2:
        use_symbols = st.checkbox("Include symbols", value=True)
    with col3:
        use_numbers = st.checkbox("Include numbers", value=True)

    if st.button("🎲 Generate password", use_container_width=True):
        if not consume_use("password"):
            show_limit_reached("Password Generator")
            return

        alphabet = string.ascii_letters
        if use_numbers:
            alphabet += string.digits
        if use_symbols:
            alphabet += "!@#$%^&*()-_=+[]{};:,.?/"

        password = "".join(
            pysecrets.choice(alphabet) for _ in range(length)
        )

        st.success("Password generated!")
        st.code(password, language=None)
        st.caption("💡 Use the copy icon in the top-right of the box.")

    st.divider()
    st.markdown("### 💪 Strength tips")
    st.markdown(
        "- Use **16+ characters** for important accounts.\n"
        "- Never reuse passwords across sites.\n"
        "- Store them in a password manager (Bitwarden, 1Password).\n"
        "- Enable **2FA** wherever possible."
    )


# ============================================================
# TOOL 3: VIDEO SCRIPT GENERATOR
# ============================================================
def render_video_generator():
    st.markdown("## 🎬 Video Script Generator")
    st.caption(
        f"Free uses left: **{remaining_uses('video')}**"
        + ("  ·  👑 Owner mode (unlimited)" if is_owner() else "")
    )

    st.info(
        "ℹ️ This tool generates a **complete video script + storyboard**. "
        "Rendering the actual video requires an external service "
        "(Runway, Replicate, etc.) — planned for a future version."
    )

    if remaining_uses("video") == 0 and not is_owner():
        show_limit_reached("Video Script Generator")
        return

    with st.form("video_form"):
        topic = st.text_input(
            "Video topic *",
            placeholder="e.g. How to start a startup in Jordan",
        )

        col_a, col_b = st.columns(2)
        with col_a:
            duration = st.selectbox(
                "Target duration",
                ["30 seconds", "60 seconds", "2-3 minutes", "5 minutes"],
            )
        with col_b:
            style = st.selectbox(
                "Style",
                ["Educational", "Marketing / Ad", "Storytelling", "Tutorial"],
            )

        col_c, col_d = st.columns(2)
        with col_c:
            language = st.selectbox("Language", ["English", "Arabic"])
        with col_d:
            platform = st.selectbox(
                "Platform", ["YouTube", "TikTok / Reels", "LinkedIn", "General"]
            )

        submitted = st.form_submit_button(
            "🎬 Generate script", use_container_width=True
        )

    if not submitted:
        return

    if not topic.strip():
        st.error("Please enter a topic.")
        return

    client = get_client()
    if client is None:
        st.error("AI service not configured.")
        return

    if not consume_use("video"):
        show_limit_reached("Video Script Generator")
        return

    video_prompt = f"""
    Create a complete video script in {language} for a {duration} {style} video
    about: "{topic}". Target platform: {platform}.

    Structure:

    ## 🎯 Hook (first 3 seconds)
    A strong opening line that grabs attention.

    ## 📝 Script
    Timestamped speaker lines. Format:
    [0:00-0:05] Speaker: "..."
    [0:05-0:15] Speaker: "..."

    ## 🎥 Visual notes (storyboard)
    For each timestamp, describe what should be on screen.

    ## 🎵 Music / tone
    Suggest background music style and overall vibe.

    ## 📢 Call to action
    A clear CTA appropriate for {platform}.

    Be concrete and production-ready. No filler.
    """

    with st.spinner("Writing your video script..."):
        try:
            response = client.chat.completions.create(
                model=st.session_state.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": video_prompt},
                ],
                temperature=0.8,
                max_completion_tokens=2048,
                timeout=REQUEST_TIMEOUT,
            )
            script = response.choices[0].message.content
        except Exception as error:
            st.error(format_error(error))
            return

    st.divider()
    st.markdown(script)
    st.divider()

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    st.download_button(
        "⬇ Download script (Markdown)",
        data=script,
        file_name=f"video_script_{stamp}.md",
        mime="text/markdown",
        use_container_width=True,
    )


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown(
        """
        <div style="padding-bottom:10px;">
            <div style="font-size:28px;font-weight:800;">🤖 Treats</div>
            <div style="color:#777;font-size:13px;">AI Assistant</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if is_owner():
        st.markdown(
            '<span class="owner-badge">👑 Owner mode active</span>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ---------- OWNER ACCESS ----------
    with st.expander("🔑 Owner access", expanded=False):
        if is_owner():
            st.success("Owner mode active ✅")
            if st.button("Log out", use_container_width=True):
                st.session_state.is_owner = False
                st.rerun()
        else:
            pw_input = st.text_input(
                "Password",
                type="password",
                key="owner_pw_field",
                label_visibility="collapsed",
                placeholder="Owner password...",
            )
            if st.button("Unlock", use_container_width=True):
                if check_owner_password(pw_input):
                    st.session_state.is_owner = True
                    st.rerun()
                else:
                    st.error("Wrong password")

    st.divider()

    # ---------- TOOL SELECTOR ----------
    st.markdown("### 🛠️ Tools")
    st.radio(
        "Choose tool",
        options=ALL_TOOLS,
        key="selected_tool",
        label_visibility="collapsed",
    )

    st.divider()

    # ---------- CHAT-ONLY SETTINGS ----------
    if st.session_state.selected_tool == TOOL_CHAT:
        st.markdown("### Settings")

        st.selectbox(
            "AI Model",
            options=AVAILABLE_MODELS,
            key="model",
        )

        st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.5,
            step=0.05,
            key="temperature",
            help="Lower = focused. Higher = creative.",
        )

        st.divider()
        st.markdown("### Conversation")

        message_count = len(st.session_state.messages)
        if message_count == 0:
            st.markdown(
                '<div class="status-text">No messages yet.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="status-text">{message_count} messages</div>',
                unsafe_allow_html=True,
            )

        if st.session_state.messages:
            stamp = datetime.now().strftime("%Y%m%d_%H%M")
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "⬇ MD",
                    data=export_markdown(),
                    file_name=f"treats_{stamp}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with c2:
                st.download_button(
                    "⬇ JSON",
                    data=export_json(),
                    file_name=f"treats_{stamp}.json",
                    mime="application/json",
                    use_container_width=True,
                )

    # ---------- CHAT-ONLY: NEW CONVERSATION ----------
    if st.session_state.selected_tool == TOOL_CHAT:
        st.divider()
        if st.button("＋ New conversation", use_container_width=True):
            clear_conversation()
            st.rerun()

    st.divider()
    st.markdown("### About")
    st.markdown(
        f"""
        **{APP_NAME}**
        Version {APP_VERSION}
        Built with Python · Streamlit · Groq
        """
    )


# ============================================================
# MAIN HEADER
# ============================================================
st.markdown(
    f"""
    <div class="treats-header">
        <div class="treats-logo">Treats</div>
        <div class="treats-subtitle">{st.session_state.selected_tool}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# API STATUS (only for tools that need AI)
# ============================================================
if not has_api_key() and st.session_state.selected_tool != TOOL_PASSWORD:
    st.warning(
        "Treats is running, but the Groq API key has not been "
        "configured in Streamlit Secrets."
    )


# ============================================================
# TOOL ROUTING
# ============================================================
current_tool = st.session_state.selected_tool

if current_tool == TOOL_CV:
    render_cv_generator()
    st.stop()

if current_tool == TOOL_PASSWORD:
    render_password_generator()
    st.stop()

if current_tool == TOOL_VIDEO:
    render_video_generator()
    st.stop()

# ============================================================
# BELOW: CHAT MODE ONLY
# ============================================================

# ---------- WELCOME SCREEN ----------
if not st.session_state.messages:
    st.markdown(
        """
        <div class="welcome-box">
            <div class="welcome-title">How can I help you?</div>
            <div class="welcome-description">Ask Treats anything.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    cols = st.columns(len(STARTER_PROMPTS))
    for col, starter in zip(cols, STARTER_PROMPTS):
        with col:
            if st.button(starter["label"], use_container_width=True):
                st.session_state.messages.append(
                    {"role": "user", "content": starter["prompt"]}
                )
                st.session_state.pending = True
                st.rerun()

# ---------- CHAT INPUT ----------
prompt = st.chat_input("Message Treats...")
if prompt:
    prompt = prompt.strip()
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.pending = True
        st.rerun()

# ---------- DISPLAY CHAT HISTORY ----------
for i, message in enumerate(st.session_state.messages):
    role = message.get("role")
    content = message.get("content", "")
    if role not in ["user", "assistant"]:
        continue

    with st.chat_message(role):
        st.markdown(content)

        if role == "assistant":
            is_last = (i == len(st.session_state.messages) - 1)
            actions = st.columns([1, 1, 6])

            with actions[0]:
                with st.popover("📋", help="Copy message"):
                    st.code(content, language=None)

            if is_last:
                with actions[1]:
                    if st.button("🔄", key=f"regen_{i}",
                                 help="Regenerate response"):
                        regenerate_last()
                        st.session_state.pending = True
                        st.rerun()

# ---------- GENERATE ASSISTANT REPLY (if pending) ----------
if st.session_state.pending:
    if (not st.session_state.messages
            or st.session_state.messages[-1]["role"] != "user"):
        st.session_state.pending = False
    else:
        with st.chat_message("assistant"):
            try:
                response = st.write_stream(stream_assistant_reply())
                if response:
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )
                    st.session_state.pending = False
                    st.rerun()
                else:
                    st.error(
                        "Treats returned an empty response. Please try again."
                    )
                    st.session_state.pending = False
            except TreatsError as error:
                st.error(str(error))
                st.session_state.pending = False


# ============================================================
# FOOTER
# ============================================================
st.markdown(
    """
    <div style="text-align:center;color:#999;font-size:12px;padding:35px 0 10px 0;">
        Treats may make mistakes. Check important information.
    </div>
    """,
    unsafe_allow_html=True,
)
