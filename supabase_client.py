# supabase_client.py
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load local .env for development only
load_dotenv()  # safe to call even if .env doesn't exist

# Get environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Fail fast if not set
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Supabase environment variables are missing! "
        "Set SUPABASE_URL and SUPABASE_KEY either in .env (local) or Render environment."
    )

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
