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
    
    admin_preview = request.args.get("admin_preview") == "1"

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
    
    if not admin_preview:
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

@landing_bp.route("/chronicle")
def chronicle():
    # 1. Check for admin preview flag
    admin_preview = request.args.get("admin_preview") == "1"

    # 2. Fetch Chronicle data from Supabase
    try:
        resp = supabase.table("chronicle_posts")\
            .select("*")\
            .eq("is_active", True)\
            .order("created_at", desc=False).execute()
        posts = resp.data or []
    except Exception as e:
        print(f"Error fetching chronicle: {e}")
        posts = []

    # 3. Log visit only if NOT in admin preview
    if not admin_preview:
        log_visit("chronicle-view")

    return render_template(
        "chronicle.html",
        posts=posts,
        admin_preview=admin_preview
    )

@landing_bp.route("/api/chronicle-updates")
def get_chronicle_updates():
    # Fetch active posts, ordered by created_at (Oldest first for chat flow)
    try:
        resp = supabase.table("chronicle_posts")\
            .select("*")\
            .eq("is_active", True)\
            .order("created_at", desc=False).execute()
        return {"success": True, "posts": resp.data or []}
    except Exception as e:
        return {"success": False, "error": str(e)}, 500
    
@landing_bp.route("/api/track-click", methods=["POST"])
def track_click():
    action = request.json.get("action")
    target = request.json.get("target") # e.g., "image", "spotify", "video"
    log_visit(f"click-{action}", extra_info=target)
    return {"success": True}