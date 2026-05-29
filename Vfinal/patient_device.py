#!/usr/bin/env python3
"""
CareMate Patient Device Interface
Complete Streamlit app that acts as a patient bedside device.
Can send voice messages and receive doctor responses.
"""
import streamlit as st
import requests
import tempfile
import os
import time
import json
from datetime import datetime
from audio_recorder_streamlit import audio_recorder
import threading
import queue

# Configure Streamlit page
st.set_page_config(
    page_title="CareMate Patient Device",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CareMate Design System ────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,300;1,9..40,400&family=DM+Mono:wght@400;500&display=swap');

/* ── CSS Variables ── */
:root {
  --primary:            #0B3C5D;
  --primary-light:      #0e4d78;
  --secondary:          #328CC1;
  --accent:             #69D2E7;
  --success:            #2EC4B6;
  --warning:            #FF9F1C;
  --destructive:        #D90429;

  --bg:                 #f7f9fc;
  --card:               #ffffff;
  --muted-bg:           #eef2f7;
  --muted-fg:           #6b7fa3;
  --border:             #dce5f0;
  --fg:                 #1a2e45;
  --fg-light:           #4a607a;

  --radius-sm:          10px;
  --radius-md:          14px;
  --radius-lg:          18px;
  --radius-xl:          22px;

  --shadow-soft:        0 1px 3px rgba(11,60,93,0.06), 0 8px 24px -12px rgba(11,60,93,0.14);
  --shadow-elevated:    0 4px 16px -2px rgba(11,60,93,0.10), 0 24px 48px -16px rgba(11,60,93,0.18);
  --shadow-glow:        0 0 0 1px rgba(50,140,193,0.22), 0 8px 32px -4px rgba(50,140,193,0.32);

  --font: 'DM Sans', ui-sans-serif, system-ui, sans-serif;
  --font-mono: 'DM Mono', ui-monospace, monospace;
  --ease: cubic-bezier(0.16, 1, 0.3, 1);
}

/* ── Base Reset ── */
html, body, [data-testid="stAppViewContainer"] {
  font-family: var(--font) !important;
  background: var(--bg) !important;
  color: var(--fg) !important;
  -webkit-font-smoothing: antialiased;
}

[data-testid="stAppViewContainer"] > .main {
  background: var(--bg) !important;
}

[data-testid="stSidebar"] {
  background: #ffffff !important;
  border-right: 1px solid var(--border) !important;
}

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }

/* ── Hero Banner ── */
.cm-hero {
  background: linear-gradient(135deg, #0B3C5D 0%, #1a6090 50%, #328CC1 85%, #69D2E7 100%);
  padding: 2.4rem 2.8rem;
  border-radius: var(--radius-xl);
  margin-bottom: 2rem;
  display: flex;
  align-items: center;
  gap: 1.6rem;
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-elevated);
}
.cm-hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at top left, rgba(105,210,231,0.28) 0%, transparent 55%),
              radial-gradient(ellipse at bottom right, rgba(46,196,182,0.18) 0%, transparent 55%);
}
.cm-hero-icon {
  font-size: 3rem;
  filter: drop-shadow(0 4px 12px rgba(0,0,0,0.25));
  position: relative;
  z-index: 1;
  animation: float-soft 4s ease-in-out infinite;
}
.cm-hero-text { position: relative; z-index: 1; }
.cm-hero-title {
  font-size: 2rem;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
  letter-spacing: -0.02em;
  line-height: 1.15;
}
.cm-hero-sub {
  font-size: 1rem;
  color: rgba(255,255,255,0.82);
  margin: 0.25rem 0 0 0;
  font-weight: 400;
  letter-spacing: 0.01em;
}

@keyframes float-soft {
  0%, 100% { transform: translateY(0px); }
  50%       { transform: translateY(-6px); }
}

/* ── Section Header ── */
.cm-section-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 1rem;
  font-weight: 600;
  color: var(--primary);
  letter-spacing: -0.01em;
  margin-bottom: 1rem;
  padding-bottom: 0.6rem;
  border-bottom: 2px solid var(--accent);
}
.cm-section-header span { font-size: 1.15rem; }

