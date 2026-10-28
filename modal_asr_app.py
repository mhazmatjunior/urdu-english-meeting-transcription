"""
STEP 3 — ASR + Diarization ko Modal pe deploy karna.

Yeh file aap ke `asr_pipeline.py` (ASRDiarizationPipeline) ka
Modal version hai. Naye concepts:

1. modal.Image  — batata hai Modal ko is code ko chalane ke liye
   kaunse packages chahiye (jaise requirements.txt, lekin code
   ke andar).
2. @app.cls(gpu="T4", ...) — Modal ko batata hai "is class ko
   GPU machine pe chalao".
3. @modal.enter() — models yahan load hote hain, SIRF EK DAFA
   jab container start hota hai (Colab mein hum ne yeh __init__
   mein kiya tha — concept wahi hai).
4. @modal.method() — yeh wo function hai jise hum "remotely"
   call kar sakte hain, jaisay ek normal function call, lekin
   asal mein yeh cloud GPU pe chal raha hota hai.
5. audio ab "path" nahi, "bytes" leta hai — kyunke Modal ka
   container humare local machine ka filesystem nahi dekh sakta,
   isliye humein file ka actual content bhejna padta hai.

Deploy karne ke liye (terminal mein):
    modal deploy modal_asr_app.py

Test karne ke liye (bina deploy kiye, seedha run karke):
    modal run modal_asr_app.py --audio-path sample_audio/test.wav
"""

import modal

app = modal.App("nlp-fyp-asr")

# Yeh "image" batata hai Modal ko ke container mein kya install
# hona chahiye — bilkul waisay jaisay Colab mein !pip install
# karte thay, bas ab yeh ek dafa build hota hai.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")  # video/audio conversion ke liye system tool
    .pip_install(
        "faster-whisper",
        "pyannote.audio",
        "torch",
        "huggingface_hub",
        "soundfile",
        "onnxruntime",
        # faster-whisper (ctranslate2) ko specifically CUDA 12 wali
        # cuBLAS/cuDNN chahiye — torch apne saath CUDA 13 wali le aata
        # hai, isliye yeh cu12 wali alag se maangni padti hain.
        "nvidia-cublas-cu12",
        "nvidia-cudnn-cu12==9.*",
    )
    # ctranslate2 ko batana ke CUDA 12 wali libraries kahan hain
    .env(
        {
            "LD_LIBRARY_PATH": (
                "/usr/local/lib/python3.11/site-packages/nvidia/cublas/lib:"
                "/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib"
            )
        }
    )
)


