# NLP-FYP-26 — Urdu-English Meeting Transcription System

An end-to-end pipeline that transcribes Urdu/code-mixed meeting audio,
identifies speakers, corrects ASR errors, and translates to English.

**FYP Mates:** Muhammad Hassan Azmat(22-CS-15), Wajeeha Islam (22-SE-18), Kinza Aslam (22-SE-76)  
**Supervisor:** Ma'am Maria · **Session:** 2022–2026, UET Taxila

---

## Architecture

```
┌─────────────────────────────────┐     ┌──────────────────────────────────┐
│      MODAL (GPU, cloud)         │     │        LOCAL MACHINE             │
│                                 │     │                                  │
│  ASRService                     │     │  Streamlit UI                    │
│    Whisper large-v3 (ASR)       │     │      ↓                           │
│    Pyannote (Diarization)       │──→──│  fast_api.py                     │
│                                 │     │      ↓                           │
│  TTSService                     │←──→─│  Correction + Translation        │
│    facebook/mms-tts-eng         │     │  (Groq LLaMA-3.3-70B)            │
│                                 │     │      ↓                           │
│                                 │     │  transcript.txt + audio          │
└─────────────────────────────────┘     └──────────────────────────────────┘
```

---

## Prerequisites

- Python 3.10
- Miniconda or Anaconda
- 8GB RAM
- 5GB disk space
- Groq API key (free tier: groq.com)
- Modal account (modal.com) — free signup, gives monthly free GPU credit
- Hugging Face account + access token, with the gated `pyannote/speaker-diarization-community-1` model terms accepted

---

## Installation

**1. Clone or download project**
```bash
cd NLP_FYP_26
```

**2. Create conda environment**
```bash
conda create -n fyp python=3.10
conda activate fyp
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Setup API key**

Create a `.env` file in the project root:
```
GROQ_API_KEY=your_key_here
```

**5. Authenticate with Modal**
```bash
modal setup
```
This opens a browser to link the CLI to your Modal account.

**6. Create a Modal secret for Hugging Face**

The ASR service needs an HF token to download the gated Pyannote diarization model:
```bash
modal secret create huggingface-secret HF_TOKEN=your_hf_token_here
```

**7. Deploy the Modal services** (one-time, or whenever `modal_asr_app.py` / `modal_tts_app.py` change)
```bash
modal deploy modal_asr_app.py
modal deploy modal_tts_app.py
```

---

## Usage

### Step 1 — Start the backend

```bash
conda activate fyp
uvicorn fast_api:app --reload --port 8000
```

This local server routes requests to your deployed Modal services (`ASRService`, `TTSService`) and to Groq for correction/translation. Check `http://127.0.0.1:8000/docs` to confirm all routes (`/transcribe`, `/synthesize`) are live.

---

### Step 2 — Start the Streamlit UI

In a second terminal:
```bash
conda activate fyp
streamlit run ui/streamlit_app.py
```

Open: **http://localhost:8501**

Then:
1. Upload an audio file directly in the UI (WAV/MP3/MP4/M4A/OGG)
2. Click **"New Transcription"** — this calls `/transcribe`, which runs ASR + diarization on Modal, then correction + translation via Groq
3. Rename speakers, filter, or toggle translation as needed
4. Download `transcript.txt`, `results.json`, or the Word doc
5. Optional: click **"🔊 Generate Audio"** — calls `/synthesize`, which runs TTS on Modal

No manual file downloads or notebook steps required — everything happens live over the two running servers.

---

## Project Structure

```
NLP_FYP_26/
│
├── src/
│   ├── __init__.py
│   ├── config.py               # Configs + API key loading
│   └── correction.py           # Groq LLaMA correction + translation
│
├── fast_api.py                 # Backend API (routes to Modal ASR/TTS)
├── modal_asr_app.py            # ASR + diarization, deployed on Modal
├── modal_tts_app.py            # TTS, deployed on Modal
│
├── ui/
│   └── streamlit_app.py        # Streamlit UI
│
├── data/
│   └── output/                 # Generated outputs
│
├── requirements.txt
├── .env                        # API key (NOT committed to git)
└── README.md
```

---

## Key Components

### ASR + Diarization (Modal — `modal_asr_app.py`)
- ASR: `Whisper large-v3` on a Modal-hosted T4 GPU, language: Urdu
- Diarization: `Pyannote` (pyannote/speaker-diarization-community-1)
- Deployed once (`modal deploy modal_asr_app.py`), invoked live via RPC from `fast_api.py`
- Returns timestamped, speaker-labelled segments directly — no intermediate file

### Text Correction & Translation (Local — `src/correction.py`)
- API: `Groq` (llama-3.3-70b-versatile)
- Two separate calls: Call 1 corrects Urdu ASR errors, Call 2 translates to English
- Handles: ASR errors, code-mixing, Urdu-English transliteration
- Rate limiting: Auto-retry with backoff

### Text-to-Speech (Modal — `modal_tts_app.py`)
- Model: `facebook/mms-tts-eng`
- Deployed once (`modal deploy modal_tts_app.py`), invoked live via RPC from `fast_api.py`
- Input: English translation per segment
- Output: Timestamp-aligned WAV audio

---

## Project Status

- [x] Conda environment setup
- [x] API key secured
- [x] ASR + Diarization deployed on Modal (Whisper + Pyannote)
- [x] TTS deployed on Modal (facebook/mms-tts-eng)
- [x] FastAPI backend routing to Modal + Groq
- [x] Correction + Translation (2-step Groq pipeline)
- [x] Streamlit UI
- [x] Speaker merging (consecutive turns → paragraphs)
- [x] Speaker renaming in UI (now reflected in Word doc export too)
- [x] results.json + transcript.txt + Word doc download
- [x] End-to-end tested with real audio
- [x] Evaluation metrics (WER, DER)
- [x] Final report

---

## Troubleshooting

### API Key Issues
```
ValueError: GROQ_API_KEY not found in .env file
```
- Verify `.env` is in project root (not inside `src/`)
- Format: `GROQ_API_KEY=gsk_xxxxxxxxxxxx` (no quotes, no spaces)
- Check key at console.groq.com

### Memory Issues
- Close other applications before running TTS
- Use Colab for audio longer than 30 minutes

### Audio Format Issues
- Supported in Colab: WAV, MP3, MP4, M4A, OGG
- Manual conversion: `ffmpeg -i input.mp3 -acodec pcm_s16le -ar 16000 output.wav`

### Colab Disconnect
- Free Colab sessions last ~1–2 hours
- Upload audio → immediately run all cells → download output before session ends

---

## Authors

- **Muhammad Hassan Azmat**(22-CS-15)
- **Wajeeha Islam** (22-SE-18)
- **Kinza Aslam** (22-SE-76)

**Supervisor:** Ma'am Maria  
**Department:** Software Engineering, UET Taxila  
**Session:** 2022–2026

---

## Notes

- Never commit `.env` to git — add it to `.gitignore`
- For demo/viva: run Colab first, then Streamlit locally

## License

For academic use only — UET Taxila FYP 2026.