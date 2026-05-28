# 🛡️ Verto AI — WhatsApp Fake News Detector

## Setup
1. Clone repo, install deps: `pip install -r requirements.txt`
2. Fill in `.env` with your Twilio + Google API keys
3. Run: `uvicorn main:app --reload --port 8000`
4. Expose: `ngrok http 8000`
5. Set Twilio Sandbox webhook → `https://YOUR_NGROK/webhook` (POST)

## Usage
- Send "join <keyword>" or "hello" → activation message
- Reply "1" → Hindi, "2" → Marathi, "3" → Gujarati
- Send any news text, image, video, or PDF → fact-check reply

## Architecture
All tools live in mcp_server.py (fastmcp server).
DeepAgent calls it via stdio. No direct API calls in agent code.

## Supported Formats
Text | JPEG/PNG/WebP images | MP4/3GP videos | PDF documents

---

## Testing Checklist

### Step 1: Start the server
```bash
uvicorn main:app --reload --port 8000
```

### Step 2: Expose via ngrok
```bash
ngrok http 8000
```

### Step 3: Configure Twilio
Set Twilio Sandbox **"When a message comes in"** = `https://YOUR_NGROK/webhook` (POST)

---

### Test 1: Activation
Send: `join sandbox-keyword`
**Expected:** Verto AI activation reply + language options

### Test 2: Language Selection
Send: `1`
**Expected:** Language set to Hindi — confirmation in Hindi

### Test 3: Multilingual Text Claim
Send: VIT Vellore Hindi news text
**Expected:** English verdict + Hindi verdict (2 separate messages)

### Test 4: Image
Send: Screenshot of a viral forward
**Expected:** Vision extraction → verdict with sources

### Test 5: Video
Send: A short news video
**Expected:** Frame sampling → vision extraction → verdict

### Test 6: PDF
Send: A PDF news article
**Expected:** Text extraction → verdict with sources

### Test 7: Fabricated Headline
Send: A completely made-up news headline
**Expected:** FAKE verdict, no fabricated URLs, confident explanation

---

## Edge Case Handling

| Situation | Response |
|---|---|
| User sends audio | "Audio not supported yet. Send text, image, video or PDF." |
| Agent timeout (>60s) | "Analysis timed out. Try a shorter snippet." |
| Media download fails | "Couldn't download the file. Please try again." |
| Agent returns no JSON | Send raw output as fallback |
| No trusted source found | `sources: ["No verified source found."]` |
| User sends gibberish | UNVERIFIED verdict with low confidence |
| Repeat "hello" | Re-send activation reply (idempotent) |
| Video >16MB | "Video too large. Please send a shorter clip or screenshot." |

---

## Project Structure

```
verto_ai/
├── main.py                    # FastAPI webhook entry point
├── mcp_server.py              # fastmcp server (6 tools)
├── agent/
│   └── deep_agent.py          # LangChain DeepAgent (spawns MCP via stdio)
├── handlers/
│   ├── sandbox_handler.py     # Activation & language selection logic
│   ├── media_handler.py       # Twilio media download + MIME categorization
│   └── reply_formatter.py     # WhatsApp message formatting
├── utils/
│   ├── language_store.py      # Per-user language preference store
│   └── logger.py              # Structured activity logger
├── user_languages.json        # Runtime language preferences (auto-created)
├── logs/
│   └── activity.log           # Activity log
├── .env                       # API keys (fill in before running)
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `TWILIO_ACCOUNT_SID` | Your Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Your Twilio Auth Token |
| `TWILIO_WHATSAPP_FROM` | Twilio sandbox number e.g. `whatsapp:+14155238886` |
| `GOOGLE_API_KEY` | Google Gemini API key |
| `USER_LANG_FILE` | Path to language store JSON (default: `user_languages.json`) |
