import json
from datetime import datetime

import streamlit as st
from groq import Groq

# ============================================================
# TREATS AI ASSISTANT
# ============================================================
# Version: 1.1.0
# Platform: Streamlit
# AI Provider: Groq
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
APP_VERSION = "1.1.0"

DEFAULT_MODEL = "openai/gpt-oss-20b"
AVAILABLE_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
]
DEFAULT_TEMPERATURE = 0.7
MAX_CONTEXT_TOKENS = 6000
REQUEST_TIMEOUT = 60  # seconds

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
        "pending": False,   # True when we need to generate a reply
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_session()


# ============================================================
# HELPERS
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
    st.divider()

    if st.button("＋ New conversation", use_container_width=True):
        clear_conversation()
        st.rerun()

    st.divider()
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
        help="Lower = focused and deterministic. Higher = creative.",
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

    # Export buttons — only shown when there is something to export
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

    st.divider()
    st.markdown("### About")
    st.markdown(
        f"""
        **{APP_NAME}**
        Version {APP_VERSION}
        A general-purpose AI assistant built with:
        - Python
        - Streamlit
        - Groq
        - GitHub
        """
    )


# ============================================================
# MAIN HEADER
# ============================================================
st.markdown(
    """
    <div class="treats-header">
        <div class="treats-logo">Treats</div>
        <div class="treats-subtitle">Your AI assistant</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# API STATUS
# ============================================================
if not has_api_key():
    st.warning(
        "Treats is running, but the Groq API key has not been "
        "configured in Streamlit Secrets."
    )

# ============================================================
# WELCOME SCREEN
# ============================================================
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

# ============================================================
# CHAT INPUT
# ============================================================
prompt = st.chat_input("Message Treats...")
if prompt:
    prompt = prompt.strip()
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.pending = True
        st.rerun()

# ============================================================
# DISPLAY CHAT HISTORY
# ============================================================
for i, message in enumerate(st.session_state.messages):
    role = message.get("role")
    content = message.get("content", "")
    if role not in ["user", "assistant"]:
        continue

    with st.chat_message(role):
        st.markdown(content)

        # Action buttons for assistant messages
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

# ============================================================
# GENERATE ASSISTANT REPLY (if pending)
# ============================================================
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
                    st.error("Treats returned an empty response. Please try again.")
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
