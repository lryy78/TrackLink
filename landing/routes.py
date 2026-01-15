from flask import Blueprint, render_template, request
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid
import os
from supabase_client import supabase  # make sure supabase_client.py exists

# Allowed birthdays
ALLOWED_BIRTHDAYS = ["030605", "ry5678"]

landing_bp = Blueprint(
    "landing",
    __name__,
    template_folder="templates"
)

# ---------- Visit Logger ----------
def log_visit(page="unknown", extra_info=None):
    """
    Log a visit to Supabase in Malaysia time (UTC+8).
    `extra_info` can be any string to append to page name.
    Logs environment based on ENV variable.
    """
    try:
        malaysia_time = datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
        malaysia_time_str = malaysia_time.isoformat(timespec="seconds")  # 2026-01-15T20:49:48+08:00

        # Detect environment
        run_env = os.getenv("ENV", "local")  # defaults to "local" if ENV not set

        log_data = {
            "id": uuid.uuid4().hex,
            "ip": request.remote_addr,
            "user_agent": request.headers.get("User-Agent"),
            "page": f"{page}{('-'+extra_info) if extra_info else ''}",
            "path": request.path,
            "visit_time": malaysia_time_str,
            "run_env": run_env
        }

        supabase.table("visits").insert(log_data).execute()
    except Exception as e:
        print(f"Failed to log visit: {e}")


# ---------- Landing Route ----------
@landing_bp.route("/", methods=["GET", "POST"])
def landing():
    birthday_verified = False
    error = None

    if request.method == "POST":
        birthday = request.form.get("birthday", "").strip()
        if birthday in ALLOWED_BIRTHDAYS:
            birthday_verified = True
            log_visit("landing-birthday-unlocked")  # logs page name
        else:
            error = "Invalid birthday"
            log_visit("landing-birthday-failed", extra_info=birthday)  # logs failed birthday

    elif request.method == "GET":
        log_visit("landing")  # normal page visit

    return render_template(
        "landing.html",
        birthday_verified=birthday_verified,
        error=error
    )
