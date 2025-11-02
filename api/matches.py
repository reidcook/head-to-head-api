from pydantic import BaseModel, Field, ValidationInfo, field_validator
from bson import ObjectId
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase


from api.dependencies.mongo import get_database
from api.utils import serialize_doc


class Match(BaseModel):
    player1: str = Field(..., description="Name of the first player (required)")
    player2: str = Field(..., description="Name of the second player (required)")
    winner: str = Field(..., description="Name of the winning player (required)")
    tournament: str = Field(..., description="Tournament the match belonged to")
    groupId: str = Field(..., description="Group ID the match belongs to (required)")

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        extra = "allow"  # Accept additional fields
        json_encoders = {ObjectId: str}

    @field_validator("winner", mode="before")
    def validate_winner(cls, v, values: ValidationInfo):
        print(values)
        if v != values.data["player1"] and v != values.data["player2"]:
            raise ValueError("Winner must be either player1 or player2")
        return v
    
    @field_validator("player2", mode="before")
    def validate_players(cls, v, values: ValidationInfo):
        print(values)
        if v == values.data["player1"]:
            raise ValueError("player1 and player2 must be different")
        return v
    
match_router = APIRouter()

@match_router.get("/matches/all", tags=["matches"])
async def get_all_matches(db: AsyncIOMotorDatabase = Depends(get_database)):
    matches = await db["matches"].find().to_list()
    return {"matches": [serialize_doc(m) for m in matches]}

@match_router.get("/matches/{groupId}", tags=["matches"])
async def get_matches_by_group(groupId: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    matches = await db["matches"].find({"groupId": groupId}).to_list()
    return {"matches": [serialize_doc(m) for m in matches]}

@match_router.post("/matches", tags=["matches"])
async def create_match(match: Match, db: AsyncIOMotorDatabase = Depends(get_database)):
    match_dict = match.model_dump()
    player1 = await db["players"].find_one({"name": match_dict["player1"], "groupId": match_dict["groupId"]})
    player2 = await db["players"].find_one({"name": match_dict["player2"], "groupId": match_dict["groupId"]})
    tournament = await db["tournaments"].find_one({"name": match_dict["tournament"], "groupId": match_dict["groupId"]})
    if not player1 or not player2:
        raise ValueError("Both players must exist in the specified group")
    if not tournament:
        raise ValueError("Tournament must exist.")
    result = await db["matches"].insert_one(match_dict)
    match_dict["_id"] = str(result.inserted_id)
    return {"match": match_dict}

@match_router.delete("/matches/all", tags=["matches"])
async def delete_all_matches(db: AsyncIOMotorDatabase = Depends(get_database)):
    result = await db["matches"].delete_many({})
    return {"deleted_count": result.deleted_count}

@match_router.delete("/matches/{match_id}", tags=["matches"])
async def delete_match(match_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    result = await db["matches"].delete_one({"_id": ObjectId(match_id)})
    return {"deleted_count": result.deleted_count}