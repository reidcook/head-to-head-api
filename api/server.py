import os

import firebase_admin
from firebase_admin import credentials
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import RequestValidationError
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.dependencies.mongo import lifespan, get_database

load_dotenv()

_service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
if _service_account_path:
    _cred = credentials.Certificate(_service_account_path)
    firebase_admin.initialize_app(_cred)
from api.players import player_router
from api.matches import match_router
from api.tournaments import tournament_router
from api.overview import overview_router
from api.admin_config import FieldConfig

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
app.include_router(overview_router)

@app.get("/")
async def health():
    return {"status": "good!"}