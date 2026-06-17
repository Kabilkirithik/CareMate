"""
CareMate Patient Device - Hybrid Setup
- Audio INPUT: Microphone on THIS computer
- Audio OUTPUT: ESP32 speaker on ANOTHER computer
"""

import streamlit as st
import requests
import os
from st_audiorec import st_audiorec
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page config
st.set_page_config(
    page_title="CareMate Patient Device",
    page_icon="🏥",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #0B3C5D;
        text-align: center;
        margin-bottom: 1rem;
    }
    .patient-info {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
    }
    .message-box {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .esp32-status {
        background: #E8F4F8;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🏥 CareMate Patient Device</div>', unsafe_allow_html=True)

# Sidebar - Patient Selection
st.sidebar.title("Patient Information")

# Patient ID input
patient_id = st.sidebar.text_input("Patient ID", value="183", key="patient_id")

# Get patient info
if patient_id:
    try:
        response = requests.get(f"{API_BASE_URL}/patients/{patient_id}/lookup", timeout=5)
        if response.status_code == 200:
            patient_data = response.json()
            patient_name = patient_data.get("name", "Unknown")
            room_id = patient_data.get("room_id", "N/A")
        else:
            patient_name = "Unknown"
            room_id = "N/A"
    except:
        patient_name = "Unknown"
        room_id = "N/A"
else:
    patient_name = "Unknown"
    room_id = "N/A"

# Display patient info
st.sidebar.markdown(f"""
<div style="background: #E8F4F8; padding: 1rem; border-radius: 10px; margin-top: 1rem;">
    <h3 style="color: #0B3C5D; margin: 0;">👤 {patient_name}</h3>
    <p style="margin: 0.5rem 0 0 0; color: #328CC1;">
        <strong>Room:</strong> {room_id}<br>
        <strong>ID:</strong> {patient_id}
    </p>
</div>
""", unsafe_allow_html=True)

# ESP32 Configuration
st.sidebar.markdown("---")
st.sidebar.subheader("🔊 Audio Output")

# Read ESP32 config from environment
esp32_receiver = os.getenv("ESP32_RECEIVER_URL", "Not configured")
if esp32_receiver != "Not configured":
    st.sidebar.success(f"**ESP32 Connected**\n\nAudio responses will be sent automatically.")
else:
    st.sidebar.info("**ESP32 Not Configured**\n\nSet ESP32_RECEIVER_URL in .env")

# Main content
st.subheader("🎤 Record Your Message")

st.info("🎙️ **Audio Input:** Input from I2S mic\n\n🔊 **Audio Output:** ESP32 speaker on another computer")

# Audio recorder
wav_audio_data = st_audiorec()

if wav_audio_data is not None:
    st.success("✓ Audio recorded! Processing...")
    
    # Save audio temporarily
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp.write(wav_audio_data)
        temp_audio_path = tmp.name
    
    # Auto-send immediately after recording
    if not patient_id:
        st.warning("Please enter a patient ID")
    else:
        with st.spinner("Processing your message..."):
            try:
                # Send voice message to API
                with open(temp_audio_path, 'rb') as audio_file:
                    files = {'file': ('audio.wav', audio_file, 'audio/wav')}
                    params = {'patient_id': patient_id}
                    
                    response = requests.post(
                        f"{API_BASE_URL}/voice",
                        files=files,
                        params=params,
                        timeout=60
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    transcript = data.get("transcript", "")
                    response_text = data.get("response_text", "")
                    intent = data.get("intent", "unknown")
                    
                    st.success(f"✓ Message sent! Intent: **{intent}**")
                    
                    # Display transcript
                    if transcript:
                        st.markdown(f"""
                        <div class="message-box">
                            <strong>📝 You said:</strong><br>
                            {transcript}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Display response
                    st.markdown(f"""
                    <div class="message-box">
                        <strong>🤖 System Response:</strong><br>
                        {response_text}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Indicate ESP32 playback
                    esp32_receiver = os.getenv("ESP32_RECEIVER_URL")
                    if esp32_receiver:
                        st.success(f"🔊 Audio response sent to ESP32 speaker")
                    else:
                        st.info("ℹ️ Configure ESP32_RECEIVER_URL in .env to enable audio output")
                    
                else:
                    st.error(f"Error: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                st.error("Request timed out. Please try again.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
            finally:
                # Clean up temp file
                if os.path.exists(temp_audio_path):
                    os.unlink(temp_audio_path)

# Text message option
st.markdown("---")
st.subheader("💬 Or Send Text Message")

message = st.text_area(
    "Type your message:",
    placeholder="e.g., 'Doctor, I have a headache'",
    height=100,
    key="text_message"
)

if st.button("📤 Send Text Message", use_container_width=True):
    if not message.strip():
        st.warning("Please enter a message")
    elif not patient_id:
        st.warning("Please enter a patient ID")
    else:
        with st.spinner("Sending message..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/chat",
                    json={"patient_id": patient_id, "message": message},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response_text", "")
                    intent = data.get("intent", "unknown")
                    
                    st.success(f"✓ Message sent! Intent: **{intent}**")
                    
                    st.markdown(f"""
                    <div class="message-box">
                        <strong>🤖 System Response:</strong><br>
                        {response_text}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if esp32_ip != "Not configured":
                        st.success(f"🔊 Audio response sent to ESP32 speaker at {esp32_ip}")
                    
                else:
                    st.error(f"Error: {response.status_code}")
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")

# Doctor messages section
st.markdown("---")
st.subheader("📬 Doctor Messages")

if st.button("🔄 Check for New Messages", use_container_width=True):
    try:
        response = requests.get(
            f"{API_BASE_URL}/patients/{patient_id}/doctor-messages",
            timeout=10
        )
        
        if response.status_code == 200:
            messages = response.json().get("messages", [])
            
            if messages:
                st.success(f"You have {len(messages)} new message(s)!")
                
                for msg in messages:
                    if msg["type"] == "text":
                        st.markdown(f"""
                        <div class="message-box">
                            <strong>👨‍⚕️ Doctor:</strong><br>
                            {msg["text"]}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    elif msg["type"] == "audio":
                        st.markdown(f"""
                        <div class="message-box">
                            <strong>👨‍⚕️ Doctor Voice Message</strong><br>
                            Audio will play on ESP32 speaker
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if esp32_ip != "Not configured":
                            st.info(f"🔊 Playing on ESP32 at {esp32_ip}")
            else:
                st.info("No new messages")
        else:
            st.error("Failed to fetch messages")
            
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p><strong>CareMate Hybrid Audio Setup</strong></p>
    <p style="font-size: 0.8rem;">
        🎙️ Input: This Computer | 🔊 Output: ESP32 Speaker
    </p>
</div>
""", unsafe_allow_html=True)
