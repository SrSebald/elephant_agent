from fastapi import APIRouter

from app.api.v1.endpoints.tickets import router as tickets_router

api_router = APIRouter()
api_router.include_router(tickets_router, prefix="/tickets", tags=["tickets"])
