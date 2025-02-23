import sys
import os
import shutil

# Add the project root directory to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask
from modules.chatbot import chat_bp
from flask_session import Session

app = Flask(__name__)
# Use a fixed secret key for session management.
app.secret_key = "my_fixed_development_key"

# Configure the session to use the filesystem (server-side)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(os.getcwd(), "flask_session")
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True

# Remove any old session files when starting the app.
if os.path.exists(app.config["SESSION_FILE_DIR"]):
    shutil.rmtree(app.config["SESSION_FILE_DIR"])
os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)

# Initialize Flask-Session
Session(app)

app.register_blueprint(chat_bp)

if __name__ == "__main__":
    app.run(debug=True)
