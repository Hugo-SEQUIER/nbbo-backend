import asyncio
import json
import websockets
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

router = APIRouter()

# WebSocket URL for Hyperliquid testnet
WS_URL = "wss://api.hyperliquid-testnet.xyz/ws"

# Supported coins
SUPPORTED_COINS = [
    "merrli:BTC", "sekaw:BTC", "btcx:BTC-FEUSD"
]

# Store active WebSocket connections
active_connections: List[WebSocket] = []

# Store latest trade data for each coin
latest_trades: Dict[str, Dict[str, Any]] = {
    "merrli:BTC": {},
    "sekaw:BTC": {},
    "btcx:BTC-FEUSD": {}
}

# Store the absolute latest trade across all coins
latest_trade_overall: Optional[Dict[str, Any]] = None

# Pydantic models for trade data
class TradeData(BaseModel):
    coin: str
    price: float
    size: float
    side: str  # "B" for buy, "A" for ask
    timestamp: int
    tid: int  # trade ID

class TradeResponse(BaseModel):
    success: bool
    data: Dict[str, TradeData]
    timestamp: int

class HyperliquidWebSocketClient:
    """WebSocket client to connect to Hyperliquid and receive trade data"""
    
    def __init__(self):
        self.websocket = None
        self.running = False
        
    async def connect(self):
        """Connect to Hyperliquid WebSocket"""
        try:
            self.websocket = await websockets.connect(WS_URL)
            self.running = True
            logging.info("Connected to Hyperliquid WebSocket")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to WebSocket: {e}")
            return False
    
    async def subscribe_to_trades(self, coins: List[str]):
        """Subscribe to trade data for specified coins"""
        if not self.websocket:
            return False
            
        for coin in coins:
            subscription = {
                "method": "subscribe",
                "subscription": {"type": "trades", "coin": coin}
            }
            await self.websocket.send(json.dumps(subscription))
            logging.info(f"Subscribed to trades for {coin}")
        
        return True
    
    async def listen_for_trades(self):
        """Listen for incoming trade data"""
        if not self.websocket:
            return
            
        try:
            async for message in self.websocket:
                if not self.running:
                    break
                    
                data = json.loads(message)
                
                # Process trade data
                if "data" in data and isinstance(data["data"], list):
                    for trade in data["data"]:
                        await self._process_trade(trade)
                        
        except websockets.exceptions.ConnectionClosed:
            logging.warning("WebSocket connection closed")
        except Exception as e:
            logging.error(f"Error listening for trades: {e}")
    
    async def _process_trade(self, trade_data: Dict[str, Any]):
        """Process individual trade data"""
        try:
            coin = trade_data.get("coin", "")
            if coin not in SUPPORTED_COINS:
                return
                
            trade = TradeData(
                coin=coin,
                price=float(trade_data.get("px", 0)),
                size=float(trade_data.get("sz", 0)),
                side=trade_data.get("side", ""),
                timestamp=trade_data.get("time", 0),
                tid=trade_data.get("tid", 0)
            )
            
            # Store latest trade for this coin
            latest_trades[coin] = trade.dict()
            
            # Update the overall latest trade if this is more recent
            global latest_trade_overall
            if (latest_trade_overall is None or 
                trade.timestamp > latest_trade_overall.get("timestamp", 0)):
                latest_trade_overall = trade.dict()
                # Only broadcast if this is now the overall latest trade
                await self._broadcast_trade_update(trade)
            
        except Exception as e:
            logging.error(f"Error processing trade: {e}")
    
    async def _broadcast_trade_update(self, trade: TradeData):
        """Broadcast trade update to all connected clients"""
        if not active_connections:
            return
            
        response = TradeResponse(
            success=True,
            data={trade.coin: trade},
            timestamp=trade.timestamp
        )
        
        message = json.dumps(response.dict())
        
        # Send to all active connections
        for connection in active_connections[:]:
            try:
                await connection.send_text(message)
            except:
                # Remove disconnected clients
                active_connections.remove(connection)
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            logging.info("Disconnected from Hyperliquid WebSocket")

# Global WebSocket client instance
ws_client = HyperliquidWebSocketClient()

async def broadcast_latest_trade_periodically():
    """Broadcast the latest trade across all DEXs every 1 minute"""
    while True:
        await asyncio.sleep(60)  # Wait 1 minute
        
        if not active_connections:
            continue
            
        # Find the latest trade across all DEXs
        latest_trade = None
        latest_timestamp = 0
        
        for coin, trade_data in latest_trades.items():
            if trade_data and trade_data.get("timestamp", 0) > latest_timestamp:
                latest_timestamp = trade_data.get("timestamp", 0)
                latest_trade = trade_data
        
        if latest_trade:
            response = TradeResponse(
                success=True,
                data={latest_trade["coin"]: latest_trade},
                timestamp=latest_trade["timestamp"]
            )
            
            message = json.dumps(response.dict())
            
            # Send to all active connections
            for connection in active_connections[:]:
                try:
                    await connection.send_text(message)
                    logging.info(f"Sent periodic update: {latest_trade['coin']} at ${latest_trade['price']}")
                except:
                    # Remove disconnected clients
                    active_connections.remove(connection)
        else:
            logging.info("No trade data available for periodic update")

@router.websocket("/ws/trades")
async def websocket_trades_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time trade data"""
    await websocket.accept()
    active_connections.append(websocket)
    logging.info(f"Client connected to trades WebSocket. Total connections: {len(active_connections)}")
    
    try:
        # Send the latest trade across all DEXs when client connects
        latest_trade = None
        latest_timestamp = 0
        
        for coin, trade_data in latest_trades.items():
            if trade_data and trade_data.get("timestamp", 0) > latest_timestamp:
                latest_timestamp = trade_data.get("timestamp", 0)
                latest_trade = trade_data
        
        if latest_trade:
            initial_response = TradeResponse(
                success=True,
                data={latest_trade["coin"]: latest_trade},
                timestamp=latest_trade["timestamp"]
            )
            await websocket.send_text(json.dumps(initial_response.dict()))
            logging.info(f"Sent initial data to new client: {latest_trade['coin']} at ${latest_trade['price']}")
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logging.info(f"Client disconnected from trades WebSocket. Total connections: {len(active_connections)}")

async def start_trade_stream():
    """Start the trade data streaming service"""
    logging.info("Starting trade data stream...")
    
    # Connect to Hyperliquid WebSocket
    if await ws_client.connect():
        # Subscribe to trades for all supported coins
        await ws_client.subscribe_to_trades(SUPPORTED_COINS)
        
        # Start listening for trades
        await ws_client.listen_for_trades()
    else:
        logging.error("Failed to start trade stream")

async def stop_trade_stream():
    """Stop the trade data streaming service"""
    await ws_client.disconnect()
    logging.info("Trade data stream stopped")

# Background task to manage WebSocket connection
async def manage_websocket_connection():
    """Manage WebSocket connection with reconnection logic"""
    while True:
        try:
            if not ws_client.running:
                await start_trade_stream()
        except Exception as e:
            logging.error(f"Error in WebSocket management: {e}")
            await asyncio.sleep(5)  # Wait before retrying
        
        await asyncio.sleep(1)

# Initialize the WebSocket connection when the module is imported
async def initialize_trade_stream():
    """Initialize the trade stream"""
    # Clear any old data on startup
    global latest_trade_overall
    latest_trade_overall = None
    for coin in SUPPORTED_COINS:
        latest_trades[coin] = {}
    
    # Start background tasks
    asyncio.create_task(manage_websocket_connection())
    asyncio.create_task(broadcast_latest_trade_periodically())

