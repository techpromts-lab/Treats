import asyncio
import base64
import json
import os
import secrets as pysecrets
import string
import subprocess
import tempfile
import time
from datetime import datetime
from io import BytesIO
from urllib.parse import quote

import edge_tts
import requests
import streamlit as st
from groq import Groq
from PIL import Image

# ============================================================
# TREATS AI ASSISTANT
# ============================================================
# Version: 2.0.0
# Tools: Chat, CV, Password, Video Script, TTS,
#        Photo Generator, Video Maker (ffmpeg), AI Video (Veo)
# ============================================================

APP_NAME = "Treats"
APP_VERSION = "2.0.0"

DEFAULT_MODEL = "llama-3.3-70b-versatile"
AVAILABLE_MODELS = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
]
DEFAULT_TEMPERATURE = 0.7
MAX_CONTEXT_TOKENS = 6000
REQUEST_TIMEOUT = 60

TOOL_CHAT = "💬 Chat"
TOOL_CV = "📄 CV Generator"
TOOL_PASSWORD = "🔐 Password Generator"
TOOL_VIDEO_SCRIPT = "🎬 Video Script Generator"
TOOL_TTS = "🔊 Text to Speech"
TOOL_PHOTO_GEN = "🎨 Photo Generator"
TOOL_VIDEO_MAKER = "🎥 Video Maker (Real MP4)"
TOOL_VIDEO_AI = "🎞️ AI Video Generator (Veo)"
ALL_TOOLS = [
    TOOL_CHAT, TOOL_CV, TOOL_PASSWORD,
    TOOL_VIDEO_SCRIPT, TOOL_TTS, TOOL_PHOTO_GEN,
    TOOL_VIDEO_MAKER, TOOL_VIDEO_AI,
]

SYSTEM_PROMPT = """You are Treats, a helpful, intelligent AI assistant.
Follow the user's language: Arabic if they write Arabic, English if English.
Be accurate, honest, and concise. Do not invent facts.
"""

VOICE_CATALOG = {
    "English": [
        {"id": "en-US-GuyNeural", "name": "Guy", "gender": "Male",
         "desc": "Deep, confident American"},
        {"id": "en-US-DavisNeural", "name": "Davis", "gender": "Male",
         "desc": "Calm, professional"},
        {"id": "en-US-JennyNeural", "name": "Jenny", "gender": "Female",
         "desc": "Warm, friendly"},
        {"id": "en-US-AriaNeural", "name": "Aria", "gender": "Female",
         "desc": "Professional, clear"},
    ],
    "Arabic": [
        {"id": "ar-EG-ShakirNeural", "name": "Shakir", "gender": "Male",
         "desc": "صوت مصري رجولي قوي"},
        {"id": "ar-SA-HamedNeural", "name": "Faisal", "gender": "Male",
         "desc": "صوت سعودي هادئ ورسمي"},
        {"id": "ar-EG-SalmaNeural", "name": "Salma", "gender": "Female",
         "desc": "صوت مصري دافئ"},
    ],
}

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Treats AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CLIENTS & KEYS
# ============================================================
@st.cache_resource(show_spinner=False)
def get_client():
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

def has_groq_key() -> bool:
    try:
        key = st.secrets.get("GROQ_API_KEY", "")
        return bool(key and key.strip())
    except Exception:
        return False

def get_google_key() -> str:
    try:
        return (st.secrets.get("GOOGLE_API_KEY", "") or "").strip()
    except Exception:
        return ""

def has_google_key() -> bool:
    return bool(get_google_key())

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
        "tts_audio": None,
        "tts_voice_name": "",
        "video_bytes": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

initialize_session()

# ============================================================
# HELPERS
# ============================================================
def estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // 4)

def trim_history(messages, max_tokens=MAX_CONTEXT_TOKENS):
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
        return "تم الوصول إلى حد الاستخدام. حاول بعد قليل."
    if "authentication" in text or "api key" in text:
        return "مفتاح API غير صالح. تحقق من الإعدادات."
    return f"حدث خطأ: {error}"

def stream_assistant_reply():
    client = get_client()
    if client is None:
        raise Exception("AI service not configured.")
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
        raise Exception(format_error(error)) from error

