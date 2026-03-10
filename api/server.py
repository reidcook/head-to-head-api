from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import RequestValidationError
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.utils import SMASH_CHARS
from api.dependencies.mongo import lifespan, get_database
from api.players import player_router, player_fields
from api.matches import match_router, match_fields
from api.tournaments import tournament_router, tournament_fields
from api.admin_config import FieldConfig

load_dotenv()


origins = [
    "https://localhost:5173"
]


app = FastAPI(lifespan=lifespan)

# Global handler for Pydantic validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": [err['msg'] for err in exc.errors()]},
    )

# Global handler for Pydantic validation errors
@app.exception_handler(ValueError)
async def validation_exception_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"error": [str(exc)]},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(player_router)
app.include_router(match_router)
app.include_router(tournament_router)

@app.get("/")
async def health():
    return {"status": "good!"}

@app.get("/admin/config")
async def model_structure(db: AsyncIOMotorDatabase = Depends(get_database)):
    enriched_player_fields = await enrich_fields(player_fields.copy(), db)
    enriched_match_fields = await enrich_fields(match_fields.copy(), db)
    enriched_tournament_fields = await enrich_fields(tournament_fields.copy(), db)       
    return {"player": enriched_player_fields, "match": enriched_match_fields.copy(), "tournament": enriched_tournament_fields}

async def enrich_fields(fields: list[FieldConfig], db):
    options = []
    for field in fields:
        if "map_to" in field: # TODO add to mongo maybe?
            if field["map_to"] == "smash_char":
                options = SMASH_CHARS
            else:
                wip_options = await db[field["map_to"]].find().to_list()
                options = [m["name"] for m in wip_options]
            field["options"] = options
    return fields