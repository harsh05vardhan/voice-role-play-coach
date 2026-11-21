# Real-Time Voice AI Role-Play Coach

Practice sales conversations by voice against an AI customer, then get a scored evaluation.

**Stack:** Python, FastAPI, WebSockets, React (Vite), Groq (GPT-OSS 120B LLM + Whisper STT), edge-tts (TTS), MongoDB.

## Architecture
```
React (mic -> MediaRecorder)
   | binary audio over WebSocket
   v
FastAPI /ws/{session_id}
   1. Whisper (Groq)      speech -> text
   2. MongoDB             load session history (memory)
   3. GPT-OSS 120B (Groq)    streamed in-character reply
   4. edge-tts            each finished sentence -> MP3 (in parallel with generation)
   5. MongoDB             save the turn
   | reply_text + MP3 per sentence
   v
React plays audio queue
```
REST endpoints: `GET /api/options`, `POST /api/sessions`, `GET /api/sessions/{id}`, `POST /api/sessions/{id}/evaluate`.

## Setup
Prerequisites: Python 3.10+, Node 18+, a free Groq API key (https://console.groq.com), MongoDB (local, or a free Atlas cluster). Without MongoDB the app still runs using in-memory storage (data is lost on restart).

**Backend**
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then put your GROQ_API_KEY in .env
uvicorn main:app --reload
```

**Frontend** (second terminal)
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. Microphone access works on `localhost` (browsers require HTTPS elsewhere).

## Notes and limits
- Groq's free tier is rate limited; heavy use may return 429 errors. edge-tts is an unofficial free service and may change or be blocked, so it isn't guaranteed for production.
- Push-to-talk (click Speak, click Stop) rather than continuous voice-activity detection.
- No user accounts or auth: anyone with a session id can read that session. Not production-ready.