# ============================================================
# TTS (edge-tts — مجاني)
# ============================================================
def synthesize_speech(text: str, voice_id: str, rate_percent: int = 0) -> bytes:
    rate_str = f"{rate_percent:+d}%"

    async def _run() -> bytes:
        communicate = edge_tts.Communicate(text, voice_id, rate=rate_str)
        audio = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        return audio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()

# ============================================================
# PHOTO GENERATOR (Pollinations — مجاني بلا حدود)
# ============================================================
def generate_image_pollinations(prompt: str, width: int = 1024,
                                height: int = 1024) -> bytes:
    encoded = quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={width}&height={height}&nologo=true&model=flux"
    )
    resp = requests.get(url, timeout=90)
    resp.raise_for_status()
    return resp.content

# ============================================================
# VIDEO MAKER (Slideshow + Voice + ffmpeg — مجاني)
# ============================================================
def generate_video_script(topic: str, language: str, duration: str) -> list:
    client = get_client()
    if client is None:
        raise Exception("AI service not configured.")
    scene_count = 5
    prompt = f"""
    Create a short video about: "{topic}" in {language}.
    Target duration: {duration}.
    Produce exactly {scene_count} scenes. For each scene, provide:
    - An IMAGE prompt in ENGLISH (for an AI image generator) —
      vivid, cinematic, specific.
    - A NARRATION line in {language} (1-2 sentences, natural spoken tone).
    Return ONLY valid JSON. Format:
    {{"scenes": [{{"image": "...", "narration": "..."}}, ...]}}
    """
    response = client.chat.completions.create(
        model=st.session_state.model,
        messages=[
            {"role": "system", "content": "You output strict JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_completion_tokens=1500,
        response_format={"type": "json_object"},
        timeout=REQUEST_TIMEOUT,
    )
    data = json.loads(response.choices[0].message.content)
    return data.get("scenes", [])

def build_video_ffmpeg(scenes, voice_id, output_path):
    with tempfile.TemporaryDirectory() as tmp:
        image_paths, audio_paths, durations = [], [], []

        for i, scene in enumerate(scenes):
            img_bytes = generate_image_pollinations(scene["image"])
            img_path = os.path.join(tmp, f"img_{i}.jpg")
            with open(img_path, "wb") as f:
                f.write(img_bytes)
            image_paths.append(img_path)

            audio_bytes = synthesize_speech(scene["narration"], voice_id)
            audio_path = os.path.join(tmp, f"audio_{i}.mp3")
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)
            audio_paths.append(audio_path)

            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration", "-of",
                 "default=noprint_wrappers=1:nokey=1", audio_path],
                capture_output=True, text=True,
            )
            try:
                dur = float(result.stdout.strip()) + 0.4
            except ValueError:
                dur = 3.0
            durations.append(dur)

        concat_file = os.path.join(tmp, "concat.txt")
        with open(concat_file, "w") as f:
            for img, dur in zip(image_paths, durations):
                f.write(f"file '{img}'\nduration {dur}\n")
            f.write(f"file '{image_paths[-1]}'\n")

        audio_concat = os.path.join(tmp, "audio_concat.txt")
        with open(audio_concat, "w") as f:
            for ap in audio_paths:
                f.write(f"file '{ap}'\n")

        merged_audio = os.path.join(tmp, "merged.mp3")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", audio_concat, "-c", "copy", merged_audio],
            capture_output=True, check=True,
        )

        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", concat_file, "-i", merged_audio,
             "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,"
                    "pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
             "-c:v", "libx264", "-preset", "fast", "-crf", "23",
             "-c:a", "aac", "-b:a", "128k",
             "-shortest", "-movflags", "+faststart", output_path],
            capture_output=True, check=True,
        )
    return output_path

