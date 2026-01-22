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
        elif table_name == "chronicle_posts":
            query = query.order("created_at", desc=True)
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

# ---------------- Edit Greeting / PS Message ----------------
@admin_bp.route("/messages/edit/<msg_id>", methods=["GET", "POST"])
def edit_message(msg_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    # Fetch existing message
    resp = supabase.table("ui_messages").select("*").eq("id", msg_id).single().execute()
    message = resp.data

    if not message:
        flash("Message not found.", "error")
        return redirect(url_for("admin.admin_messages"))

    if request.method == "POST":
        try:
            update_data = {
                "message_type": request.form.get("message_type"),
                "content": request.form.get("content"),
                "start_time": request.form.get("start_time"),
                "end_time": request.form.get("end_time"),
                "active": True if request.form.get("active") == "on" else False,
            }

            supabase.table("ui_messages").update(update_data).eq("id", msg_id).execute()
            flash("Message updated successfully!", "success")
            return redirect(url_for("admin.admin_messages"))

        except Exception as e:
            print("[EDIT MESSAGE ERROR]", e)
            flash(f"Update failed: {e}", "error")

    return render_template("create_message.html", message=message, edit_mode=True)

# ---------------- Landing Preview (Admin Only) ----------------
@admin_bp.route("/landing-preview")
def landing_preview():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    # Import here to avoid circular import
    from landing.routes import get_landing_messages

    greeting_text, ps_text = get_landing_messages()

    return render_template(
        "landing.html",
        greeting_text=greeting_text,
        ps_text=ps_text,
        birthday_verified=True,   # force unlocked
        admin_preview=True,       # special flag
        error=None
    )

# ---------------- Visit Cleanup Utility ----------------
@admin_bp.route("/cleanup/visits", methods=["GET"])
def visit_cleanup_list():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    try:
        # Get counts of unique user agents to see which ones are "junk"
        resp = supabase.table("visits").select("user_agent").execute()
        agents = {}
        for row in (resp.data or []):
            ua = row.get("user_agent") or "Empty / None"
            agents[ua] = agents.get(ua, 0) + 1
        
        # Sort by count descending
        sorted_agents = sorted(agents.items(), key=lambda x: x[1], reverse=True)
    except Exception as e:
        flash(f"Error fetching agents: {e}", "error")
        sorted_agents = []

    return render_template("cleanup_visits.html", agents=sorted_agents)

@admin_bp.route("/cleanup/visits/delete", methods=["POST"])
def delete_by_agent():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    ua_to_delete = request.form.get("user_agent")
    
    # Handle the 'Empty' case logic
    target_ua = "" if ua_to_delete == "Empty / None" else ua_to_delete

    try:
        supabase.table("visits").delete().eq("user_agent", target_ua).execute()
        flash(f"Successfully deleted all records for agent: '{ua_to_delete}'", "success")
    except Exception as e:
        flash(f"Delete failed: {e}", "error")

    return redirect(url_for("admin.visit_cleanup_list"))

@admin_bp.route("/chronicle/create", methods=["GET", "POST"])
def create_chronicle_post():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    if request.method == "POST":
        content = request.form.get("content")
        media_type = request.form.get("media_type")
        media_url = ""

        try:
            # --- Handling File Uploads (Image/Video) ---
            if media_type in ['image', 'video']:
                file = request.files.get('file')
                if file and file.filename != '':
                    file_extension = file.filename.rsplit('.', 1)[-1]
                    unique_name = f"{uuid.uuid4()}.{file_extension}"
                    file_path = f"uploads/{unique_name}"
                    
                    file_content = file.read()
                    
                    # Upload to Supabase Storage
                    upload_resp = supabase.storage.from_("chronicle").upload(
                        path=file_path, 
                        file=file_content, 
                        file_options={"content-type": file.content_type}
                    )
                    
                    # Get the Public URL
                    media_url = supabase.storage.from_("chronicle").get_public_url(file_path)
                else:
                    flash("No file selected for upload!", "error")
                    return redirect(request.url)

            # --- Handling Spotify Links ---
            elif media_type == 'spotify':
                raw_url = request.form.get("spotify_url")
                if "track/" in raw_url:
                    # Extracts the ID from the link and creates an embed URL
                    track_id = raw_url.split("track/")[1].split("?")[0]
                    media_url = f"https://open.spotify.com/embed/track/{track_id}"
                else:
                    flash("Invalid Spotify link format!", "error")
                    return redirect(request.url)

            # --- Insert into Database ---
            supabase.table("chronicle_posts").insert({
                "content": content,
                "media_type": media_type,
                "media_url": media_url,
                "is_active": True
            }).execute()

            flash("Transmission sent to Chronicle!", "success")
            return redirect(url_for("admin.manage_chronicle")) # Redirect to manage page to see it

        except Exception as e:
            print(f"[CHRONICLE ERROR] {e}")
            flash(f"Dispatch failed: {str(e)}", "error")
            return redirect(request.url)

    return render_template("create_chronicle.html")

@admin_bp.route("/chronicle-preview")
def chronicle_preview():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))
    
    source = request.args.get("source")

    # Reuse the logic to fetch posts
    try:
        resp = supabase.table("chronicle_posts")\
            .select("*")\
            .eq("is_active", True)\
            .order("created_at", desc=False).execute()
        posts = resp.data or []
    except Exception as e:
        posts = []

    return render_template(
        "chronicle.html",
        posts=posts,
        admin_preview=True,
        source=source
    )

