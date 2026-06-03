from fastapi import APIRouter, HTTPException, Request, Depends
from db.session import get_db
from security.auth import get_client_info, create_access_token, token_required
from .schema import LoginSchema
from core.config import settings
import utils.util as util
from fastapi.responses import JSONResponse
import uuid
auth_router = APIRouter()

@auth_router.get("/verify")
def verify(user_data: dict = Depends(token_required(allowed_roles=["user"]))):
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": "verify sucess",
            "data": None,
            "error": None
        }
    )

@auth_router.post("/login")
async def login(
    request: Request,
    data: LoginSchema
):
    try:
        if data.username != settings.USER_NAME or data.password != settings.PASSWORD:
            raise HTTPException(status_code=403, detail="invalid Cradential")
        
        random_uuid = str(uuid.uuid4())
        if data.remember_me == True:
            minute = settings.ACCESS_TOKEN_EXPIRE_MINUTES_LONG
            exp_time = settings.ACCESS_TOKEN_EXPIRE_MLSECOND_LONG
        else:
            minute = settings.ACCESS_TOKEN_EXPIRE_MINUTES_SHORT
            exp_time = settings.ACCESS_TOKEN_EXPIRE_MLSECOND_SHORT

        client_info =  await get_client_info(request)
        fingerprint = util.generate_fingerprint(client_info["ip"], client_info["user_agent"])
        
        token = create_access_token(1, "user", "active", random_uuid, minute, fingerprint)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Login success full",
                "data":{
                    "role": "user",
                    "token": token,
                    "exp_time": exp_time
                    },
                "error": None   
            }
        )
    except HTTPException as http:
        raise http
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

