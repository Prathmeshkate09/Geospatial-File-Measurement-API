import json
from pydantic import BaseModel, validator
from typing import Optional, List

class FileResponse(BaseModel):
    id: str
    filename: str
    status: str
    feature_count: Optional[int] = None
    crs: Optional[str] = None

    class Config:
        orm_mode = True

class FeatureMeasurementResponse(BaseModel):
    feature_index: int
    geom_type: str
    area: Optional[float] = None
    length: Optional[float] = None
    properties: Optional[dict] = None

    @validator("properties", pre=True)
    def parse_properties(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v

    class Config:
        orm_mode = True
