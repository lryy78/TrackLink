from flask import Flask
import os
from chat.routes import chat_bp, init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "chat", "templates"),
    static_folder=os.path.join(BASE_DIR, "chat"),
)

# Upload folder
app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "chat", "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize database
init_db()

# Register blueprint
app.register_blueprint(chat_bp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  
    app.run(host="0.0.0.0", port=port, debug=True)
