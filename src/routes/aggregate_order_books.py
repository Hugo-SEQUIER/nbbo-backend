from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from hyperliquid.info import Info
from hyperliquid.utils import constants

router = APIRouter()
API_URL = constants.TESTNET_API_URL

class OrderLevel(BaseModel):
    price: float
    size: float
    orders: int

class OrderBook(BaseModel):
    coin: str
    timestamp: int
    bids: List[OrderLevel]
    asks: List[OrderLevel]
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    spread: Optional[float] = None
    mid_price: Optional[float] = None

class OrderBookResponse(BaseModel):
    success: bool
    data: OrderBook
    metadata: Dict[str, Any]

LIST_COIN = [
    "merrli:BTC", "sekaw:BTC"
]

@router.get("/aggregate-order-books", response_model=OrderBookResponse)
async def aggregate_order_books():
    """
    Get aggregated orderbook from all assets in LIST_COIN.
    Returns a single consolidated orderbook with combined bids and asks from all coins.
    """
    try:
        all_bids = []
        all_asks = []
        processed_coins = []
        
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
        
        if not processed_coins:
            raise HTTPException(status_code=500, detail="Failed to retrieve orderbook data for any coins")
        
        # Create aggregated orderbook
        aggregated_orderbook = _create_aggregated_orderbook(all_bids, all_asks, processed_coins)
        
        return OrderBookResponse(
            success=True,
            data=aggregated_orderbook,
            metadata={"coins_processed": len(processed_coins), "total_coins": len(LIST_COIN)}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve aggregate order book data: {e}")

def _reconstruct_orderbook(raw_data: Dict[str, Any], coin: str) -> OrderBook:
    """
    Reconstruct raw orderbook data into a proper orderbook format.
    
    Args:
        raw_data: Raw orderbook data from Hyperliquid API
        coin: Coin symbol
        
    Returns:
        OrderBook: Reconstructed orderbook with bids, asks, and calculated metrics
    """
    levels = raw_data.get("levels", [])
    
    # Parse bids (first array - buy orders, sorted by price descending)
    bids = []
    if len(levels) > 0:
        for level in levels[0]:
            bids.append(OrderLevel(
                price=float(level["px"]),
                size=float(level["sz"]),
                orders=level["n"]
            ))
    
    # Parse asks (second array - sell orders, sorted by price ascending)
    asks = []
    if len(levels) > 1:
        for level in levels[1]:
            asks.append(OrderLevel(
                price=float(level["px"]),
                size=float(level["sz"]),
                orders=level["n"]
            ))
    
    # Calculate metrics
    best_bid = bids[0].price if bids else None
    best_ask = asks[0].price if asks else None
    spread = (best_ask - best_bid) if (best_bid and best_ask) else None
    mid_price = (best_bid + best_ask) / 2 if (best_bid and best_ask) else None
    
    return OrderBook(
        coin=coin,
        timestamp=raw_data.get("time", 0),
        bids=bids,
        asks=asks,
        best_bid=best_bid,
        best_ask=best_ask,
        spread=spread,
        mid_price=mid_price
    )

def _create_aggregated_orderbook(all_bids: List[OrderLevel], all_asks: List[OrderLevel], processed_coins: List[str]) -> OrderBook:
    """
    Create a single aggregated orderbook by combining bids and asks from all coins.
    
    Args:
        all_bids: List of all bid levels from all coins
        all_asks: List of all ask levels from all coins
        processed_coins: List of coins that were successfully processed
        
    Returns:
        OrderBook: Single aggregated orderbook with combined bids and asks
    """
    # Aggregate bids by price level (combine sizes for same prices)
    bid_aggregation = {}
    for bid in all_bids:
        price_key = bid.price
        if price_key in bid_aggregation:
            bid_aggregation[price_key]["size"] += bid.size
            bid_aggregation[price_key]["orders"] += bid.orders
        else:
            bid_aggregation[price_key] = {
                "price": bid.price,
                "size": bid.size,
                "orders": bid.orders
            }
    
    # Aggregate asks by price level (combine sizes for same prices)
    ask_aggregation = {}
    for ask in all_asks:
        price_key = ask.price
        if price_key in ask_aggregation:
            ask_aggregation[price_key]["size"] += ask.size
            ask_aggregation[price_key]["orders"] += ask.orders
        else:
            ask_aggregation[price_key] = {
                "price": ask.price,
                "size": ask.size,
                "orders": ask.orders
            }
    
    # Convert aggregated data back to OrderLevel objects
    aggregated_bids = [
        OrderLevel(
            price=data["price"],
            size=data["size"],
            orders=data["orders"]
        )
        for data in bid_aggregation.values()
    ]
    
    aggregated_asks = [
        OrderLevel(
            price=data["price"],
            size=data["size"],
            orders=data["orders"]
        )
        for data in ask_aggregation.values()
    ]
    
    # Sort bids by price descending (highest bid first)
    aggregated_bids.sort(key=lambda x: x.price, reverse=True)
    
    # Sort asks by price ascending (lowest ask first)
    aggregated_asks.sort(key=lambda x: x.price)
    
    # Calculate metrics for aggregated orderbook
    best_bid = aggregated_bids[0].price if aggregated_bids else None
    best_ask = aggregated_asks[0].price if aggregated_asks else None
    spread = (best_ask - best_bid) if (best_bid and best_ask) else None
    mid_price = (best_bid + best_ask) / 2 if (best_bid and best_ask) else None
    
    return OrderBook(
        coin="BTC",  # Special identifier for aggregated orderbook
        timestamp=int(__import__("time").time() * 1000),  # Current timestamp
        bids=aggregated_bids,
        asks=aggregated_asks,
        best_bid=best_bid,
        best_ask=best_ask,
        spread=spread,
        mid_price=mid_price
    )