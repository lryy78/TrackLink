from flask import (
    request,
    redirect,
    render_template,
    make_response,
    send_from_directory,
    current_app,
)
from datetime import datetime, date
from zoneinfo import ZoneInfo
import os
import sqlite3
import uuid

from . import chat_bp


DB_FILE = "chat.db"
USER_BIRTHDAYS = ["030605", "ry5678"]


# ---------- Database Helpers ----------
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        birthday TEXT PRIMARY KEY,
        display_name TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        time TEXT NOT NULL,
        birthday TEXT NOT NULL,
        text TEXT,
        file_path TEXT,
        active INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_activity (
        id TEXT PRIMARY KEY,
        birthday TEXT NOT NULL,
        page TEXT NOT NULL,
        access_time TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bottles (
        id TEXT PRIMARY KEY,
        birthday TEXT NOT NULL,
        text TEXT NOT NULL,
        file_path TEXT,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bottle_views (
        id TEXT PRIMARY KEY,
        birthday TEXT NOT NULL,
        bottle_id TEXT NOT NULL,
        view_date TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


# ---------- Activity Logger ----------
def log_activity(birthday, page):
    conn = get_db_connection()
    cur = conn.cursor()
    now = datetime.utcnow().replace(
        tzinfo=ZoneInfo("UTC")
    ).astimezone(ZoneInfo("Asia/Kuala_Lumpur"))

    cur.execute(
        "INSERT INTO user_activity VALUES (?, ?, ?, ?)",
        (uuid.uuid4().hex, birthday, page, now.strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


# ---------- Login ----------
@chat_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        birthday = request.form.get("birthday")

        if birthday not in USER_BIRTHDAYS:
            log_activity(f"unknown-{birthday}", "login_failed")
            return render_template("login.html", error="Invalid birthday")

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE birthday=?", (birthday,))
        user = cur.fetchone()

        if not user:
            cur.execute(
                "INSERT INTO users VALUES (?, ?)",
                (birthday, "ry" if birthday == "ry5678" else "user"),
            )
            conn.commit()

        conn.close()

        log_activity(birthday, "login_success")
        resp = make_response(redirect("/dashboard"))
        resp.set_cookie("birthday", birthday, max_age=31536000)
        return resp

    return render_template("login.html")


# ---------- Message ----------
@chat_bp.route("/message", methods=["GET", "POST"])
def message():
    birthday = request.cookies.get("birthday")
    if not birthday:
        return redirect("/")

    log_activity(birthday, "message")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT display_name FROM users WHERE birthday=?", (birthday,))
    user = cur.fetchone()
    if not user:
        conn.close()
        return redirect("/")

    name = user["display_name"]

    if request.method == "POST":
        text = request.form.get("message")
        file = request.files.get("file")
        file_path = None

        if file and file.filename:
            ext = os.path.splitext(file.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"], filename
            )
            file.save(save_path)
            file_path = filename

        if text or file_path:
            now = datetime.utcnow().replace(
                tzinfo=ZoneInfo("UTC")
            ).astimezone(ZoneInfo("Asia/Kuala_Lumpur"))

            cur.execute(
                "INSERT INTO messages VALUES (?, ?, ?, ?, ?, 1)",
                (
                    uuid.uuid4().hex,
                    now.strftime("%Y-%m-%d %H:%M:%S"),
                    birthday,
                    text,
                    file_path,
                ),
            )
            conn.commit()

        conn.close()
        return redirect("/message")

    cur.execute("""
        SELECT m.id, m.time, m.text, m.file_path, u.display_name
        FROM messages m
        JOIN users u ON m.birthday = u.birthday
        WHERE m.active = 1
        ORDER BY m.time DESC
    """)
    messages = cur.fetchall()
    conn.close()

    return render_template("message.html", name=name, messages=messages)


# ---------- Upload Serving ----------
@chat_bp.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"], filename
    )


# ---------- Dashboard ----------
@chat_bp.route("/dashboard")
def dashboard():
    birthday = request.cookies.get("birthday")
    if not birthday:
        return redirect("/")

    log_activity(birthday, "dashboard")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT display_name FROM users WHERE birthday=?", (birthday,))
    name = cur.fetchone()["display_name"]

    cur.execute("SELECT COUNT(*) cnt FROM messages WHERE birthday=?", (birthday,))
    messages_count = cur.fetchone()["cnt"]

    cur.execute("SELECT COUNT(*) cnt FROM bottles WHERE birthday=?", (birthday,))
    bottles_count = cur.fetchone()["cnt"]

    cur.execute("""
        SELECT page, access_time
        FROM user_activity
        WHERE birthday=?
        ORDER BY access_time DESC
        LIMIT 5
    """, (birthday,))
    recent_activity = cur.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        name=name,
        messages_count=messages_count,
        bottles_count=bottles_count,
        recent_activity=recent_activity,
    )

# ---------- Bottle (Drift Bottle) ----------
@chat_bp.route("/bottle", methods=["GET", "POST"])
def bottle():
    birthday = request.cookies.get("birthday")
    if not birthday:
        return redirect("/")

    log_activity(birthday, "bottle")

    conn = get_db_connection()
    cur = conn.cursor()
    today_str = date.today().strftime("%Y-%m-%d")

    # Handle POST: send a new bottle
    if request.method == "POST":
        text = request.form.get("message")
        file = request.files.get("file")
        file_path = None

        if file and file.filename:
            ext = os.path.splitext(file.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            file_path = filename

        if text or file_path:
            now = datetime.utcnow().replace(
                tzinfo=ZoneInfo("UTC")
            ).astimezone(ZoneInfo("Asia/Kuala_Lumpur"))

            cur.execute(
                "INSERT INTO bottles VALUES (?, ?, ?, ?, ?)",
                (
                    uuid.uuid4().hex,
                    birthday,
                    text,
                    file_path,
                    now.strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()

    # Handle GET: show a bottle for today
    # Check if already viewed
    cur.execute(
        "SELECT bottle_id FROM bottle_views WHERE birthday=? AND view_date=?",
        (birthday, today_str),
    )
    view = cur.fetchone()

    bottle_to_show = None
    no_bottle = False

    if view:
        cur.execute("SELECT * FROM bottles WHERE id=?", (view["bottle_id"],))
        bottle_to_show = cur.fetchone()
    else:
        cur.execute(
            "SELECT * FROM bottles WHERE birthday != ? ORDER BY RANDOM() LIMIT 1",
            (birthday,),
        )
        bottle_to_show = cur.fetchone()
        if bottle_to_show:
            cur.execute(
                "INSERT INTO bottle_views VALUES (?, ?, ?, ?)",
                (uuid.uuid4().hex, birthday, bottle_to_show["id"], today_str),
            )
            conn.commit()
        else:
            no_bottle = True

    # Count bottles picked up from this user
    cur.execute(
        "SELECT COUNT(*) cnt FROM bottle_views bv JOIN bottles b ON bv.bottle_id = b.id WHERE b.birthday=?",
        (birthday,),
    )
    picked_count = cur.fetchone()["cnt"]

    conn.close()
    return render_template(
        "bottle.html",
        bottle=bottle_to_show,
        no_bottle=no_bottle,
        picked_count=picked_count,
    )

# ---------- Delete Message ----------
@chat_bp.route("/delete_message", methods=["POST"])
def delete_message():
    birthday = request.cookies.get("birthday")
    message_id = request.form.get("id")
    if not birthday or not message_id:
        return redirect("/message")

    conn = get_db_connection()
    cur = conn.cursor()

    # Only delete messages belonging to this user
    cur.execute("SELECT file_path FROM messages WHERE id=? AND birthday=?", (message_id, birthday))
    msg = cur.fetchone()
    if msg:
        # Remove uploaded file if exists
        if msg["file_path"]:
            path = os.path.join(current_app.config["UPLOAD_FOLDER"], msg["file_path"])
            if os.path.exists(path):
                os.remove(path)
        # Soft delete by marking active=0
        cur.execute("UPDATE messages SET active=0 WHERE id=? AND birthday=?", (message_id, birthday))
        conn.commit()
    conn.close()
    return redirect("/message")

