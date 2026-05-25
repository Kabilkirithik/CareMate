import os
from rag_pipeline import CareMateRAG
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "caremate_db"

def interactive_test():
    rag = CareMateRAG()
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    print("\n=== CareMate RAG Security Test ===")
    
    # 1. Pick two random patients to demonstrate security
    patients = list(db.patients.find().limit(2))
    if len(patients) < 2:
        print("Not enough patients found to test.")
        return

    p1 = patients[0]
    p2 = patients[1]

    print(f"\nPatient A: {p1['name']} (ID: {p1['patient_id']})")
    print(f"Patient B: {p2['name']} (ID: {p2['patient_id']})")

    # 2. Query as Patient A
    query = "Tell me about my medical report findings."
    
    print(f"\n--- ACTION: Searching as {p1['name']} ---")
    res1 = rag.query_reports(query, p1['patient_id'])
    if res1['documents'][0]:
        print(f"RESULT FOR {p1['name']}:")
        print(res1['documents'][0][0][:200] + "...")
    else:
        print(f"No results found for {p1['name']}.")

    # 3. Security Check: Search for Patient A's query but using Patient B's ID
    # It should NOT show Patient A's data.
    print(f"\n--- SECURITY CHECK: Searching with {p2['name']}'s ID ---")
    res2 = rag.query_reports(query, p2['patient_id'])
    if res2['documents'][0]:
        print(f"RESULT FOR {p2['name']}:")
        print(res2['documents'][0][0][:200] + "...")
        # Verify it's actually Patient B's report
        if p1['name'] in res2['documents'][0][0]:
            print("\n❌ SECURITY ALERT: Patient B saw Patient A's data!")
        else:
            print(f"\n✅ SUCCESS: Patient B only saw their own data.")
    else:
        print(f"No results found for {p2['name']}.")

if __name__ == "__main__":
    interactive_test()
