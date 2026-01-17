from flask import Blueprint, render_template, request
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid
from supabase_client import supabase

ALLOWED_BIRTHDAYS = ["030605", "ry5678"]

landing_bp = Blueprint(
    "landing",
    __name__,
    template_folder="templates"
)

# ---------- Visit Logger ----------
def log_visit(page="unknown", extra_info=None):
    try:
        malaysia_time = datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
        malaysia_time_str = malaysia_time.isoformat(timespec="seconds")
        log_data = {
            "id": uuid.uuid4().hex,
            "ip": request.remote_addr,
            "user_agent": request.headers.get("User-Agent"),
            "page": f"{page}{('-'+extra_info) if extra_info else ''}",
            "visit_time": malaysia_time_str
        }
        supabase.table("visits").insert(log_data).execute()
    except Exception as e:
        print(f"Failed to log visit: {e}")

# ---------- Fetch greeting/PS ----------
def get_landing_messages():
    now = datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
    current_time = now.strftime("%H:%M")  # e.g., "20:35"

    resp = supabase.table("ui_messages").select("*").eq("active", True).execute()
    messages = resp.data

    greeting, ps = None, None
    for m in messages:
        if m["start_time"] <= current_time < m["end_time"]:
            if m["message_type"] == "greeting":
                greeting = m["content"]
            elif m["message_type"] == "ps":
                ps = m["content"]

    # fallback
    if not greeting:
        greeting = "nothing here yet.. come back later..?🫣"
    if not ps:
        ps = "haha, dk when will update on it.🫨"

    return greeting, ps

# ---------- Landing Route ----------
@landing_bp.route("/", methods=["GET", "POST"])
def landing():
    birthday_verified = False
    error = None
    greeting_text, ps_text = get_landing_messages()

    if request.method == "POST":
        birthday = request.form.get("birthday", "").strip()
        if birthday in ALLOWED_BIRTHDAYS:
            birthday_verified = True
            log_visit("landing-success", birthday)
        else:
            error = "Invalid birthday"
            log_visit("landing-failed", birthday)
        return {"success": birthday_verified, "error": error}
    
    log_visit("landing")
    return render_template(
        "landing.html",
        birthday_verified=birthday_verified,
        error=error,
        greeting_text=greeting_text,
        ps_text=ps_text
    )

@landing_bp.route("/current_messages")
def current_messages():
    """Return current greeting and PS in JSON."""
    greeting, ps = get_landing_messages()
    return {"greeting": greeting, "ps": ps}

