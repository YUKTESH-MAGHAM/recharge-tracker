import os
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import create_client

security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Verify the Supabase JWT by calling Supabase's own get_user() API.
    Works with both HS256 and ES256 — no key management needed.
    Returns the authenticated user's UUID.
    user_id is always extracted from the verified server response — never trusted from the client.
    """
    token = credentials.credentials

    url = os.environ.get("SUPABASE_URL")
    anon_key = os.environ.get("SUPABASE_ANON_KEY")

    if not url or not anon_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set.")

    try:
        client = create_client(url, anon_key)
        # Supabase verifies the token server-side and returns the user
        response = client.auth.get_user(token)

        if not response or not response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        return str(response.user.id)

    except HTTPException:
        raise
    except Exception as e:
        err = str(e).lower()
        if "invalid" in err or "expired" in err or "unauthorized" in err or "jwt" in err:
            raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Could not verify token: {str(e)}")