@admin_bp.route("/chronicle/manage")
def manage_chronicle():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))
    
    # Fetch all posts (including inactive ones)
    resp = supabase.table("chronicle_posts").select("*").order("created_at", desc=True).execute()
    return render_template("manage_chronicle.html", posts=resp.data)

@admin_bp.route("/chronicle/toggle/<post_id>", methods=["POST"])
def toggle_chronicle(post_id):
    # 1. Get current status
    post = supabase.table("chronicle_posts").select("is_active").eq("id", post_id).single().execute()
    new_status = not post.data['is_active']
    
    # 2. Update status
    supabase.table("chronicle_posts").update({"is_active": new_status}).eq("id", post_id).execute()
    return redirect(url_for("admin.manage_chronicle"))

@admin_bp.route("/chronicle/delete/<post_id>")
def delete_chronicle(post_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    try:
        # 1. Get the post data first so we know the file path
        resp = supabase.table("chronicle_posts").select("media_url, media_type").eq("id", post_id).single().execute()
        post = resp.data

        if post and post.get("media_url") and post.get("media_type") in ['image', 'video']:
            # 2. Extract the file path from the URL
            # The URL looks like: .../storage/v1/object/public/chronicle/uploads/filename.jpg
            # We need: "uploads/filename.jpg"
            full_url = post["media_url"]
            if "uploads/" in full_url:
                file_path = "uploads/" + full_url.split("uploads/")[1]
                
                # 3. Delete from Supabase Storage
                supabase.storage.from_("chronicle").remove([file_path])
                print(f"Deleted file from storage: {file_path}")

        # 4. Delete from Database
        supabase.table("chronicle_posts").delete().eq("id", post_id).execute()
        flash("Post and associated media deleted successfully.", "info")

    except Exception as e:
        print(f"Delete error: {e}")
        flash(f"Error during deletion: {e}", "error")

    return redirect(url_for("admin.manage_chronicle"))

# ---------------- Edit Chronicle Post ----------------
@admin_bp.route("/chronicle/edit/<post_id>", methods=["GET", "POST"])
def edit_chronicle(post_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    # 1. Fetch existing post
    resp = supabase.table("chronicle_posts").select("*").eq("id", post_id).single().execute()
    post = resp.data

    if not post:
        flash("Post not found.", "error")
        return redirect(url_for("admin.manage_chronicle"))

    if request.method == "POST":
        try:
            content = request.form.get("content")
            # Note: We usually don't allow changing media_type/file on edit 
            # to keep it simple, but we update the text content.
            
            update_data = {
                "content": content,
                "updated_at": "now()" # Supabase handles this if you have a column, else remove
            }

            supabase.table("chronicle_posts").update(update_data).eq("id", post_id).execute()
            flash("Chronicle updated successfully!", "success")
            return redirect(url_for("admin.manage_chronicle"))

        except Exception as e:
            flash(f"Update failed: {e}", "error")

    # Reuse create_chronicle.html but pass the post object and edit_mode flag
    return render_template("create_chronicle.html", post=post, edit_mode=True)