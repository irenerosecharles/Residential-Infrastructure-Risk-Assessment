import os
import json
import numpy as np
from pydantic import BaseModel, Field
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure GenAI SDK
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# Path to guidelines
GUIDELINES_PATH = os.path.join(os.path.dirname(__file__), "guidelines.json")

# In-memory guidelines cache
guidelines_db = []
guideline_embeddings = []

# Pydantic Schemas for Structured JSON outputs

class ImageValidationResult(BaseModel):
    is_residential_infrastructure: bool = Field(description="True if the image contains residential building elements, structural components, rooms, systems, or surfaces. False if it contains flowers, pets, selfies, cars, landscapes, or food.")
    confidence: float = Field(description="AI confidence score from 0.0 to 1.0")
    reason: str = Field(description="Detailed explanation justifying the assessment")

class DefectAnalysisResult(BaseModel):
    defect_class: str = Field(description="One of: 'Electrical Safety', 'Structural Integrity', 'Water Damage & Dampness', 'Fire Safety', 'Mechanical & Plumbing', 'Quality & Finish'")
    severity: str = Field(description="One of: 'Critical', 'High', 'Medium', 'Low'")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0")
    observed_details: str = Field(description="Concise description of the specific observed defect elements in the image")

class RAGSynthesisResult(BaseModel):
    priority: str = Field(description="One of: 'Immediate Action', 'Within 24 Hours', 'Schedule Inspection', 'Monitor'")
    recommendation: str = Field(description="A concise action plan explaining what should be done, referencing the relevant building codes")

# Load and embed guidelines on startup
def load_and_index_guidelines():
    global guidelines_db, guideline_embeddings
    try:
        with open(GUIDELINES_PATH, "r") as f:
            guidelines_db = json.load(f)
    except Exception as e:
        print(f"Error loading guidelines.json: {e}")
        return
        
    if not API_KEY:
        print("Warning: GEMINI_API_KEY not found. Guidelines indexed using keyword fallback.")
        return
        
    # Pre-calculate embeddings using Gemini embedding model
    print("Pre-computing guidelines embeddings using Gemini text-embedding-004...")
    try:
        texts = [f"{g['category']} {g['title']}: {g['description']}" for g in guidelines_db]
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=texts,
            task_type="retrieval_document"
        )
        guideline_embeddings = response['embedding']
        print(f"Successfully embedded {len(guideline_embeddings)} guidelines.")
    except Exception as e:
        print(f"Error during guideline embedding initialization: {e}. Falling back to keyword search.")
        guideline_embeddings = []

# Simple local TF-IDF / Bag of Words vector search fallback
def get_keyword_overlap(text, doc):
    text_words = set(text.lower().split())
    doc_words = set(doc.lower().split())
    return len(text_words.intersection(doc_words))

def vector_search(query_text, top_n=2):
    """
    Finds the top N matching building guidelines for a given query text.
    Uses cosine similarity if embeddings are available, otherwise falls back to keyword overlap.
    """
    if not guidelines_db:
        return []
        
    # If API_KEY and embeddings are active, perform cosine similarity
    if API_KEY and guideline_embeddings:
        try:
            response = genai.embed_content(
                model="models/text-embedding-004",
                content=query_text,
                task_type="retrieval_query"
            )
            query_vector = np.array(response['embedding'])
            
            similarities = []
            for emb in guideline_embeddings:
                emb_vector = np.array(emb)
                dot_product = np.dot(query_vector, emb_vector)
                norm_query = np.linalg.norm(query_vector)
                norm_emb = np.linalg.norm(emb_vector)
                cos_sim = dot_product / (norm_query * norm_emb)
                similarities.append(cos_sim)
                
            top_indices = np.argsort(similarities)[::-1][:top_n]
            return [guidelines_db[idx] for idx in top_indices]
        except Exception as e:
            print(f"Error in vector embedding similarity calculation: {e}. Falling back to keywords.")
            
    # Fallback keyword overlap search
    scores = []
    for g in guidelines_db:
        doc_text = f"{g['category']} {g['title']} {g['description']} {g['code']}"
        score = get_keyword_overlap(query_text, doc_text)
        scores.append(score)
        
    top_indices = np.argsort(scores)[::-1][:top_n]
    return [guidelines_db[idx] for idx in top_indices]

# Pipeline Stage 0: Image Validation
def validate_image(image_bytes, mime_type="image/jpeg"):
    """
    Verifies if the uploaded image actually depicts residential structure/building components.
    """
    if not API_KEY:
        # Fallback response for offline demo
        return ImageValidationResult(
            is_residential_infrastructure=True,
            confidence=0.99,
            reason="[Offline Demo Fallback Mode] Pre-approved input verification."
        )
        
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        image_part = {
            "mime_type": mime_type,
            "data": image_bytes
        }
        
        prompt = (
            "Analyze the uploaded image. Check if it contains elements of residential infrastructure, "
            "building components, rooms, surfaces (walls, floors, ceiling), electrical panels, plumbing fixtures, "
            "or structures. If the image depicts non-structural items like plants/flowers, pets/animals, selfies/people "
            "with no room context, landscapes, cars, or food, set is_residential_infrastructure to false. "
            "Return output strictly adhering to the JSON schema."
        )
        
        response = model.generate_content(
            [image_part, prompt],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=ImageValidationResult
            )
        )
        
        res_json = json.loads(response.text)
        return ImageValidationResult(**res_json)
    except Exception as e:
        print(f"Error in Stage 0 image validation: {e}")
        # Default safety fallback
        return ImageValidationResult(
            is_residential_infrastructure=True,
            confidence=0.5,
            reason=f"Validation error encountered ({str(e)}). Proceeding with caution."
        )

