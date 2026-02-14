"""
============================================
DIYA — AI Voice Assistant | Python Backend
============================================
Flask server powering the voice assistant.
Handles: Weather, Wikipedia, System Commands,
Calculations, Notes, App Launching, and more.
============================================
"""

import os
import re
import json
import math
import time
import webbrowser
import subprocess
import datetime
import threading
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

import requests
import wikipedia
import pyttsx3

# ============================================
# APP SETUP
# ============================================

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# ============================================
# CONFIGURATION
# ============================================

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')
NOTES_FILE = os.path.join(os.path.dirname(__file__), 'notes.json')

DEFAULT_CONFIG = {
    'assistant_name': 'Diya',
    'weather_city': 'Delhi',
    'weather_api_key': '',
    'youtube_api_key': 'AIzaSyBOzxeH5C41hTLCg-cYxUBCxdcfn59d5rw',
    'voice_speed': 150,
    'voice_volume': 1.0,
    'language': 'en'
}


def load_config():
    """Load configuration from file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                saved = json.load(f)
                return {**DEFAULT_CONFIG, **saved}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """Save configuration to file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


config = load_config()


# ============================================
# TEXT-TO-SPEECH ENGINE (runs in background)
# ============================================

tts_lock = threading.Lock()


def speak_text(text):
    """Speak text using pyttsx3 in a background thread with a female voice."""
    def _speak():
        with tts_lock:
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', config.get('voice_speed', 160))
                engine.setProperty('volume', config.get('voice_volume', 1.0))

                # Set female voice — prioritize Zira (Windows female English voice)
                voices = engine.getProperty('voices')
                female_voice = None

                # Priority order for female voices on Windows
                female_keywords = ['zira', 'hazel', 'susan', 'female', 'woman']

                for keyword in female_keywords:
                    for voice in voices:
                        if keyword in voice.name.lower():
                            female_voice = voice
                            break
                    if female_voice:
                        break

                # If no female voice found by keyword, pick the second voice
                # (on Windows, voices[0] = David/male, voices[1] = Zira/female)
                if not female_voice and len(voices) > 1:
                    female_voice = voices[1]

                if female_voice:
                    engine.setProperty('voice', female_voice.id)
                    print(f"Using voice: {female_voice.name}")

                engine.say(text)
                engine.runAndWait()
                engine.stop()
            except Exception as e:
                print(f"TTS Error: {e}")

    thread = threading.Thread(target=_speak, daemon=True)
    thread.start()


# ============================================
# NOTES MANAGEMENT
# ============================================

