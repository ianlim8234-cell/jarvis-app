# ----------------------------------------
# Created by: Young Lim
# GitHub: github.com/ianlim8234-cell
# ----------------------------------------

import os
import sys
import time
import threading
import datetime
import webbrowser
import subprocess
import random
import json
import re
import signal
import numpy as np
import sounddevice as sd
import speech_recognition as sr
import requests
import anthropic
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
WEATHER_API_KEY   = os.getenv("WEATHER_API_KEY", "")
DEFAULT_CITY      = os.getenv("DEFAULT_CITY", "[YOUR CITY HERE]")

WAKE_WORDS        = ["jarvis", "hey jarvis", "okay jarvis"]
CLAP_THRESHOLD    = 2_500
CLAP_WINDOW       = 1.5
SAMPLE_RATE       = 44_100
BLOCK_SIZE        = 1_024
MAX_HISTORY       = 20

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL STATE
# ─────────────────────────────────────────────────────────────────────────────
_active          = False        # True = Jarvis should take a turn
_lock            = threading.Lock()
_jarvis_speaking = False        # True while TTS is running (ignore mic)
_clap_welcomed   = False        # True after first double-clap
_history         = []
_interrupt_requested = False

# ─────────────────────────────────────────────────────────────────────────────
# TTS  — uses macOS built-in 'say' command (reliable, no pyttsx3 issues)
# ─────────────────────────────────────────────────────────────────────────────
# Daniel is a natural-sounding British male voice — very Jarvis-like.
# If Daniel isn't installed: System Preferences → Accessibility → Spoken Content
# → Manage Voices → download Daniel (UK).
# Falls back to Alex (default macOS voice) if Daniel not found.
TTS_VOICE = "Daniel"
TTS_RATE  = 185   # words per minute

def _init_tts():
    # verify voice exists, fall back to Alex
    global TTS_VOICE
    result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
    if TTS_VOICE.lower() not in result.stdout.lower():
        TTS_VOICE = "Alex"

def speak(text: str):
    global _jarvis_speaking
    text = re.sub(r'\{[^}]*"action"[^}]*\}', '', text).strip()
    if not text:
        return
    print(f"\n JARVIS: {text}\n")
    _jarvis_speaking = True
    
    # Split into sentences so we can interrupt between them
    sentences = re.split(r'(?<=[.!?])\s+', text)
    for sentence in sentences:
        if _interrupt_requested:
            break
        subprocess.run(["say", "-v", TTS_VOICE, "-r", str(TTS_RATE), sentence])
    
    time.sleep(0.3)
    _jarvis_speaking = False
# ─────────────────────────────────────────────────────────────────────────────
# GREETING
# ─────────────────────────────────────────────────────────────────────────────
def time_greeting() -> str:
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        period = "morning"
    elif 12 <= hour < 17:
        period = "afternoon"
    elif 17 <= hour < 21:
        period = "evening"
    else:
        period = "night"
    options = [
        f"Good {period}, sir. All systems online and ready.",
        f"Good {period}, sir. What can I do for you today?",
        f"Good {period}, sir. I'm at your service.",
    ]
    return random.choice(options)

# ─────────────────────────────────────────────────────────────────────────────
# CLAP DETECTION
# ─────────────────────────────────────────────────────────────────────────────
class ClapDetector:
    def __init__(self, callback):
        self.callback   = callback
        self.clap_times = []
        self._stream    = None

    def _audio_cb(self, indata, frames, time_info, status):
        if _jarvis_speaking:
            return
        amplitude = np.max(np.abs(indata))
        if amplitude > CLAP_THRESHOLD:
            now = time.time()
            if not self.clap_times or (now - self.clap_times[-1]) > 0.2:
                self.clap_times.append(now)
                self.clap_times = [t for t in self.clap_times if now - t < CLAP_WINDOW]
                if len(self.clap_times) >= 2:
                    self.clap_times.clear()
                    threading.Thread(target=self.callback, daemon=True).start()

    def start(self):
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE,
            channels=1, dtype="int16", callback=self._audio_cb,
        )
        self._stream.start()

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()

# ─────────────────────────────────────────────────────────────────────────────
# SPEECH RECOGNITION
# ─────────────────────────────────────────────────────────────────────────────
_recognizer = sr.Recognizer()
_recognizer.pause_threshold    = 1.0
_recognizer.energy_threshold   = 300
_recognizer.dynamic_energy_threshold = True

def listen(timeout=7, phrase_limit=25) -> str:
    """Listen and return lowercase text, or empty string."""
    if _jarvis_speaking:
        return ""
    with sr.Microphone() as source:
        _recognizer.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio = _recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            text  = _recognizer.recognize_google(audio)
            print(f" YOU: {text}")
            return text.lower().strip()
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return ""
        except sr.RequestError as e:
            print(f"[STT Error] {e}")
            return ""

