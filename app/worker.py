import os
import logging
from celery import Celery
from .database import SessionLocal
from .models import UploadedFile, FeatureMeasurement
from .geo_utils import process_file_measurements

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

@celery_app.task(name="process_geospatial_file")
def process_geospatial_file(file_id: str, file_path: str, original_filename: str):
    db = SessionLocal()
    
    # Get the file record
    db_file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if not db_file:
        db.close()
        return "File record not found."
    
    try:
        db_file.status = "PROCESSING"
        db.commit()

        # Process the file
        features, crs = process_file_measurements(file_path, original_filename)
        
        # Save features to DB
        measurements_to_insert = []
        for feat in features:
            measurements_to_insert.append(
                FeatureMeasurement(
                    file_id=file_id,
                    feature_index=feat['feature_index'],
                    geom_type=feat['geom_type'],
                    area=feat['area'],
                    length=feat['length'],
                    geometry=f"SRID=4326;{feat['geometry_wkt']}" if feat['geometry_wkt'] else None,
                    properties=feat['properties']
                )
            )
        
        db.bulk_save_objects(measurements_to_insert)
        

        # Update file status
        db_file.status = "COMPLETED"
        db_file.feature_count = len(features)
        db_file.crs = crs
        db.commit()
        logger.info(f"Successfully processed file {file_id}. Found {len(features)} features.")
        
    except Exception as e:
        db_file.status = "FAILED"
        db.commit()
        logger.error(f"Error processing file {file_id}: {str(e)}", exc_info=True)
    finally:
        db.close()
        # Optionally remove the uploaded file to save disk space
        if os.path.exists(file_path):
            os.remove(file_path)

    return f"Processed {file_id}"
