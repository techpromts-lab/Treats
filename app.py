import streamlit as st
import requests
import json
import random
import asyncio
import io
import os
from urllib.parse import quote
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(page_title="Treats", page_icon="🧠", layout="wide")

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
        raise TreatsError("GROQ_API_KEY غير موجود في secrets.")
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
    """جلب قائمة موديلات توليد الصور ديناميكيًا."""
    try:
        r = requests.get("https://image.pollinations.ai/models", timeout=10)
        r.raise_for_status()
        data = r.json()
        # API قد يرجع list أو dict — نتعامل مع الحالتين
        if isinstance(data, list):
            models = [m.get("name") or m for m in data] if data and isinstance(data[0], dict) else data
        elif isinstance(data, dict):
            models = list(data.keys())
        else:
            models = ["flux", "turbo", "flux-realism"]
        # فلترة القيم غير الصالحة
        models = [str(m) for m in models if m]
        return models if models else ["flux", "turbo"]
    except Exception:
        # fallback
        return ["flux", "turbo", "flux-realism", "flux-anime", "flux-3d"]


def generate_image(prompt: str, width: int = 1024, height: int = 1024,
                   model: str = "flux", seed: int = None,
                   enhance: bool = True, nologo: bool = True) -> bytes:
    """يولّد صورة من Pollinations ويرجع bytes."""
    if not prompt or not prompt.strip():
        raise TreatsError("اكتب وصف الصورة أولاً.")

    encoded = quote(prompt.strip())
    url = f"https://image.pollinations.ai/prompt/{encoded}"

    params = {
        "width": width,
        "height": height,
        "model": model,
        "seed": seed if seed is not None else -1,
        "nologo": str(nologo).lower(),
        "enhance": str(enhance).lower(),
    }

    try:
        r = requests.get(url, params=params, timeout=60)
        if r.status_code == 429:
            raise TreatsError("الخدمة مشغولة حاليًا (Rate limit). حاول بعد شوية.")
        r.raise_for_status()
        if not r.content or len(r.content) < 500:
            raise TreatsError("الصورة رجعت فارغة أو تالفة. جرّب وصف تاني.")
        return r.content
    except requests.exceptions.Timeout:
        raise TreatsError("انتهت مدة الانتظار (60ث). جرّب وصف أبسط أو أبعاد أصغر.")
    except requests.exceptions.RequestException as e:
        raise TreatsError(f"فشل الاتصال بـ Pollinations: {e}")


# ============================================================
# TTS — VOICES
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_available_voice_ids():
    """جلب الأصوات المتاحة ديناميكيًا من edge-tts."""
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


async def _tts_generate(text: str, voice: str, rate: str, pitch: str, volume: str) -> bytes:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


# ============================================================
# SIDEBAR NAV
# ============================================================
TOOLS = {
    "💬 Chat": "chat",
    "📄 CV Generator": "cv",
    "🔐 Password Generator": "password",
    "🎬 Video Script": "video",
    "🔊 Text to Speech": "tts",
    "🎨 Photo Generator": "photo",
}

with st.sidebar:
    st.title("🧠 Treats")
    choice_label = st.radio("الأدوات", list(TOOLS.keys()), label_visibility="collapsed")
    tool = TOOLS[choice_label]
    st.divider()
    st.caption("Treats v1.5.0")


