import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  (registers all models on Base.metadata)
from app.api.routes import auth, chat, documents, integrations, live_insights, live_meetings, meetings, pilot_phase1, pilot_voice, search, tasks, users, workspaces
from app.core.config import settings
from app.api.routes import vexa_audio


from starlette.requests import Request
from starlette.responses import JSONResponse

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="MeetPilot AI API", version="0.1.0")

# Comprehensive CORS origins for local development and production
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
for origin in settings.cors_origins_list:
    if origin not in origins:
        origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Global exception on {request.url.path}: {exc}", exc_info=True)
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )
    origin = request.headers.get("origin")
    if origin in origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    return response

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(workspaces.router)
app.include_router(meetings.router)
app.include_router(live_meetings.router)
app.include_router(live_insights.router)
app.include_router(tasks.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(integrations.router)
app.include_router(pilot_phase1.router)
app.include_router(pilot_voice.router)
app.include_router(vexa_audio.router)



@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
