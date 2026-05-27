import requests

# ✅ Paste the ngrok URL printed by the notebook here
BASE_URL = " https://stateless-hygroscopically-tristen.ngrok-free.dev"  # no trailing slash

def ask_caremate(message: str, max_new_tokens=120, temperature=0.4, top_p=0.8):
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={
                "message": message,
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
                "top_p": top_p
            },
            timeout=120   # model can take time — don't cut it short
        )
        response.raise_for_status()
        return response.json()["response"]

    except requests.exceptions.Timeout:
        return "Error: Request timed out. The model is still generating — try a higher timeout."
    except requests.exceptions.ConnectionError:
        return "Error: Cannot reach server. Is the notebook still running? Has the ngrok URL changed?"
    except Exception as e:
        return f"Error: {e}"

def health_check():
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        print("Server status:", r.json())
    except Exception as e:
        print("Health check failed:", e)

if __name__ == "__main__":
    # 1. Check server is up
    health_check()

    # 2. Ask questions
    questions = [
        "What are the symptoms of pneumonia?",
        "What is the normal blood pressure range for adults?",
        "What are first-line treatments for Type 2 diabetes?",
    ]

    for q in questions:
        print(f"\nPatient: {q}")
        print(f"CareMate: {ask_caremate(q)}")
        print("-" * 60)