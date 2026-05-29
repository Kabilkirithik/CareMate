#!/usr/bin/env python3
"""
Fix intent boundaries:
- general_conversation: General medical knowledge ("What is diabetes?")
- doctor_query: Personal medication/doses/treatment + requesting doctor
- nurse_request: Needing medication administered NOW
- status_query: Asking about own condition/results
"""
import pandas as pd
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(base_dir, 'caremate_big_dataset.csv')

df = pd.read_csv(data_path)
df['text'] = df['text'].astype(str).str.strip()

print(f"Before: {len(df)} rows")
print(df['intent'].value_counts())

# ─────────────────────────────────────────────
# 1. Move general medical knowledge questions
#    FROM doctor_query → general_conversation
# ─────────────────────────────────────────────
general_knowledge_patterns = [
    "what is diabetes", "what is hypertension", "what is cancer",
    "what is pneumonia", "what is anemia", "what is cholesterol",
    "what is a fracture", "what is arthritis", "what is asthma",
    "what is copd", "what is sepsis", "what is a blood clot",
    "what is a stroke", "what is a heart attack", "what is kidney failure",
    "what is liver disease", "what is an infection", "what is inflammation",
    "what is chemotherapy", "what is dialysis", "what is an ecg",
    "what is an mri", "what is a ct scan", "what is an ultrasound",
    "what is a biopsy", "what is radiation therapy", "what is palliative care",
    "what is physical therapy", "what is occupational therapy",
    "what causes diabetes", "what causes fever", "what causes this",
    "how to cure diabetes", "how to cure it", "how to cure",
    "how does this medicine work", "how does surgery work",
    "how does the immune system", "how do antibiotics work",
    "explain diabetes", "explain hypertension", "explain my condition",
    "tell me about diabetes", "tell me about hypertension",
    "can you explain what", "can you tell me about",
    "do you know what diabetes", "do you know what hypertension",
    "what does fever mean", "what does chronic mean",
    "what is the difference between", "what is the prognosis",
    "what is the treatment for this", "what are the side effects",
    "is this condition curable", "is there a cure",
    "what are my treatment options", "what is the best treatment",
    "how effective is this treatment", "what are the alternatives",
    "what is the success rate", "how painful will",
    "what is the recovery process", "what is the recovery time",
    "what are the long-term effects", "what are the risks",
    "what lifestyle changes", "how do i prevent",
    "is this hereditary", "can my family get this",
    "what is normal blood sugar", "what is normal blood pressure",
    "what is a normal temperature", "what is oxygen saturation",
    "what is a virus", "what is a bacterial infection",
]

# Move these from doctor_query to general_conversation
moved_to_general = 0
for idx, row in df.iterrows():
    if row['intent'] == 'doctor_query':
        text_lower = row['text'].lower()
        if any(pat in text_lower for pat in general_knowledge_patterns):
            df.at[idx, 'intent'] = 'general_conversation'
            moved_to_general += 1

print(f"\nMoved {moved_to_general} rows: doctor_query → general_conversation")

# ─────────────────────────────────────────────
# 2. Add new doctor_query samples for
#    personal medication/dose questions
# ─────────────────────────────────────────────
personal_medication_doctor_samples = [
    # Personal medication/dose questions → doctor_query
    "What is my dosage?",
    "What medication am I on?",
    "What medicines have I been prescribed?",
    "Can you tell me what drugs I am taking?",
    "What dose am I supposed to take?",
    "How many times a day should I take my medicine?",
    "Can the doctor change my medication?",
    "Can the doctor switch me to a different medicine?",
    "I want to change my painkiller",
    "Can the doctor review my medication?",
    "What painkiller am I on?",
    "Can I get a stronger painkiller?",
    "My medication is not working, can the doctor change it?",
    "What antibiotic am I taking?",
    "Can the doctor prescribe something for my pain?",
    "I need a prescription change",
    "Can the doctor adjust my dose?",
    "Is my current dose correct?",
    "Why was my medication changed?",
    "Can I stop taking this medication?",
    "When should I stop taking this medicine?",
    "Can the doctor come and explain my treatment plan?",
    "I want to discuss my treatment with the doctor",
    "Can the doctor explain my surgery?",
    "I need to speak with my doctor about my treatment",
    "Can the doctor come see me?",
    "Please send the doctor to my room",
    "I need the doctor urgently",
    "Can I get a second opinion from another doctor?",
    "Can the doctor review my pain management?",
    "What is the doctor's plan for my recovery?",
    "Can the doctor tell me about my operation?",
    "I want to know about my surgical procedure",
    "Can the doctor explain the risks of my surgery?",
    "What did the doctor prescribe for me?",
    "Can the doctor come and check on me?",
    "I need to talk to my doctor",
    "Can you get the doctor for me?",
    "Doctor please come to my room",
    "I need medical advice from the doctor",
]

