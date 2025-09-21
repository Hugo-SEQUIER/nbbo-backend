from fastapi import FastAPI
from .health import router as health_router
from .get_order_books import router as order_books_router
from .best_prices_ws import router as websocket_router, start_price_stream

def register_routes(app: FastAPI):
    app.include_router(health_router)
    app.include_router(order_books_router)
    app.include_router(websocket_router)
    
    # Start the price streaming background task
    @app.on_event("startup")
    async def startup_event():
        start_price_stream()