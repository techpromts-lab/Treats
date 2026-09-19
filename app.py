import streamlit as st
from groq import Groq
from datetime import datetime


# ============================================================
# TREATS AI ASSISTANT
# ============================================================
# Version: 1.0.1
# Platform: Streamlit
# AI Provider: Groq
#
# This version includes improved chat readability and
# typography for assistant responses.
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


# ============================================================
# GLOBAL CSS
# ============================================================
#
# IMPORTANT:
# The typography rules below intentionally force Treats to use
# a clean system sans-serif font instead of an unclear,
# handwritten, decorative, or script-style font.
#
# This applies to:
# - Assistant responses
# - User messages
# - Markdown
# - Headings
# - Lists
# - Tables
# - Code
# - Sidebar
# - Buttons
# - Chat input
# ============================================================

st.markdown(
    """
    <style>

    /* ========================================================
       GLOBAL FONT
       ======================================================== */

    html,
    body,
    [class*="css"],
    .stApp,
    .stApp * {
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            Helvetica,
            Arial,
            sans-serif !important;
    }


    /* ========================================================
       APPLICATION BACKGROUND
       ======================================================== */

    .stApp {
        background-color: #ffffff;
    }


    /* ========================================================
       MAIN HEADER
       ======================================================== */

    .treats-header {
        padding: 12px 0 20px 0;
        border-bottom: 1px solid #eeeeee;
        margin-bottom: 20px;
    }

    .treats-logo {
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            Helvetica,
            Arial,
            sans-serif !important;

        font-size: 32px;
        font-weight: 800;
        letter-spacing: -1px;
        line-height: 1.2;
        margin: 0;
        color: #111111;
    }

    .treats-subtitle {
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            Helvetica,
            Arial,
            sans-serif !important;

        color: #777777;
        font-size: 14px;
        font-weight: 400;
        line-height: 1.5;
        margin-top: 4px;
    }


    /* ========================================================
       CHAT MESSAGE CONTAINERS
       ======================================================== */

    [data-testid="stChatMessage"] {
        border-radius: 14px;
    }


    /* ========================================================
       ALL CHAT TEXT
       ======================================================== */

    [data-testid="stChatMessage"] *,
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] div,
    [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] ul,
    [data-testid="stChatMessage"] ol,
    [data-testid="stChatMessage"] blockquote,
    [data-testid="stChatMessage"] table,
    [data-testid="stChatMessage"] td,
    [data-testid="stChatMessage"] th {
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            Helvetica,
            Arial,
            sans-serif !important;

        font-style: normal !important;
    }


    /* ========================================================
       ASSISTANT RESPONSE TEXT
       ======================================================== */

    [data-testid="stChatMessage"]:has(
        [data-testid="chatAvatarIcon-assistant"]
    ) p {
        font-size: 16px !important;
        font-weight: 400 !important;
        line-height: 1.75 !important;
        letter-spacing: 0 !important;
        color: #202124 !important;
        font-style: normal !important;
    }


    /* ========================================================
       USER MESSAGE TEXT
       ======================================================== */

    [data-testid="stChatMessage"]:has(
        [data-testid="chatAvatarIcon-user"]
    ) p {
        font-size: 16px !important;
        font-weight: 400 !important;
        line-height: 1.7 !important;
        letter-spacing: 0 !important;
        color: #202124 !important;
        font-style: normal !important;
    }


    /* ========================================================
       MARKDOWN TEXT
       ======================================================== */

    .stMarkdown,
    .stMarkdown p,
    .stMarkdown span,
    .stMarkdown li,
    .stMarkdown div {
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            Helvetica,
            Arial,
            sans-serif !important;

        font-style: normal !important;
    }


    /* ========================================================
       HEADINGS INSIDE CHAT
       ======================================================== */

    [data-testid="stChatMessage"] h1,
    [data-testid="stChatMessage"] h2,
    [data-testid="stChatMessage"] h3,
    [data-testid="stChatMessage"] h4,
    [data-testid="stChatMessage"] h5,
    [data-testid="stChatMessage"] h6 {
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            Helvetica,
            Arial,
            sans-serif !important;

        font-style: normal !important;
        color: #111111 !important;
        line-height: 1.35 !important;
        margin-top: 18px !important;
        margin-bottom: 10px !important;
    }


    /* ========================================================
       LISTS
       ======================================================== */

    [data-testid="stChatMessage"] ul,
    [data-testid="stChatMessage"] ol {
        padding-left: 28px !important;
        margin-top: 8px !important;
        margin-bottom: 12px !important;
    }

    [data-testid="stChatMessage"] li {
        margin-bottom: 6px !important;
        line-height: 1.7 !important;
    }


    /* ========================================================
       BOLD TEXT
       ======================================================== */

    [data-testid="stChatMessage"] strong,
    [data-testid="stChatMessage"] b {
        font-weight: 700 !important;
        font-style: normal !important;
        color: #111111 !important;
    }


    /* ========================================================
       ITALIC TEXT
       ======================================================== */

    [data-testid="stChatMessage"] em,
    [data-testid="stChatMessage"] i {
        font-style: italic !important;
    }


    /* ========================================================
       CODE BLOCKS
       ======================================================== */

    [data-testid="stChatMessage"] pre,
    [data-testid="stChatMessage"] code {
        font-family:
            "SFMono-Regular",
            Consolas,
            "Liberation Mono",
            Menlo,
            monospace !important;

        font-style: normal !important;
    }

    [data-testid="stChatMessage"] pre {
        border-radius: 10px !important;
        padding: 16px !important;
        line-height: 1.6 !important;
    }


    /* ========================================================
       INLINE CODE
       ======================================================== */

    [data-testid="stChatMessage"] code {
        font-size: 0.9em !important;
    }


    /* ========================================================
       QUOTES
       ======================================================== */

    [data-testid="stChatMessage"] blockquote {
        border-left: 3px solid #cccccc !important;
        padding-left: 16px !important;
        color: #555555 !important;
        font-style: normal !important;
    }


    /* ========================================================
       TABLES
       ======================================================== */

    [data-testid="stChatMessage"] table {
        width: 100% !important;
        border-collapse: collapse !important;
        font-size: 15px !important;
    }

    [data-testid="stChatMessage"] th,
    [data-testid="stChatMessage"] td {
        padding: 9px 10px !important;
        border-bottom: 1px solid #eeeeee !important;
        text-align: left !important;
        line-height: 1.5 !important;
    }


    /* ========================================================
       SIDEBAR
       ======================================================== */

    section[data-testid="stSidebar"] {
        border-right: 1px solid #eeeeee;
    }

    section[data-testid="stSidebar"] * {
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            Helvetica,
            Arial,
            sans-serif !important;

        font-style: normal !important;
    }


    /* ========================================================
       BUTTONS
       ======================================================== */

    .stButton > button {
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            Helvetica,
            Arial,
            sans-serif !important;

        border-radius: 10px;
        font-weight: 600;
        font-style: normal !important;
    }


    /* ========================================================
       CHAT INPUT
       ======================================================== */

    div[data-testid="stChatInput"] {
        border-radius: 14px;
    }

    div[data-testid="stChatInput"] *,
    div[data-testid="stChatInput"] textarea,
    div[data-testid="stChatInput"] input {
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            Helvetica,
            Arial,
            sans-serif !important;

        font-size: 16px !important;
        font-style: normal !important;
    }


    /* ========================================================
       WELCOME SCREEN
       ======================================================== */

    .welcome-box {
        padding: 50px 20px;
        text-align: center;
        border: 1px solid #eeeeee;
        border-radius: 18px;
        margin-top: 40px;
    }

    .welcome-title {
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            Helvetica,
            Arial,
            sans-serif !important;

        font-size: 34px;
        font-weight: 800;
        line-height: 1.25;
        color: #111111;
        margin-bottom: 8px;
        font-style: normal !important;
    }

    .welcome-description {
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            Helvetica,
            Arial,
            sans-serif !important;

        color: #777777;
        font-size: 16px;
        line-height: 1.6;
        font-style: normal !important;
    }


    /* ========================================================
       STATUS TEXT
       ======================================================== */

    .status-text {
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            Helvetica,
            Arial,
            sans-serif !important;

        color: #777777;
        font-size: 13px;
        line-height: 1.5;
        font-style: normal !important;
    }


    /* ========================================================
       FOOTER
       ======================================================== */

    .treats-footer {
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            Helvetica,
            Arial,
            sans-serif !important;

        text-align: center;
        color: #999999;
        font-size: 12px;
        line-height: 1.5;
        padding: 35px 0 10px 0;
        font-style: normal !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# API KEY
# ============================================================

def get_api_key():
    """
    Read the Groq API key from Streamlit Secrets.

    Streamlit Secrets should contain:

    GROQ_API_KEY = "your_new_key_here"

    The API key is intentionally NOT stored in this file.
    """

    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass

    return None


# ============================================================
# GROQ CLIENT
# ============================================================

def get_client():

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

    if "conversation_started" not in st.session_state:
        st.session_state.conversation_started = False

    if "message_count" not in st.session_state:
        st.session_state.message_count = 0


initialize_session()


# ============================================================
# CONVERSATION FUNCTIONS
# ============================================================

def clear_conversation():

    st.session_state.messages = []
    st.session_state.conversation_started = False
    st.session_state.message_count = 0


def trim_history(messages):

    if len(messages) <= MAX_HISTORY_MESSAGES:
        return messages

    return messages[-MAX_HISTORY_MESSAGES:]


def build_messages():

    conversation = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    conversation.extend(
        trim_history(st.session_state.messages)
    )

    return conversation


# ============================================================
# AI RESPONSE
# ============================================================

def generate_response(user_message):

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

            return (
                "I couldn't generate a response. "
                "Please try again."
            )

        return response

    except Exception as error:

        error_message = str(error)

        if "rate_limit" in error_message.lower():

            return (
                "Treats has temporarily reached the API "
                "rate limit. Please wait a moment and try again."
            )

        if "authentication" in error_message.lower():

            return (
                "Treats could not authenticate with the AI "
                "service. Please check the Groq API key in "
                "Streamlit Secrets."
            )

        if "model" in error_message.lower():

            return (
                "The selected AI model is currently unavailable. "
                "Please check the configured model."
            )

        return (
            "Treats encountered an unexpected error while "
            "generating the response.\n\n"
            f"Technical details: {error_message}"
        )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div style="padding-bottom:10px;">
            <div style="
                font-size:28px;
                font-weight:800;
                line-height:1.2;
                color:#111111;
            ">
                🤖 Treats
            </div>

            <div style="
                color:#777777;
                font-size:13px;
                line-height:1.5;
            ">
                AI Assistant
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    if st.button(
        "＋ New conversation",
        use_container_width=True,
    ):

        clear_conversation()
        st.rerun()

    st.divider()

    st.markdown("### Settings")

    st.session_state.model = st.selectbox(
        "AI Model",
        options=[
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
        ],
        index=(
            0
            if st.session_state.model == "openai/gpt-oss-20b"
            else 1
        ),
    )

    st.divider()

    st.markdown("### Conversation")

    if st.session_state.message_count == 0:

        st.markdown(
            '<div class="status-text">No messages yet.</div>',
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            f'<div class="status-text">'
            f'{st.session_state.message_count} messages'
            f'</div>',
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

    if st.button(
        "Clear conversation",
        use_container_width=True,
    ):

        clear_conversation()
        st.rerun()


# ============================================================
# MAIN HEADER
# ============================================================

st.markdown(
    """
    <div class="treats-header">

        <div class="treats-logo">
            Treats
        </div>

        <div class="treats-subtitle">
            Your AI assistant
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# API STATUS
# ============================================================

api_key = get_api_key()

if not api_key:

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

            <div class="welcome-title">
                How can I help you?
            </div>

            <div class="welcome-description">
                Ask Treats anything.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    col1, col2, col3 = st.columns(3)


    # --------------------------------------------------------
    # BRAINSTORM
    # --------------------------------------------------------

    with col1:

        if st.button(
            "💡 Brainstorm an idea",
            use_container_width=True,
        ):

            prompt = (
                "Help me brainstorm a new product idea. "
                "Give me several practical ideas and explain "
                "how each one could work."
            )

            st.session_state.messages.append(
                {
                    "role": "user",
                    "content": prompt,
                }
            )

            st.session_state.conversation_started = True
            st.session_state.message_count += 1

            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):

                with st.spinner("Thinking..."):

                    response = generate_response(prompt)

                st.markdown(response)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": response,
                }
            )

            st.session_state.message_count += 1

            st.rerun()


    # --------------------------------------------------------
    # CODING
    # --------------------------------------------------------

    with col2:

        if st.button(
            "💻 Help me code",
            use_container_width=True,
        ):

            prompt = (
                "Help me build a Python application. "
                "Ask me the important questions first and "
                "then propose a clean architecture."
            )

            st.session_state.messages.append(
                {
                    "role": "user",
                    "content": prompt,
                }
            )

            st.session_state.conversation_started = True
            st.session_state.message_count += 1

            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):

                with st.spinner("Thinking..."):

                    response = generate_response(prompt)

                st.markdown(response)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": response,
                }
            )

            st.session_state.message_count += 1

            st.rerun()


    # --------------------------------------------------------
    # LEARNING
    # --------------------------------------------------------

    with col3:

        if st.button(
            "📚 Explain something",
            use_container_width=True,
        ):

            prompt = (
                "Teach me an interesting subject in a simple "
                "but detailed way."
            )

            st.session_state.messages.append(
                {
                    "role": "user",
                    "content": prompt,
                }
            )

            st.session_state.conversation_started = True
            st.session_state.message_count += 1

            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):

                with st.spinner("Thinking..."):

                    response = generate_response(prompt)

                st.markdown(response)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": response,
                }
            )

            st.session_state.message_count += 1

            st.rerun()


# ============================================================
# DISPLAY CONVERSATION
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

prompt = st.chat_input(
    "Message Treats..."
)


if prompt:

    prompt = prompt.strip()

    if prompt:

        # ----------------------------------------------------
        # USER MESSAGE
        # ----------------------------------------------------

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        st.session_state.conversation_started = True
        st.session_state.message_count += 1

        with st.chat_message("user"):

            st.markdown(prompt)


        # ----------------------------------------------------
        # ASSISTANT RESPONSE
        # ----------------------------------------------------

        with st.chat_message("assistant"):

            with st.spinner("Treats is thinking..."):

                response = generate_response(prompt)

            st.markdown(response)


        # ----------------------------------------------------
        # SAVE ASSISTANT RESPONSE
        # ----------------------------------------------------

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response,
            }
        )

        st.session_state.message_count += 1

        st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="treats-footer">
        Treats may make mistakes. Check important information.
    </div>
    """,
    unsafe_allow_html=True,
)
