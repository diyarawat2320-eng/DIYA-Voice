"""
============================================
DIYA — AI Voice Assistant | Vercel Serverless
============================================
Serverless Flask API for Vercel deployment.
Handles: Weather, Wikipedia, YouTube Search,
Calculator, Notes, and more.
============================================
"""

import os
import re
import json
import math
import time
import datetime
import random

from flask import Flask, request, jsonify
import requests

try:
    import wikipedia
    HAS_WIKIPEDIA = True
except ImportError:
    HAS_WIKIPEDIA = False

# ============================================
# APP SETUP
# ============================================

app = Flask(__name__)

# ============================================
# CONFIGURATION (from environment variables)
# ============================================

config = {
    'assistant_name': os.environ.get('ASSISTANT_NAME', 'Diya'),
    'weather_city': os.environ.get('WEATHER_CITY', 'Delhi'),
    'weather_api_key': os.environ.get('WEATHER_API_KEY', ''),
    'youtube_api_key': os.environ.get('YOUTUBE_API_KEY', ''),
    'voice_speed': 150,
    'voice_volume': 1.0,
    'language': 'en'
}

# In-memory notes (wiped on cold start — serverless limitation)
notes_store = []


# ============================================
# COMMAND PROCESSING ENGINE
# ============================================

def process_command(user_input):
    """Process a user command and return a response dict."""
    text = user_input.strip()
    lower = text.lower()

    # ---- WAKE WORD ----
    wake_names = ['hey diya', 'hey ' + config['assistant_name'].lower()]
    for wake in wake_names:
        if lower.startswith(wake):
            after = text[len(wake):].strip()
            if after:
                return process_command(after)
            return resp("Hey! I'm here. How can I help you?")

    # ---- TIME ----
    if any(kw in lower for kw in ['time', 'samay', 'baje']):
        if any(kw in lower for kw in ['what', 'tell', 'current', 'kya', 'kitne', 'batao']):
            now = datetime.datetime.now()
            time_str = now.strftime('%I:%M %p')
            return resp(f"The current time is {time_str}.")

    # ---- DATE ----
    if any(kw in lower for kw in ['date', 'today', 'din', 'tarikh']):
        now = datetime.datetime.now()
        date_str = now.strftime('%A, %B %d, %Y')
        return resp(f"Today is {date_str}.")

    # ---- WEATHER ----
    if any(kw in lower for kw in ['weather', 'temperature', 'mausam', 'taapmaan']):
        return handle_weather(lower)

    # ---- OPEN WEBSITES (send URL to frontend) ----
    websites = {
        'youtube': ('https://www.youtube.com', 'YouTube'),
        'gmail': ('https://mail.google.com', 'Gmail'),
        'mail': ('https://mail.google.com', 'Gmail'),
        'google': ('https://www.google.com', 'Google'),
        'github': ('https://github.com', 'GitHub'),
        'instagram': ('https://www.instagram.com', 'Instagram'),
        'whatsapp': ('https://web.whatsapp.com', 'WhatsApp Web'),
        'twitter': ('https://x.com', 'X (Twitter)'),
        'linkedin': ('https://www.linkedin.com', 'LinkedIn'),
        'chatgpt': ('https://chat.openai.com', 'ChatGPT'),
        'facebook': ('https://www.facebook.com', 'Facebook'),
        'spotify': ('https://open.spotify.com', 'Spotify'),
        'reddit': ('https://www.reddit.com', 'Reddit'),
        'amazon': ('https://www.amazon.in', 'Amazon'),
        'flipkart': ('https://www.flipkart.com', 'Flipkart'),
        'netflix': ('https://www.netflix.com', 'Netflix'),
    }

    if 'open' in lower:
        for key, (url, name) in websites.items():
            if key in lower:
                return resp(
                    f"Opening {name} for you!",
                    action='open_website',
                    data={'url': url, 'name': name}
                )

    # ---- WEB SEARCH ----
    if lower.startswith('search') or lower.startswith('google') or 'search for' in lower:
        query = re.sub(r'^(search|google|search for)\s*', '', text, flags=re.IGNORECASE).strip()
        if query:
            url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
            return resp(
                f'Searching Google for "{query}".',
                action='open_website',
                data={'url': url, 'query': query}
            )
        return resp("What would you like me to search for?")

    # ---- PLAY MUSIC / YOUTUBE ----
    if 'play' in lower:
        query = re.sub(r'^.*?play\s*', '', text, flags=re.IGNORECASE).strip()
        query = re.sub(r'^(a |the |some |me )?(song |music |video |gaana |gana )?', '', query, flags=re.IGNORECASE).strip()
        search_term = query or 'relaxing music'
        return handle_youtube_search(search_term)

    # ---- CALCULATOR ----
    if 'calculate' in lower or ('what is' in lower and re.search(r'[\d+\-*/^%]', lower)):
        expr = re.sub(r'^.*?(calculate|what is|what\'s)\s*', '', text, flags=re.IGNORECASE).strip()
        return handle_calculation(expr)

    # Math words
    math_match = re.search(r'(\d+\.?\d*)\s*(plus|minus|times|multiplied by|divided by|into|x)\s*(\d+\.?\d*)', lower)
    if math_match:
        a = float(math_match.group(1))
        op = math_match.group(2)
        b = float(math_match.group(3))
        result = None
        if op == 'plus': result = a + b
        elif op == 'minus': result = a - b
        elif op in ('times', 'multiplied by', 'into', 'x'): result = a * b
        elif op == 'divided by': result = a / b if b != 0 else 'undefined (division by zero)'
        return resp(f"{a} {op} {b} = {result}")

    # ---- NOTES ----
    if any(kw in lower for kw in ['take a note', 'save a note', 'note down', 'remember this']):
        content = re.sub(r'^.*?(take a note|save a note|note down|remember this)\s*', '', text, flags=re.IGNORECASE).strip()
        if content:
            note = {
                'id': int(time.time() * 1000),
                'content': content,
                'time': datetime.datetime.now().strftime('%d %b %Y, %I:%M %p')
            }
            notes_store.append(note)
            return resp(f'Got it! I\'ve saved your note: "{content}".', action='note_saved', data=note)
        return resp("What would you like me to note down?")

    if any(kw in lower for kw in ['show notes', 'my notes', 'open notes', 'list notes']):
        return resp(
            f"You have {len(notes_store)} note(s)." if notes_store else "You don't have any notes yet.",
            action='show_notes',
            data={'notes': notes_store}
        )

    if 'delete all notes' in lower or 'clear notes' in lower:
        notes_store.clear()
        return resp("All notes have been cleared!", action='notes_cleared')

    # ---- GREETINGS ----
    if re.match(r'^(hi|hello|hey|namaste|namaskar|hola|good morning|good afternoon|good evening)', lower):
        hour = datetime.datetime.now().hour
        greeting = 'Good morning' if hour < 12 else ('Good afternoon' if hour < 17 else 'Good evening')
        responses = [
            f"{greeting}! I'm {config['assistant_name']}. How can I assist you today?",
            f"Hey there! {greeting}! What can I do for you?",
            f"{greeting}! 😊 Ready to help!",
        ]
        return resp(random.choice(responses))

    # ---- SYSTEM INFO ----
    if 'system info' in lower or 'device info' in lower:
        return resp(
            f"I'm {config['assistant_name']}, running as a serverless assistant on the cloud. "
            "I can help with YouTube music, weather, calculations, notes, Wikipedia, and more!"
        )

    # ---- WIKIPEDIA ----
    if any(kw in lower for kw in ['tell me about', 'who is', 'what is', 'wikipedia', 'explain']):
        query = re.sub(r'^.*?(tell me about|who is|what is|wikipedia|explain)\s*', '', text, flags=re.IGNORECASE).strip()
        if query:
            return handle_wikipedia(query)

    # ---- JOKES ----
    if any(kw in lower for kw in ['joke', 'funny', 'laugh']):
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything! 😄",
            "I told my computer I needed a break, and it said 'No problem, I'll crash!' 💻",
            "Why did the developer go broke? Because he used up all his cache! 🤣",
            "What's a computer's favourite snack? Microchips! 🍟",
            "Why was the JavaScript developer sad? Because he didn't Node how to Express himself! 😂",
            "What does a cloud do when it gets an itch? It uses a scratch server! ☁️",
        ]
        return resp(random.choice(jokes))

    # ---- HELP ----
    if any(kw in lower for kw in ['what can you do', 'help', 'features', 'capabilities']):
        return resp(
            f"I'm {config['assistant_name']}! I can: 🎵 Play music from YouTube, "
            "🌤 Check weather, ⏰ Tell time & date, 🧮 Calculate math, "
            "📝 Take & manage notes, 🔍 Search Google, 🌐 Open websites, "
            "📖 Search Wikipedia, 😄 Tell jokes, and more! Just ask!"
        )

    # ---- DEFAULT: Google search ----
    url = f"https://www.google.com/search?q={requests.utils.quote(text)}"
    return resp(
        f"I searched Google for '{text}'.",
        action='open_website',
        data={'url': url, 'query': text}
    )


