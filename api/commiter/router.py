from fastapi import APIRouter, HTTPException, Request, Depends
from db.session import get_db
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from security.auth import get_client_info
from core.config import settings
from worker.task import commiter

commiter_router = APIRouter()


@commiter_router.get("/deepti")
def deepti(key: str):
    try:
        if key != settings.API_ACCESS_KEY:
            raise HTTPException(status_code=401, detail="Invalid key")
        commiter()
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "messgae": None,
                "data": None,
                "error": None,
            }
        )
    except HTTPException as httpe:
        raise httpe
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ERROR 11: {e}")