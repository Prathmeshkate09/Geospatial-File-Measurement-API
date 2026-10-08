from sqlalchemy import Column, Integer, String, Float, ForeignKey
from geoalchemy2 import Geometry
from .database import Base

class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, index=True)
    status = Column(String, index=True)  # PENDING, PROCESSING, COMPLETED, FAILED
    feature_count = Column(Integer, nullable=True)
    crs = Column(String, nullable=True)

class FeatureMeasurement(Base):
    __tablename__ = "feature_measurements"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String, ForeignKey("uploaded_files.id", ondelete="CASCADE"), index=True)
    feature_index = Column(Integer)
    geom_type = Column(String)
    area = Column(Float, nullable=True)
    length = Column(Float, nullable=True)
    # 4326 is WGS 84 (Latitude/Longitude). Storing original geometries.
    geometry = Column(Geometry(geometry_type='GEOMETRY', srid=4326), nullable=True)
    properties = Column(String, nullable=True) # Storing as JSON string
