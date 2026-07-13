from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# connect_args={"check_same_thread": False} is required only for SQLite.
# It allows multiple threads to access the database connection concurrently,
# which is common during FastAPI request handling.
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args
)

# sessionmaker creates configured Session classes.
# autocommit=False ensures transactions are manually committed/rolled back.
# autoflush=False prevents automatic database query flushes before commitments.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative ORM models
Base = declarative_base()
