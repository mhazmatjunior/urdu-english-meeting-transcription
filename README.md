NLP-FYP-26: Urdu-English Meeting Transcription System

An end-to-end pipeline that transcribes Urdu and Urdu-English meeting audio, labels each speaker, corrects recognition errors, translates to English, and can read the translation aloud.

Final Year Project, Department of Software Engineering, UET Taxila (session 2022-2026).
Team: Muhammad Hassan Azmat, Wajeeha Islam, Kinza Aslam. Supervisor: Ma'am Maria.

HOW IT WORKS

Streamlit UI -> FastAPI backend -> Modal (cloud GPU): Whisper large-v3 (speech recognition) and pyannote (speaker diarization) -> Groq LLaMA 3.3 70B (Urdu correction, then English translation) -> optional English speech with facebook/mms-tts-eng on Modal.

FEATURES

- Urdu and code-mixed Urdu-English speech recognition
- Speaker labels, with editable speaker names
- Two-step correction and translation with a language model
- Filterable transcript view
- Export to JSON, plain text, and Word
- Optional English audio, timed to the original recording

SETUP

You need Python 3.10, a Groq API key, a Modal account, and a Hugging Face token that has accepted the terms for pyannote/speaker-diarization-community-1.

1. Create an environment and install:
   pip install -r requirements.txt

2. Create a file named .env in the project root:
   GROQ_API_KEY=your_key_here

3. Log in to Modal and save your Hugging Face token:
   modal setup
   modal secret create huggingface-secret HF_TOKEN=your_hf_token_here

4. Deploy the GPU services:
   modal deploy modal_asr_app.py
   modal deploy modal_tts_app.py

RUN

Terminal 1:  uvicorn fast_api:app --reload --port 8000
Terminal 2:  streamlit run ui/streamlit_app.py

Open http://localhost:8501, upload a recording, and click to transcribe.

PROJECT STRUCTURE

fast_api.py          backend API that calls the Modal services and Groq
modal_asr_app.py     speech recognition and diarization on Modal
modal_tts_app.py     text-to-speech on Modal
src/correction.py    Groq correction and translation pipeline
src/config.py        settings and API key loading
ui/streamlit_app.py  Streamlit web interface

NOTES

Never commit your .env file. Audio files and model downloads are excluded by .gitignore.

License: for academic use, UET Taxila FYP 2026.
