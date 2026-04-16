"""
One-time script: removes the image field from all player documents in MongoDB.

Usage:
    uv run python clear_images_from_mongo.py
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()


async def clear_images():
    client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
    db = client.get_default_database()

    result = await db["players"].update_many({}, {"$unset": {"image": ""}})
    print(f"Cleared image field from {result.modified_count} player(s).")
    client.close()


if __name__ == "__main__":
    asyncio.run(clear_images())
