from flask import Blueprint
from .health import bp as health_bp

def register_routes(app):
    app.register_blueprint(health_bp)


