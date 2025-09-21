from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter
import asyncio
import random
from typing import List

router = APIRouter()

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

async def stream_random_prices():
    """Stream random numbers to all connected clients every 2 seconds"""
    while True:
        if active_connections:
            #TODO: Implement the actual prices and order books of the platform
            
            random_price = round(random.uniform(100, 200), 2)
            
            for connection in active_connections[:]:
                try:
                    await connection.send_text(str(random_price))
                except:
                    active_connections.remove(connection)
            
            print(f"Sent price {random_price} to {len(active_connections)} clients")
        
        await asyncio.sleep(2)

async def start_price_stream():
    """Start the price streaming background task"""
    asyncio.create_task(stream_random_prices()) 