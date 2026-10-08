"""Workspace-authorized WebSocket for native live co-pilot alerts."""

import asyncio
import json
import uuid

import redis
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.api.deps import get_meeting_for_member
from app.core.config import settings
from app.core.security import verify_clerk_token
from app.database.session import SessionLocal
from app.models.user import User

router = APIRouter(prefix="/api/v1/meetings/live", tags=["live-meetings"])


@router.websocket("/{meeting_id}/insights")
async def stream_live_insights(websocket: WebSocket, meeting_id: uuid.UUID):
    await websocket.accept()
    db = SessionLocal()
    sub = None
    try:
        hello = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        claims = verify_clerk_token(hello.get("token", "")) if isinstance(hello, dict) else None
        user = db.query(User).filter(User.clerk_id == claims["sub"]).one_or_none() if claims and claims.get("sub") else None
        if user is None:
            await websocket.close(code=1008)
            return
        get_meeting_for_member(meeting_id, user, db)
        client = redis.Redis.from_url(settings.REDIS_URL)
        channel = f"native-meeting:{meeting_id}:insights"
        sub = client.pubsub(ignore_subscribe_messages=True)
        sub.subscribe(channel)
        for raw in reversed(client.lrange(f"native-meeting:{meeting_id}:insights-recent", 0, 19)):
            await websocket.send_json(json.loads(raw))
        while True:
            db.expire_all()
            get_meeting_for_member(meeting_id, user, db)
            message = await asyncio.to_thread(sub.get_message, timeout=1)
            if message:
                await websocket.send_json(json.loads(message["data"]))
            else:
                await websocket.send_json({"kind": "heartbeat"})
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    except HTTPException:
        await websocket.close(code=1008)
    finally:
        if sub:
            sub.close()
        db.close()