# ============================================================
# AI VIDEO (Google Veo via Gemini API)
# ============================================================
def veo_generate_video(prompt: str, aspect_ratio: str = "16:9") -> bytes:
    """
    Generate a real video using Google Veo 3.1 via Gemini API.
    Returns MP4 bytes.
    """
    api_key = get_google_key()
    if not api_key:
        raise Exception("GOOGLE_API_KEY not configured in secrets.")

    base = "https://generativelanguage.googleapis.com/v1beta"
    model = "veo-3.1-generate-preview"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }

    # --- 1. Start generation ---
    start_url = f"{base}/models/{model}:predictLongRunning"
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {"aspectRatio": aspect_ratio},
    }
    resp = requests.post(start_url, json=payload, headers=headers, timeout=60)
    if resp.status_code != 200:
        raise Exception(
            f"Veo start failed [{resp.status_code}]: {resp.text[:300]}"
        )

    operation_name = resp.json().get("name")
    if not operation_name:
        raise Exception(f"No operation name returned: {resp.text[:300]}")

    # --- 2. Poll until done ---
    poll_url = f"{base}/{operation_name}"
    max_wait = 300
    waited = 0
    interval = 5
    result = None

    while waited < max_wait:
        time.sleep(interval)
        waited += interval
        poll = requests.get(poll_url, headers=headers, timeout=60)
        if poll.status_code != 200:
            continue
        data = poll.json()
        if data.get("done"):
            result = data
            break

    if result is None:
        raise Exception("Veo generation timed out (>5 min).")

    # --- 3. Extract video ---
    response = result.get("response", {})
    gen = response.get("generateVideoResponse", {})
    samples = gen.get("generatedSamples", [])
    if not samples:
        samples = response.get("generatedSamples", [])
    if not samples:
        raise Exception(f"No video in response: {str(result)[:300]}")

    sample = samples[0]
    video_obj = sample.get("video", sample)

    if "bytesBase64Encoded" in video_obj:
        return base64.b64decode(video_obj["bytesBase64Encoded"])

    uri = video_obj.get("uri") or video_obj.get("fileUri")
    if uri:
        dl = requests.get(uri, headers={"x-goog-api-key": api_key},
                          timeout=120)
        if dl.status_code == 200:
            return dl.content
        raise Exception(f"Failed to download video from URI: {uri}")

    raise Exception(
        f"Cannot extract video. Keys: {list(video_obj.keys())}"
    )

