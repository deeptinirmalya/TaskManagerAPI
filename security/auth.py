import jwt
import os
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
from sqlalchemy import select
from core.config import settings
from utils import util
from db.session import get_db
# from db.base import TokenBlacklist

SECRET_KEY = settings.SECRET_KEY
if settings.PYTHON_ENV == "production" and len(SECRET_KEY) < 32:
    raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters in production for high-grade security")

ALGORITHM = settings.ALGORITHM

def create_access_token(user_id: int, role: str, status: str, jti: str, minutes: int, fingerprint: str = None):
    """Creates a short-lived access token (using config value)."""
    expire = util.get_now_utc() + timedelta(minutes=minutes)
    to_encode = {
        "sub": str(user_id),
        "user_id": user_id,
        "role": role,
        "status": status,
        "jti": jti,
        "fpt": fingerprint, 
        "exp": expire,
        "type": "access"
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def token_required(allowed_roles: list):

    async def token_checker(request: Request):
        referer = request.headers.get("referer", "")
        is_docs_request = "/docs" in referer or "/redoc" in referer
        is_dev = settings.PYTHON_ENV == "development"

        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        
        if not token:
            raise HTTPException(status_code=401, detail="Missing access token")

        if not auth_header and request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            if not is_docs_request and not request.headers.get("X-Requested-With"):
                raise HTTPException(status_code=403, detail="CSRF Protection: Missing X-Requested-With header")
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            if payload.get("type") != "access":
                raise HTTPException(status_code=401, detail="Invalid token type")

            client = await get_client_info(request)
            current_fpt = util.generate_fingerprint(client['ip'], client['user_agent'])
            token_fpt = payload.get("fpt")
            
            if token_fpt and token_fpt != current_fpt:
                raise HTTPException(status_code=401, detail="Session binding violation. Please login again.")

            # jti = payload.get("jti")
            # db_gen = get_db()
            # db = next(db_gen) 
            # try:
            #     blocked = db.execute(
            #         select(TokenBlacklist.jti).where(
            #             TokenBlacklist.jti == jti,
            #             TokenBlacklist.expires_at > util.get_now_utc()
            #         )
            #     ).scalar_one_or_none()
                
            #     if blocked:
            #         raise HTTPException(status_code=401, detail="Token has been revoked/logged out")
            # finally:

            #     next(db_gen, None) 
            # -----------------------------

            if payload.get("status") != "active":
                raise HTTPException(status_code=403, detail="Account is not active")

            if payload.get("role") not in allowed_roles:
                raise HTTPException(status_code=403, detail="Permission denied")

            request.state.user = payload
            return payload

        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
            
    return token_checker


async def get_client_info(request: Request):
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "Unknown"

    user_agent = request.headers.get("user-agent", "Unknown")

    # print(f"IP == {ip}")
    # print(f"USER AGENT == {user_agent}")
    
    return {
        "ip": ip,
        "user_agent": user_agent
    }