# ─────────────────────────────────────────────
# 3. Add general_conversation medical knowledge
#    samples (the ones we wrongly added as doctor_query)
# ─────────────────────────────────────────────
general_medical_knowledge_samples = [
    "What is diabetes?",
    "Do you know what diabetes is?",
    "What causes diabetes?",
    "How to cure diabetes?",
    "How to cure it?",
    "What is hypertension?",
    "What does high blood pressure mean?",
    "Can you explain what diabetes is?",
    "What is the treatment for diabetes?",
    "What are the side effects of diabetes?",
    "Is diabetes curable?",
    "What causes this illness?",
    "How does this medicine work in general?",
    "What is the prognosis for this disease?",
    "What is the normal blood sugar level?",
    "What is a normal blood pressure reading?",
    "What does fever mean?",
    "What is causing my symptoms in general?",
    "What is cholesterol?",
    "What is anemia?",
    "What is pneumonia?",
    "What is a fracture?",
    "How does surgery work in general?",
    "What is the recovery process for this?",
    "What are the risks of this type of surgery?",
    "What are the long-term effects of this condition?",
    "What is inflammation?",
    "What is an infection?",
    "How do antibiotics work?",
    "What is a virus?",
    "What is a bacterial infection?",
    "How does the immune system work?",
    "What is chemotherapy?",
    "What is radiation therapy?",
    "What is dialysis?",
    "What is an ECG?",
    "What does oxygen saturation mean?",
    "What is sepsis?",
    "What is a blood clot?",
    "What is a stroke?",
    "What is a heart attack?",
    "What is kidney failure?",
    "What is liver disease?",
    "What is asthma?",
    "What is COPD?",
    "What is arthritis?",
    "What is osteoporosis?",
    "What is cancer?",
    "What is a biopsy?",
    "What is an MRI?",
    "What is a CT scan?",
    "What is an ultrasound?",
    "What does chronic mean?",
    "What is an acute condition?",
    "What is palliative care?",
    "What is physical therapy?",
    "What is occupational therapy?",
    "How do I prevent this from happening again?",
    "What lifestyle changes should I make?",
    "Is this hereditary?",
    "Can my family get this too?",
    "Is there a cure for this disease?",
    "What are my treatment options in general?",
    "What is the best treatment for this condition?",
    "How effective is this type of treatment?",
    "What are the alternatives to surgery?",
    "What is the success rate of this type of surgery?",
    "How painful is this procedure generally?",
    "What is the general recovery time?",
    "What are the long-term effects of this medicine?",
    "What is the difference between type 1 and type 2 diabetes?",
    "What is normal body temperature?",
    "What is a normal heart rate?",
    "What does high fever mean?",
    "What is the immune system?",
    "What is a white blood cell?",
    "What is a red blood cell?",
    "What is hemoglobin?",
    "What is blood pressure?",
    "What is a pulse?",
    "What is respiration rate?",
]

# Build new rows
new_doctor_rows = pd.DataFrame({
    'text': personal_medication_doctor_samples,
    'intent': ['doctor_query'] * len(personal_medication_doctor_samples)
})

new_general_rows = pd.DataFrame({
    'text': general_medical_knowledge_samples,
    'intent': ['general_conversation'] * len(general_medical_knowledge_samples)
})

# Remove the wrongly added doctor_query samples from previous run
# (the ones that were general knowledge)
df = df[~df['text'].isin(general_medical_knowledge_samples)]

# Append new samples
df_updated = pd.concat([df, new_doctor_rows, new_general_rows], ignore_index=True)

# Drop duplicates
df_updated = df_updated.drop_duplicates(subset=['text']).reset_index(drop=True)

print(f"\nAfter: {len(df_updated)} rows")
print(df_updated['intent'].value_counts())

df_updated.to_csv(data_path, index=False)
print("\n✅ Dataset updated. Now run: python retrain_final.py")
