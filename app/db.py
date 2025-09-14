# app/db.py
from typing import Optional
from pydantic_settings import BaseSettings
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from dotenv import load_dotenv

# load .env file (if present)
load_dotenv()

class Settings(BaseSettings):
    MONGO_URI: str = "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
    DB_NAME: str = "assessment_db"
    COLLECTION_NAME: str = "employees"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

settings = Settings()

# Global client/db references (populated on startup)
_mongo_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None
_employees_coll: Optional[AsyncIOMotorCollection] = None

async def connect_to_mongo() -> None:
    global _mongo_client, _db, _employees_coll
    try:
        _mongo_client = AsyncIOMotorClient(settings.MONGO_URI)
        _db = _mongo_client[settings.DB_NAME]
        _employees_coll = _db[settings.COLLECTION_NAME]
        await _employees_coll.create_index("employee_id", unique=True)
        await _employees_coll.create_index("department")
        await _employees_coll.create_index("skills")
        await _employees_coll.create_index("joining_date")

        print(f"[db] Connected to MongoDB: {settings.DB_NAME}/{settings.COLLECTION_NAME}")
    except Exception as e:
        print(f"[db] Failed to connect to MongoDB: {e}")
        raise

async def close_mongo_connection() -> None:
    """Close Motor client (call on app shutdown)."""
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        print("[db] MongoDB connection closed")

def get_db() -> AsyncIOMotorDatabase:
    """Return the Motor database instance (non-async function usable as dependency)."""
    if _db is None:
        raise RuntimeError("Database is not initialized. Did you run connect_to_mongo() on startup?")
    return _db

def get_employees_collection() -> AsyncIOMotorCollection:
    """Return the employees collection object."""
    if _employees_coll is None:
        raise RuntimeError("Employees collection is not initialized. Did you run connect_to_mongo() on startup?")
    return _employees_coll