# ============================================
# HELPER HANDLERS
# ============================================

def resp(text, action=None, data=None):
    """Build a standard response dict."""
    return {
        'response': text,
        'action': action,
        'data': data
    }


def handle_weather(lower):
    """Fetch weather from OpenWeatherMap API."""
    api_key = config.get('weather_api_key', '')
    if not api_key:
        return resp("Weather API key is not configured. Please add it in Settings.")

    city = config.get('weather_city', 'Delhi')
    city_match = re.search(r'(?:weather|temperature)\s+(?:in|at|of|for)\s+(.+)', lower)
    if city_match:
        city = city_match.group(1).strip()

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            temp = data['main']['temp']
            feels = data['main']['feels_like']
            desc = data['weather'][0]['description'].capitalize()
            humidity = data['main']['humidity']
            wind = data['wind']['speed']
            return resp(
                f"Weather in {city.title()}: {desc}, {temp}°C (feels like {feels}°C). "
                f"Humidity: {humidity}%, Wind: {wind} m/s.",
                action='weather',
                data={'city': city, 'temp': temp, 'description': desc}
            )
        return resp(f"Couldn't find weather for '{city}'. Check the city name.")
    except Exception:
        return resp("Sorry, I couldn't fetch the weather right now.")


def handle_youtube_search(query):
    """Search YouTube using the Data API v3."""
    api_key = config.get('youtube_api_key', '')
    if not api_key:
        url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
        return resp(
            f'Searching YouTube for "{query}"! 🎵',
            action='open_website',
            data={'url': url, 'query': query}
        )

    try:
        search_url = 'https://www.googleapis.com/youtube/v3/search'
        params = {
            'part': 'snippet',
            'q': query,
            'key': api_key,
            'maxResults': 5,
            'type': 'video',
            'videoCategoryId': '10',
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

                results = []
                for item in items[:5]:
                    results.append({
                        'videoId': item['id']['videoId'],
                        'title': item['snippet']['title'],
                        'channel': item['snippet']['channelTitle'],
                        'thumbnail': item['snippet']['thumbnails']['medium']['url']
                    })

                return resp(
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
    except Exception as e:
        print(f"YouTube error: {e}")

    url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
    return resp(
        f'Playing "{query}" on YouTube! 🎵',
        action='open_website',
        data={'url': url, 'query': query}
    )


def handle_wikipedia(query):
    """Fetch a Wikipedia summary."""
    if not HAS_WIKIPEDIA:
        return resp("Wikipedia module is not available.")
    try:
        summary = wikipedia.summary(query, sentences=3)
        return resp(summary)
    except wikipedia.DisambiguationError as e:
        options = ', '.join(e.options[:5])
        return resp(f"Multiple results found. Did you mean: {options}?")
    except wikipedia.PageError:
        return resp(f"I couldn't find a Wikipedia article for \"{query}\".")
    except Exception:
        return resp("Let me search that for you online.")


def handle_calculation(expr):
    """Safely evaluate a math expression."""
    try:
        sanitized = expr.replace('^', '**').replace('×', '*').replace('÷', '/')
        sanitized = re.sub(r'[^0-9+\-*/.()%\s]', '', sanitized)
        sanitized = sanitized.replace('%', '/100')
        if not sanitized.strip():
            return resp("Please give me a valid math expression, like 'calculate 25 * 4'.")
        result = eval(sanitized, {"__builtins__": {}}, {
            "math": math, "sqrt": math.sqrt, "pi": math.pi,
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "log": math.log, "log10": math.log10
        })
        return resp(f"{expr} = {result}", action='calculation', data={'expr': expr, 'result': result})
    except Exception:
        return resp("Sorry, I couldn't calculate that. Try something like 'calculate 25 * 4'.")


# ============================================
# FLASK ROUTES
# ============================================

@app.route('/api/health')
def api_health():
    return jsonify({
        'status': 'ok',
        'assistant': config['assistant_name'],
        'version': '1.0.0',
        'platform': 'vercel'
    })


@app.route('/api/command', methods=['POST', 'OPTIONS'])
def api_command():
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json(force=True)
    user_input = data.get('command', '').strip()
    if not user_input:
        return jsonify({'response': "I didn't catch that. Could you try again?", 'action': None, 'data': None})
    result = process_command(user_input)
    return jsonify(result)


@app.route('/api/settings', methods=['GET', 'POST', 'OPTIONS'])
def api_settings():
    if request.method == 'OPTIONS':
        return '', 200
    if request.method == 'POST':
        data = request.get_json(force=True)
        config['assistant_name'] = data.get('assistant_name', config['assistant_name'])
        config['weather_city'] = data.get('weather_city', config['weather_city'])
        config['weather_api_key'] = data.get('weather_api_key', config['weather_api_key'])
        return jsonify({'status': 'ok'})
    return jsonify({
        'assistant_name': config['assistant_name'],
        'weather_city': config['weather_city'],
        'weather_api_key': config.get('weather_api_key', ''),
    })


@app.route('/api/notes', methods=['GET', 'OPTIONS'])
def api_get_notes():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify(notes_store)


@app.route('/api/notes', methods=['POST'])
def api_add_note():
    data = request.get_json(force=True)
    content = data.get('content', '').strip()
    if content:
        note = {
            'id': int(time.time() * 1000),
            'content': content,
            'time': datetime.datetime.now().strftime('%d %b %Y, %I:%M %p')
        }
        notes_store.append(note)
        return jsonify(note)
    return jsonify({'error': 'No content'}), 400


@app.route('/api/notes/clear', methods=['POST', 'OPTIONS'])
def api_clear_notes():
    if request.method == 'OPTIONS':
        return '', 200
    notes_store.clear()
    return jsonify({'status': 'cleared'})


@app.route('/api/notes/<int:note_id>', methods=['DELETE', 'OPTIONS'])
def api_delete_note(note_id):
    if request.method == 'OPTIONS':
        return '', 200
    global notes_store
    notes_store = [n for n in notes_store if n['id'] != note_id]
    return jsonify({'status': 'deleted'})


# Vercel requires the app to be importable
# The handler is automatically detected
