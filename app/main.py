import os
import uuid
import shutil
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas
from .database import engine, get_db, Base
from .worker import process_geospatial_file

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Geospatial File Measurement API",
    description="API for processing and measuring geometries in geospatial files.",
    version="1.0.0"
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/files/", response_model=schemas.FileResponse, status_code=202)
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Uploads and processes a geospatial file (.zip Shapefile or .kml).
    Returns immediately while processing happens in the background.
    """
    valid_extensions = ('.zip', '.kml')
    if not file.filename.lower().endswith(valid_extensions):
        raise HTTPException(status_code=400, detail="Only .zip (Shapefile) or .kml files are supported.")
        
    # Basic MIME type checking
    if file.content_type not in ["application/zip", "application/x-zip-compressed", "application/vnd.google-earth.kml+xml", "application/xml", "text/xml"]:
        # Some clients send kml as application/xml or text/xml
        raise HTTPException(status_code=400, detail="Invalid file content type.")
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    
    # Save the file to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create DB record
    db_file = models.UploadedFile(
        id=file_id,
        filename=file.filename,
        status="PENDING"
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    # Send task to Celery
    process_geospatial_file.delay(file_id, file_path, file.filename)
    
    return db_file

@app.get("/api/files/{id}/", response_model=schemas.FileResponse)
def get_file_info(id: str, db: Session = Depends(get_db)):
    """
    Returns information about the uploaded file and its processing status.
    """
    db_file = db.query(models.UploadedFile).filter(models.UploadedFile.id == id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    return db_file

@app.get("/api/files/{id}/measurements/", response_model=List[schemas.FeatureMeasurementResponse])
def get_measurements(id: str, db: Session = Depends(get_db)):
    """
    Returns measurements for the features in the file.
    """
    db_file = db.query(models.UploadedFile).filter(models.UploadedFile.id == id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
        
    if db_file.status != "COMPLETED":
        raise HTTPException(status_code=400, detail=f"File processing status is {db_file.status}")

    measurements = db.query(models.FeatureMeasurement).filter(models.FeatureMeasurement.file_id == id).all()
    return measurements
