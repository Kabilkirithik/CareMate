#!/usr/bin/env python3
"""
Add medical knowledge question samples to the training dataset and retrain.
These are questions patients ask about their conditions — currently misclassified.
"""
import pandas as pd
import os

# New medical knowledge samples that should be doctor_query
new_doctor_query_samples = [
    # Medical knowledge questions
    "What is diabetes?",
    "Do you know what diabetes is?",
    "What causes diabetes?",
    "How to cure diabetes?",
    "How to cure it?",
    "What is hypertension?",
    "What does high blood pressure mean?",
    "What is my diagnosis?",
    "Can you explain my condition?",
    "What does this disease mean?",
    "How serious is my condition?",
    "What is the treatment for this?",
    "How long will my recovery take?",
    "What are the side effects of this medication?",
    "Is this condition curable?",
    "What causes this illness?",
    "How does this medicine work?",
    "What is the prognosis?",
    "Can you explain what the doctor said?",
    "What does my test result mean?",
    "Is my condition getting better?",
    "What is the normal blood sugar level?",
    "What is a normal blood pressure reading?",
    "What does fever mean?",
    "Why do I have this pain?",
    "What is causing my symptoms?",
    "How do I manage this condition?",
    "What foods should I avoid with this condition?",
    "Can I exercise with this condition?",
    "What is the difference between type 1 and type 2 diabetes?",
    "What is cholesterol?",
    "What is anemia?",
    "What is pneumonia?",
    "What is a fracture?",
    "How does surgery work?",
    "What happens during the procedure?",
    "What is the recovery process?",
    "How long will I be in the hospital?",
    "What are the risks of this surgery?",
    "Can you tell me about my medication?",
    "What is this pill for?",
    "Why am I taking this medicine?",
    "What is the dosage?",
    "How often should I take this?",
    "What is an IV drip?",
    "What is a blood test for?",
    "What does the scan show?",
    "Can you explain the X-ray results?",
    "What is inflammation?",
    "What is an infection?",
    "How do antibiotics work?",
    "What is a virus?",
    "What is a bacterial infection?",
    "How does the immune system work?",
    "What is chemotherapy?",
    "What is radiation therapy?",
    "What is dialysis?",
    "What is a catheter?",
    "What is an ECG?",
    "What does my heart rate mean?",
    "What is oxygen saturation?",
    "What is a normal temperature?",
    "Why is my temperature high?",
    "What is sepsis?",
    "What is a blood clot?",
    "What is a stroke?",
    "What is a heart attack?",
    "How is a heart attack treated?",
    "What is kidney failure?",
    "What is liver disease?",
    "What is asthma?",
    "What is COPD?",
    "What is arthritis?",
    "What is osteoporosis?",
    "What is cancer?",
    "What stage is my cancer?",
    "What is chemotherapy doing to my body?",
    "What is a biopsy?",
    "What is an MRI?",
    "What is a CT scan?",
    "What is an ultrasound?",
    "What does the doctor mean by chronic?",
    "What is a chronic condition?",
    "What is an acute condition?",
    "What is palliative care?",
    "What is physical therapy?",
    "What is occupational therapy?",
    "How do I prevent this from happening again?",
    "What lifestyle changes should I make?",
    "Is this hereditary?",
    "Can my family get this too?",
    "What is the cure for this?",
    "Is there a cure?",
    "What are my treatment options?",
    "What is the best treatment?",
    "How effective is this treatment?",
    "What are the alternatives?",
    "Can I get a second opinion?",
    "What is the success rate of this surgery?",
    "How painful will the procedure be?",
    "Will I need surgery?",
    "Do I need an operation?",
    "What is the recovery time?",
    "When can I go back to normal activities?",
    "Can I drink alcohol with this medication?",
    "Can I drive while taking this medicine?",
    "What happens if I miss a dose?",
    "Can I take this with other medicines?",
    "What are the long-term effects?",
]

# Load existing dataset
dataset_path = os.path.join(os.path.dirname(__file__), "caremate_big_dataset.csv")
df = pd.read_csv(dataset_path)

print(f"Original dataset size: {len(df)}")
print(f"Original intent distribution:\n{df['intent'].value_counts()}\n")

# Create new samples dataframe
new_samples = pd.DataFrame({
    "text": new_doctor_query_samples,
    "intent": ["doctor_query"] * len(new_doctor_query_samples)
})

# Append to dataset
df_updated = pd.concat([df, new_samples], ignore_index=True)

# Save updated dataset
df_updated.to_csv(dataset_path, index=False)

print(f"Updated dataset size: {len(df_updated)}")
print(f"Updated intent distribution:\n{df_updated['intent'].value_counts()}")
print(f"\n✅ Added {len(new_doctor_query_samples)} new doctor_query samples")
print("Now run: python retrain_v5.py")