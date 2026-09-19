import streamlit as st
from groq import Groq
from datetime import datetime

# ============================================================
# TREATS AI ASSISTANT
# ============================================================
# Version: 1.0.1
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
APP_VERSION = "1.0.1"

DEFAULT_MODEL = "openai/gpt-oss-20b"
AVAILABLE_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
]
MAX_HISTORY_MESSAGES = 40

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
# CUSTOM CSS (theme is set in .streamlit/config.toml)
# ============================================================
st.markdown(
    """
    <style>
    /* Header */
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
    /* Sidebar */
    section[data-testid="stSidebar"] {
        border-right: 1px solid #eeeeee;
    }
    /* Buttons */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
    }
    /* Chat input */
    div[data-testid="stChatInput"] {
        border-radius: 14px;
    }
    /* Small status text */
    .status-text {
        color: #777777;
        font-size: 13px;
    }
    /* Welcome screen */
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
# API KEY / CLIENT
# ============================================================
def get_api_key():
    """Load the Groq API key from Streamlit Secrets."""
    try:
        key = st.secrets.get("GROQ_API_KEY", "")
        if key and key.strip():
            return key.strip()
    except Exception:
        pass
    return None


def get_client():
    """Create and return a Groq client, or None if not configured."""
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        return Groq(api_key=api_key)
    except Exception:
        return None


# ============================================================
# SESSION STATE
# ============================================================
def initialize_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "model" not in st.session_state:
        st.session_state.model = DEFAULT_MODEL


initialize_session()


# ============================================================
# HELPERS
# ============================================================
def clear_conversation():
    st.session_state.messages = []


def trim_history(messages):
    """Prevent the history from growing indefinitely.
    Future versions: replace with summarization / vector memory.
    """
    if len(messages) <= MAX_HISTORY_MESSAGES:
        return messages
    return messages[-MAX_HISTORY_MESSAGES:]


def build_messages():
    conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
    conversation.extend(trim_history(st.session_state.messages))
    return conversation


def generate_response(user_message: str) -> str:
    """Send the conversation to Groq and return the assistant reply."""
    client = get_client()
    if client is None:
        return (
            "Treats is not connected to the AI service yet.\n\n"
            "Please configure the `GROQ_API_KEY` secret in "
            "Streamlit before starting the conversation."
        )

    conversation = build_messages()

    try:
        completion = client.chat.completions.create(
            model=st.session_state.model,
            messages=conversation,
            temperature=0.7,
            max_completion_tokens=4096,
        )
        response = completion.choices[0].message.content
        if not response:
            return "I couldn't generate a response. Please try again."
        return response

    except Exception as error:
        error_message = str(error).lower()
        if "rate_limit" in error_message:
            return (
                "Treats has temporarily reached the API rate limit. "
                "Please wait a moment and try again."
            )
        if "authentication" in error_message or "api key" in error_message:
            return (
                "Treats could not authenticate with the AI service. "
                "Please check the Groq API key in Streamlit Secrets."
            )
        if "model" in error_message:
            return (
                "The selected AI model is currently unavailable. "
                "Please check the configured model."
            )
        return (
            "Treats encountered an unexpected error while generating "
            f"the response.\n\nTechnical details: {error}"
        )


def format_timestamp() -> str:
    return datetime.now().strftime("%H:%M")


def send_message(prompt: str) -> None:
    """Append user message, generate reply, append it."""
    st.session_state.messages.append({"role": "user", "content": prompt})
    reply = generate_response(prompt)
    st.session_state.messages.append({"role": "assistant", "content": reply})


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

    st.session_state.model = st.selectbox(
        "AI Model",
        options=AVAILABLE_MODELS,
        index=AVAILABLE_MODELS.index(st.session_state.model),
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

        Designed for future expansion.
        """
    )

    st.divider()
    if st.button("Clear conversation", use_container_width=True):
        clear_conversation()
        st.rerun()

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
if not get_api_key():
    st.warning(
        "Treats is running, but the Groq API key has not been "
        "configured in Streamlit Secrets."
    )

# ============================================================
# WELCOME SCREEN (only when there are no messages)
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
                send_message(starter["prompt"])
                st.rerun()

# ============================================================
# DISPLAY CHAT HISTORY
# ============================================================
for message in st.session_state.messages:
    role = message.get("role")
    content = message.get("content", "")
    if role not in ["user", "assistant"]:
        continue
    with st.chat_message(role):
        st.markdown(content)

# ============================================================
# CHAT INPUT
# ============================================================
prompt = st.chat_input("Message Treats...")
if prompt:
    prompt = prompt.strip()
    if prompt:
        send_message(prompt)
        st.rerun()

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
