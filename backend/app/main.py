import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import app.models  # noqa: F401  (registers all models on Base.metadata)
from app.api.routes import auth, chat, documents, integrations, live_meetings, meetings, search, tasks, users, workspaces
from app.core.config import settings

from app.database.base import Base
from app.database.session import engine

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
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Global exception on {request.url.path}: {exc}", exc_info=True)
    response = JSONResponse(
        status_code=500,
        content={"detail": str(exc) or "Internal Server Error"},
    )
    origin = request.headers.get("origin")
    if origin:
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
app.include_router(tasks.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(integrations.router)



@app.on_event("startup")
def on_startup() -> None:
    # Ensures the pgvector extension exists and schema columns are synchronized
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'password_hash') THEN
                        ALTER TABLE users DROP COLUMN password_hash;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'clerk_id') THEN
                        ALTER TABLE users ADD COLUMN clerk_id VARCHAR(255);
                        CREATE UNIQUE INDEX IF NOT EXISTS ix_users_clerk_id ON users (clerk_id);
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'avatar_url') THEN
                        ALTER TABLE users ADD COLUMN avatar_url VARCHAR(1024);
                    END IF;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'meetings') THEN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'meetings' AND column_name = 'source') THEN
                        ALTER TABLE meetings ADD COLUMN source VARCHAR(32) DEFAULT 'upload' NOT NULL;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'meetings' AND column_name = 'native_meeting_id') THEN
                        ALTER TABLE meetings ADD COLUMN native_meeting_id VARCHAR(255);
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'meetings' AND column_name = 'vexa_bot_id') THEN
                        ALTER TABLE meetings ADD COLUMN vexa_bot_id VARCHAR(255);
                    END IF;
                END IF;
            END $$;
        """))
    Base.metadata.create_all(bind=engine)




@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
