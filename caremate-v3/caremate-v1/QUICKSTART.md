# CareMate Backend - Quick Start Guide

## 🚀 Get Started in 10 Minutes

This guide will help you set up and run CareMate backend quickly.

---

## Step 1: Get API Keys (5 minutes)

### Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key - it looks like: `AIzaSy...`

### Sarvam AI API Key

1. Go to [Sarvam AI](https://www.sarvam.ai/)
2. Click "Get Started" or "Sign Up"
3. Complete registration
4. Go to Dashboard → API Keys
5. Generate a new API key
6. Copy the key - it looks like: `srvk_...`

---

## Step 2: Choose Your Setup Method

### Option A: Google Colab (Easiest - No Installation)

1. **Open the Colab Notebook:**
   - Upload `caremate_colab_setup.ipynb` to Google Colab
   - Or open directly: [Open in Colab](#)

2. **Add Your API Keys:**
   - Click the 🔑 (key) icon in left sidebar
   - Add secret: `GEMINI_API_KEY` = your_gemini_key
   - Add secret: `SARVAM_API_KEY` = your_sarvam_key

3. **Run All Cells:**
   - Click Runtime → Run all
   - Wait for setup to complete (~3-5 minutes)

4. **Get Your API URL:**
   - The ngrok URL will be displayed in the output
   - Example: `https://xxxx-xx-xx-xx-xx.ngrok-free.app`

5. **Test the API:**
   ```python
   # Run this cell in Colab
   import requests
   
   url = "YOUR_NGROK_URL/api/v1/health"
   response = requests.get(url)
   print(response.json())
   ```

✅ **Done! Your backend is running in the cloud.**

---

### Option B: Local Setup (For Development)

1. **Prerequisites:**
   ```bash
   # Check Python version (need 3.10+)
   python3 --version
   
   # Install MongoDB
   # Ubuntu/Debian:
   sudo apt-get install mongodb
   
   # macOS:
   brew install mongodb-community
   
   # Windows: Download from mongodb.com
   ```

2. **Clone/Download Files:**
   ```bash
   mkdir caremate_backend
   cd caremate_backend
   # Copy all files here
   ```

3. **Create Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

4. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure Environment:**
   ```bash
   # Copy template
   cp .env.template .env
   
   # Edit .env file and add your API keys
   nano .env  # or use any text editor
   ```

6. **Start MongoDB:**
   ```bash
   # Ubuntu/Debian
   sudo systemctl start mongodb
   
   # macOS
   brew services start mongodb-community
   
   # Windows: Start MongoDB service from Services
   ```

7. **Run the Backend:**
   ```bash
   python caremate_backend.py
   ```

8. **Verify It's Running:**
   ```bash
   # Open another terminal
   curl http://localhost:8000/api/v1/health
   ```

✅ **Done! Your backend is running locally.**

---

## Step 3: Test the System

### Test 1: Check Health

```bash
curl http://localhost:8000/api/v1/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-02-05T10:30:00",
  "version": "1.0.0"
}
```

### Test 2: Get Patient Info

```bash
curl http://localhost:8000/api/v1/patient/PT001
```

**Expected Response:**
```json
{
  "hospital_id": "PT001",
  "name": "Rajesh Kumar",
  "age": 45,
  ...
}
```

### Test 3: View API Documentation

Open in browser:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Test 4: Process a Query (Simulated)

Create a file `test_query.py`:

```python
import requests
import json

# Simulated audio (in real scenario, this would be actual audio from ESP32)
test_query = {
    "audio_base64": "simulated_audio_base64",
    "hospital_id": "PT001",
    "room_number": "201",
    "bed_number": "A"
}

# Note: This will fail without actual audio, but tests the endpoint
response = requests.post(
    "http://localhost:8000/api/v1/query",
    json=test_query
)

print(response.json())
```

Run it:
```bash
python test_query.py
```

---

## Step 4: Understand the Two-Agent System

### Agent 1: Patient Intelligence Agent

**What it does:**
1. Gets patient medical record
2. Understands what patient wants
3. Detects if it's urgent or emergency
4. Remembers past conversations

**Example:**
```
Patient says: "मुझे दर्द हो रहा है" (I'm in pain)

Agent analyzes:
- Patient: PT001, Rajesh Kumar
- Current medications: Metformin, Lisinopril
- Intent: MEDICAL (pain complaint)
- Urgency: MEDIUM
- Distress detected: YES
```

### Agent 2: Central Orchestrator Agent

**What it does:**
1. Reads the analysis from Agent 1
2. Checks hospital rules
3. Decides what to do
4. Generates response
5. Alerts nurse if needed

**Example:**
```
Receives analysis: Patient in pain (MEDICAL, MEDIUM urgency)

Applies rules:
- Medical request → Needs nurse approval
- Not emergency → Don't bypass normal flow

Actions:
- Generate response: "I'll inform Nurse Priya right away"
- Send notification to nurse
- Log everything
```

---

## Step 5: Monitor the System

### View Logs

```bash
# Logs will appear in the terminal where you ran the backend
# Look for lines like:
# [INFO] Processing patient query...
# [INFO] Agent 1: Analyzing context...
# [INFO] Agent 2: Making decision...
```

### Check Database

```python
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["caremate_db"]

# Check patients
print("Patients:", db.patients.count_documents({}))

# Check interactions
print("Interactions:", db.interactions.count_documents({}))

# View recent interaction
latest = db.interactions.find_one(sort=[("timestamp", -1)])
print("Latest:", latest)
```

---

## Common Issues & Solutions

### Issue 1: "ModuleNotFoundError: No module named 'crewai'"

**Solution:**
```bash
pip install -r requirements.txt
```

### Issue 2: "MongoDB connection refused"

**Solution:**
```bash
# Check if MongoDB is running
sudo systemctl status mongodb

# Start it if not running
sudo systemctl start mongodb

# Or use MongoDB Atlas (cloud)
```

### Issue 3: "Invalid API key"

**Solution:**
- Double-check your API keys in `.env` file
- Make sure there are no extra spaces
- Verify keys are active in respective dashboards

### Issue 4: "Port 8000 already in use"

**Solution:**
```bash
# Find what's using port 8000
lsof -i :8000

# Kill it or change port in .env file
PORT=8001
```

---

## Next Steps

1. **Connect ESP32 Device:**
   - Configure ESP32 to send audio to your API endpoint
   - Test voice interaction

2. **Build Dashboard:**
   - Create React dashboard for nurses/doctors
   - Connect to FastAPI backend

3. **Production Deployment:**
   - Deploy to cloud platform (GCP, AWS, Azure)
   - Set up proper database (MongoDB Atlas)
   - Configure SSL/HTTPS
   - Set up monitoring and alerts

4. **Enhance System:**
   - Add more patient scenarios
   - Improve intent classification
   - Add more languages
   - Implement feedback loop

---

## Getting Help

- **Documentation:** See README.md for full documentation
- **API Reference:** http://localhost:8000/docs
- **Troubleshooting:** See README.md troubleshooting section

---

## Summary Checklist

- [ ] Got Gemini API key
- [ ] Got Sarvam AI API key
- [ ] Installed dependencies
- [ ] Configured .env file
- [ ] MongoDB running
- [ ] Backend started successfully
- [ ] Health check passes
- [ ] Can retrieve patient data
- [ ] Understand two-agent system
- [ ] Ready to connect ESP32

**Time to Complete:** ~10-15 minutes

**Status:** ✅ Ready to use!

---

**Need help?** Check the full README.md or create an issue on GitHub.
