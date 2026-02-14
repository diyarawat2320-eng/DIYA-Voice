# 🎤 DIYA - AI Voice Assistant

A premium AI voice assistant built with Python (Flask) backend and a modern glassmorphism UI frontend.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-Backend-green?logo=flask)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-yellow?logo=javascript)
![License](https://img.shields.io/badge/License-MIT-purple)

## ✨ Features

- 🎙️ **Voice Commands** — Always-on wake word detection ("Hey Diya")
- 🎵 **YouTube Music Player** — Search & play songs inline with YouTube API
- 🌤️ **Weather Updates** — Real-time weather via OpenWeatherMap API
- 📝 **Notes Management** — Save, view, and delete voice notes
- 🔍 **Web Search** — Google search via voice or text
- 🧮 **Calculator** — Natural language math calculations
- 📖 **Wikipedia** — Quick knowledge lookups
- 🌐 **Website Launcher** — Open popular sites by voice
- 💻 **System Apps** — Launch Windows applications
- 😄 **Jokes & Fun** — Entertainment commands
- 🎨 **Premium UI** — Dark/light glassmorphism theme with animations
- ⌨️ **Keyboard Shortcuts** — Ctrl+/ to focus input, Escape to close panels

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/diyarawat2320-eng/DIYA-Voice.git
cd DIYA-Voice

# Install Python dependencies
pip install flask flask-cors requests wikipedia pyttsx3 pywhatkit

# Run the server
python main.py
```

Open `http://localhost:5000` in your browser.

### Configuration

Create a `config.json` in the root directory:

```json
{
  "assistant_name": "Diya",
  "weather_city": "Delhi",
  "weather_api_key": "YOUR_OPENWEATHERMAP_KEY",
  "youtube_api_key": "YOUR_YOUTUBE_API_KEY",
  "voice_speed": 150,
  "voice_volume": 1.0,
  "language": "en"
}
```

## 🗣️ Voice Commands

| Command | Action |
|---------|--------|
| "Hey Diya" | Wake word to activate |
| "Play [song name]" | Search & play on YouTube |
| "What's the weather?" | Get weather report |
| "What time is it?" | Current time |
| "Search [query]" | Google search |
| "Take a note [text]" | Save a note |
| "Show my notes" | Display saved notes |
| "Open YouTube/Gmail/..." | Launch websites |
| "Calculate 25 * 4" | Math calculation |
| "Tell me a joke" | Random joke |
| "Tell me about [topic]" | Wikipedia summary |

## 🛠️ Tech Stack

- **Backend**: Python, Flask, Flask-CORS, pyttsx3, Wikipedia API
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **APIs**: YouTube Data API v3, OpenWeatherMap API
- **Voice**: Web Speech API, SpeechSynthesis API

## 📁 Project Structure

```
DIYA-Voice/
├── main.py          # Flask backend server
├── index.html       # Frontend UI
├── style.css        # Premium design system
├── script.js        # Frontend logic & voice handling
├── config.json      # Settings (gitignored)
├── notes.json       # User notes (gitignored)
└── README.md
```

## 👩‍💻 Author

**Diya Rawat** — [@diyarawat2320-eng](https://github.com/diyarawat2320-eng)

---

Made with ❤️ and AI
