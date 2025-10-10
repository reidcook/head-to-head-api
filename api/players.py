
from multiprocessing import Value
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator
from bson import ObjectId

from api.dependencies.mongo import get_database
from api.utils import serialize_doc


class Player(BaseModel):
    name: str = Field(..., description="Player's name (required)")
    groupId: str = Field(..., description="Group ID the player belongs to (required)")

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        extra = "allow"  # Accept additional fields
        json_encoders = {ObjectId: str}

    @field_validator("name", mode="before")
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Name must be a non-empty string")
        return v

player_router = APIRouter()

@player_router.get("/players/all", tags=["players"])
async def get_all_players(db: AsyncIOMotorDatabase = Depends(get_database)):
    players = await db["players"].find().to_list()
    return {"players": [serialize_doc(p) for p in players]}

@player_router.get("/players/{groupId}", tags=["players"])
async def get_players_by_group(groupId: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    players = await db["players"].find({"groupId": groupId}).to_list()
    return {"players": [serialize_doc(p) for p in players]}

@player_router.post("/players", tags=["players"])
async def create_player(player: Player, db: AsyncIOMotorDatabase = Depends(get_database)):
    player_dict = player.model_dump()
    player_same_name = await db["players"].find_one({"name": player_dict["name"], "groupId": player_dict["groupId"]})
    if player_same_name:
        raise ValueError("Player with the same name and group ID already exists")
    result = await db["players"].insert_one(player_dict)
    player_dict["_id"] = str(result.inserted_id)
    return {"player": player_dict}

@player_router.delete("/players/all", tags=["players"])
async def delete_all_players(db: AsyncIOMotorDatabase = Depends(get_database)):
    result = await db["players"].delete_many({})
    return {"deleted_count": result.deleted_count}

@player_router.delete("/players/{name}/{groupId}", tags=["players"])
async def delete_player(name: str, groupId: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    result = await db["players"].delete_one({"name": name, "groupId": groupId})
    return {"deleted_count": result.deleted_count}