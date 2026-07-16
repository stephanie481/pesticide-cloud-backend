# cloud_main.py
import os
from typing import List, Dict, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Import our database schemas and helper utilities
from cloud_models import Base, CloudFieldProfile, CloudSprayLog
from spatial_helpers import json_to_polygon, json_to_linestring

# Configure the PostgreSQL + PostGIS Connection URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://username:password@localhost:5432/pesticide_cloud_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Ensure database tables exist (automatically provisions PostGIS tables)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Pesticide Analytics Central Cloud Ingestion Hub",
    description="Secured endpoint registry receiving GIS and ML tracking logs from edge gateways.",
    version="1.0.0"
)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Schemas for Ingestion validation ---
class FieldSyncInput(BaseModel):
    uuid: str
    farmer_name: str
    crop_type: str
    area_hectares: float
    pest_history_index: float
    polygon_coordinates: Optional[List[Dict[str, float]]] = None

class SprayLogSyncInput(BaseModel):
    uuid: str
    field_uuid: str
    technician_name: str
    chemical_used: str
    dosage_liters: float
    gps_path_coordinates: Optional[List[Dict[str, float]]] = None


# --- 1. Field Profile Sync Ingest ---
@app.post("/api/sync/fields/", status_code=status.HTTP_201_CREATED)
def sync_field_profile(payload: FieldSyncInput, db: Session = Depends(get_db)):
    # Check if this record was already synced previously to prevent duplicates
    existing = db.query(CloudFieldProfile).filter(CloudFieldProfile.uuid == payload.uuid).first()
    if existing:
        return {"status": "skipped", "message": f"Field {payload.uuid} already synchronized."}

    # Convert coordinates to native PostGIS Polygon geometry
    boundary_geo = None
    if payload.polygon_coordinates:
        try:
            boundary_geo = json_to_polygon(payload.polygon_coordinates)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid boundary polygon format: {str(e)}")

    db_field = CloudFieldProfile(
        uuid=payload.uuid,
        farmer_name=payload.farmer_name,
        crop_type=payload.crop_type,
        area_hectares=payload.area_hectares,
        pest_history_index=payload.pest_history_index,
        boundary_polygon=boundary_geo
    )
    
    db.add(db_field)
    db.commit()
    return {"status": "success", "synced_uuid": payload.uuid}


# --- 2. Spray Log Sync Ingest ---
@app.post("/api/sync/spray-logs/", status_code=status.HTTP_201_CREATED)
def sync_spray_log(payload: SprayLogSyncInput, db: Session = Depends(get_db)):
    existing = db.query(CloudSprayLog).filter(CloudSprayLog.uuid == payload.uuid).first()
    if existing:
        return {"status": "skipped", "message": f"Spray Log {payload.uuid} already synchronized."}

    # Verify that the parent field exists in our cloud DB
    parent_field = db.query(CloudFieldProfile).filter(CloudFieldProfile.uuid == payload.field_uuid).first()
    if not parent_field:
        raise HTTPException(
            status_code=400, 
            detail=f"Foreign Key Error: Parent Field UUID '{payload.field_uuid}' does not exist on Cloud."
        )

    # Convert GPS paths into native PostGIS LineString geometry
    path_geo = None
    if payload.gps_path_coordinates:
        try:
            path_geo = json_to_linestring(payload.gps_path_coordinates)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid GPS tracking coordinates: {str(e)}")

    db_log = CloudSprayLog(
        uuid=payload.uuid,
        field_uuid=payload.field_uuid,
        technician_name=payload.technician_name,
        chemical_used=payload.chemical_used,
        dosage_liters=payload.dosage_liters,
        gps_path_line=path_geo
    )

    db.add(db_log)
    db.commit()
    return {"status": "success", "synced_uuid": payload.uuid}

@app.get("/api/sync/spray-logs/")
def get_spray_logs(db: Session = Depends(get_db)):
    """Debug route to fetch telemetry spray logs and expose errors."""
    import traceback
    try:
        # 1. Attempt to query the database
        logs = db.query(models.SprayLog).order_by(models.SprayLog.applied_at.desc()).all()
        return logs
    except Exception as e:
        # 2. Capture the full traceback and return it inside the 500 error
        error_details = traceback.format_exc()
        raise HTTPException(
            status_code=500, 
            detail={
                "message": "Database query failed!",
                "error": str(e),
                "traceback": error_details.split("\n")  # Keeps it readable in JSON
            }
        )
