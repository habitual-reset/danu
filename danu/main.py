from contextlib import asynccontextmanager

from fastapi import FastAPI

from danu.api.routes.health import router as health_router
from danu.api.routes.twilio_sms import router as twilio_sms_router
from danu.api.routes.twilio_voice import router as twilio_voice_router
from danu.config import get_settings
from danu.db.base import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="DANU",
        description="Personal AI assistant with reliable persistent memory",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.include_router(health_router)
    app.include_router(twilio_sms_router)
    app.include_router(twilio_voice_router)
    return app


app = create_app()