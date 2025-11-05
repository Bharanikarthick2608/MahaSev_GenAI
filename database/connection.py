"""
Database connection setup for Supabase PostgreSQL.
Uses SQLAlchemy with StaticPool for connection management.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

# Load environment variables
load_dotenv()

# Get database connection URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Please check your .env file.")

# Create the SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    poolclass=StaticPool,
    pool_pre_ping=True,
    pool_reset_on_return="commit",
    pool_recycle=300,
    echo=False
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Yields a database session and closes it after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Usage:
        with get_db_session() as db:
            result = db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def test_connection() -> bool:
    """Test database connection."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        error_msg = str(e)
        print(f"Database connection failed: {error_msg}")
        
        # Provide helpful debugging info
        if "password authentication failed" in error_msg.lower():
            print("\n⚠️  Authentication Error - Possible issues:")
            print("   1. Check if DATABASE_PASSWORD in .env matches your Supabase password")
            print("   2. Check if DATABASE_URL in .env has the correct password")
            print("   3. Verify the password in config/settings.py matches your Supabase credentials")
            print(f"\n   Current DATABASE_URL format: postgresql://postgres.vwbtwbmtbcvbuhjvzhcq:[PASSWORD]@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres")
        
        return False


def get_db_connection():
    """
    Get a raw database connection from the engine.
    Returns a connection object that can be used with execute(), commit(), close().
    
    Usage:
        conn = get_db_connection()
        try:
            result = conn.execute(text("SELECT * FROM table"))
            conn.execute(text("INSERT INTO table ..."))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    """
    try:
        return engine.connect()
    except Exception as e:
        print(f"Database connection error: {e}")
        raise


def get_connection_info() -> dict:
    """Get database connection information for debugging (without exposing password)."""
    url_parts = DATABASE_URL.split('@')
    if len(url_parts) == 2:
        user_part = url_parts[0].split('//')[1] if '//' in url_parts[0] else url_parts[0]
        host_part = url_parts[1]
        username = user_part.split(':')[0] if ':' in user_part else user_part
        
        return {
            "username": username,
            "host": host_part.split('/')[0] if '/' in host_part else host_part,
            "database": host_part.split('/')[1] if '/' in host_part else "postgres",
            "has_password": ":" in user_part and len(user_part.split(':')) > 1
        }
    return {"error": "Could not parse DATABASE_URL"}

