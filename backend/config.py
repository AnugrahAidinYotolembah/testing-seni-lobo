import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file relative to this file's directory
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
JWT_SECRET = os.getenv("JWT_SECRET", "lobo-palu-secret-key-change-in-production").strip()

supabase = None

def get_supabase():
    global supabase
    if supabase is not None:
        return supabase
    if not SUPABASE_URL or not SUPABASE_KEY or "your-" in SUPABASE_URL or "your-" in SUPABASE_KEY or "PASTE_YOUR" in SUPABASE_KEY:
        print("WARNING: Supabase not configured. Please update .env file with real credentials.")
        return None
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("SUCCESS: Connected to Supabase!")
        return supabase
    except Exception as e:
        print(f"WARNING: Failed to connect to Supabase: {e}")
        return None

# Initialize on import
supabase = get_supabase()
