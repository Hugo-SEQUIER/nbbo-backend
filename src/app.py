from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import register_routes

def create_app():
    app = FastAPI(
        title="NBBO Backend",
        description="Backend API for NBBO (National Best Bid and Offer)",
        version="1.0.0"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure this properly for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # register routers from routes/
    register_routes(app)

    return app