# ============================================================
# TOOL: CHAT
# ============================================================
def render_chat():
    st.header("💬 Chat")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        model = st.selectbox("AI Model", options=AVAILABLE_MODELS, key="model")
    with col2:
        temp = st.slider("Temperature", 0.0, 1.5, 0.7, 0.1, key="temp")
    with col3:
        if st.button("🆕 New conversation", key="new_conv"):
            st.session_state.messages = []
            st.rerun()

    # عرض الرسائل
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                c1, c2 = st.columns([1, 9])
                with c1:
                    if st.button("📋", key=f"copy_{i}", help="Copy"):
                        st.toast("انسخ النص يدويًا (st.code أدناه)")
                    if st.button("🔄", key=f"regen_{i}", help="Regenerate"):
                        # إزالة آخر رد وإعادة التوليد
                        st.session_state.messages = st.session_state.messages[:i]
                        st.session_state.regenerate = True
                        st.rerun()

    # Starter prompts
    if not st.session_state.messages:
        st.markdown("**جرّب:**")
        cols = st.columns(3)
        starters = [
            "اشرح لي الـ Vector Databases ببساطة.",
            "اكتب لي إيميل احترافي لطلب إجازة.",
            "اعطني 5 أفكار لمشاريع Streamlit.",
        ]
        for c, s in zip(cols, starters):
            with c:
                if st.button(s, key=f"starter_{s[:10]}"):
                    st.session_state.messages.append({"role": "user", "content": s})
                    st.rerun()

    # إدخال
    prompt = st.chat_input("اكتب رسالتك...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    # توليد الرد
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
            st.error(f"خطأ غير متوقع: {e}")

    # Export
    if st.session_state.messages:
        col1, col2 = st.columns(2)
        with col1:
            md = "\n\n".join(
                f"**{m['role'].capitalize()}:** {m['content']}"
                for m in st.session_state.messages
            )
            st.download_button(
                "⬇️ Export MD",
                data=md,
                file_name=f"treats_chat_{datetime.now():%Y%m%d_%H%M}.md",
                mime="text/markdown",
            )
        with col2:
            st.download_button(
                "⬇️ Export JSON",
                data=json.dumps(st.session_state.messages, ensure_ascii=False, indent=2),
                file_name=f"treats_chat_{datetime.now():%Y%m%d_%H%M}.json",
                mime="application/json",
            )


# ============================================================
# TOOL: CV GENERATOR
# ============================================================
def render_cv():
    st.header("📄 CV Generator")
    with st.form("cv_form"):
        name = st.text_input("الاسم الكامل")
        role = st.text_input("الوظيفة المستهدفة")
        exp = st.text_area("الخبرات (نقاط، سطر لكل خبرة)")
        edu = st.text_input("التعليم")
        skills = st.text_input("المهارات (مفصولة بفواصل)")
        lang = st.selectbox("اللغة", ["العربية", "English"])
        tone = st.selectbox("النبرة", ["Professional", "Concise", "Academic"])
        submitted = st.form_submit_button("✨ توليد السيرة")

    if submitted:
        if not name or not role:
            st.warning("الاسم والوظيفة مطلوبان.")
            return
        try:
            client = get_client()
            prompt = f"""اكتب سيرة ذاتية احترافية باللغة {lang} بنبرة {tone}.
الاسم: {name}
الوظيفة: {role}
الخبرات: {exp}
التعليم: {edu}
المهارات: {skills}
اجعلها بتنسيق Markdown منظم مع عناوين واضحة."""
            with st.spinner("جاري التوليد..."):
                resp = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.6,
                )
            cv_text = resp.choices[0].message.content
            st.markdown(cv_text)
            st.download_button("⬇️ تحميل MD", cv_text, "cv.md", "text/markdown")
            st.download_button("⬇️ تحميل TXT", cv_text, "cv.txt", "text/plain")
        except TreatsError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"خطأ: {e}")


# ============================================================
# TOOL: PASSWORD GENERATOR
# ============================================================
def render_password():
    st.header("🔐 Password Generator")
    import string

    length = st.slider("الطول", 8, 64, 16)
    use_symbols = st.checkbox("رموز (!@#$...)", value=True)
    use_numbers = st.checkbox("أرقام", value=True)

    chars = string.ascii_letters
    if use_numbers:
        chars += string.digits
    if use_symbols:
        chars += "!@#$%^&*()-_=+"

    if st.button("🎲 توليد"):
        pwd = "".join(random.choice(chars) for _ in range(length))
        st.code(pwd, language=None)
        st.download_button("⬇️ تحميل", pwd, "password.txt")


# ============================================================
# TOOL: VIDEO SCRIPT
# ============================================================
def render_video():
    st.header("🎬 Video Script Generator")
    with st.form("video_form"):
        topic = st.text_input("الموضوع")
        duration = st.selectbox("المدة", ["30 ثانية", "60 ثانية", "3 دقائق", "5 دقائق"])
        style = st.selectbox("الأسلوب", ["تعليمي", "ترويجي", "قصصي", "ترفيهي"])
        lang = st.selectbox("اللغة", ["العربية", "English"])
        platform = st.selectbox("المنصة", ["YouTube", "TikTok", "Instagram", "LinkedIn"])
        submitted = st.form_submit_button("🎬 توليد السكربت")

    if submitted:
        if not topic:
            st.warning("اكتب الموضوع.")
            return
        try:
            client = get_client()
            prompt = f"""اكتب سكربت فيديو باللغة {lang} لمنصة {platform}.
الموضوع: {topic}
المدة: {duration}
الأسلوب: {style}
قسّمه إلى مشاهد مع storyboard (الوقت + الوصف البصري + النص)."""
            with st.spinner("جاري التوليد..."):
                resp = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                )
            script = resp.choices[0].message.content
            st.markdown(script)
            st.download_button("⬇️ تحميل MD", script, "script.md", "text/markdown")
        except TreatsError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"خطأ: {e}")


