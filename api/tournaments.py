from bson import ObjectId
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.dependencies.mongo import get_database
from api.utils import serialize_doc
from api.admin_config import FieldConfig

class Tournament(BaseModel):
    name: str = Field(..., description="Tournament name (required)")
    winner: str = Field(..., description="Name of player who won (required)")
    date: str = Field(..., description="Date of the Tournament (required)")
    groupId: str = Field(..., description="Group ID the match belongs to (required)")

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        extra = "allow"  # Accept additional fields
        json_encoders = {ObjectId: str}

tournament_router = APIRouter()

tournament_fields: FieldConfig = [
    {"field": "name", "headerName": "Name", "map_to": "tournaments", "form_type": "autocomplete"}, 
    {"field": "winner", "headerName": "Winner", "map_to": "players", "form_type": "autocomplete"}, 
    {"field": "date", "headerName": "Date", "form_type": "input"}
]

@tournament_router.get("/tournaments/all", tags=["tournaments"])
async def get_all_matches(db: AsyncIOMotorDatabase = Depends(get_database)):
    tournaments = await db["tournaments"].find().to_list()
    return {"tournaments": [serialize_doc(m) for m in tournaments]}

@tournament_router.get("/tournaments/{groupId}", tags=["tournaments"])
async def get_matches_by_group(groupId: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    tournaments = await db["tournaments"].find({"groupId": groupId}).to_list()
    return {"tournaments": [serialize_doc(m) for m in tournaments]}

@tournament_router.post("/tournaments", tags=["tournaments"])
async def create_match(match: Tournament, db: AsyncIOMotorDatabase = Depends(get_database)):
    tournament_dict = match.model_dump()
    tournament_same_name = await db["tournaments"].find_one({"name": tournament_dict["name"], "groupId": tournament_dict["groupId"]})
    player_exists = await db["players"].find_one({"name": tournament_dict["winner"], "groupId": tournament_dict["groupId"]})
    if tournament_same_name:
        raise ValueError("Tournament with the same name and group ID already exists")
    if not player_exists:
        raise ValueError(f"Player {tournament_dict['winner']} does not exists.")
    result = await db["tournaments"].insert_one(tournament_dict)
    tournament_dict["_id"] = str(result.inserted_id)
    return {"tournament": tournament_dict}


@tournament_router.put("/tournaments/{tournament_id}", tags=["tournaments"])
async def update_tournament(tournament_id: str, tournament: Tournament, db: AsyncIOMotorDatabase = Depends(get_database)):
    tdict = tournament.model_dump()
    player_exists = await db["players"].find_one({"name": tdict["winner"], "groupId": tdict["groupId"]})
    if not player_exists:
        raise ValueError(f"Player {tdict['winner']} does not exists.")
    result = await db["tournaments"].update_one({"_id": ObjectId(tournament_id)}, {"$set": tdict})
    if result.matched_count == 0:
        raise ValueError("Tournament not found")
    updated = await db["tournaments"].find_one({"_id": ObjectId(tournament_id)})
    return {"tournament": serialize_doc(updated)}

@tournament_router.delete("/tournaments/all", tags=["tournaments"])
async def delete_all_matches(db: AsyncIOMotorDatabase = Depends(get_database)):
    result = await db["tournaments"].delete_many({})
    return {"deleted_count": result.deleted_count}

@tournament_router.delete("/tournaments/{tournament_id}", tags=["tournaments"])
async def delete_tournament(tournament_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    result = await db["tournaments"].delete_one({"_id": ObjectId(tournament_id)})
    return {"deleted_count": result.deleted_count}