# ============================================================
# TOOL RENDERERS
# ============================================================
def render_chat():
    if not st.session_state.messages:
        st.markdown("### How can I help you?")
        st.write("")
        cols = st.columns(3)
        starters = ["💡 Brainstorm", "💻 Code", "📚 Explain"]
        for col, label in zip(cols, starters):
            with col:
                if st.button(label, use_container_width=True,
                             key=f"st_{label}"):
                    st.session_state.messages.append(
                        {"role": "user", "content": label}
                    )
                    st.session_state.pending = True
                    st.rerun()

    prompt = st.chat_input("Message Treats...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.pending = True
        st.rerun()

    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if st.session_state.pending:
        if (st.session_state.messages
                and st.session_state.messages[-1]["role"] == "user"):
            with st.chat_message("assistant"):
                try:
                    response = st.write_stream(stream_assistant_reply())
                    if response:
                        st.session_state.messages.append(
                            {"role": "assistant", "content": response}
                        )
                        st.session_state.pending = False
                        st.rerun()
                except Exception as e:
                    st.error(str(e))
                    st.session_state.pending = False

def render_cv_generator():
    st.markdown("## 📄 CV Generator")
    st.caption("Generate a professional CV — download as Markdown or Text.")
    with st.form("cv_form"):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full name *")
        with col2:
            target_role = st.text_input("Target role")
        experience = st.text_area("Describe your experience *", height=180)
        col3, col4 = st.columns(2)
        with col3:
            cv_language = st.selectbox("CV language", ["English", "Arabic"])
        with col4:
            tone = st.selectbox("Tone", ["Professional", "Concise"])
        submitted = st.form_submit_button("✨ Generate CV",
                                          use_container_width=True)

    if not submitted:
        return
    if not full_name.strip() or not experience.strip():
        st.error("Please fill in name and experience.")
        return

    client = get_client()
    if client is None:
        st.error("AI service not configured.")
        return

    cv_prompt = f"""
    Create a professional CV in {cv_language}.
    Tone: {tone}.
    Name: {full_name}
    Role: {target_role}
    Experience: {experience}
    Output in clean Markdown.
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
        except Exception as e:
            st.error(format_error(e))
            return

    st.divider()
    st.markdown(cv_text)
    st.divider()
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("⬇ Download MD", data=cv_text,
                           file_name=f"cv_{stamp}.md", mime="text/markdown",
                           use_container_width=True, key="cv_md")
    with col2:
        st.download_button("⬇ Download TXT", data=cv_text,
                           file_name=f"cv_{stamp}.txt", mime="text/plain",
                           use_container_width=True, key="cv_txt")

def render_password_generator():
    st.markdown("## 🔐 Password Generator")
    col1, col2, col3 = st.columns(3)
    with col1:
        length = st.slider("Length", 8, 64, 16)
    with col2:
        use_symbols = st.checkbox("Symbols", value=True)
    with col3:
        use_numbers = st.checkbox("Numbers", value=True)
    if st.button("🎲 Generate", use_container_width=True, key="pw_gen"):
        alphabet = string.ascii_letters
        if use_numbers:
            alphabet += string.digits
        if use_symbols:
            alphabet += "!@#$%^&*()-_=+[]{};:,.?/"
        password = "".join(pysecrets.choice(alphabet) for _ in range(length))
        st.success("Password generated!")
        st.code(password)

def render_video_script():
    st.markdown("## 🎬 Video Script Generator")
    st.caption("Generate a complete video script + storyboard.")
    st.info("ℹ️ This tool generates a script only. To create the actual "
            "video, use **🎥 Video Maker** or **🎞️ AI Video Generator**.")
    with st.form("video_script_form"):
        topic = st.text_input("Video topic *")
        col1, col2 = st.columns(2)
        with col1:
            duration = st.selectbox("Duration", ["30 seconds", "60 seconds"])
        with col2:
            style = st.selectbox("Style", ["Educational", "Marketing"])
        language = st.selectbox("Language", ["English", "Arabic"])
        submitted = st.form_submit_button("🎬 Generate",
                                          use_container_width=True)
    if not submitted or not topic.strip():
        return
    client = get_client()
    if client is None:
        st.error("AI not configured.")
        return
    prompt = (f"Create a video script in {language} for a {duration} "
              f"{style} video about: '{topic}'. Include Hook, Script, "
              f"Visual notes, Music, CTA.")
    with st.spinner("Writing..."):
        try:
            resp = client.chat.completions.create(
                model=st.session_state.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8, max_completion_tokens=2048,
            )
            script = resp.choices[0].message.content
        except Exception as e:
            st.error(format_error(e))
            return
    st.divider()
    st.markdown(script)
    st.divider()
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    st.download_button("⬇ Download MD", data=script,
                       file_name=f"script_{stamp}.md", mime="text/markdown",
                       use_container_width=True, key="vscr_dl")

def render_tts():
    st.markdown("## 🔊 Text to Speech")
    language = st.selectbox("Language", list(VOICE_CATALOG.keys()),
                            key="tts_lang")
    voices = VOICE_CATALOG[language]
    voice_labels = [f"{v['name']} ({v['gender']}) · {v['desc']}"
                    for v in voices]
    idx = st.selectbox("Voice", range(len(voices)),
                       format_func=lambda i: voice_labels[i],
                       key="tts_voice")
    voice = voices[idx]
    speed = st.slider("Speed", 0.5, 2.0, 1.0, 0.05, key="tts_speed")
    text = st.text_area("Text *", height=150, key="tts_text")

    if st.button("🔊 Generate", use_container_width=True, key="tts_gen"):
        if not text.strip():
            st.error("Enter text.")
            return
        rate = int(round((speed - 1.0) * 100))
        with st.spinner("Generating audio..."):
            try:
                audio = synthesize_speech(text.strip(), voice["id"], rate)
                st.session_state.tts_audio = audio
                st.session_state.tts_voice_name = voice["name"]
            except Exception as e:
                st.error(f"Failed: {e}")
                return

    if st.session_state.get("tts_audio"):
        st.divider()
        st.markdown(f"### 🎧 {st.session_state.tts_voice_name}")
        st.audio(st.session_state.tts_audio, format="audio/mp3")
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        st.download_button("⬇ Download MP3",
                           data=st.session_state.tts_audio,
                           file_name=f"speech_{stamp}.mp3",
                           mime="audio/mp3",
                           use_container_width=True, key="tts_dl")
        if st.button("Clear", use_container_width=True, key="tts_clr"):
            st.session_state.tts_audio = None
            st.rerun()

def render_photo_generator():
    st.markdown("## 🎨 Photo Generator")
    st.caption("Generate images from text. Free, unlimited, no API key.")

    prompt = st.text_input(
        "Describe the image *",
        placeholder="e.g. A futuristic city with neon lights, cyberpunk style",
        key="img_prompt",
    )
    col1, col2 = st.columns(2)
    with col1:
        width = st.slider("Width", 512, 1920, 1024, 64, key="img_w")
    with col2:
        height = st.slider("Height", 512, 1920, 1024, 64, key="img_h")

    if st.button("🎨 Generate Image", use_container_width=True,
                 key="img_gen"):
        if not prompt.strip():
            st.error("Enter a description.")
            return
        with st.spinner("Generating image..."):
            try:
                img_bytes = generate_image_pollinations(
                    prompt.strip(), width, height
                )
                image = Image.open(BytesIO(img_bytes))
                st.image(image, caption="Generated Image",
                         use_column_width=True)
                stamp = datetime.now().strftime("%Y%m%d_%H%M")
                st.download_button(
                    "⬇ Download JPG",
                    data=img_bytes,
                    file_name=f"image_{stamp}.jpg",
                    mime="image/jpeg",
                    use_container_width=True, key="img_dl",
                )
            except Exception as e:
                st.error(f"Failed: {e}")

def render_video_maker():
    st.markdown("## 🎥 Video Maker (Real MP4)")
    st.caption("Generate a real MP4 slideshow video — free. "
               "Script by AI, images by Pollinations, voice by edge-tts.")
    st.info("⏱️ Generation takes 1-3 minutes. "
            "Each scene: 1 image + 1 audio clip, merged into MP4.")

    topic = st.text_input(
        "Video topic *",
        placeholder="e.g. Why Jordan is great for startups",
        key="vm_topic",
    )
    col1, col2 = st.columns(2)
    with col1:
        language = st.selectbox("Narration language",
                                ["English", "Arabic"], key="vm_lang")
    with col2:
        duration = st.selectbox("Target duration",
                                ["20 seconds", "30 seconds", "45 seconds"],
                                key="vm_dur")

    voices = VOICE_CATALOG[language]
    voice_labels = [f"{v['name']} ({v['gender']})" for v in voices]
    idx = st.selectbox("Voice", range(len(voices)),
                       format_func=lambda i: voice_labels[i],
                       key="vm_voice")
    voice = voices[idx]

    if st.button("🎬 Generate Video", use_container_width=True,
                 key="vm_gen"):
        if not topic.strip():
            st.error("Please enter a topic.")
            return
        if get_client() is None:
            st.error("AI not configured.")
            return
        progress = st.progress(0, text="Generating script...")
        try:
            scenes = generate_video_script(topic, language, duration)
            if not scenes:
                st.error("Failed to generate scenes.")
                return
            progress.progress(15,
                              text=f"Got {len(scenes)} scenes. Building...")
            output_path = os.path.join(
                tempfile.gettempdir(),
                f"treats_video_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"
            )
            with st.spinner("Rendering video (1-3 minutes)..."):
                build_video_ffmpeg(scenes, voice["id"], output_path)
            progress.progress(100, text="Done!")
            with open(output_path, "rb") as f:
                video_bytes = f.read()
            st.session_state.video_bytes = video_bytes
            st.success("✅ Video ready!")
            st.video(video_bytes)
            stamp = datetime.now().strftime("%Y%m%d_%H%M")
            st.download_button("⬇ Download MP4", data=video_bytes,
                               file_name=f"video_{stamp}.mp4",
                               mime="video/mp4",
                               use_container_width=True, key="vm_dl")
            try:
                os.remove(output_path)
            except Exception:
                pass
        except Exception as e:
            st.error(f"Video generation failed: {e}")

def render_video_ai():
    st.markdown("## 🎞️ AI Video Generator (Veo)")
    st.caption("Generate a real short video from text using "
               "Google's Veo 3.1.")

    if not has_google_key():
        st.error(
            "🔑 **GOOGLE_API_KEY not configured.**\n\n"
            "Add it to Streamlit Secrets, then reload the app."
        )
        with st.expander("How to get a key", expanded=True):
            st.markdown(
                "1. Go to [aistudio.google.com/apikey]"
                "(https://aistudio.google.com/apikey)\n"
                "2. Click **Create API key**\n"
                "3. Copy the key (starts with `AIza...`)\n"
                "4. Paste it in Streamlit Secrets:\n"
                "```toml\nGOOGLE_API_KEY = \"AIza...\"\n```"
            )
        return

    st.info("⏱️ Generation takes 1-3 minutes. "
            "Free tier has daily limits.")

    prompt = st.text_area(
        "Describe your video *",
        height=120,
        placeholder="e.g. A cinematic shot of a cat surfing on a wave "
                    "at sunset, realistic style",
        key="veo_prompt",
    )
    aspect = st.selectbox("Aspect ratio", ["16:9", "9:16"], key="veo_ar")

    if st.button("🎞️ Generate Video (Veo)", use_container_width=True,
                 key="veo_gen"):
        if not prompt.strip():
            st.error("Enter a description.")
            return

        with st.spinner("Generating video with Veo... (1-3 min)"):
            try:
                video_bytes = veo_generate_video(prompt.strip(), aspect)
            except Exception as e:
                st.error(f"❌ {e}")
                return

        st.success("✅ Video generated!")
        st.video(video_bytes)
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        st.download_button(
            "⬇ Download MP4",
            data=video_bytes,
            file_name=f"veo_{stamp}.mp4",
            mime="video/mp4",
            use_container_width=True, key="veo_dl",
        )

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### 🤖 Treats AI")
    st.divider()
    st.markdown("### 🛠️ Tools")
    st.radio("Choose tool", options=ALL_TOOLS, key="selected_tool",
             label_visibility="collapsed")
    st.divider()

    if st.session_state.selected_tool == TOOL_CHAT:
        with st.expander("⚙️ Settings", expanded=False):
            st.selectbox("Model", AVAILABLE_MODELS, key="model")
            st.slider("Temperature", 0.0, 1.5, 0.7, 0.05, key="temperature")
        if st.button("＋ New Chat", use_container_width=True, key="new_chat"):
            st.session_state.messages = []
            st.session_state.pending = False
            st.rerun()

    st.divider()
    st.markdown("### 🔑 API Status")
    st.markdown(
        f"- Groq: {'✅' if has_groq_key() else '❌'}\n"
        f"- Google: {'✅' if has_google_key() else '❌'}"
    )
    st.divider()
    st.markdown(f"**Version** {APP_VERSION}")

# ============================================================
# MAIN
# ============================================================
st.markdown(f"## Treats — {st.session_state.selected_tool}")

if not has_groq_key() and st.session_state.selected_tool not in [
    TOOL_PASSWORD, TOOL_TTS, TOOL_PHOTO_GEN, TOOL_VIDEO_AI
]:
    st.warning("GROQ_API_KEY not configured.")

tool = st.session_state.selected_tool

if tool == TOOL_CV: render_cv_generator(); st.stop()
if tool == TOOL_PASSWORD: render_password_generator(); st.stop()
if tool == TOOL_VIDEO_SCRIPT: render_video_script(); st.stop()
if tool == TOOL_TTS: render_tts(); st.stop()
if tool == TOOL_PHOTO_GEN: render_photo_generator(); st.stop()
if tool == TOOL_VIDEO_MAKER: render_video_maker(); st.stop()
if tool == TOOL_VIDEO_AI: render_video_ai(); st.stop()

render_chat()

st.markdown("---")
st.caption("Treats may make mistakes. Check important information.")
