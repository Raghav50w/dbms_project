import os
from flask import Flask
from .routes import bp

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")
    app.register_blueprint(bp)
    return app