def load_notes():
    """Load notes from file."""
    if os.path.exists(NOTES_FILE):
        try:
            with open(NOTES_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_notes(notes):
    """Save notes to file."""
    with open(NOTES_FILE, 'w') as f:
        json.dump(notes, f, indent=2)


# ============================================
# COMMAND PROCESSING ENGINE
# ============================================

def process_command(user_input):
    """
    Process a user command and return a response dict:
    { 'response': str, 'action': str|None, 'data': dict|None }
    """
    text = user_input.strip()
    lower = text.lower()

    # ---- WAKE WORD ----
    wake_names = ['hey diya', 'hey ' + config['assistant_name'].lower()]
    for wake in wake_names:
        if lower.startswith(wake):
            after = text[len(wake):].strip()
            if after:
                return process_command(after)
            return response("Hey! I'm here. How can I help you?")

    # ---- TIME ----
    if any(kw in lower for kw in ['time', 'samay', 'baje']):
        if any(kw in lower for kw in ['what', 'tell', 'current', 'kya', 'kitne', 'batao']):
            now = datetime.datetime.now()
            time_str = now.strftime('%I:%M %p')
            return response(f"The current time is {time_str}.")

    # ---- DATE ----
    if any(kw in lower for kw in ['date', 'today', 'din', 'tarikh']):
        now = datetime.datetime.now()
        date_str = now.strftime('%A, %B %d, %Y')
        return response(f"Today is {date_str}.")

    # ---- WEATHER ----
    if any(kw in lower for kw in ['weather', 'temperature', 'mausam', 'taapmaan']):
        return handle_weather(lower)

    # ---- OPEN WEBSITES ----
    websites = {
        'youtube': ('https://www.youtube.com', 'YouTube'),
        'gmail': ('https://mail.google.com', 'Gmail'),
        'mail': ('https://mail.google.com', 'Gmail'),
        'google': ('https://www.google.com', 'Google'),
        'github': ('https://github.com', 'GitHub'),
        'instagram': ('https://www.instagram.com', 'Instagram'),
        'whatsapp': ('https://web.whatsapp.com', 'WhatsApp Web'),
        'twitter': ('https://x.com', 'X (Twitter)'),
        'x.com': ('https://x.com', 'X (Twitter)'),
        'linkedin': ('https://www.linkedin.com', 'LinkedIn'),
        'chatgpt': ('https://chat.openai.com', 'ChatGPT'),
        'facebook': ('https://www.facebook.com', 'Facebook'),
        'spotify': ('https://open.spotify.com', 'Spotify'),
        'reddit': ('https://www.reddit.com', 'Reddit'),
        'stackoverflow': ('https://stackoverflow.com', 'Stack Overflow'),
        'amazon': ('https://www.amazon.in', 'Amazon'),
        'flipkart': ('https://www.flipkart.com', 'Flipkart'),
    }

    if 'open' in lower:
        for key, (url, name) in websites.items():
            if key in lower:
                webbrowser.open(url)
                return response(f"Opening {name} for you!", action='open_website', data={'url': url, 'name': name})

    # ---- OPEN SYSTEM APPS ----
    if 'open' in lower:
        result = handle_open_app(lower)
        if result:
            return result

    # ---- WEB SEARCH ----
    if lower.startswith('search') or lower.startswith('google') or 'search for' in lower:
        query = re.sub(r'^(search|google|search for)\s*', '', text, flags=re.IGNORECASE).strip()
        if query:
            url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
            webbrowser.open(url)
            return response(f'Searching Google for "{query}".', action='search', data={'query': query, 'url': url})
        else:
            return response("What would you like me to search for?")

    # ---- PLAY MUSIC / PLAY SONG ----
    if 'play' in lower:
        # Extract song/query name
        query = re.sub(r'^.*?play\s*', '', text, flags=re.IGNORECASE).strip()
        # Clean up extra words
        query = re.sub(r'^(a |the |some |me )?(song |music |video |gaana |gana )?', '', query, flags=re.IGNORECASE).strip()
        search_term = query or 'relaxing music'
        return handle_youtube_search(search_term)

    # ---- CALCULATOR ----
    if 'calculate' in lower or ('what is' in lower and re.search(r'[\d+\-*/^%]', lower)):
        expr = re.sub(r'^.*?(calculate|what is|what\'s)\s*', '', text, flags=re.IGNORECASE).strip()
        return handle_calculation(expr)

    # Math words: "5 plus 3"
    math_match = re.search(r'(\d+\.?\d*)\s*(plus|minus|times|multiplied by|divided by|into|x)\s*(\d+\.?\d*)', lower)
    if math_match:
        a = float(math_match.group(1))
        op = math_match.group(2)
        b = float(math_match.group(3))
        result = None
        if op == 'plus':
            result = a + b
        elif op == 'minus':
            result = a - b
        elif op in ('times', 'multiplied by', 'into', 'x'):
            result = a * b
        elif op == 'divided by':
            result = a / b if b != 0 else 'undefined (division by zero)'
        return response(f"{a} {op} {b} = {result}")

    # ---- NOTES ----
    if any(kw in lower for kw in ['take a note', 'save a note', 'note down', 'remember this']):
        content = re.sub(r'^.*?(take a note|save a note|note down|remember this)\s*', '', text, flags=re.IGNORECASE).strip()
        if content:
            notes = load_notes()
            note = {
                'id': int(time.time() * 1000),
                'content': content,
                'time': datetime.datetime.now().strftime('%d %b %Y, %I:%M %p')
            }
            notes.append(note)
            save_notes(notes)
            return response(f'Got it! I\'ve saved your note: "{content}".', action='note_saved', data=note)
        else:
            return response("What would you like me to note down?")

    if any(kw in lower for kw in ['show notes', 'my notes', 'open notes', 'list notes']):
        notes = load_notes()
        return response(
            f"You have {len(notes)} note(s)." if notes else "You don't have any notes yet. Say 'Take a note' to add one!",
            action='show_notes',
            data={'notes': notes}
        )

    if 'delete all notes' in lower or 'clear notes' in lower:
        save_notes([])
        return response("All notes have been cleared! 🗑️", action='notes_cleared')

    # ---- GREETINGS ----
    if re.match(r'^(hi|hello|hey|namaste|namaskar|hola|good morning|good afternoon|good evening)', lower):
        hour = datetime.datetime.now().hour
        if hour < 12:
            greeting = 'Good morning'
        elif hour < 17:
            greeting = 'Good afternoon'
        else:
            greeting = 'Good evening'
        responses = [
            f"{greeting}! I'm {config['assistant_name']}. How can I assist you today?",
            f"Hey there! {greeting}! What can I do for you?",
            f"{greeting}! 😊 Ready to help!",
            f"Namaste! {greeting}! How may I help you?"
        ]
        import random
        return response(random.choice(responses))

    # ---- HOW ARE YOU ----
    if any(kw in lower for kw in ['how are you', 'kaise ho', 'how do you do']):
        import random
        replies = [
            "I'm doing great, thank you! Always ready to help you.",
            "I'm wonderful! Thanks for asking. What can I do for you?",
            "I'm feeling fantastic! Ready for your commands. 😊"
        ]
        return response(random.choice(replies))

    # ---- WHAT CAN YOU DO ----
    if any(kw in lower for kw in ['what can you do', 'help', 'features', 'capabilities']):
        return response(
            f"I can help you with many things! Here's what I can do: "
            f"🌦 Check the weather, ⏰ Tell time and date, 🔍 Search the web, "
            f"🎵 Play music on YouTube, 🌐 Open websites like YouTube/Gmail/GitHub, "
            f"📂 Open system apps like Calculator/Notepad/VS Code, "
            f"🧮 Do calculations, 📝 Take and manage notes, "
            f"📖 Look up Wikipedia info, 😂 Tell jokes, and much more!"
        )

    # ---- JOKES ----
    if any(kw in lower for kw in ['joke', 'funny', 'make me laugh', 'mazak']):
        import random
        jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs! 🐛",
            "Why was the JavaScript developer sad? Because he didn't Node how to Express himself! 😄",
            "What's a computer's favorite snack? Microchips! 🍪",
            "Why did the developer go broke? Because he used up all his cache! 💸",
            "I told my computer I needed a break. Now it won't stop sending me Kit-Kat ads! 😂",
            "Why do Java developers wear glasses? Because they can't C#! 🤓",
            "What do you call a programmer from Finland? Nerdic! 🇫🇮",
            "How do trees access the internet? They log in! 🌳"
        ]
        return response(random.choice(jokes))

    # ---- WHO MADE YOU ----
    if any(kw in lower for kw in ['who made you', 'who created you', 'who built you', 'kisne banaya']):
        return response("I was created by a talented developer as a voice assistant project! I'm Diya, here to help you. 🚀")

    # ---- YOUR NAME ----
    if 'your name' in lower or 'tumhara naam' in lower:
        return response(f"My name is {config['assistant_name']}! I'm your personal AI voice assistant. 😊")

    # ---- THANK YOU ----
    if any(kw in lower for kw in ['thank', 'thanks', 'shukriya', 'dhanyawad', 'dhanyavaad']):
        import random
        replies = [
            "You're welcome! Always happy to help! 😊",
            "Glad I could help! Let me know if you need anything else.",
            "My pleasure! That's what I'm here for. ✨"
        ]
        return response(random.choice(replies))

    # ---- BYE ----
    if re.match(r'^(bye|goodbye|see you|tata|alvida|good night)', lower):
        return response("Goodbye! Have a wonderful day! See you soon! 👋✨")

    # ---- WIKIPEDIA / INFO ----
    if re.match(r'^(who is|what is|tell me about|define|explain)', lower):
        query = re.sub(r'^(who is|what is|tell me about|define|explain)\s*', '', text, flags=re.IGNORECASE).strip()
        if query:
            return handle_wikipedia(query)

    # ---- SYSTEM INFO ----
    if 'system info' in lower or 'my computer' in lower:
        import platform
        info = (
            f"You're running {platform.system()} {platform.release()} "
            f"({platform.machine()}). Processor: {platform.processor()}. "
            f"Computer: {platform.node()}."
        )
        return response(info)

    # ---- DEFAULT: Search ----
    url = f"https://www.google.com/search?q={requests.utils.quote(text)}"
    webbrowser.open(url)
    return response(
        f"I'm not sure about that, so I searched Google for you!",
        action='search',
        data={'query': text, 'url': url}
    )


