
from multiprocessing import Value
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator
from bson import ObjectId

from api.dependencies.mongo import get_database
from api.dependencies.auth import verify_admin
from api.utils import serialize_doc, upload_image_to_s3
from api.admin_config import FieldConfig
from api.utils import SMASH_CHARS


class Player(BaseModel):
    name: str = Field(..., description="Player's name (required)")
    character: str = Field(..., description="Player's character (required)")
    debut: str = Field(description="Player's debut tournament", default="")
    image: str = Field(..., description="Player's image (required)")
    details: str = Field(description="Player details", default="")
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

    return {"players": players_out}

@player_router.post("/players", tags=["players"])
async def create_player(player: Player, db: AsyncIOMotorDatabase = Depends(get_database), _=Depends(verify_admin)):
    player_dict = player.model_dump()
    player_same_name = await db["players"].find_one({"name": player_dict["name"], "groupId": player_dict["groupId"]})
    tournament_exists = True
    if player_dict.get("debut"):
        tournament_exists = await db["tournaments"].find_one({"name": player_dict["debut"], "groupId": player_dict["groupId"]})
    if player_same_name:
        raise ValueError("Player with the same name and group ID already exists")
    if not tournament_exists:
        raise ValueError(f"Tournament {player_dict['debut']} does not exist.")
    # If image is base64, upload to S3 and store the URL instead
    if player_dict.get("image", "").startswith("data:") or (len(player_dict.get("image", "")) > 500 and "/" not in player_dict.get("image", "")[:30]):
        player_dict["image"] = upload_image_to_s3(player_dict["name"], player_dict["image"])
    result = await db["players"].insert_one(player_dict)
    player_dict["_id"] = str(result.inserted_id)
    return {"player": player_dict}


@player_router.put("/players/{name}/{groupId}", tags=["players"])
async def update_player(name: str, groupId: str, player_dict: dict, db: AsyncIOMotorDatabase = Depends(get_database), _=Depends(verify_admin)):
    # ensure referenced debut tournament exists
    if player_dict.get("debut"):
        tournament_exists = await db["tournaments"].find_one({"name": player_dict["debut"], "groupId": groupId})
        if not tournament_exists:
            raise ValueError(f"Tournament {player_dict['debut']} does not exist.")
    # If image is base64, upload to S3 and store the URL instead
    if player_dict.get("image") and (player_dict["image"].startswith("data:") or (len(player_dict["image"]) > 500 and "/" not in player_dict["image"][:30])):
        player_dict["image"] = upload_image_to_s3(name, player_dict["image"])
    result = await db["players"].update_one({"name": name, "groupId": groupId}, {"$set": player_dict})
    if result.matched_count == 0:
        raise ValueError("Player not found")
    updated = await db["players"].find_one({"name": name, "groupId": groupId})
    return {"player": serialize_doc(updated)}

@player_router.delete("/players/all", tags=["players"])
async def delete_all_players(db: AsyncIOMotorDatabase = Depends(get_database)):
    result = await db["players"].delete_many({})
    return {"deleted_count": result.deleted_count}

@player_router.delete("/players/{name}/{groupId}", tags=["players"])
async def delete_player(name: str, groupId: str, db: AsyncIOMotorDatabase = Depends(get_database), _=Depends(verify_admin)):
    result = await db["players"].delete_one({"name": name, "groupId": groupId})
    return {"deleted_count": result.deleted_count}

@player_router.get("/smash_characters", tags=["players"])
async def get_smash_characters():
    return {"smash_characters": SMASH_CHARS}