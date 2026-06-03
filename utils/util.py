from datetime import timezone, datetime
import secrets
import string
import hashlib

def get_now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def get_now_utc_formated() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def ensure_aware(dt):
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def generate_fingerprint(ip: str, user_agent: str) -> str:
    data = f"{ip}|{user_agent}"
    return hashlib.sha256(data.encode()).hexdigest()