# ============================================
# HELPER HANDLERS
# ============================================

def response(text, action=None, data=None):
    """Build a standard response dict."""
    return {
        'response': text,
        'action': action,
        'data': data
    }


def handle_weather(lower):
    """Fetch weather from OpenWeatherMap API."""
    city = config['weather_city']

    # Extract city from query
    city_match = re.search(r'(?:weather\s+(?:in|of|for|at)\s+)([\w\s]+)', lower)
    if city_match:
        city = city_match.group(1).strip()

    api_key = config.get('weather_api_key', '')
    if not api_key:
        url = f"https://www.google.com/search?q=weather+{requests.utils.quote(city)}"
        webbrowser.open(url)
        return response(
            f"No weather API key configured. I've opened a Google search for weather in {city}. "
            f"To get live weather data, add your OpenWeatherMap API key in Settings!",
            action='search',
            data={'url': url}
        )

    try:
        api_url = f"https://api.openweathermap.org/data/2.5/weather?q={requests.utils.quote(city)}&appid={api_key}&units=metric"
        res = requests.get(api_url, timeout=10)
        data = res.json()

        if data.get('cod') == 200:
            temp = round(data['main']['temp'])
            feels_like = round(data['main']['feels_like'])
            humidity = data['main']['humidity']
            desc = data['weather'][0]['description']
            main_weather = data['weather'][0]['main']
            city_name = data['name']

            emoji_map = {
                'Clear': '☀️', 'Clouds': '☁️', 'Rain': '🌧', 'Drizzle': '🌦',
                'Thunderstorm': '⛈', 'Snow': '❄️', 'Mist': '🌫', 'Haze': '🌫',
                'Fog': '🌫', 'Smoke': '🌫'
            }
            emoji = emoji_map.get(main_weather, '🌡')

            return response(
                f"{emoji} Weather in {city_name}: {desc}, {temp}°C (feels like {feels_like}°C). Humidity: {humidity}%.",
                action='weather',
                data={
                    'city': city_name, 'temp': temp, 'feels_like': feels_like,
                    'humidity': humidity, 'description': desc, 'main': main_weather
                }
            )
        else:
            return response(f"Sorry, I couldn't find weather for \"{city}\". Please check the city name.")
    except requests.exceptions.Timeout:
        return response("The weather service is taking too long. Please try again.")
    except Exception as e:
        return response(f"Error fetching weather: {str(e)}")


