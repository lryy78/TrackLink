# main.py
import os
from flask import Flask
from admin.routes import admin_bp
from landing.routes import landing_bp  # no circular import
from landing.utils import log_visit  # optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "landing", "templates")

app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.secret_key = "SuperSecretSessionKey"

# ---------------- Register Blueprints ----------------
app.register_blueprint(admin_bp)
app.register_blueprint(landing_bp, url_prefix="/")  # "/" prefix

# ---------------- Run App ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
