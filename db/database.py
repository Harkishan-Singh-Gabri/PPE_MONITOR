import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from db.models import Base
from utils.logger import log

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine       = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    log.info("Database tables created/verified")


def get_session():
    return SessionLocal()


if __name__ == "__main__":
    init_db()
    log.info("Database initialized successfully")