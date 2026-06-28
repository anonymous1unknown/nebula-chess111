from fastapi import APIRouter
router = APIRouter()

@router.get("/")
async def list_tournaments():
    return {"tournaments": [], "message": "Tournament system ready — v2 expansion"}
