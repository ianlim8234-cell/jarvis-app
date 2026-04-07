# 🤖 JARVIS — Complete Setup Guide

## What Jarvis Can Do
- **Wake up** on two claps (start) or hearing "Jarvis" / "Hey Jarvis"
- **Greet you** based on time of day ("Good morning, Young")
- **Full AI conversation** powered by Claude (same brain as Claude.ai)
- **Weather** — "Jarvis, what's the weather?"
- **Alarms** — "Jarvis, set an alarm for 7:30 AM"
- **Web search** — "Jarvis, search for the latest iPhone"
- **YouTube** — "Jarvis, search YouTube for lo-fi music"
- **Open websites** — "Jarvis, open reddit.com"
- **Spotify** — "Jarvis, play Drake on Spotify"
- **Jokes** — "Jarvis, tell me a joke"
- **Time & Date** — "What time is it?" / "What day is it?"
- **General knowledge** — Anything you'd ask ChatGPT or Claude

---

## STEP 1 — Install Python

You need **Python 3.10 or newer**.

Check if you have it:
```
python --version
```

If not, download from: https://www.python.org/downloads/

---

## STEP 2 — Get Your API Keys

### Anthropic (REQUIRED)
1. Go to https://console.anthropic.com
2. Sign up / log in
3. Click **API Keys** → **Create Key**
4. Copy the key (starts with `sk-ant-...`)

### OpenWeatherMap (FREE — for weather)
1. Go to https://home.openweathermap.org/users/sign_up
2. Create a free account
3. Go to **API Keys** tab → copy your default key
4. Note: it takes ~10 minutes to activate after sign-up

---

## STEP 3 — Set Up the Project

### Windows
```cmd
cd Desktop
mkdir jarvis
cd jarvis
```
Copy `jarvis.py`, `requirements.txt`, `.env` into this folder.

### Mac / Linux
```bash
cd ~/Desktop
mkdir jarvis && cd jarvis
```
Copy the three files into this folder.

---

## STEP 4 — Install System Dependencies

### Windows
Install **PyAudio** (the tricky one):
```cmd
pip install pipwin
pipwin install pyaudio
```

Or download the wheel directly from:
https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
Then:
```cmd
pip install PyAudio‑0.2.14‑cp311‑cp311‑win_amd64.whl
```

### Mac
```bash
brew install portaudio
pip install pyaudio
```
(Install Homebrew first if needed: https://brew.sh)

### Linux (Ubuntu/Debian)
```bash
sudo apt-get install python3-pyaudio portaudio19-dev python3-dev
pip install pyaudio
```

---

## STEP 5 — Install Python Packages

```bash
pip install -r requirements.txt
```

This installs: anthropic, sounddevice, speechrecognition, pyttsx3, numpy, requests, python-dotenv, pyaudio, soundfile

---

## STEP 6 — Add Your API Keys

Open the `.env` file in any text editor (Notepad, VS Code, etc.) and fill it in:

```
ANTHROPIC_API_KEY=sk-ant-XXXXXXXXXXXXXXXXXX
WEATHER_API_KEY=your_openweathermap_key_here
DEFAULT_CITY=Houston
```

Save and close.

---

## STEP 7 — Run Jarvis

```bash
python jarvis.py
```

You'll see:
```
============================================================
  J.A.R.V.I.S.  —  Just A Rather Very Intelligent System
============================================================
  • Clap TWICE to wake Jarvis (first launch)
  • Say 'Jarvis' or 'Hey Jarvis' to activate at any time
  • Press Ctrl+C to quit
============================================================
```

**First launch:** Clap twice sharply → Jarvis greets you based on time of day.

**After that:** Just say **"Jarvis"** or **"Hey Jarvis"** and it activates.

---

## Example Commands to Try

| Say this... | Jarvis does... |
|---|---|
| "Jarvis, what's the weather?" | Reads Houston weather |
| "Jarvis, set an alarm for 8:30 AM" | Sets alarm, confirms |
| "Jarvis, search YouTube for lofi beats" | Opens YouTube search |
| "Jarvis, play Kendrick Lamar on Spotify" | Opens Spotify |
| "Jarvis, open twitter.com" | Opens browser |
| "Jarvis, tell me a joke" | Tells a joke |
| "Jarvis, what time is it?" | Reads the time |
| "Jarvis, explain quantum computing" | Full AI answer |
| "Jarvis, write me a Python function to sort a list" | Codes for you |
| "Jarvis, what's the capital of France?" | Instant answer |

---

## Troubleshooting

**"No module named pyaudio"**
→ Follow Step 4 for your OS exactly.

**Jarvis can't hear me / poor recognition**
→ Make sure your mic is set as default input in System Settings. Speak clearly and at normal volume.

**Clap detection not working**
→ Clap sharply and close-ish to the microphone. You can adjust `CLAP_THRESHOLD` in `jarvis.py` line ~40 (lower = more sensitive, e.g. 1500).

**"ANTHROPIC_API_KEY not set"**
→ Make sure your `.env` file is in the same folder as `jarvis.py`.

**Weather not working**
→ Make sure WEATHER_API_KEY is set and wait 10 min after creating OpenWeatherMap account.

**Jarvis voice sounds robotic / wrong voice**
→ On Windows: Go to Settings → Time & Language → Speech → install more voices. On Mac you can change the voice in System Preferences → Accessibility → Spoken Content.

---

## Optional: Run on Startup (so Jarvis is always on)

### Mac
Create a `.plist` launchd file or add to Login Items.

### Windows
Add a shortcut to the jarvis folder in:
`C:\Users\YourName\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`

### Linux
Add to crontab: `@reboot python3 /path/to/jarvis.py`

---

## File Structure
```
jarvis/
├── jarvis.py          ← Main program
├── requirements.txt   ← Python dependencies
└── .env               ← Your secret API keys (never share this!)
```

---

## Credits
Built with: Claude API (Anthropic), Google Speech Recognition, pyttsx3, OpenWeatherMap API