# ============================================================
# TOOL: TTS
# ============================================================
def render_tts():
    st.header("🔊 Text to Speech")
    voices = fetch_available_voice_ids()

    lang_choice = st.radio("اللغة", ["English", "العربية"], horizontal=True)
    voice_pool = voices["en"] if lang_choice == "English" else voices["ar"]

    if not voice_pool:
        st.warning("لا توجد أصوات متاحة حاليًا. حاول لاحقًا.")
        return

    voice = st.selectbox("الصوت", voice_pool, key="tts_voice")
    text = st.text_area("النص", height=150)
    c1, c2, c3 = st.columns(3)
    with c1:
        rate_val = st.slider("السرعة", 0.5, 2.0, 1.0, 0.1)
    with c2:
        pitch_val = st.slider("النبرة (Hz)", -50, 50, 0, 5)
    with c3:
        vol_val = st.slider("مستوى الصوت", 0, 100, 100, 5)

    rate = f"{'+' if rate_val >= 1 else ''}{int((rate_val - 1) * 100)}%"
    pitch = f"{'+' if pitch_val >= 0 else ''}{pitch_val}Hz"
    volume = f"+{vol_val}%"

    if st.button("🔊 توليد الصوت"):
        if not text.strip():
            st.warning("اكتب النص.")
            return
        try:
            with st.spinner("جاري التوليد..."):
                audio = asyncio.run(_tts_generate(text, voice, rate, pitch, volume))
            st.audio(audio, format="audio/mp3")
            st.download_button("⬇️ تحميل MP3", audio, "treats_tts.mp3", "audio/mpeg")
        except Exception as e:
            st.error(f"فشل التوليد: {e}")


# ============================================================
# TOOL: PHOTO GENERATOR  ⭐ الجديد
# ============================================================
def render_photo():
    st.header("🎨 Photo Generator")
    st.caption("مدعوم بـ Pollinations AI — مجاني، بدون مفتاح.")

    # جلب الموديلات ديناميكيًا
    with st.spinner("جاري جلب الموديلات..."):
        models = fetch_image_models()

    # مدخلات
    prompt = st.text_area(
        "وصف الصورة (Prompt)",
        placeholder="مثال: قطة تشرب قهوة في مقهى باريسي، إضاءة سينمائية، 4K",
        height=100,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        model = st.selectbox("Model", models, key="photo_model")
    with c2:
        aspect = st.selectbox(
            "الأبعاد",
            ["1:1 (1024×1024)", "16:9 (1344×768)", "9:16 (768×1344)", "4:3 (1152×896)"],
            key="photo_aspect",
        )
    with c3:
        enhance = st.checkbox("تحسين الـ Prompt تلقائيًا", value=True, key="photo_enhance")

    # تحويل الأبعاد
    dims = {
        "1:1 (1024×1024)": (1024, 1024),
        "16:9 (1344×768)": (1344, 768),
        "9:16 (768×1344)": (768, 1344),
        "4:3 (1152×896)": (1152, 896),
    }
    w, h = dims[aspect]

    # Seed
    c1, c2 = st.columns([3, 1])
    with c1:
        seed = st.number_input("Seed (اترك 0 لعشوائي)", min_value=0, value=0, step=1, key="photo_seed")
    with c2:
        randomize = st.button("🎲 عشوائي", key="photo_random")
        if randomize:
            st.session_state["photo_seed"] = random.randint(1, 999999)
            st.rerun()

    use_seed = int(seed) if seed > 0 else None

    # توليد
    if st.button("🎨 Generate Image", type="primary", key="photo_gen"):
        if not prompt.strip():
            st.warning("اكتب وصف الصورة.")
            return
        try:
            with st.spinner("جاري توليد الصورة... (قد يستغرق 10-30 ثانية)"):
                img_bytes = generate_image(
                    prompt=prompt,
                    width=w,
                    height=h,
                    model=model,
                    seed=use_seed,
                    enhance=enhance,
                )
            st.session_state["last_image"] = img_bytes
            st.session_state["last_prompt"] = prompt
        except TreatsError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"خطأ غير متوقع: {e}")

    # عرض آخر صورة
    if "last_image" in st.session_state:
        st.divider()
        st.image(st.session_state["last_image"], caption=st.session_state.get("last_prompt", ""))
        st.download_button(
            "⬇️ تحميل PNG",
            data=st.session_state["last_image"],
            file_name=f"treats_photo_{datetime.now():%Y%m%d_%H%M%S}.png",
            mime="image/png",
        )
        if st.button("🔄 Regenerate", key="photo_regen"):
            # seed جديد
            new_seed = random.randint(1, 999999)
            try:
                with st.spinner("جاري التوليد من جديد..."):
                    img_bytes = generate_image(
                        prompt=st.session_state["last_prompt"],
                        width=w,
                        height=h,
                        model=model,
                        seed=new_seed,
                        enhance=enhance,
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
