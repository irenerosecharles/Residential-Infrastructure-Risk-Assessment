import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Import our custom backend modules
import database as db
import ai_engine as ai
import trend_analysis as ta
import pdf_generator as pdf

app = FastAPI(title="ResiIntel API", description="FastAPI Backend for Infrastructure Safety Assessment")

# Configure CORS so local frontend can communicate with the server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local portfolio development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Mount static file endpoints
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
# If assets directory exists, mount it
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# Startup Event to initialize database tables
@app.on_event("startup")
def startup_event():
    db.init_db()

# Pydantic Schemas for JSON Requests

class OverrideRequest(BaseModel):
    finding_id: str
    inspector_defect_class: str
    inspector_severity: str
    override_reason: str
    override_by: str = "Inspector-01"

# API Endpoints

@app.get("/api/properties")
def get_properties():
    try:
        return db.get_all_properties_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/properties/{property_id}")
def get_property_details(property_id: str):
    data = db.get_property_details(property_id)
    if not data:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Calculate historical trends
    trends = ta.calculate_risk_trend(data.get("risk_history", []))
    data["trends"] = trends
    
    return data

@app.post("/api/properties/inspect")
async def inspect_room(
    room_id: str = Form(...),
    notes_text: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        # 1. Read file bytes
        image_bytes = await image.read()
        
        # Determine property_id from room_id
        conn = db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT property_id, name FROM rooms WHERE id = ?", (room_id,))
        room_info = cursor.fetchone()
        
        if not room_info:
            conn.close()
            raise HTTPException(status_code=404, detail="Room not found")
        property_id = room_info["property_id"]
        room_name = room_info["name"]
        
        # 2. Pipeline Stage 0: Image Validation
        validation_res = ai.validate_image(image_bytes, image.content_type)
        
        if not validation_res.is_residential_infrastructure:
            # Save validation failed to timeline
            timestamp = db.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            cursor.execute("""
                INSERT INTO timeline (property_id, timestamp, event_type, message)
                VALUES (?, ?, 'validation_failed', ?)
            """, (property_id, timestamp, f"Validation failed in {room_name}. Uploaded file does not contain residential infrastructure: {validation_res.reason}"))
            conn.commit()
            conn.close()
            
            return {
                "success": False,
                "error": "validation_failed",
                "reason": validation_res.reason,
                "confidence": validation_res.confidence
            }
            
        conn.close() # Close connection for processing
        
        # 3. Save Valid Image File
        file_ext = os.path.splitext(image.filename)[1]
        filename = f"img_{db.datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            buffer.write(image_bytes)
            
        image_url = f"/uploads/{filename}"
        
        # 4. Pipeline Stage 1: Multimodal Defect Analysis
        defect_res = ai.analyze_defect_multimodal(image_bytes, notes_text, image.content_type)
        
        # 5. Pipeline Stage 2: RAG Guidelines Vector Search
        retrieved_codes_raw = ai.vector_search(defect_res.observed_details, top_n=2)
        retrieved_codes = [g["code"] for g in retrieved_codes_raw]
        
        # 6. Pipeline Stage 3: RAG synthesis for custom recommendations
        synthesis_res = ai.synthesize_recommendation(notes_text, defect_res.defect_class, retrieved_codes_raw)
        
        # 7. Insert finding into database and update scores
        finding_id = db.insert_new_finding(
            room_id=room_id,
            image_url=image_url,
            notes_text=notes_text,
            ai_data=defect_res.dict(),
            retrieved_codes=retrieved_codes,
            recommendations=synthesis_res.recommendation,
            priority=synthesis_res.priority
        )
        
        return {
            "success": True,
            "finding_id": finding_id,
            "image_url": image_url,
            "defect_analysis": defect_res,
            "retrieved_codes": retrieved_codes_raw,
            "synthesis": synthesis_res
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/properties/override")
def override_ai_finding(req: OverrideRequest):
    success = db.save_inspector_override(
        finding_id=req.finding_id,
        inspector_defect=req.inspector_defect_class,
        inspector_severity=req.inspector_severity,
        override_reason=req.override_reason,
        override_by=req.override_by
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to apply inspector override")
    return {"success": True}

@app.get("/api/properties/{property_id}/export")
def export_property_report(property_id: str):
    data = db.get_property_details(property_id)
    if not data:
        raise HTTPException(status_code=404, detail="Property not found")
        
    trends = ta.calculate_risk_trend(data.get("risk_history", []))
    
    filename = f"report_{property_id}_{db.datetime.now().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    try:
        pdf.generate_property_pdf(data, trends, filepath)
        return FileResponse(
            filepath,
            media_type="application/pdf",
            filename=f"resiintel_report_{property_id}.pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF Generation Error: {str(e)}")
