from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from security.auth import token_required
from core.config import settings
import requests

vibelist_router = APIRouter()


@vibelist_router.get("/view-creator-entries")
def view_creator_entries(_user_data: dict = Depends(token_required(allowed_roles=["user"]))):
    try:
        url = "https://filestoresystem-deepti.onrender.com/stp/v1/creator_entries"

        headers = {
            "MASTER-API-KEY": settings.MASTER_API_KEY
        }


        response = requests.get(url, headers=headers, timeout=10)

        response_data = response.json()

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Data retrieved successfully",
                "data": response_data.get("data"),
                "error": None
            }
        )
    except HTTPException as http:
        raise http
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@vibelist_router.get("/view-partner-entries")
def view_partner_entries(_user_data: dict = Depends(token_required(allowed_roles=["user"]))):
    try:
        url = "https://filestoresystem-deepti.onrender.com/stp/v1/partners_entries"

        headers = {
            "MASTER-API-KEY": settings.MASTER_API_KEY
        }


        response = requests.get(url, headers=headers, timeout=10)

        response_data = response.json()

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Data retrieved successfully",
                "data": response_data.get("data"),
                "error": None
            }
        )
    except HTTPException as http:
        raise http
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")