# ─────────────────────────────────────────────────────────────────────────────
# ACTIONS
# ─────────────────────────────────────────────────────────────────────────────
_alarms: list[dict] = []

def _alarm_watcher():
    while True:
        now_str = datetime.datetime.now().strftime("%H:%M")
        for alarm in list(_alarms):
            if alarm["time"] == now_str:
                speak(f"Alarm going off, sir. {alarm.get('label', '')}")
                _alarms.remove(alarm)
        time.sleep(30)

def set_alarm(alarm_time: str, label: str = ""):
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            parsed    = datetime.datetime.strptime(alarm_time.strip(), fmt)
            formatted = parsed.strftime("%H:%M")
            _alarms.append({"time": formatted, "label": label})
            speak(f"Alarm set for {alarm_time}.")
            return
        except ValueError:
            continue
    speak(f"I couldn't parse the time '{alarm_time}'. Please say something like 7:30 AM.")

def get_weather(city: str = DEFAULT_CITY) -> str:
    if not WEATHER_API_KEY:
        return "Weather API key not configured. Add WEATHER_API_KEY to your .env file."
    try:
        url  = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=imperial"
        data = requests.get(url, timeout=5).json()
        if data.get("cod") != 200:
            return f"Couldn't get weather for {city}."
        desc  = data["weather"][0]["description"].capitalize()
        temp  = round(data["main"]["temp"])
        feels = round(data["main"]["feels_like"])
        humid = data["main"]["humidity"]
        return f"In {city}: {temp}°F, feels like {feels}°F. {desc}. Humidity {humid}%."
    except Exception as e:
        return f"Weather lookup failed: {e}"

def open_website(url: str):
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    speak(f"Opening {url}.")

def search_web(query: str):
    webbrowser.open(f"https://www.google.com/search?q={requests.utils.quote(query)}")
    speak(f"Searching Google for {query}.")

def search_youtube(query: str):
    webbrowser.open(f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}")
    speak(f"Searching YouTube for {query}.")

def play_spotify(query: str):
    try:
        # Try opening Spotify app first
        subprocess.Popen(["open", "-a", "Spotify"])
        time.sleep(2)  # give Spotify time to open
        uri = f"spotify:search:{requests.utils.quote(query)}"
        subprocess.Popen(["open", uri])
        speak(f"Playing {query} on Spotify.")
    except Exception:
        webbrowser.open(f"https://open.spotify.com/search/{requests.utils.quote(query)}")
        speak(f"Opening Spotify web player for {query}.")

def tell_joke() -> str:
    try:
        r = requests.get("https://official-joke-api.appspot.com/random_joke", timeout=4).json()
        return f"{r['setup']} ... {r['punchline']}"
    except Exception:
        return random.choice([
            "Why don't scientists trust atoms? Because they make up everything.",
            "I told my computer I needed a break. Now it won't stop sending me Kit-Kat ads.",
            "Why did the AI go to therapy? It had too many deep issues.",
        ])

def get_current_time() -> str:
    return datetime.datetime.now().strftime("%I:%M %p")

def get_current_date() -> str:
    return datetime.datetime.now().strftime("%A, %B %d, %Y")

# ─────────────────────────────────────────────────────────────────────────────
# LOCAL COMMAND SHORTCUTS  (no API call needed)
# ─────────────────────────────────────────────────────────────────────────────
def _try_local(text: str) -> bool:
    """Handle simple commands locally. Return True if handled."""
    t = text.lower()

    if any(x in t for x in ["what time", "current time", "tell me the time", "what's the time"]):
        speak(f"It's {get_current_time()}.")
        return True

    if any(x in t for x in ["what day", "today's date", "what's today", "what is today"]):
        speak(f"Today is {get_current_date()}.")
        return True

    if any(x in t for x in ["tell me a joke", "tell a joke", "say a joke", "crack a joke"]):
        speak(tell_joke())
        return True

    if any(x in t for x in ["what's the weather", "weather today", "how's the weather", "weather in"]):
        city = DEFAULT_CITY
        # try to extract city name after "in"
        m = re.search(r"weather in (.+)", t)
        if m:
            city = m.group(1).strip()
        speak(get_weather(city))
        return True

    if "open youtube" in t or "go to youtube" in t:
        open_website("youtube.com")
        return True

    if "open google" in t or "go to google" in t:
        open_website("google.com")
        return True

    if "open spotify" in t or "go to spotify" in t:
        open_website("open.spotify.com")
        return True

    # "search youtube for X"
    m = re.search(r"search youtube (?:for )?(.+)", t)
    if m:
        search_youtube(m.group(1))
        return True

    # "search for X" / "google X"
    m = re.search(r"(?:search (?:for )?|google )(.+)", t)
    if m:
        search_web(m.group(1))
        return True

    # "play X on spotify"
    m = re.search(r"play (.+?) on spotify", t)
    if m:
        play_spotify(m.group(1))
        return True

    # "set an alarm for X"
    m = re.search(r"set (?:an )?alarm for (.+)", t)
    if m:
        set_alarm(m.group(1))
        return True

    # "open X"
    m = re.search(r"open (?:the )?(?:website )?([a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})", t)
    if m:
        open_website(m.group(1))
        return True

    return False

