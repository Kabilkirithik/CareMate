import os
import uuid
import random
import logging
import unicodedata
from datetime import datetime, timedelta
from pymongo import MongoClient
from fpdf import FPDF, XPos, YPos
from faker import Faker
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "caremate_db"

# Global Faker instances
fake = Faker('en_IN')

REPORT_TYPES = [
    {
        "type": "blood_test", 
        "title": "BLOOD HEMATOLOGY REPORT", 
        "findings": "Complete Blood Count shows normal hemoglobin levels. White blood cell count is within the reference range, indicating no active infection. Platelet count is stable. Peripheral smear shows normocytic normochromic red cells.",
        "params": [("Hemoglobin", "14.2 g/dL", "13.5 - 17.5"), ("WBC Count", "7,500 /mcL", "4,500 - 11,000"), ("Platelets", "250,000 /mcL", "150k - 450k")]
    },
    {
        "type": "mri_scan", 
        "title": "MRI BRAIN SCAN REPORT", 
        "findings": "MRI of the brain shows normal ventricular system. No evidence of intracranial hemorrhage or infarct. Midline structures are central. The grey-white matter differentiation is preserved. No significant abnormalities detected in the cerebellum.",
        "params": [("Scan Quality", "Optimal", "N/A"), ("Contrast", "Used", "N/A"), ("Impression", "Normal Study", "No lesions")]
    },
    {
        "type": "x_ray", 
        "title": "CHEST X-RAY REPORT", 
        "findings": "The lungs are clear without focal consolidation, effusion, or pneumothorax. The cardiomediastinal silhouette is within normal limits. Bony structures of the chest wall are intact. No acute cardiopulmonary process identified.",
        "params": [("View", "PA View", "N/A"), ("Lungs", "Clear", "Normal Expansion"), ("Bones", "Intact", "N/A")]
    },
    {
        "type": "lab_report", 
        "title": "BIOCHEMISTRY ANALYSIS", 
        "findings": "Renal function tests are within normal limits. Blood urea and serum creatinine levels indicate healthy kidney function. Electrolyte levels (Sodium, Potassium) are balanced. Liver enzymes show no signs of hepatotoxicity.",
        "params": [("Blood Sugar", "98 mg/dL", "70 - 100"), ("Creatinine", "0.9 mg/dL", "0.7 - 1.3"), ("Urea", "25 mg/dL", "15 - 45")]
    },
    {
        "type": "radiology_report", 
        "title": "ULTRASOUND ABDOMEN", 
        "findings": "The liver is normal in size and echotexture. Gallbladder is well-distended with no calculi. Both kidneys appear normal in size and position with preserved corticomedullary differentiation. No free fluid seen in the peritoneal cavity.",
        "params": [("Liver", "Normal Size", "No fatty change"), ("Kidneys", "Normal", "No stones"), ("Spleen", "Normal", "N/A")]
    }
]

def clean_text(text):
    """Ensure text only contains characters supported by standard PDF fonts."""
    if not isinstance(text, str):
        return str(text)
    # Normalize unicode characters and encode to ascii/ignore non-latin
    normalized = unicodedata.normalize('NFKD', text)
    return normalized.encode('ascii', 'ignore').decode('ascii')

def generate_pdf(patient_name, patient_id, report_info):
    reports_dir = os.path.join("Vfinal", "patient_reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    patient_name = clean_text(patient_name)
    
    doc_id = str(uuid.uuid4())
    file_name = f"{report_info['type']}_{doc_id[:8]}.pdf"
    file_path = os.path.join(reports_dir, file_name)
    
    pdf = FPDF()
    pdf.add_page()
    
    # Hospital Header
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(200, 10, text="CARE MATE MULTISPECIALITY HOSPITAL", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font("Helvetica", size=10)
    pdf.cell(200, 5, text="Electronic Health Record System | Managed by CareMate AI", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.line(10, 30, 200, 30)
    
    # Patient Details Section
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(200, 10, text=report_info['title'], new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
    pdf.set_font("Helvetica", size=10)
    pdf.cell(100, 7, text=f"Patient Name: {patient_name}", new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(100, 7, text=f"Date: {datetime.now().strftime('%d-%m-%Y')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(100, 7, text=f"Patient ID: {patient_id}", new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(100, 7, text=f"Report ID: {doc_id[:8].upper()}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Report Content
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(200, 8, text="CLINICAL FINDINGS", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=10)
    pdf.ln(2)
    content = report_info['findings']
    pdf.multi_cell(0, 6, text=content)
    
    # Results Table
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(60, 8, "Parameter", 1)
    pdf.cell(60, 8, "Result", 1)
    pdf.cell(60, 8, "Reference Range", 1)
    pdf.ln(8)
    pdf.set_font("Helvetica", size=10)
    
    for p, r, ref in report_info['params']:
        pdf.cell(60, 8, p, 1)
        pdf.cell(60, 8, r, 1)
        pdf.cell(60, 8, ref, 1)
        pdf.ln(8)
            
    # Footer
    pdf.ln(20)
    pdf.set_font("Helvetica", 'I', 8)
    pdf.cell(200, 5, text="This is a computer-generated report. No physical signature is required.", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.cell(200, 5, text="CONFIDENTIAL MEDICAL RECORD", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    
    pdf.output(file_path)
    return doc_id, f"/patient_reports/{file_name}", content

def run():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    logger.info("Fetching patients...")
    patients = list(db.patients.find({}))
    
    if not patients:
        logger.error("No patients found in database!")
        return

    logger.info(f"Clearing existing documents...")
    db.documents.drop()
    
    docs_to_insert = []
    
    logger.info(f"Generating 1 report for each of the {len(patients)} patients...")
    for idx, patient in enumerate(patients):
        p_id = patient['patient_id']
        p_name = patient['name'] # Use the real name from MongoDB
        
        # Find a visit for this patient
        visit = db.visits.find_one({"patient_id": p_id})
        v_id = visit['visit_id'] if visit else str(uuid.uuid4())
        
        # Select a random report type
        report_info = random.choice(REPORT_TYPES)
        
        # Generate PDF
        doc_id, file_url, extracted_text = generate_pdf(p_name, p_id, report_info)
        
        docs_to_insert.append({
            "document_id": doc_id,
            "patient_id": p_id,
            "visit_id": v_id,
            "document_type": report_info['type'],
            "extracted_text": extracted_text,
            "file_path": file_url,
            "upload_source": "nurse_station",
            "processing_status": "COMPLETED",
            "uploaded_at": datetime.now() - timedelta(days=random.randint(1, 30))
        })
        
        if (idx + 1) % 50 == 0:
            logger.info(f"Progress: {idx+1} PDFs generated...")

    if docs_to_insert:
        db.documents.insert_many(docs_to_insert)
        logger.info(f"Successfully inserted {len(docs_to_insert)} document records into MongoDB.")

    logger.info("Task completed successfully.")

if __name__ == "__main__":
    run()
