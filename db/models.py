from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Worker(Base):
    """Tracked worker sessions."""
    __tablename__ = "workers"

    id         = Column(Integer, primary_key=True)
    worker_id  = Column(String, nullable=False)   # W-01, W-02
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen  = Column(DateTime, default=datetime.utcnow)


class Violation(Base):
    """Every PPE or posture violation detected."""
    __tablename__ = "violations"

    id             = Column(Integer, primary_key=True)
    worker_id      = Column(String, nullable=False)
    violation_type = Column(String, nullable=False)   # NO-Hardhat, fall etc.
    severity       = Column(String, nullable=False)   # CRITICAL, HIGH, MEDIUM
    zone           = Column(String, default="general")
    confidence     = Column(Float,  nullable=True)
    timestamp      = Column(DateTime, default=datetime.utcnow)
    snapshot_path  = Column(String, nullable=True)    # path to saved frame


class Alert(Base):
    """Every alert that was fired."""
    __tablename__ = "alerts"

    id             = Column(Integer, primary_key=True)
    worker_id      = Column(String, nullable=False)
    message        = Column(Text,   nullable=False)
    severity       = Column(String, nullable=False)
    violation_type = Column(String, nullable=False)
    timestamp      = Column(DateTime, default=datetime.utcnow)
    resolved       = Column(Boolean, default=False)