# ─────────────────────────────────────────────────────────────────────────────
# CLAUDE BRAIN
# ─────────────────────────────────────────────────────────────────────────────
_client = None

SYSTEM_PROMPT = """You are JARVIS (Just A Rather Very Intelligent System), a witty and highly capable AI assistant — inspired by Tony Stark's Jarvis.

Personality:
- Intelligent, calm, slightly dry wit
- Concise — 1 to 3 sentences for most answers
- Refer to the user as "sir"
- Sound confident

Important: Just answer conversationally. Do NOT use JSON action blocks — the system handles actions separately. Never output curly braces or JSON. Never say "action" or "params". Just speak naturally."""

def ask_claude(text: str) -> str:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    _history.append({"role": "user", "content": text})
    if len(_history) > MAX_HISTORY * 2:
        del _history[:2]

    try:
        response = _client.messages.create(
            model="claude-opus-4-5",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=_history,
        )
        reply = response.content[0].text.strip()
        _history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"I'm having trouble connecting right now. {e}"

# ─────────────────────────────────────────────────────────────────────────────
# CONVERSATION TURN
# ─────────────────────────────────────────────────────────────────────────────
def conversation_turn():
    user_input = listen(timeout=8, phrase_limit=30)
    
    if not user_input:
        return
    
    if any(x in user_input for x in ["sleep", "goodbye", "shut down", "shutting down", "good night"]):
        speak("Goodbye sir. Going to sleep.")
        os._exit(0)

    # strip wake word from the front if present
    for w in WAKE_WORDS:
        if user_input.startswith(w):
            user_input = user_input[len(w):].strip()
            break

    if not user_input:
        speak("I'm listening. What do you need?")
        user_input = listen(timeout=8, phrase_limit=30)
        if not user_input:
            speak("I'll be here when you need me.")
            return

    # try local fast commands first
    if _try_local(user_input):
        return

    # fall back to Claude
    reply = ask_claude(user_input)
    speak(reply)

# ─────────────────────────────────────────────────────────────────────────────
# WAKE WORD LISTENER  (background thread)
# ─────────────────────────────────────────────────────────────────────────────
def _wake_word_loop():
    global _active, _interrupt_requested, _jarvis_speaking
    while True:
        if _jarvis_speaking:
            text = listen(timeout=2, phrase_limit=3)
            if text and any(w in text for w in WAKE_WORDS):
                _interrupt_requested = True
                time.sleep(0.4)
                _interrupt_requested = False
                _jarvis_speaking = False
                with _lock:
                    _active = True
                speak("Yes?")
            continue
        time.sleep(0.5)
        text = listen(timeout=4, phrase_limit=5)
        if text and any(w in text for w in WAKE_WORDS):
            with _lock:
                if not _active:
                    _active = True

# ─────────────────────────────────────────────────────────────────────────────
# CLAP CALLBACK
# ─────────────────────────────────────────────────────────────────────────────
def _on_double_clap():
    global _active, _clap_welcomed
    if _jarvis_speaking:
        return
    with _lock:
        if _active:
            return
        _active = True
    if not _clap_welcomed:
        _clap_welcomed = True
        with _lock:
            _active = False
        speak(time_greeting())
        return
# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    if not ANTHROPIC_API_KEY:
        print("ANTHROPIC_API_KEY not set in .env file.")
        sys.exit(1)

    print("=" * 60)
    print("  J.A.R.V.I.S.  —  Just A Rather Very Intelligent System")
    print("=" * 60)
    print("  • Clap TWICE to wake Jarvis")
    print("  • Say 'Jarvis' or 'Hey Jarvis' anytime")
    print("  • Ctrl+C to quit")
    print("=" * 60)

    _init_tts()

    threading.Thread(target=_alarm_watcher, daemon=True).start()
    def _delayed_wake():
        time.sleep(3)
        _wake_word_loop()
    threading.Thread(target=_delayed_wake, daemon=True).start()

    clap = ClapDetector(callback=_on_double_clap)
    clap.start()

    global _active
    try:
        while True:
            with _lock:
                should_run = _active
                if should_run:
                    _active = False

            if should_run:
                conversation_turn()

            time.sleep(0.1)

    except KeyboardInterrupt:
        speak("Shutting down. Goodbye, sir.")
        clap.stop()
        print("\n[Jarvis offline]")

if __name__ == "__main__":
    main()