def handle_wikipedia(query):
    """Fetch a Wikipedia summary."""
    try:
        wikipedia.set_lang('en')
        summary = wikipedia.summary(query, sentences=3)
        if len(summary) > 400:
            summary = summary[:400] + '...'
        return response(summary, action='wikipedia', data={'query': query})
    except wikipedia.exceptions.DisambiguationError as e:
        options = ', '.join(e.options[:5])
        return response(f'"{query}" could refer to multiple topics: {options}. Please be more specific.')
    except wikipedia.exceptions.PageError:
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        webbrowser.open(url)
        return response(f"I couldn't find a Wikipedia article for \"{query}\". I've searched Google instead.")
    except Exception:
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        webbrowser.open(url)
        return response(f"Let me search that for you online.")


def handle_calculation(expr):
    """Safely evaluate a math expression."""
    try:
        # Clean expression
        sanitized = expr.replace('^', '**').replace('×', '*').replace('÷', '/')
        sanitized = re.sub(r'[^0-9+\-*/.()%\s]', '', sanitized)
        sanitized = sanitized.replace('%', '/100')
        if not sanitized.strip():
            return response("Please give me a valid math expression, like 'calculate 25 * 4'.")
        # Safe evaluation with math functions
        result = eval(sanitized, {"__builtins__": {}}, {
            "math": math, "sqrt": math.sqrt, "pi": math.pi,
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "log": math.log, "log10": math.log10
        })
        return response(f"{expr} = {result}", action='calculation', data={'expr': expr, 'result': result})
    except Exception:
        return response("Sorry, I couldn't calculate that. Try something like 'calculate 25 * 4'.")