# Pipeline Stage 1: Multimodal Defect Analysis
def analyze_defect_multimodal(image_bytes, notes_text, mime_type="image/jpeg"):
    """
    Stage 1: Uses Gemini Vision to classify the defect type, raw severity, and confidence score.
    """
    if not API_KEY:
        # Fallback offline classifier based on notes keywords
        notes_lower = notes_text.lower()
        if "wire" in notes_lower or "cable" in notes_lower or "electric" in notes_lower:
            return DefectAnalysisResult(defect_class="Electrical Safety", severity="Critical", confidence=0.95, observed_details="Exposed wires detected in room (mock).")
        elif "crack" in notes_lower or "foundation" in notes_lower or "beam" in notes_lower:
            return DefectAnalysisResult(defect_class="Structural Integrity", severity="Critical", confidence=0.92, observed_details="Visible concrete cracks (mock).")
        elif "damp" in notes_lower or "leak" in notes_lower or "water" in notes_lower or "moist" in notes_lower:
            return DefectAnalysisResult(defect_class="Water Damage & Dampness", severity="High", confidence=0.88, observed_details="Moisture damage indicators (mock).")
        elif "smoke" in notes_lower or "detector" in notes_lower or "fire" in notes_lower:
            return DefectAnalysisResult(defect_class="Fire Safety", severity="Critical", confidence=0.96, observed_details="Fire safety alarm concern (mock).")
        elif "pipe" in notes_lower or "plumb" in notes_lower or "drain" in notes_lower:
            return DefectAnalysisResult(defect_class="Mechanical & Plumbing", severity="High", confidence=0.90, observed_details="Plumbing system concerns (mock).")
        else:
            return DefectAnalysisResult(defect_class="Quality & Finish", severity="Medium", confidence=0.80, observed_details="Finishing concerns (mock).")
            
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        image_part = {
            "mime_type": mime_type,
            "data": image_bytes
        }
        
        prompt = (
            f"Inspect this residential space image and review the inspector notes: '{notes_text}'.\n"
            "Identify the primary defect category and classify it as one of the following classes:\n"
            "- 'Electrical Safety'\n"
            "- 'Structural Integrity'\n"
            "- 'Water Damage & Dampness'\n"
            "- 'Fire Safety'\n"
            "- 'Mechanical & Plumbing'\n"
            "- 'Quality & Finish'\n\n"
            "Assess the severity of the hazard: 'Critical' (severe hazard to life/structure), 'High' (significant risk needing rapid action), 'Medium' (moderately concerning), 'Low' (minor cosmetic/quality issues).\n"
            "Determine your confidence (0.0 to 1.0) and write down the observed details. Adhere strictly to the JSON schema."
        )
        
        response = model.generate_content(
            [image_part, prompt],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=DefectAnalysisResult
            )
        )
        
        res_json = json.loads(response.text)
        return DefectAnalysisResult(**res_json)
    except Exception as e:
        print(f"Error in Stage 1 defect classification: {e}")
        return DefectAnalysisResult(
            defect_class="Quality & Finish",
            severity="Medium",
            confidence=0.5,
            observed_details="Failed to communicate with AI classification server."
        )

# Pipeline Stage 3: RAG Synthesis Recommendation
def synthesize_recommendation(notes_text, defect_class, retrieved_guidelines):
    """
    Stage 3: Takes original notes and retrieved guidelines, prompts Gemini to create
    a clear contextual recommendation and action priority based exactly on those guidelines.
    """
    codes_str = "\n".join([f"- Code: {g['code']} | Title: {g['title']} | Description: {g['description']}" for g in retrieved_guidelines])
    
    if not API_KEY:
        # Fallback offline synthesis
        rec = f"Action needed based on {', '.join([g['code'] for g in retrieved_guidelines])}. Correct the defect immediately to align with safety standard rules."
        return RAGSynthesisResult(priority="Schedule Inspection", recommendation=rec)
        
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = (
            f"You are a residential safety inspector expert.\n"
            f"The inspector observed: '{notes_text}'\n"
            f"The classified defect category is: '{defect_class}'\n\n"
            f"The following building safety guidelines were retrieved as references:\n{codes_str}\n\n"
            "Use this retrieved regulatory context to write a professional, plain-language action plan and recommendation for the inspector. "
            "Determine the priority level: 'Immediate Action' (severe code violations), 'Within 24 Hours' (major hazards), 'Schedule Inspection' (minor non-compliance), 'Monitor' (negligible issues). "
            "Cite the code names directly in your recommendation text. Adhere strictly to the JSON schema."
        )
        
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=RAGSynthesisResult
            )
        )
        
        res_json = json.loads(response.text)
        return RAGSynthesisResult(**res_json)
    except Exception as e:
        print(f"Error in Stage 3 RAG synthesis: {e}")
        return RAGSynthesisResult(
            priority="Schedule Inspection",
            recommendation=f"Examine safety guidelines related to {defect_class}. Align installation with regulatory standards."
        )

# Initialize on module import
load_and_index_guidelines()
