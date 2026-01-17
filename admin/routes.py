from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from supabase_client import supabase
import uuid

admin_bp = Blueprint(
    "admin",
    __name__,
    template_folder="templates",
    url_prefix="/admin"
)

ADMIN_KEY = "secret-5678"

# ---------------- Login ----------------
@admin_bp.route("/", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("secret_key") == ADMIN_KEY:
            session["admin_logged_in"] = True
            return redirect(url_for("admin.dashboard"))
        return render_template("admin_login.html", error="Invalid secret key")
    return render_template("admin_login.html")


@admin_bp.route("/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.admin_login"))

# ---------------- Dashboard ----------------
@admin_bp.route("/dashboard")
def dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    chat_tables = [
        "users",
        "messages",
        "user_activity",
        "bottles",
        "bottle_views"
    ]
    activity_tables = ["visits"]
    ui_tables = ["ui_messages"]

    return render_template(
        "dashboard.html",
        chat_tables=chat_tables,
        activity_tables=activity_tables,
        ui_tables=ui_tables,
        name="Admin"
    )

# ---------------- View Table ----------------
@admin_bp.route("/table/<db_name>/<table_name>")
def view_table(db_name, table_name):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    try:
        query = supabase.table(table_name).select("*")

        if table_name == "messages":
            query = query.order("time", desc=True)
        elif table_name == "user_activity":
            query = query.order("access_time", desc=True)
        elif table_name == "bottles":
            query = query.order("created_at", desc=True)
        elif table_name == "visits":
            query = query.order("visit_time", desc=True)
        else:
            query = query.order("id", desc=True)

        resp = query.limit(500).execute()
        rows = resp.data or []
        columns = list(rows[0].keys()) if rows else []

    except Exception as e:
        print("[ADMIN TABLE ERROR]", e)
        rows = []
        columns = []

    return render_template(
        "table_view.html",
        db_name=db_name,
        table_name=table_name,
        rows=rows,
        columns=columns,
        can_delete=(db_name == "chat")
    )

# ---------------- UI Messages ----------------
@admin_bp.route("/messages")
def admin_messages():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    resp = supabase.table("ui_messages").select("*").execute()
    messages = resp.data or []

    return render_template("admin_messages.html", messages=messages)

# ---------------- Create Greeting / PS Message ----------------
@admin_bp.route("/messages/create", methods=["GET", "POST"])
def create_message():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    if request.method == "POST":
        try:
            message_type = request.form.get("message_type")
            content = request.form.get("content")
            start_time = request.form.get("start_time")  # e.g., "20:30"
            end_time = request.form.get("end_time")      # e.g., "21:15"
            active = True if request.form.get("active") == "on" else False

            new_msg = {
                "id": str(uuid.uuid4()),
                "message_type": message_type,
                "content": content,
                "start_time": start_time,
                "end_time": end_time,
                "active": active,
                "is_default": False
            }

            resp = supabase.table("ui_messages").insert(new_msg).execute()
            print("Supabase insert response:", resp)

            flash("Message created successfully!", "success")
            return redirect(url_for("admin.admin_messages"))

        except Exception as e:
            print("[CREATE MESSAGE ERROR]", e)
            flash(f"Failed to create message: {e}", "error")
            return redirect(url_for("admin.create_message"))

    return render_template("create_message.html")

# ---------------- Toggle Message Status ----------------
@admin_bp.route("/messages/toggle/<msg_id>")
def toggle_message(msg_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    try:
        # 1. Get current status
        current = supabase.table("ui_messages").select("active").eq("id", msg_id).single().execute()
        if current.data:
            new_status = not current.data['active']
            # 2. Update to opposite
            supabase.table("ui_messages").update({"active": new_status}).eq("id", msg_id).execute()
            flash(f"Message {'activated' if new_status else 'deactivated'}.", "success")
    except Exception as e:
        flash(f"Error toggling status: {e}", "error")

    return redirect(url_for("admin.admin_messages"))

# ---------------- Delete Message (Optional but Recommended) ----------------
@admin_bp.route("/messages/delete/<msg_id>")
def delete_ui_message(msg_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))
    
    supabase.table("ui_messages").delete().eq("id", msg_id).execute()
    flash("Message deleted.", "info")
    return redirect(url_for("admin.admin_messages"))
