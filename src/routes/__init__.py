from fastapi import FastAPI
from .health import router as health_router
from .best_prices_ws import router as websocket_router, start_price_stream
from .chart_data import router as chart_router
from .tests.test_db_data import router as test_db_router
from .tests.get_order_books import router as order_books_router
from .get_user_balance import router as user_balance_router
from .user_historical_data import router as user_historical_data_router
from .trades_websocket import router as trades_router, initialize_trade_stream
from .aggregate_order_books import router as aggregate_order_books_router
from .user_position import router as user_position_router

def register_routes(app: FastAPI):
    app.include_router(health_router)
    app.include_router(order_books_router)
    app.include_router(websocket_router)
    app.include_router(chart_router)
    app.include_router(test_db_router)
    app.include_router(trades_router)
    app.include_router(user_historical_data_router)
    app.include_router(user_position_router)
    app.include_router(user_balance_router)
    @app.on_event("startup")
    async def startup_event():
        await start_price_stream()
        await initialize_trade_stream()

        
    app.include_router(aggregate_order_books_router)

