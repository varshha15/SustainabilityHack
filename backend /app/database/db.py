from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "sustainability_db"
    ML_SERVICE_URL: str = "http://localhost:8001"
    APP_ENV: str = "development"
    SECRET_KEY: str = "dev-secret-key"

    class Config:
        env_file = ".env"


settings = Settings()

# Global client instance
client: AsyncIOMotorClient = None


async def connect_db():
    """Connect to MongoDB on app startup."""
    global client
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    print(f"[DB] Connected to MongoDB → {settings.DATABASE_NAME}")


async def close_db():
    """Disconnect from MongoDB on app shutdown."""
    global client
    if client:
        client.close()
        print("[DB] MongoDB connection closed")


def get_database():
    return client[settings.DATABASE_NAME]


def get_collection(name: str):
    return get_database()[name]
