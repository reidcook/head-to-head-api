import os

from mangum import Mangum
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


from api.players import player_router
from api.matches import match_router
from api.tournaments import tournament_router
from api.overview import overview_router
from api.admin_config import FieldConfig

_service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
if _service_account_json:
    import json
    _cred = credentials.Certificate(json.loads(_service_account_json))
    firebase_admin.initialize_app(_cred)

origins = [
    "http://localhost:5173",
    "https://localhost:5173",
    "https://romega.club",
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
    allow_origins=origins,
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

handler = Mangum(app)