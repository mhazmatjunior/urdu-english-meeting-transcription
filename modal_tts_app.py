"""
TTS (facebook/mms-tts-eng) ko Modal pe deploy karna — bilkul wahi
pattern jo humne ASR (modal_asr_app.py) ke liye use kiya tha.

Farac sirf itna: is model ko Hugging Face token/login nahi chahiye
(public model hai), isliye setup thora simpler hai.

Deploy karne ke liye:
    modal deploy modal_tts_app.py

Standalone test (deploy se pehle, sirf yeh check karne ke liye ke
sab sahi kaam kar raha hai):
    modal run modal_tts_app.py --text "Hello, this is a test."
"""

import modal

app = modal.App("nlp-fyp-tts")

image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "torch",
    "transformers",
    "soundfile",
    "numpy",
)

@app.cls(gpu="T4", image=image, timeout=300)
class TTSService:
    @modal.enter()
    def load_model(self):
        import torch
        from transformers import AutoTokenizer, VitsModel

        model_name = "facebook/mms-tts-eng"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.sample_rate = 16000

        print(f"Loading TTS model ({model_name})...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = VitsModel.from_pretrained(model_name).to(self.device)
        self.model.eval()
        print("TTS model loaded — ready for requests.")

    def _chunk_text(self, text: str) -> list:
        # Lambi text ko sentence-boundary pe todna — isse data loss
        # nahi hota (aap ke original tts.py mein bhi yehi tha).
        import re

        if not text or not text.strip():
            return []
        chunks = re.split(r"(?<=[.!?])\s+", text)
        return [c.strip() for c in chunks if c.strip()]

    @modal.method()
    def synthesize(self, text: str, target_duration: float = 0.0) -> bytes:
        import io

        import numpy as np
        import soundfile as sf
        import torch

        chunks = self._chunk_text(text)
        if not chunks:
            return b""

        full_audio = []
        for chunk in chunks:
            inputs = self.tokenizer(chunk, return_tensors="pt").to(self.device)
            with torch.no_grad():
                output = self.model(**inputs)
            full_audio.append(output.waveform[0].cpu().numpy())

        if not full_audio:
            return b""

        audio = np.concatenate(full_audio)
        if len(audio) < 1000:
            return b""

        # Original segment ki duration se match karna — agar English
        # audio chota hai to silence se pad kar dete hain (lamba hai
        # to waisay hi rehne dete hain, kaat-na trim karna ajeeb lagta hai)
        if target_duration and target_duration > 0:
            target_samples = int(target_duration * self.sample_rate)
            actual_samples = len(audio)
            if actual_samples < target_samples:
                padding = np.zeros(target_samples - actual_samples, dtype=audio.dtype)
                audio = np.concatenate([audio, padding])

        # Numpy array ki jagah WAV bytes wapas bhejna — isse local
        # machine aur Modal container ke numpy version match karne ki
        # zarurat khatam ho jaati hai (bytes hamesha safe hote hain).
        buffer = io.BytesIO()
        sf.write(buffer, audio, self.sample_rate, format="WAV")
        return buffer.getvalue()

@app.local_entrypoint()
def main(text: str = "Hello, this is a test of the text to speech system."):
    from pathlib import Path

    service = TTSService()
    audio_bytes = service.synthesize.remote(text)

    if not audio_bytes:
        print("Koi audio generate nahi hui.")
        return

    Path("output").mkdir(exist_ok=True)
    with open("output/tts_test.wav", "wb") as f:
        f.write(audio_bytes)
    print(f"Saved: output/tts_test.wav ({len(audio_bytes)} bytes)")