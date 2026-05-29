import streamlit as st
import os
import requests
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
import time

load_dotenv()

# --- Configuration ---
API_URL = "http://localhost:8000"
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "caremate_db"

st.set_page_config(page_title="CareMate AI Assistant", page_icon="🏥", layout="wide")

# --- Custom CSS for Production Look ---
st.markdown("""
<style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    .stSidebar { background-color: #f8f9fa; }
    .status-badge { padding: 5px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; }
    .intent-tag { background-color: #e3f2fd; color: #0d47a1; padding: 2px 8px; border-radius: 5px; font-size: 0.7rem; }
</style>
""", unsafe_allow_html=True)

# --- State Management ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "patient_id" not in st.session_state:
    st.session_state.patient_id = None
if "patient_name" not in st.session_state:
    st.session_state.patient_name = None
if "last_checked" not in st.session_state:
    st.session_state.last_checked = datetime.now()

# --- Bedside Device Logic: Listen for Doctor ---
def check_for_doctor_messages():
    """Polls the interaction DB for new messages from the doctor dashboard."""
    try:
        client = MongoClient("mongodb+srv://Caremate-frontend:FIOWipLqLhFyp4uP@cluster0.agxm8kg.mongodb.net/?appName=Cluster0")
        db = client["caremate_interaction_db"]
        
        new_msg = db.doctor_messages.find_one({
            "patient_id": st.session_state.patient_id,
            "played": False
        }, sort=[("sent_at", -1)])
        
        if new_msg:
            st.toast("🔔 Message from Doctor received!")
            st.session_state.messages.append({
                "role": "assistant", 
                "content": "Message from your Doctor:",
                "audio": new_msg["audio_url"]
            })
            # Mark as played so it doesn't repeat
            db.doctor_messages.update_one(
                {"_id": new_msg["_id"]},
                {"$set": {"played": True}}
            )
            st.rerun()
    except:
        pass

# --- Sidebar: Patient Selection ---
with st.sidebar:
    st.title("📟 Bedside Device")
    st.info("Assign this device to a room/patient.")
    
    try:
        # Use the SECONDARY database for fast lookup
        client = MongoClient("mongodb+srv://Caremate-frontend:FIOWipLqLhFyp4uP@cluster0.agxm8kg.mongodb.net/?appName=Cluster0")
        db = client["caremate_interaction_db"]
        
        # Fetch synchronized patient lookup list
        patients = list(db.patient_lookup.find({}, {"name": 1, "patient_id": 1, "room_id": 1}).sort("patient_id", 1))
        
        patient_options = {f"Patient {p['patient_id']} - {p['name']} (Room {p['room_id']})": p['patient_id'] for p in patients}
        selected_option = st.selectbox("Assign Device:", options=list(patient_options.keys()))
        
        if selected_option:
            st.session_state.patient_id = patient_options[selected_option]
            p_info = db.patient_lookup.find_one({"patient_id": st.session_state.patient_id})
            st.session_state.patient_name = p_info['name'] if p_info else "Unknown"
            st.success(f"Device Active in Room {p_info['room_id']}")
            st.write(f"**Patient:** {p_info['name']}")
            st.write(f"**ID:** {p_info['patient_id']}")
            
    except Exception as e:
        st.error(f"Sync Error: {e}")

    st.divider()
    if st.button("Clear Screen"):
        st.session_state.messages = []
        st.rerun()

# Run polling logic
if st.session_state.patient_id:
    check_for_doctor_messages()

# --- Main Chat UI ---
st.title("CareMate Bedside Assistant")
st.caption("Press 'Process Voice' or type to speak with CareMate.")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "audio" in message and message["audio"]:
            st.audio(message["audio"])
        if "intent" in message:
            st.markdown(f"<span class='intent-tag'>Intent: {message['intent']}</span>", unsafe_allow_html=True)

# Chat Input
if prompt := st.chat_input("How can I help you today?"):
    if not st.session_state.patient_id:
        st.warning("Please select a patient from the sidebar first.")
    else:
        # Add user message to UI
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Call Backend API
        with st.spinner("CareMate is thinking..."):
            try:
                response = requests.post(
                    f"{API_URL}/chat",
                    json={"patient_id": st.session_state.patient_id, "message": prompt},
                    timeout=120
                )
                response.raise_for_status()
                data = response.json()
                
                # Add AI message to UI
                ai_message = {
                    "role": "assistant", 
                    "content": data["response_text"],
                    "audio": data["response_audio_url"],
                    "intent": data["intent"]
                }
                st.session_state.messages.append(ai_message)
                
                with st.chat_message("assistant"):
                    st.markdown(ai_message["content"])
                    if ai_message["audio"]:
                        st.audio(ai_message["audio"])
                    st.markdown(f"<span class='intent-tag'>Intent: {ai_message['intent']}</span>", unsafe_allow_html=True)
                    
            except Exception as e:
                st.error(f"API Error: {str(e)}")

# Voice Input Section
st.divider()
st.subheader("🎤 Voice Interaction")
uploaded_file = st.file_uploader("Upload patient voice recording (.mp3)", type=["mp3", "wav"])

if uploaded_file and st.session_state.patient_id:
    if st.button("Process Voice"):
        with st.spinner("Processing speech..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "audio/mpeg")}
                response = requests.post(
                    f"{API_URL}/voice",
                    params={
                        "patient_id": st.session_state.patient_id,
                        "patient_name": st.session_state.patient_name
                    },
                    files=files,
                    timeout=120
                )
                response.raise_for_status()
                data = response.json()
                
                # Update UI with voice results
                st.session_state.messages.append({"role": "user", "content": f"[Voice] {data['transcript']}"})
                ai_message = {
                    "role": "assistant", 
                    "content": data["response_text"],
                    "audio": data["response_audio_url"],
                    "intent": data["intent"]
                }
                st.session_state.messages.append(ai_message)
                st.rerun()
                
            except Exception as e:
                st.error(f"Voice API Error: {str(e)}")
