import os
import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader
from pymongo import MongoClient
from dotenv import load_dotenv
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "caremate_db"
CHROMA_PATH = os.path.join("Vfinal", "chroma_db")
REPORTS_DIR = os.path.join("Vfinal", "patient_reports")

class CareMateRAG:
    def __init__(self):
        # 1. Initialize ChromaDB (Local Persistent)
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        
        # 2. Use a free, local embedding model (all-MiniLM-L6-v2)
        # This model is small (~90MB) and very fast.
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # 3. Create or get the collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="patient_reports",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"} # Use cosine similarity for better semantic match
        )

    def extract_text_from_pdf(self, pdf_path):
        """Extracts all text from a given PDF file."""
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error reading {pdf_path}: {e}")
            return None

    def index_reports(self):
        """Indexes medical content from PDFs into ChromaDB, focusing on high-signal data."""
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        
        docs_metadata = list(db.documents.find({}))
        if not docs_metadata:
            logger.error("No document metadata found in MongoDB.")
            return

        logger.info("Clearing existing ChromaDB collection for a clean index...")
        try:
            self.chroma_client.delete_collection("patient_reports")
        except:
            pass
        self.collection = self.chroma_client.create_collection(
            name="patient_reports",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )

        logger.info(f"Indexing {len(docs_metadata)} reports into ChromaDB...")
        
        ids = []
        documents = []
        metadatas = []

        for doc in docs_metadata:
            relative_path = doc['file_path'].lstrip('/')
            full_path = os.path.join("Vfinal", relative_path)
            
            if not os.path.exists(full_path):
                continue

            raw_text = self.extract_text_from_pdf(full_path)
            if not raw_text:
                continue

            # --- RAG OPTIMIZATION: Focus on Medical Signal ---
            # We split the document into high-signal chunks to avoid "diluting" the search with hospital headers
            
            lines = raw_text.split('\n')
            findings = ""
            results = ""
            in_findings = False
            in_results = False

            for line in lines:
                if "CLINICAL FINDINGS" in line:
                    in_findings = True
                    in_results = False
                    continue
                if "Parameter Result" in line:
                    in_results = True
                    in_findings = False
                    continue
                if "This is a computer-generated report" in line:
                    break # End of high-signal content
                
                if in_findings:
                    findings += line + " "
                if in_results:
                    results += line + " "

            # Index the chunks separately for higher precision
            if findings.strip():
                chunk_id = f"{doc['document_id']}_findings"
                ids.append(chunk_id)
                documents.append(f"Clinical Findings for {doc['document_type']}: {findings.strip()}")
                metadatas.append({"patient_id": doc['patient_id'], "type": "findings"})

            if results.strip():
                chunk_id = f"{doc['document_id']}_results"
                ids.append(chunk_id)
                documents.append(f"Laboratory Results for {doc['document_type']}: {results.strip()}")
                metadatas.append({"patient_id": doc['patient_id'], "type": "results"})

        if documents:
            self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
            logger.info(f"Successfully indexed {len(documents)} high-signal medical chunks.")

    def query_reports(self, query_text, patient_id, n_results=3):
        """
        Secure multi-tenant search.
        Only returns results where metadata['patient_id'] matches the provided ID.
        """
        logger.info(f"Searching reports for Patient: {patient_id} | Query: '{query_text}'")
        
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where={"patient_id": patient_id} # SECURE FILTER
        )
        
        return results

# Example Usage / Initialization Script
if __name__ == "__main__":
    rag = CareMateRAG()
    
    # Run indexing
    rag.index_reports()
    
    # Test with a sample patient
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    sample_doc = db.documents.find_one()
    
    if sample_doc:
        p_id = sample_doc['patient_id']
        print(f"\n--- Testing RAG for Patient: {p_id} ---")
        test_query = "What were the clinical findings in my report?"
        results = rag.query_reports(test_query, p_id)
        
        if results['documents'][0]:
            print(f"Top Match Found:\n{results['documents'][0][0][:300]}...")
        else:
            print("No results found for this patient.")
