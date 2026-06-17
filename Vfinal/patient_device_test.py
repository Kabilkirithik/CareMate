"""
CareMate Patient Device - LOCAL TESTING VERSION
- Audio INPUT:  Microphone on THIS computer
- Audio OUTPUT: THIS computer's speakers (no ESP32 needed)

Run with:
    streamlit run patient_device_test.py
"""

import streamlit as st
import requests
import os
import tempfile
import logging
from st_audiorec import st_audiorec

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="CareMate — Local Test",
    page_icon="🧪",
    layout="wide"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: bold;
        color: #0B3C5D;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .badge {
        display: inline-block;
        background: #FFF3CD;
        color: #856404;
        border: 1px solid #FFEAA7;
        border-radius: 8px;
        padding: 0.3rem 0.8rem;
        font-size: 0.8rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
    }
    .message-box {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .response-box {
        background: #E8F4F8;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #328CC1;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🧪 CareMate — Local Testing</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center"><span class="badge">🖥️ Audio plays on THIS computer</span></div>', unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.title("Patient Information")
patient_id = st.sidebar.text_input("Patient ID", value="183", key="patient_id")

patient_name, room_id = "Unknown", "N/A"
if patient_id:
    try:
        r = requests.get(f"{API_BASE_URL}/patients/{patient_id}/lookup", timeout=5)
        if r.status_code == 200:
            d = r.json()
            patient_name = d.get("name", "Unknown")
            room_id = d.get("room_id", "N/A")
    except:
        pass

st.sidebar.markdown(f"""
<div style="background:#E8F4F8;padding:1rem;border-radius:10px;margin-top:1rem;">
    <h3 style="color:#0B3C5D;margin:0;">👤 {patient_name}</h3>
    <p style="margin:0.5rem 0 0 0;color:#328CC1;">
        <strong>Room:</strong> {room_id}<br>
        <strong>ID:</strong> {patient_id}
    </p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.info("🔊 **Audio output:** This computer's speakers\n\n✅ No ESP32 required for testing")


# ── Helper: play audio in browser ────────────────────────────────────────────
def play_audio_response(audio_url: str):
    """Fetch audio from backend and play it in the Streamlit interface."""
    if not audio_url:
        return
    try:
        r = requests.get(audio_url, timeout=15)
        if r.status_code == 200:
            st.audio(r.content, format="audio/mpeg", autoplay=True)
        else:
            st.warning(f"Could not load audio (status {r.status_code})")
    except Exception as e:
        st.warning(f"Audio playback error: {e}")


# ── Section 1: Voice recording ───────────────────────────────────────────────
st.subheader("🎤 Record Your Message")
st.info("🎙️ **Input:** Microphone on this computer   🔊 **Output:** Speakers on this computer")

wav_audio_data = st_audiorec()

if wav_audio_data is not None:
    st.success("✓ Audio recorded! Sending…")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_audio_data)
        temp_path = tmp.name

    if not patient_id:
        st.warning("Please enter a patient ID")
    else:
        with st.spinner("Processing your message…"):
            try:
                with open(temp_path, "rb") as af:
                    resp = requests.post(
                        f"{API_BASE_URL}/voice",
                        files={"file": ("audio.wav", af, "audio/wav")},
                        params={"patient_id": patient_id},
                        timeout=90,
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    transcript   = data.get("transcript", "")
                    response_text = data.get("response_text", "")
                    intent        = data.get("intent", "unknown")
                    audio_url     = data.get("response_audio_url", "")

                    st.success(f"✓ Processed  |  Intent: **{intent}**")

                    if transcript:
                        st.markdown(f"""
                        <div class="message-box">
                            <strong>📝 You said:</strong><br>{transcript}
                        </div>""", unsafe_allow_html=True)

                    st.markdown(f"""
                    <div class="response-box">
                        <strong>🤖 CareMate:</strong><br>{response_text}
                    </div>""", unsafe_allow_html=True)

                    # ── Play audio on THIS computer ──
                    if audio_url:
                        st.markdown("**🔊 Playing response audio:**")
                        play_audio_response(audio_url)
                    else:
                        st.info("No audio response generated.")

                else:
                    st.error(f"API error {resp.status_code}: {resp.text[:200]}")

            except requests.exceptions.Timeout:
                st.error("Request timed out (90s). Try again.")
            except Exception as e:
                st.error(f"Error: {e}")
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)


# ── Section 2: Text message ───────────────────────────────────────────────────
st.markdown("---")
st.subheader("💬 Send Text Message")

message = st.text_area(
    "Type your message:",
    placeholder="e.g., I need water please",
    height=90,
    key="text_message",
)

if st.button("📤 Send Text Message", use_container_width=True):
    if not message.strip():
        st.warning("Please enter a message")
    elif not patient_id:
        st.warning("Please enter a patient ID")
    else:
        with st.spinner("Sending…"):
            try:
                resp = requests.post(
                    f"{API_BASE_URL}/chat",
                    json={"patient_id": patient_id, "message": message},
                    timeout=60,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    response_text = data.get("response_text", "")
                    intent        = data.get("intent", "unknown")
                    audio_url     = data.get("response_audio_url", "")

                    st.success(f"✓ Sent  |  Intent: **{intent}**")
                    st.markdown(f"""
                    <div class="response-box">
                        <strong>🤖 CareMate:</strong><br>{response_text}
                    </div>""", unsafe_allow_html=True)

                    if audio_url:
                        st.markdown("**🔊 Playing response audio:**")
                        play_audio_response(audio_url)

                else:
                    st.error(f"API error {resp.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")


# ── Section 3: Doctor messages ────────────────────────────────────────────────
st.markdown("---")
st.subheader("📬 Doctor Messages")

if st.button("🔄 Check for New Messages", use_container_width=True):
    try:
        resp = requests.get(
            f"{API_BASE_URL}/patients/{patient_id}/doctor-messages",
            timeout=10,
        )
        if resp.status_code == 200:
            messages = resp.json().get("messages", [])
            if messages:
                st.success(f"You have {len(messages)} new message(s)!")
                for msg in messages:
                    if msg.get("type") == "text":
                        st.markdown(f"""
                        <div class="message-box">
                            <strong>👨‍⚕️ Doctor:</strong><br>{msg.get("text", "")}
                        </div>""", unsafe_allow_html=True)
                    elif msg.get("type") == "audio":
                        st.markdown("""
                        <div class="message-box">
                            <strong>👨‍⚕️ Doctor Voice Message</strong>
                        </div>""", unsafe_allow_html=True)
                        audio_url = msg.get("audio_url", "")
                        if audio_url:
                            st.markdown("**🔊 Playing doctor's voice message:**")
                            play_audio_response(audio_url)
            else:
                st.info("No new messages from your doctor.")
        else:
            st.error("Failed to fetch messages")
    except Exception as e:
        st.error(f"Error: {e}")


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center;color:#666;font-size:0.85rem;">
    <strong>CareMate Local Testing Mode</strong><br>
    <span style="font-size:0.75rem;">🎙️ Input: Microphone &nbsp;|&nbsp; 🔊 Output: Browser speakers</span>
</div>
""", unsafe_allow_html=True)
