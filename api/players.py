
from multiprocessing import Value
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator
from bson import ObjectId

from api.dependencies.mongo import get_database
from api.utils import serialize_doc
from api.admin_config import FieldConfig


class Player(BaseModel):
    name: str = Field(..., description="Player's name (required)")
    character: str = Field(..., description="Player's character (required)")
    debut: str = Field(..., description="Player's debut tournament (required)")
    image: str = Field(..., description="Player's image (required)")
    details: str = Field(..., description="Player details (required)")
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

player_fields: list[FieldConfig] = [
    {"field": "name", "headerName": "Name", "map_to": "players", "form_type": "autocomplete"}, 
    {"field": "character", "headerName": "Character", "map_to": "smash_char", "form_type": "autocomplete"}, 
    {"field": "debut", "headerName": "Debut", "map_to": "tournaments", "form_type": "autocomplete"},
    {"field": "details", "headerName": "Details", "form_type": "input"},
    {"field": "image", "hide": True, "form_type": "image"},
]
player_match_fields: list[FieldConfig] = [
    {"field": "opponent", "headerName": "Opponent"}, 
    {"field": "winner", "headerName": "Winner"}, 
    {"field": "tournament", "headerName": "Tournament"}
]

@player_router.get("/players/all", tags=["players"])
async def get_all_players(db: AsyncIOMotorDatabase = Depends(get_database)):
    players = await db["players"].find().to_list()
    return {"players": [serialize_doc(p) for p in players]}

@player_router.get("/players/{groupId}", tags=["players"])
async def get_players_by_group(groupId: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    # fetch players in this group
    players = await db["players"].find({"groupId": groupId}).to_list()

    # fetch all matches in the same group so we can associate them to players
    matches = await db["matches"].find({"groupId": groupId}).to_list()

    # serialize matches once for reuse
    serialized_matches = [serialize_doc(m) for m in matches]

    players_out = []
    for p in players:
        p_doc = serialize_doc(p)
        name = p_doc.get("name")
        # collect matches where this player is player1 or player2
        p_matches = []
        wins = 0
        losses = 0
        if name:
            for m in serialized_matches:
                p1 = m.get("player1")
                p2 = m.get("player2")
                if p1 == name or p2 == name:
                    p_match = m.copy()
                    p_match["opponent"] = p1 if p2 == name else p2
                    del p_match["player1"]
                    del p_match["player2"]
                    p_matches.append(p_match)
                    # increment wins/losses based on the recorded winner
                    winner = p_match.get("winner")
                    if winner == name:
                        wins += 1
                    else:
                        losses += 1

        p_doc["matches"] = {"data": p_matches}
        p_doc["wins"] = wins
        p_doc["losses"] = losses
        players_out.append(p_doc)

    return {"players": players_out, "player_display_data": player_fields, "matches_display_data": player_match_fields}

@player_router.post("/players", tags=["players"])
async def create_player(player: Player, db: AsyncIOMotorDatabase = Depends(get_database)):
    player_dict = player.model_dump()
    player_same_name = await db["players"].find_one({"name": player_dict["name"], "groupId": player_dict["groupId"]})
    tournament_exists = await db["tournaments"].find_one({"name": player_dict["debut"], "groupId": player_dict["groupId"]})
    if player_same_name:
        raise ValueError("Player with the same name and group ID already exists")
    if not tournament_exists:
        raise ValueError(f"Tournament {player_dict['debut']} does not exist.")
    result = await db["players"].insert_one(player_dict)
    player_dict["_id"] = str(result.inserted_id)
    return {"player": player_dict}


@player_router.put("/players/{player_id}", tags=["players"])
async def update_player(player_id: str, player: Player, db: AsyncIOMotorDatabase = Depends(get_database)):
    player_dict = player.model_dump()
    # ensure referenced debut tournament exists
    tournament_exists = await db["tournaments"].find_one({"name": player_dict["debut"], "groupId": player_dict["groupId"]})
    if not tournament_exists:
        raise ValueError(f"Tournament {player_dict['debut']} does not exist.")
    # ensure no other player in this group has the same name
    existing = await db["players"].find_one({"name": player_dict["name"], "groupId": player_dict["groupId"], "_id": {"$ne": ObjectId(player_id)}})
    if existing:
        raise ValueError("Player with the same name and group ID already exists")

    result = await db["players"].update_one({"_id": ObjectId(player_id)}, {"$set": player_dict})
    if result.matched_count == 0:
        raise ValueError("Player not found")
    updated = await db["players"].find_one({"_id": ObjectId(player_id)})
    return {"player": serialize_doc(updated)}

@player_router.delete("/players/all", tags=["players"])
async def delete_all_players(db: AsyncIOMotorDatabase = Depends(get_database)):
    result = await db["players"].delete_many({})
    return {"deleted_count": result.deleted_count}

@player_router.delete("/players/{name}/{groupId}", tags=["players"])
async def delete_player(name: str, groupId: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    result = await db["players"].delete_one({"name": name, "groupId": groupId})
    return {"deleted_count": result.deleted_count}