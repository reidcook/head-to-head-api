from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi

_db = None
_client = None


MONGO_URL = os.getenv("MONGODB_URI")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client, _db
    _client = AsyncIOMotorClient(MONGO_URL, server_api=ServerApi("1"))
    _db = _client.get_database()
    print("CONNECTED")
    yield
    print("DISCONNECTED")
    _client.close()

async def get_database():   
    if _db is None:
        raise HTTPException("Database not initialized")
    return _db
