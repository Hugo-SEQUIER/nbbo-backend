from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter
import asyncio
import json
from typing import List, Dict, Any
from .aggregate_order_books import _reconstruct_orderbook, _create_aggregated_orderbook
from hyperliquid.info import Info
from hyperliquid.utils import constants

router = APIRouter()
API_URL = constants.TESTNET_API_URL
FREQUENCY = 3 #In seconds

active_connections: List[WebSocket] = []

@router.websocket("/ws/prices")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    print(f"Client connected. Total connections: {len(active_connections)}")
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print(f"Client disconnected. Total connections: {len(active_connections)}")

async def stream_aggregated_order_books():
    """Stream aggregated order book data to all connected clients every 3 seconds"""
    print("Starting aggregated order book stream...")
    LIST_COIN = ["merrli:BTC", "sekaw:BTC"]
    last_orderbook = None
    
    while True:
        if active_connections:
            try:
                all_bids = []
                all_asks = []
                processed_coins = []
                
                # Aggregate order books from all coins
                for coin in LIST_COIN:
                    try:
                        info = Info(API_URL, skip_ws=True)
                        payload = {
                            "type": "l2Book",
                            "coin": coin,
                        }
                        
                        # Get raw order book data
                        try:
                            raw_ob = info.post("/info", payload)
                        except TypeError:
                            raw_ob = info.post(payload)
                        
                        # Reconstruct the orderbook
                        orderbook = _reconstruct_orderbook(raw_ob, coin)
                        
                        # Collect bids and asks from this coin
                        all_bids.extend(orderbook.bids)
                        all_asks.extend(orderbook.asks)
                        processed_coins.append(coin)
                        
                    except Exception as e:
                        # Log error but continue with other coins
                        print(f"Error processing coin {coin}: {e}")
                        continue
                
                if processed_coins:
                    # Create aggregated orderbook
                    aggregated_orderbook = _create_aggregated_orderbook(all_bids, all_asks, processed_coins)
                    
                    # Create WebSocket message
                    message = {
                        "type": "aggregated_order_book",
                        "data": {
                            "coin": aggregated_orderbook.coin,
                            "timestamp": aggregated_orderbook.timestamp,
                            "bids": [{"price": bid.price, "size": bid.size, "orders": bid.orders} for bid in aggregated_orderbook.bids],
                            "asks": [{"price": ask.price, "size": ask.size, "orders": ask.orders} for ask in aggregated_orderbook.asks],
                            "best_bid": aggregated_orderbook.best_bid,
                            "best_ask": aggregated_orderbook.best_ask,
                            "spread": aggregated_orderbook.spread,
                            "mid_price": aggregated_orderbook.mid_price
                        },
                        "metadata": {
                            "coins_processed": len(processed_coins),
                            "total_coins": len(LIST_COIN)
                        }
                    }
                    
                    # Broadcast to all connected clients
                    for connection in active_connections[:]:
                        try:
                            await connection.send_text(json.dumps(message))
                        except:
                            active_connections.remove(connection)
                    
                    last_orderbook = message
                    print(f"Sent aggregated order book to {len(active_connections)} clients (processed {len(processed_coins)}/{len(LIST_COIN)} coins)")
                    
                else:
                    # If no coins processed successfully, send last known data or error
                    if last_orderbook:
                        for connection in active_connections[:]:
                            try:
                                error_message = {
                                    "type": "error",
                                    "message": "Failed to retrieve order book data, sending last known data",
                                    "data": last_orderbook["data"],
                                    "metadata": last_orderbook["metadata"]
                                }
                                await connection.send_text(json.dumps(error_message))
                            except:
                                active_connections.remove(connection)
                        print(f"Sent last known order book to {len(active_connections)} clients due to API failure")
                    else:
                        print("No order book data available and no previous data to send")
                        
            except Exception as e:
                print(f"Error in aggregated order book streaming: {e}")
                # Send error message to clients
                for connection in active_connections[:]:
                    try:
                        error_message = {
                            "type": "error",
                            "message": f"Failed to retrieve aggregated order book: {str(e)}"
                        }
                        await connection.send_text(json.dumps(error_message))
                    except:
                        active_connections.remove(connection)
        
        await asyncio.sleep(FREQUENCY)

async def start_price_stream():
    """Start the aggregated order book streaming background task"""
    print("Starting price stream background task...")
    task = asyncio.create_task(stream_aggregated_order_books())
    return task 