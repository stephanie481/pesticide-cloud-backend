import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry

Base = declarative_base()

class CloudFieldProfile(Base):
    __tablename__ = "field_profiles"

    id = Column(Integer, primary_key=True, index=True)
    
    # UUID allows safe sync ingestion from multiple offline Raspberry Pis without ID collisions
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    
    farmer_name = Column(String(150), index=True, nullable=False)
    crop_type = Column(String(100), nullable=False)
    area_hectares = Column(Float, nullable=False)
    pest_history_index = Column(Float, default=0.0)
    
    # POSTGIS Spatial Polygon Type (SRID 4326 stands for WGS 84 GPS standard coordinates)
    boundary_polygon = Column(Geometry(geometry_type='POLYGON', srid=4326), nullable=True)
    
    # Metadata for ingestion tracing
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    synced_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Parent-child relation with spray logs
    spray_logs = relationship("CloudSprayLog", back_populates="field", cascade="all, delete-orphan")


class CloudSprayLog(Base):
    __tablename__ = "spray_logs"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    
    # Relational linking using UUIDs so database tables line up even across networks
    field_uuid = Column(String(36), ForeignKey("field_profiles.uuid", ondelete="CASCADE"), nullable=False)
    
    technician_name = Column(String(150), nullable=False)
    chemical_used = Column(String(100), nullable=False)
    dosage_liters = Column(Float, nullable=False)
    
    # POSTGIS Spatial LineString Type (Traces the GPS path taken during pesticide spraying)
    gps_path_line = Column(Geometry(geometry_type='LINESTRING', srid=4326), nullable=True)
    
    applied_at = Column(DateTime, default=datetime.datetime.utcnow)
    synced_at = Column(DateTime, server_default=func.now())

    field = relationship("CloudFieldProfile", back_populates="spray_logs")


class CloudPestAlert(Base):
    __tablename__ = "pest_alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    description = Column(String(500), nullable=False)
    severity_level = Column(String(20), default="Medium")
    target_region = Column(String(100), nullable=False)
    
    # Point representing the center of the outbreak alert zone
    outbreak_center = Column(Geometry(geometry_type='POINT', srid=4326), nullable=True)
    
    broadcasted_at = Column(DateTime, default=datetime.datetime.utcnow)