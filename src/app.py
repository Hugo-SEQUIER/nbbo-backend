from flask import Flask
from flask_cors import CORS
from .routes import register_routes

def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config.from_mapping(
        SECRET_KEY="dev",  # or from env
        JSON_SORT_KEYS=False,
    )

    # register blueprints from routes/
    register_routes(app)

    return app