def handle_open_app(lower):
    """Open system applications on Windows."""
    apps = {
        'calculator': 'calc',
        'notepad': 'notepad',
        'paint': 'mspaint',
        'task manager': 'taskmgr',
        'command prompt': 'cmd',
        'cmd': 'cmd',
        'terminal': 'wt',
        'powershell': 'powershell',
        'file explorer': 'explorer',
        'explorer': 'explorer',
        'control panel': 'control',
        'settings': 'ms-settings:',
        'word': 'winword',
        'excel': 'excel',
        'powerpoint': 'powerpnt',
        'snipping tool': 'SnippingTool',
        'camera': 'microsoft.windows.camera:',
    }

    # VS Code special handling
    if any(kw in lower for kw in ['vs code', 'vscode', 'visual studio code']):
        try:
            subprocess.Popen(['code'], shell=True)
            return response("Opening VS Code! 💻")
        except Exception:
            return response("Couldn't open VS Code. Make sure it's installed and in PATH.")

    # Chrome special handling
    if 'chrome' in lower:
        try:
            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            if os.path.exists(chrome_path):
                subprocess.Popen([chrome_path])
            else:
                subprocess.Popen(['start', 'chrome'], shell=True)
            return response("Opening Google Chrome! 🌐")
        except Exception:
            return response("Couldn't open Chrome. Make sure it's installed.")

    for app_name, app_cmd in apps.items():
        if app_name in lower:
            try:
                if ':' in app_cmd:
                    os.startfile(app_cmd)
                else:
                    subprocess.Popen([app_cmd], shell=True)
                return response(f"Opening {app_name.title()}! 🚀")
            except Exception as e:
                return response(f"Sorry, I couldn't open {app_name.title()}: {str(e)}")

    return None  # Not an app command


def handle_youtube_search(query):
    """Search YouTube using the Data API v3 and return the top result."""
    api_key = config.get('youtube_api_key', '')

    if not api_key:
        # Fallback: open YouTube search in browser
        url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
        webbrowser.open(url)
        return response(
            f'Searching YouTube for "{query}"! 🎵',
            action='play_music',
            data={'query': query, 'fallback': True, 'url': url}
        )

    try:
        search_url = 'https://www.googleapis.com/youtube/v3/search'
        params = {
            'part': 'snippet',
            'q': query,
            'key': api_key,
            'maxResults': 5,
            'type': 'video',
            'videoCategoryId': '10',  # Music category
        }
        r = requests.get(search_url, params=params, timeout=8)

        if r.status_code == 200:
            data = r.json()
            items = data.get('items', [])

            if items:
                video = items[0]
                video_id = video['id']['videoId']
                title = video['snippet']['title']
                channel = video['snippet']['channelTitle']
                thumbnail = video['snippet']['thumbnails']['high']['url']

                # Build results list for frontend
                results = []
                for item in items[:5]:
                    results.append({
                        'videoId': item['id']['videoId'],
                        'title': item['snippet']['title'],
                        'channel': item['snippet']['channelTitle'],
                        'thumbnail': item['snippet']['thumbnails']['medium']['url']
                    })

                return response(
                    f'Now playing: "{title}" by {channel} 🎵',
                    action='play_youtube',
                    data={
                        'videoId': video_id,
                        'title': title,
                        'channel': channel,
                        'thumbnail': thumbnail,
                        'url': f'https://www.youtube.com/watch?v={video_id}',
                        'embed': f'https://www.youtube.com/embed/{video_id}?autoplay=1',
                        'results': results,
                        'query': query
                    }
                )
            else:
                # No results
                url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
                webbrowser.open(url)
                return response(
                    f'No exact match found. Searching YouTube for "{query}".',
                    action='play_music',
                    data={'query': query, 'fallback': True, 'url': url}
                )
        else:
            error_msg = r.json().get('error', {}).get('message', 'Unknown error')
            print(f"YouTube API error: {r.status_code} - {error_msg}")
            # Fallback
            url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
            webbrowser.open(url)
            return response(
                f'Playing "{query}" on YouTube! 🎵',
                action='play_music',
                data={'query': query, 'fallback': True, 'url': url}
            )

    except Exception as e:
        print(f"YouTube search error: {e}")
        url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
        webbrowser.open(url)
        return response(
            f'Playing "{query}" on YouTube! 🎵',
            action='play_music',
            data={'query': query, 'fallback': True, 'url': url}
        )


