import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import database
from app.services.ticket_service import ticket_service

logging.basicConfig(level=logging.INFO, format="%(message)s")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await database.initialize()
    await ticket_service.warm_codebase()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def healthcheck():
    return {"status": "ok", "codebase": "solidusio/solidus"}