/* ── Cards ── */
.cm-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1.4rem 1.6rem;
  box-shadow: var(--shadow-soft);
  margin-bottom: 1rem;
  transition: box-shadow 0.3s var(--ease);
}
.cm-card:hover { box-shadow: var(--shadow-elevated); }

/* ── Message Bubbles ── */
.cm-msg-patient {
  background: linear-gradient(135deg, #eef8fb 0%, #e0f4f8 100%);
  border: 1px solid rgba(105,210,231,0.35);
  border-left: 3px solid var(--accent);
  border-radius: var(--radius-md);
  padding: 0.85rem 1.1rem;
  margin: 0.45rem 0;
  font-size: 0.9rem;
  color: var(--fg);
}
.cm-msg-patient .cm-msg-label {
  font-weight: 600;
  color: var(--secondary);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 0.3rem;
}
.cm-msg-doctor {
  background: linear-gradient(135deg, #f0faf9 0%, #e4f7f5 100%);
  border: 1px solid rgba(46,196,182,0.3);
  border-left: 3px solid var(--success);
  border-radius: var(--radius-md);
  padding: 0.85rem 1.1rem;
  margin: 0.45rem 0;
  font-size: 0.9rem;
  color: var(--fg);
}
.cm-msg-doctor .cm-msg-label {
  font-weight: 600;
  color: var(--success);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 0.3rem;
}
.cm-msg-time {
  font-size: 0.72rem;
  color: var(--muted-fg);
  font-family: var(--font-mono);
  margin-left: 0.5rem;
}

/* ── Patient Info Badge ── */
.cm-patient-badge {
  background: linear-gradient(135deg, #eef8fb, #e4f7f5);
  border: 1px solid rgba(50,140,193,0.25);
  border-radius: var(--radius-md);
  padding: 0.85rem 1rem;
  margin: 0.6rem 0;
}
.cm-patient-badge .cm-badge-name {
  font-weight: 700;
  font-size: 0.98rem;
  color: var(--primary);
}
.cm-patient-badge .cm-badge-meta {
  font-size: 0.78rem;
  color: var(--muted-fg);
  font-family: var(--font-mono);
  margin-top: 0.15rem;
}

/* ── Status Bar ── */
.cm-status-ok {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: rgba(46,196,182,0.12);
  border: 1px solid rgba(46,196,182,0.35);
  color: #1a8a7f;
  padding: 0.35rem 0.85rem;
  border-radius: 100px;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.04em;
}
.cm-status-ok::before {
  content: '';
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 0 2px rgba(46,196,182,0.3);
  animation: pulse-dot 2s ease-in-out infinite;
}

.cm-status-err {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: rgba(217,4,41,0.08);
  border: 1px solid rgba(217,4,41,0.28);
  color: var(--destructive);
  padding: 0.35rem 0.85rem;
  border-radius: 100px;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.04em;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}

/* ── Divider ── */
.cm-divider {
  border: none;
  border-top: 1px solid var(--border);
  margin: 1.2rem 0;
}

/* ── Empty State ── */
.cm-empty {
  text-align: center;
  padding: 2.5rem 1rem;
  color: var(--muted-fg);
  font-size: 0.9rem;
}
.cm-empty-icon { font-size: 2.4rem; margin-bottom: 0.6rem; opacity: 0.55; }

/* ── Streamlit widget overrides ── */
[data-testid="stTextInput"] input {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  font-family: var(--font) !important;
  color: var(--fg) !important;
  background: var(--card) !important;
  padding: 0.55rem 0.85rem !important;
  box-shadow: none !important;
  transition: border-color 0.25s var(--ease), box-shadow 0.25s var(--ease) !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: var(--secondary) !important;
  box-shadow: var(--shadow-glow) !important;
}

[data-testid="stButton"] > button {
  font-family: var(--font) !important;
  font-weight: 600 !important;
  border-radius: var(--radius-md) !important;
  border: 1px solid var(--border) !important;
  background: var(--card) !important;
  color: var(--primary) !important;
  padding: 0.5rem 1.1rem !important;
  transition: all 0.25s var(--ease) !important;
  box-shadow: var(--shadow-soft) !important;
}
[data-testid="stButton"] > button:hover {
  background: var(--muted-bg) !important;
  border-color: var(--secondary) !important;
  box-shadow: var(--shadow-glow) !important;
  transform: translateY(-1px) !important;
}

/* Primary button */
[data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%) !important;
  color: #ffffff !important;
  border: none !important;
  box-shadow: 0 4px 14px -2px rgba(11,60,93,0.38) !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
  box-shadow: 0 6px 20px -2px rgba(11,60,93,0.48) !important;
  transform: translateY(-2px) !important;
}

/* Alerts */
[data-testid="stAlert"] {
  border-radius: var(--radius-md) !important;
  font-family: var(--font) !important;
  border: none !important;
}
[data-testid="stAlert"][data-baseweb="notification"] {
  box-shadow: var(--shadow-soft) !important;
}

/* Audio player */
audio {
  width: 100%;
  border-radius: var(--radius-sm);
  accent-color: var(--secondary);
}

/* Spinner */
[data-testid="stSpinner"] { color: var(--secondary) !important; }

/* Subheader → hidden, replaced by cm-section-header */
h2, h3 { 
  font-family: var(--font) !important; 
  color: var(--primary) !important;
  letter-spacing: -0.02em !important;
}

/* Sidebar labels */
[data-testid="stSidebar"] label {
  font-family: var(--font) !important;
  font-size: 0.82rem !important;
  font-weight: 600 !important;
  color: var(--muted-fg) !important;
  text-transform: uppercase !important;
  letter-spacing: 0.06em !important;
}

/* Sidebar header */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
  font-size: 1rem !important;
  color: var(--primary) !important;
}

/* Code blocks */
code { 
  font-family: var(--font-mono) !important;
  background: var(--muted-bg) !important;
  border-radius: 6px !important;
  padding: 0.15em 0.45em !important;
  font-size: 0.85em !important;
  color: var(--primary) !important;
}

/* Activity log area */
[data-testid="stMarkdownContainer"] {
  font-family: var(--font) !important;
}

hr { border-color: var(--border) !important; }

/* Column gap */
[data-testid="stHorizontalBlock"] { gap: 1.5rem !important; }

/* Sidebar divider */
[data-testid="stSidebar"] hr { border-color: var(--border) !important; }
</style>
""", unsafe_allow_html=True)

# API Configuration
API_BASE_URL = "http://localhost:8000"

def init_session_state():
    """Initialize session state variables"""
    if 'patient_id' not in st.session_state:
        st.session_state.patient_id = "183"
    if 'patient_name' not in st.session_state:
        st.session_state.patient_name = ""
    if 'room_id' not in st.session_state:
        st.session_state.room_id = ""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'last_check' not in st.session_state:
        st.session_state.last_check = datetime.now()
    if 'lookup_done' not in st.session_state:
        st.session_state.lookup_done = False

def lookup_patient(patient_id: str):
    """Auto-lookup patient name and room from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/patients/{patient_id}/lookup", timeout=5)
        if response.status_code == 200:
            data = response.json()
            st.session_state.patient_name = data.get("name", "Unknown")
            st.session_state.room_id = data.get("room_id", "N/A")
            st.session_state.lookup_done = True
            return True
        else:
            st.session_state.patient_name = f"Patient {patient_id}"
            st.session_state.room_id = "N/A"
            return False
    except Exception:
        st.session_state.patient_name = f"Patient {patient_id}"
        return False

def send_voice_to_caremate(audio_bytes, patient_id, patient_name=None):
    """Send voice message to CareMate API with extended timeout"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file_path = tmp_file.name

        url = f"{API_BASE_URL}/voice"
        params = {"patient_id": patient_id}
        if patient_name:
            params["patient_name"] = patient_name

        with open(tmp_file_path, "rb") as audio_file:
            files = {"file": ("recording.wav", audio_file, "audio/wav")}
            response = requests.post(url, files=files, params=params, timeout=90)

        return response

    finally:
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)

def check_doctor_messages(patient_id):
    """Check for new doctor messages"""
    try:
        response = requests.get(f"{API_BASE_URL}/patients/{patient_id}/doctor-messages", timeout=5)
        if response.status_code == 200:
            return response.json().get('messages', [])
    except Exception as e:
        st.error(f"Error checking doctor messages: {e}")
    return []

def check_api_health():
    """Check if API server is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    init_session_state()

    # ── Hero Banner ──────────────────────────────────────────────────────────
    st.markdown("""
    <div class="cm-hero">
      <div class="cm-hero-icon">🏥</div>
      <div class="cm-hero-text">
        <p class="cm-hero-title">CareMate Patient Device</p>
        <p class="cm-hero-sub">Voice-First Hospital Assistant</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── API Health Check ─────────────────────────────────────────────────────
    api_ok = check_api_health()
    if api_ok:
        st.markdown('<span class="cm-status-ok">API Connected</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="cm-status-err">⚠ API Offline</span>', unsafe_allow_html=True)
        st.error("CareMate API server is not running. Please start the server first.")
        st.code("cd Vfinal && python api.py")
        return

    st.markdown("<div style='margin-bottom:1.5rem'></div>", unsafe_allow_html=True)

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style="padding:0.6rem 0 1rem 0;">
          <div style="font-size:1.05rem;font-weight:700;color:#0B3C5D;letter-spacing:-0.01em;">
            📟 Bedside Device
          </div>
          <div style="font-size:0.75rem;color:#6b7fa3;margin-top:0.2rem;">
            Patient identification
          </div>
        </div>
        """, unsafe_allow_html=True)

        new_patient_id = st.text_input("Patient ID", value=st.session_state.patient_id)

        if new_patient_id != st.session_state.patient_id or not st.session_state.lookup_done:
            st.session_state.patient_id = new_patient_id
            if new_patient_id:
                with st.spinner("Looking up patient…"):
                    found = lookup_patient(new_patient_id)
                if found:
                    st.success(f"✅ {st.session_state.patient_name} — Room {st.session_state.room_id}")
                else:
                    st.warning("Patient not found in database")

        if st.session_state.patient_name and st.session_state.patient_name != f"Patient {st.session_state.patient_id}":
            st.markdown(f"""
            <div class="cm-patient-badge">
              <div class="cm-badge-name">👤 {st.session_state.patient_name}</div>
              <div class="cm-badge-meta">Room {st.session_state.room_id} &nbsp;·&nbsp; ID {st.session_state.patient_id}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<hr class="cm-divider">', unsafe_allow_html=True)

        if st.button("🔄 Check for Doctor Messages"):
            messages = check_doctor_messages(st.session_state.patient_id)
            if messages:
                st.success(f"Found {len(messages)} new message(s)!")
                for msg in messages:
                    st.session_state.messages.append({
                        'type': 'doctor',
                        'content': msg,
                        'timestamp': datetime.now()
                    })
            else:
                st.info("No new messages from doctor")

    # ── Two-column layout ────────────────────────────────────────────────────
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("""
        <div class="cm-section-header">
          <span>🎤</span> Send Voice Message
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="cm-card">', unsafe_allow_html=True)

        audio_bytes = audio_recorder(
            text="Click to record your message",
            recording_color="#FF9F1C",
            neutral_color="#328CC1",
            icon_name="microphone",
            icon_size="3x",
            key="patient_recorder"
        )

        if audio_bytes:
            st.audio(audio_bytes, format="audio/wav")
            st.markdown(
                f'<div style="font-size:0.78rem;color:var(--muted-fg);font-family:var(--font-mono);'
                f'margin:0.4rem 0 0.8rem 0;">📁 {len(audio_bytes):,} bytes recorded</div>',
                unsafe_allow_html=True
            )

            if st.button("📤 Send to CareMate", type="primary"):
                with st.spinner("Processing your message…"):
                    try:
                        response = send_voice_to_caremate(
                            audio_bytes,
                            st.session_state.patient_id,
                            st.session_state.patient_name
                        )

                        if response.status_code == 200:
                            result = response.json()
                            st.success("✅ Message sent successfully!")

                            st.session_state.messages.append({
                                'type': 'patient',
                                'content': {
                                    'transcript': result.get('transcript'),
                                    'response': result.get('response_text'),
                                    'audio_url': result.get('response_audio_url')
                                },
                                'timestamp': datetime.now()
                            })

                            st.markdown(f"""
                            <div class="cm-msg-patient" style="margin-top:0.8rem">
                              <div class="cm-msg-label">🗣 Your Message</div>
                              {result.get('transcript', '')}
                            </div>
                            <div class="cm-msg-doctor">
                              <div class="cm-msg-label">🤖 CareMate Response</div>
                              {result.get('response_text', '')}
                            </div>
                            """, unsafe_allow_html=True)

                            if result.get('response_audio_url'):
                                st.audio(result['response_audio_url'])

                        else:
                            st.error(f"❌ Error: {response.status_code}")
                            try:
                                st.json(response.json())
                            except:
                                st.text(response.text)

                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="cm-section-header">
          <span>💬</span> Doctor Messages
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="cm-card">', unsafe_allow_html=True)

        if st.button("🔄 Refresh Messages"):
            messages = check_doctor_messages(st.session_state.patient_id)
            if messages:
                for msg in messages:
                    if msg not in [m['content'] for m in st.session_state.messages if m['type'] == 'doctor']:
                        st.session_state.messages.append({
                            'type': 'doctor',
                            'content': msg,
                            'timestamp': datetime.now()
                        })

        doctor_messages = [msg for msg in st.session_state.messages if msg['type'] == 'doctor']

        if doctor_messages:
            for msg in reversed(doctor_messages[-5:]):
                ts = msg['timestamp'].strftime('%H:%M:%S')
                if isinstance(msg['content'], dict):
                    body = msg['content'].get('text', str(msg['content']))
                else:
                    body = str(msg['content'])

                st.markdown(f"""
                <div class="cm-msg-doctor">
                  <div class="cm-msg-label">
                    👨‍⚕️ Doctor
                    <span class="cm-msg-time">{ts}</span>
                  </div>
                  {body}
                </div>
                """, unsafe_allow_html=True)

                if isinstance(msg['content'], dict) and msg['content'].get('audio_url'):
                    st.audio(msg['content']['audio_url'])
        else:
            st.markdown("""
            <div class="cm-empty">
              <div class="cm-empty-icon">📭</div>
              No messages from doctor yet.<br>They will appear here when received.
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ── Activity Log ─────────────────────────────────────────────────────────
    st.markdown('<hr style="border:none;border-top:1px solid #dce5f0;margin:1.5rem 0">', unsafe_allow_html=True)

    st.markdown("""
    <div class="cm-section-header">
      <span>📋</span> Recent Activity
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.messages:
        for msg in reversed(st.session_state.messages[-10:]):
            ts = msg['timestamp'].strftime('%H:%M:%S')

            if msg['type'] == 'patient':
                transcript = msg['content'].get('transcript', 'Voice message')
                st.markdown(f"""
                <div class="cm-msg-patient">
                  <div class="cm-msg-label">
                    🗣 You
                    <span class="cm-msg-time">{ts}</span>
                  </div>
                  {transcript}
                </div>
                """, unsafe_allow_html=True)

            elif msg['type'] == 'doctor':
                if isinstance(msg['content'], dict):
                    body = msg['content'].get('text', str(msg['content']))
                else:
                    body = str(msg['content'])
                st.markdown(f"""
                <div class="cm-msg-doctor">
                  <div class="cm-msg-label">
                    👨‍⚕️ Doctor
                    <span class="cm-msg-time">{ts}</span>
                  </div>
                  {body}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="cm-empty">
          <div class="cm-empty-icon">🩺</div>
          No activity yet. Start by recording a voice message!
        </div>
        """, unsafe_allow_html=True)

    # Auto-refresh
    time.sleep(0.1)

if __name__ == "__main__":
    main()