@app.cls(
    gpu="T4",
    image=image,
    secrets=[modal.Secret.from_name("huggingface-secret")],
    timeout=600,  # pehli dafa model download hone mein waqt lagta hai
)
class ASRService:
    @modal.enter()
    def load_models(self):
        import os

        import torch
        from faster_whisper import WhisperModel
        from huggingface_hub import login
        from pyannote.audio import Pipeline

        login(token=os.environ["HF_TOKEN"])

        print("Loading Whisper large-v3...")
        self.whisper_model = WhisperModel(
            "large-v3", device="cuda", compute_type="float16"
        )

        print("Loading Pyannote pipeline...")
        self.diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-community-1", token=True
        )
        self.diarization_pipeline.to(torch.device("cuda"))
        print("Models loaded — ready for requests.")

    @modal.method()
    def run(self, audio_bytes: bytes, filename: str = "audio.wav") -> dict:
        import os
        import subprocess
        import tempfile

        # Audio bytes ko temporary file mein likhna — yeh original
        # format mein hai (mp4, m4a, mp3, wav — kuch bhi ho sakta hai).
        suffix = os.path.splitext(filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            original_path = tmp.name

        # Chahay input mp4/video ho ya koi bhi audio format, hum ise
        # hamesha ek standard 16kHz mono WAV mein convert kar dete hain.
        # Isse Whisper aur Pyannote dono ko hamesha same, predictable
        # format milta hai — bilkul waisay jaisay humne pehle manually
        # `ffmpeg` command se kiya tha, ab yeh khud-ba-khud hota hai.
        audio_path = original_path + "_converted.wav"
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", original_path,
                "-ar", "16000", "-ac", "1",
                audio_path,
            ],
            check=True,
        )

        try:
            segments_gen, _ = self.whisper_model.transcribe(
                audio_path,
                language="ur",
                beam_size=5,
                vad_filter=True,
                initial_prompt="یہ ایک اردو میٹنگ ہے۔ لوگ Urdu اور English میں بات کر رہے ہیں۔",
                vad_parameters=dict(max_speech_duration_s=15),
            )
            segments = [
                {"start": s.start, "end": s.end, "text": s.text.strip()}
                for s in segments_gen
            ]

            # Pyannote ko seedha file path dene ki jagah, hum audio khud
            # "soundfile" se parh ke waveform (numbers) ki shakal mein
            # dete hain — isse torchcodec/ffmpeg ki zarurat hi nahi rehti.
            import soundfile as sf
            import torch as _torch

            waveform_np, sample_rate = sf.read(
                audio_path, dtype="float32", always_2d=True
            )
            waveform_tensor = _torch.from_numpy(waveform_np.T)  # (channels, time)

            diarization_output = self.diarization_pipeline(
                {"waveform": waveform_tensor, "sample_rate": sample_rate}
            )
            diarization_segments = list(diarization_output.speaker_diarization)

            for seg in segments:
                speaker = None
                best_overlap = 0
                for turn, spk in diarization_segments:
                    overlap = max(
                        0, min(seg["end"], turn.end) - max(seg["start"], turn.start)
                    )
                    if overlap > best_overlap:
                        best_overlap = overlap
                        speaker = spk
                if speaker is None:
                    seg_mid = (seg["start"] + seg["end"]) / 2
                    nearest = min(
                        diarization_segments,
                        key=lambda x: abs((x[0].start + x[0].end) / 2 - seg_mid),
                    )
                    speaker = nearest[1]
                try:
                    spk_num = int(speaker.split("_")[-1]) + 1
                    seg["speaker"] = f"SPEAKER_{spk_num}"
                except Exception:
                    seg["speaker"] = speaker

            return {"segments": segments}
        finally:
            os.remove(original_path)
            if os.path.exists(audio_path):
                os.remove(audio_path)


# Yeh function AAP KE LOCAL machine pe chalta hai, lekin jab
# `service.run.remote(...)` call karta hai, wo call cloud GPU pe
# jaake chalta hai — bilkul waisay jaisay hum ne /process route
# se AdvancedCorrectionPipeline ko call kiya tha.
@app.local_entrypoint()
def main(audio_path: str):
    import json
    from pathlib import Path

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    service = ASRService()
    result = service.run.remote(audio_bytes, filename=audio_path)

    Path("output").mkdir(exist_ok=True)

    # Poori raw JSON save karna — pehle sirf 3 segments print ho
    # rahe thay, ab saari (14) segments file mein save hongi.
    with open("output/asr_raw_output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(
        f"Raw ASR output saved: output/asr_raw_output.json "
        f"({len(result['segments'])} segments)"
    )

    # Ab yeh raw output correction.py (Groq) se guzarte hain —
    # yeh hissa AAP KE LOCAL machine pe chalta hai, Modal ke
    # GPU container mein nahi (isliye .env wali GROQ key yahan
    # se hi uthegi, jo pehle se kaam kar rahi hai).
    from src.correction import AdvancedCorrectionPipeline

    print("\nRunning correction + translation on each segment...")
    pipeline = AdvancedCorrectionPipeline()
    for seg in result["segments"]:
        correction_result = pipeline.correct_segment_advanced(
            seg["text"], speaker=seg.get("speaker", "")
        )
        seg.update(correction_result)

    with open("output/final_corrected_output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("Final corrected output saved: output/final_corrected_output.json")

    print("\nSample (first 3 segments, corrected):")
    for seg in result["segments"][:3]:
        print(f"[{seg['speaker']}] {seg.get('corrected_text', seg['text'])[:60]}")