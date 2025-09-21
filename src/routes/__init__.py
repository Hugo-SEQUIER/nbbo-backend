from fastapi import FastAPI
from .health import router as health_router
from .tests.get_order_books import router as order_books_router
from .aggregate_order_books import router as aggregate_order_books_router

def register_routes(app: FastAPI):
    app.include_router(health_router)
    app.include_router(order_books_router)
    app.include_router(aggregate_order_books_router)