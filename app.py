from flask import Flask, request, make_response, send_file
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid
import os

app = Flask(__name__)

# New web page file
WEBPAGE_FILE = os.path.join(os.path.dirname(__file__), "webpage.html")

LOG_FILE = os.path.join(os.path.dirname(__file__), "clicks.log")

# Function to log visitor info
def log_click(visitor_id):
    try:
        malaysia_time = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
        time_str = malaysia_time.strftime("%Y-%m-%d %H:%M:%S")

        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        ua = request.headers.get("User-Agent")

        with open(LOG_FILE, "a") as f:
            f.write(f"{time_str} | {visitor_id} | {ip} | {ua}\n")
            f.flush()

        print(f"[LOG] {time_str} | {visitor_id} | {ip} | {ua}")

    except Exception as e:
        print(f"[ERROR] Logging failed: {e}")

# Main route serving your web page
@app.route("/")
def track():
    visitor_id = request.cookies.get("visitor_id")
    if not visitor_id:
        visitor_id = str(uuid.uuid4())

    log_click(visitor_id)

    response = make_response(send_file(WEBPAGE_FILE))
    response.set_cookie(
        "visitor_id",
        visitor_id,
        max_age=60*60*24*365,
        httponly=True,
        samesite="Lax"
    )
    return response

# Stats page
@app.route("/stats")
def stats():
    if not os.path.exists(LOG_FILE):
        return "No clicks yet."

    total_clicks = 0
    visitor_counts = {}
    log_entries = []

    with open(LOG_FILE, "r") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) == 4:
                time, visitor_id, ip, ua = [p.strip() for p in parts]
                total_clicks += 1
                visitor_counts[visitor_id] = visitor_counts.get(visitor_id, 0) + 1
                log_entries.append({"time": time, "visitor_id": visitor_id, "ip": ip, "ua": ua})

    unique_visitors = len(visitor_counts)
    log_entries.reverse()

    table_html = "<table border='1' cellpadding='5'><tr><th>Time (MYT)</th><th>Visitor ID</th><th>IP</th><th>Browser</th><th>Total Clicks</th></tr>"
    for entry in log_entries[-50:]:
        count = visitor_counts.get(entry["visitor_id"], 0)
        visitor_color = " style='color:red'" if count > 1 else ""
        table_html += (
            f"<tr{visitor_color}>"
            f"<td>{entry['time']}</td>"
            f"<td>{entry['visitor_id']}</td>"
            f"<td>{entry['ip']}</td>"
            f"<td>{entry['ua']}</td>"
            f"<td>{count}</td>"
            f"</tr>"
        )
    table_html += "</table>"

    return (
        f"<b>Total accesses:</b> {total_clicks}<br>"
        f"<b>Unique visitors:</b> {unique_visitors}<br><br>"
        f"<b>Recent clicks (newest first, repeated visitors in red, total clicks per visitor shown):</b><br>"
        f"{table_html}"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
