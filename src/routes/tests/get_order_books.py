from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from hyperliquid.info import Info
from hyperliquid.utils import constants

router = APIRouter()
API_URL = constants.TESTNET_API_URL  # e.g. https://api.hyperliquid-testnet.xyz

# Pydantic models for orderbook structure
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

@router.get("/order-books")
async def get_order_books(
    coin: str = Query(..., description="Perp coin symbol, e.g. 'BTC'"),
    n_sig_figs: Optional[int] = Query(None, ge=2, le=5),
    mantissa: Optional[int] = Query(None, description="Only allowed if n_sig_figs == 5 (1,2,5)")
):
    try:
        info = Info(API_URL, skip_ws=True)
        payload = {
            "type": "l2Book",
            "coin": coin,
        }
        if n_sig_figs is not None:
            payload["nSigFigs"] = n_sig_figs
        if mantissa is not None:
            payload["mantissa"] = mantissa

        # Current SDKs: post(path, payload). Fallback for older SDKs: post(payload)
        try:
            ob = info.post("/info", payload)
        except TypeError:
            ob = info.post(payload)

        return {"success": True, "data": ob, "metadata": {"coin": coin, "nSigFigs": n_sig_figs, "mantissa": mantissa}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve order book data: {e}")

@router.get("/order-books/reconstructed", response_model=OrderBookResponse)
async def get_reconstructed_order_book(
    coin: str = Query(..., description="Perp coin symbol, e.g. 'BTC'"),
    n_sig_figs: Optional[int] = Query(None, ge=2, le=5),
    mantissa: Optional[int] = Query(None, description="Only allowed if n_sig_figs == 5 (1,2,5)")
):
    """
    Get order book data and reconstruct it into a proper orderbook format.
    Returns bids (buy orders) and asks (sell orders) with calculated metrics.
    """
    try:
        info = Info(API_URL, skip_ws=True)
        payload = {
            "type": "l2Book",
            "coin": coin,
        }
        if n_sig_figs is not None:
            payload["nSigFigs"] = n_sig_figs
        if mantissa is not None:
            payload["mantissa"] = mantissa

        # Get raw order book data
        try:
            raw_ob = info.post("/info", payload)
        except TypeError:
            raw_ob = info.post(payload)

        # Reconstruct the orderbook
        orderbook = _reconstruct_orderbook(raw_ob, coin)
        
        return OrderBookResponse(
            success=True,
            data=orderbook,
            metadata={"coin": coin, "nSigFigs": n_sig_figs, "mantissa": mantissa}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve and reconstruct order book: {e}")

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