# ============================================
# FLASK ROUTES
# ============================================

@app.route('/favicon.ico')
def favicon():
    """Return a simple SVG favicon to avoid 404."""
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="45" fill="#7c3aed"/>
        <text x="50" y="68" font-size="50" text-anchor="middle" fill="white">🎤</text>
    </svg>'''
    return app.response_class(svg, mimetype='image/svg+xml')


@app.route('/')
def serve_index():
    """Serve the frontend."""
    return send_from_directory('.', 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory('.', filename)


@app.route('/api/command', methods=['POST'])
def api_command():
    """Process a voice/text command."""
    data = request.get_json()
    user_input = data.get('command', '').strip()

    if not user_input:
        return jsonify({'response': 'I didn\'t catch that. Could you try again?', 'action': None, 'data': None})

    result = process_command(user_input)

    # Optionally speak the response via pyttsx3 (server-side TTS)
    if data.get('use_server_tts', False):
        speak_text(result['response'])

    return jsonify(result)


@app.route('/api/weather', methods=['GET'])
def api_weather():
    """Get weather for a city."""
    city = request.args.get('city', config['weather_city'])
    api_key = config.get('weather_api_key', '')

    if not api_key:
        return jsonify({'error': 'No API key configured'}), 400

    try:
        api_url = f"https://api.openweathermap.org/data/2.5/weather?q={requests.utils.quote(city)}&appid={api_key}&units=metric"
        res = requests.get(api_url, timeout=10)
        return jsonify(res.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notes', methods=['GET'])
def api_get_notes():
    """Get all notes."""
    return jsonify(load_notes())


@app.route('/api/notes', methods=['POST'])
def api_add_note():
    """Add a new note."""
    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Note content is empty'}), 400

    notes = load_notes()
    note = {
        'id': int(time.time() * 1000),
        'content': content,
        'time': datetime.datetime.now().strftime('%d %b %Y, %I:%M %p')
    }
    notes.append(note)
    save_notes(notes)
    return jsonify(note)


@app.route('/api/notes', methods=['DELETE'])
def api_clear_notes():
    """Clear all notes."""
    save_notes([])
    return jsonify({'message': 'All notes cleared'})


@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
def api_delete_note(note_id):
    """Delete a specific note."""
    notes = load_notes()
    notes = [n for n in notes if n['id'] != note_id]
    save_notes(notes)
    return jsonify({'message': 'Note deleted'})


@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """Get current settings."""
    return jsonify(config)


@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    """Update settings."""
    global config
    data = request.get_json()
    config.update(data)
    save_config(config)
    return jsonify({'message': 'Settings saved', 'settings': config})


@app.route('/api/speak', methods=['POST'])
def api_speak():
    """Server-side text-to-speech."""
    data = request.get_json()
    text = data.get('text', '')
    if text:
        speak_text(text)
        return jsonify({'message': 'Speaking...'})
    return jsonify({'error': 'No text provided'}), 400


@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'assistant': config['assistant_name'],
        'version': '1.0.0',
        'timestamp': datetime.datetime.now().isoformat()
    })


# ============================================
# STARTUP
# ============================================

if __name__ == '__main__':
    print("")
    print("  ==========================================")
    print(f"    {config['assistant_name']} -- AI Voice Assistant")
    print("    Backend Server v1.0")
    print("    Running at http://localhost:5000")
    print("  ==========================================")
    print("")
    app.run(host='0.0.0.0', port=5000, debug=True)
