import socket
import threading
import time
import wave
import numpy as np
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse

# ================= CONFIG =================
UDP_IP = "0.0.0.0"
UDP_PORT = 3333

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = np.int16
BLOCKSIZE = 512
RECORD_SECONDS = 10

NOISE_THRESHOLD = 300
NORMALIZE_LEVEL = 0.85

WAV_FILE = "esp32_audio.wav"

app = FastAPI()

# Shared state
recorded_frames = []
is_recording = False

# ================= UDP AUDIO RECEIVER =================
def udp_audio_receiver():
    global recorded_frames, is_recording

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    print("🎧 UDP audio listener started")

    while True:
        recorded_frames.clear()
        is_recording = True
        start_time = time.time()

        print("🎙 Recording started")

        while time.time() - start_time < RECORD_SECONDS:
            data, _ = sock.recvfrom(2048)
            audio = np.frombuffer(data, dtype=DTYPE)
            recorded_frames.append(audio)

        is_recording = False
        print("🛑 Recording finished")

        process_and_save_wav()

# ================= AUDIO PROCESSING =================
def process_and_save_wav():
    audio = np.concatenate(recorded_frames)

    # Noise gate
    audio[np.abs(audio) < NOISE_THRESHOLD] = 0

    # Normalize
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = (audio / peak * (32767 * NORMALIZE_LEVEL)).astype(np.int16)

    with wave.open(WAV_FILE, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

    print(f"✅ WAV saved: {WAV_FILE}")

# ================= HTTP STREAM ENDPOINT =================
@app.get("/audio")
def get_audio():
    with open(WAV_FILE, "rb") as f:
        data = f.read()

    return Response(
        content=data,
        media_type="audio/wav",
        headers={
            "Content-Disposition": "inline; filename=esp32_audio.wav"
        }
    )

# ================= START UDP THREAD =================
@app.on_event("startup")
def start_udp_thread():
    thread = threading.Thread(target=udp_audio_receiver, daemon=True)
    thread.start()