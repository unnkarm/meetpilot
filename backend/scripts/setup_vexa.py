"""Create local Vexa service credentials once, without printing secrets."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[2]
target = root / "backend/.env.vexa"
if target.exists():
    print("Keeping existing backend/.env.vexa")
else:
    token = lambda: secrets.token_hex(32)
    admin, stt, tts, bus, storage, database = (token() for _ in range(6))
    values = {
        "VEXA_API_URL": "http://vexa:8056", "VEXA_ADMIN_URL": "http://vexa:8001",
        "VEXA_ADMIN_TOKEN": admin, "ADMIN_API_TOKEN": admin,
        "VEXA_STT_TOKEN": stt, "TRANSCRIPTION_SERVICE_TOKEN": stt,
        "VEXA_TTS_TOKEN": tts, "TTS_API_TOKEN": tts,
        "VEXA_REDIS_PASSWORD": bus, "VEXA_REDIS_URL": f"redis://:{bus}@vexa_redis:6379/0",
        "REDIS_URL": f"redis://:{bus}@vexa_redis:6379/0",
        "DB_PASSWORD": database, "POSTGRES_PASSWORD": database,
        "MINIO_ACCESS_KEY": "meetpilot-vexa", "ROOT_ACCESS_KEY": "meetpilot-vexa",
        "MINIO_SECRET_KEY": storage, "ROOT_SECRET_KEY": storage,
        "NEXTAUTH_SECRET": token(), "JWT_SECRET": token(),
        "TRANSCRIPTION_SERVICE_URL": "http://backend:8000/internal/vexa",
        "TTS_SERVICE_URL": "http://backend:8000/internal/vexa",
    }
    target.write_text("\n".join(f"{k}={v}" for k, v in values.items()) + "\n", encoding="utf-8")
    print("Created backend/.env.vexa. Keep this file private and retain it across restarts.")
