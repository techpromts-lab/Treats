<div align="center">

<img src="https://raw.githubusercontent.com/techpromts-lab/Treats/main/.streamlit/logo.svg" width="120" alt="Treats Logo" />

# 🧠 Treats

**A multi-tool AI assistant — chat, vision, voice, and images**

A Streamlit-based AI assistant powered by Groq, with automatic rotation across 10 API keys and a fair daily limit of 5,000 tokens.

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Groq](https://img.shields.io/badge/Groq-Powered-F55036?style=flat-square)](https://groq.com)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 💬 Smart Chat
- Full image analysis (Vision)
- LLaMA 4 Scout & Maverick models
- Real-time streaming responses
- Full conversation management (create, delete, rename, export as ZIP)

### 🎨 Image Generation
- Multiple models (Flux, Turbo, ...)
- Multiple aspect ratios (1:1, 16:9, 9:16, 4:3)
- Fixed or random seed
- Built-in image gallery

</td>
<td width="50%">

### 🔊 Text to Speech
- 5 languages supported (Arabic, English, French, Spanish, German)
- Adjustable rate, pitch, and volume
- Direct MP3 download

### 📄 Extra Tools
- **CV Builder** — professional resumes
- **Video Script** — storyboards with scene breakdowns
- **Password Generator** — strong, secure passwords

</td>
</tr>
</table>

---

## 🚀 Technical Highlights

| Feature | Description |
|---|---|
| 🔄 **Automatic Key Rotation** | Smart switching across 10 Groq keys on quota exhaustion (429) |
| 📊 **5,000 Daily Tokens** | Transparent counter with automatic midnight reset |
| 🌙 **Dark Mode** | Instant toggle between Light & Dark themes |
| ⚙️ **Flexible Settings** | Adjustable display density and font size |
| 💾 **Conversation Export** | Download all conversations as a ZIP file |
| 📱 **Responsive** | Works on mobile and desktop |

---

## 🛠️ Tech Stack

<div align="center">

| | Technology | Purpose |
|:---:|:---:|:---|
| ![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white) | **Python 3.11** | Core language |
| ![Streamlit](https://img.shields.io/badge/-Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white) | **Streamlit** | Web framework |
| ![Groq](https://img.shields.io/badge/-Groq-F55036?style=flat-square) | **Groq API** | LLaMA 4 models |
| ![Edge](https://img.shields.io/badge/-Edge_TTS-0078D4?style=flat-square&logo=microsoftedge&logoColor=white) | **Edge TTS** | Text-to-speech |
| ![Pollinations](https://img.shields.io/badge/-Pollinations-8B5CF6?style=flat-square) | **Pollinations AI** | Image generation |

</div>

---

## 📦 Local Installation

### 1. Clone the repository

```bash
git clone https://github.com/techpromts-lab/Treats.git
cd Treats
