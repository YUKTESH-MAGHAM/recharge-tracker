import os
from supabase import create_client, Client

def get_supabase_admin() -> Client:
    """
    Returns a Supabase client using the SERVICE ROLE key.
    This client bypasses RLS — only used server-side for token verification.
    Never expose this client or its key to the frontend.
    """
    url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not service_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment variables.")
    return create_client(url, service_key)

def get_supabase_anon() -> Client:
    """
    Returns a Supabase client using the ANON key.
    Used only where RLS is expected to enforce access control.
    """
    url = os.environ.get("SUPABASE_URL")
    anon_key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not anon_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables.")
    return create_client(url, anon_key)
