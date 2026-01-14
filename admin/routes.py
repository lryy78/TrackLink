from flask import Blueprint, render_template, request, redirect, url_for, session
import os, sqlite3

admin_bp = Blueprint("admin", __name__, template_folder="templates", url_prefix="/admin")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAT_DB = os.path.join(BASE_DIR, "chat.db")
ACTIVITY_DB = os.path.join(BASE_DIR, "activity.db")
ADMIN_KEY = "secret-5678"

# ---------------- DB Helper ----------------
def get_db_connection(db_file):
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- Login / Logout ----------------
@admin_bp.route("/", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        key = request.form.get("secret_key")
        if key == ADMIN_KEY:
            session["admin_logged_in"] = True
            return redirect(url_for("admin.dashboard"))
        else:
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

    # Get all table names
    def get_tables(db_file):
        conn = get_db_connection(db_file)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        conn.close()
        return [t["name"] for t in tables]

    chat_tables = get_tables(CHAT_DB)
    activity_tables = get_tables(ACTIVITY_DB)

    return render_template(
        "dashboard.html",
        chat_tables=chat_tables,
        activity_tables=activity_tables,
        name="Admin"
    )

# ---------------- View Table Data ----------------
@admin_bp.route("/table/<db_name>/<table_name>")
def view_table(db_name, table_name):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    db_file = CHAT_DB if db_name == "chat" else ACTIVITY_DB
    conn = get_db_connection(db_file)

    try:
        # Columns
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = [col["name"] for col in cursor.fetchall()]

        # Decide correct time column
        if "access_time" in columns:
            order_sql = "ORDER BY datetime(access_time) DESC"
        elif "time" in columns:
            order_sql = "ORDER BY datetime(time) DESC"
        elif "created_at" in columns:
            order_sql = "ORDER BY datetime(created_at) DESC"
        elif "visit_time" in columns:
            order_sql = "ORDER BY datetime(visit_time) DESC"
        elif "id" in columns:
            order_sql = "ORDER BY id DESC"
        else:
            order_sql = ""

        query = f"SELECT * FROM {table_name} {order_sql}"
        rows = conn.execute(query).fetchall()

    except sqlite3.Error as e:
        print("DB error:", e)
        rows = []
        columns = []

    conn.close()

    return render_template(
        "table_view.html",
        db_name=db_name,
        table_name=table_name,
        rows=rows,
        columns=columns,
        can_delete=(db_name == "chat"),
    )

