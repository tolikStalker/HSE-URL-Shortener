from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.links import router as links_router
from app.api.redirect import router as redirect_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(links_router)
api_router.include_router(redirect_router)
