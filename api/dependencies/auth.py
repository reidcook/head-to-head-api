import os

import firebase_admin
from firebase_admin import auth
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_scheme = HTTPBearer()


def verify_admin(creds: HTTPAuthorizationCredentials = Security(bearer_scheme)):
    token = creds.credentials
    try:
        decoded = auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    allowed_email = os.getenv("ALLOWED_ADMIN_EMAIL")
    if decoded.get("email") != allowed_email:
        raise HTTPException(status_code=403, detail="Not authorized")

    return decoded
