from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime,timezone

Base = declarative_base()

class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True)
    worker_id = Column(String, nullable=False)
    first_seen = Column(DateTime, default=datetime.now(timezone.utc))
    last_seen = Column(DateTime, default=datetime.now(timezone.utc))

class Violation(Base):
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True)
    worker_id = Column(String, nullable=False)
    violation_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    zone = Column(String, default="general")
    confidence = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))
    snapshot_path = Column(String, nullable=True)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    worker_id = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String, nullable=False)
    violation_type = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))
    resolved = Column(Boolean, default=False)