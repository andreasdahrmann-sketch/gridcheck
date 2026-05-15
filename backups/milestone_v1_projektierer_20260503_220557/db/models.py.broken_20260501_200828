from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from datetime import datetime, timezone
from .database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    project_type = Column(String)
    power_kw = Column(Float)
    voltage_level = Column(String)
    location = Column(String)
    grid_operator = Column(String)
    distance_to_grid_m = Column(Float)
    existing_connection = Column(Boolean, default=False)
    status = Column(String, default="draft")
    result_score = Column(Float, default=0.0)
    result_traffic_light = Column(String, default="unknown")
    result_details = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    role = Column(String, default="projektierer")
    role_inputs = Column(Text, default="{}")
    role_results = Column(Text, default="{}")
