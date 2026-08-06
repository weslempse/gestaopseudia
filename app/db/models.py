from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import pathlib

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/healthdb.sqlite3")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine)

def init_db():
    # execute migrations/init.sql to create tables
    root = pathlib.Path(__file__).parent.parent
    sqlfile = root / "migrations" / "init.sql"
    with engine.begin() as conn:
        conn.execute(sqlfile.read_text())
