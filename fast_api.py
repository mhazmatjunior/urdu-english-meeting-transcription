from fastapi import FastAPI, UploadFile, File
import modal
from src.correction import AdvancedCorrectionPipeline

import io
import numpy as np
import soundfile as sf
from fastapi.responses import Response

app = FastAPI()
pipeline = AdvancedCorrectionPipeline()

# Deployed Modal service ko "dhoondhna" — dobara deploy nahi karna
asr_service = modal.Cls.from_name("nlp-fyp-asr", "ASRService")()
tts_service = modal.Cls.from_name("nlp-fyp-tts", "TTSService")()

@app.get("/")
def welcome():
    return {"message": "Welcome to the ASR + Correction API. Use /transcribe to upload audio and get corrected text."}

@app.post("/process")
def process_text(payload: dict):
    raw_text = payload.get("text", "")
    return pipeline.correct_segment_advanced(raw_text)

@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()

    # Step 1: Modal (cloud GPU) se ASR + diarization karwana
    asr_result = await asr_service.run.remote.aio(audio_bytes, filename=audio.filename)

    # Step 2: Har segment ko Groq se correction/translation ke liye guzarna
    for seg in asr_result["segments"]:
        correction_result = pipeline.correct_segment_advanced(
            seg["text"], speaker=seg.get("speaker", "")
        )
        seg.update(correction_result)

    return asr_result   

@app.post("/synthesize")
async def synthesize(payload: dict):
    segments = payload.get("segments", [])
    sample_rate = 16000
    all_audio = []

    for seg in segments:
        text = seg.get("translation_en", "")
        if not text.strip():
            continue
        duration = seg.get("end", 0) - seg.get("start", 0)

        audio_bytes = await tts_service.synthesize.remote.aio(text, target_duration=duration)
        if audio_bytes:
            audio_np, _ = sf.read(io.BytesIO(audio_bytes))
            all_audio.append(audio_np)

    if not all_audio:
        return Response(content=b"", media_type="audio/wav")

    final_audio = np.concatenate(all_audio)
    buffer = io.BytesIO()
    sf.write(buffer, final_audio, sample_rate, format="WAV")

    return Response(content=buffer.getvalue(), media_type="audio/wav")