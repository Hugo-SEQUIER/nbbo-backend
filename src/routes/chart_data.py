from fastapi import APIRouter, HTTPException, Query
from src.database.price_db import PriceDatabase
from datetime import datetime
from typing import Optional
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

router = APIRouter()
db = PriceDatabase()

@router.get("/chart/{coin}")
async def get_chart_data(
    coin: str,
    timeframe: Optional[str] = Query("15min", description="Timeframe: 1h, 4h, 1d")
):
    """
    Get chart data for a coin
    Default: Returns last 24 hours of 1-hour candles
    """
    try:
        timeframe_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '1h': 60,
            '4h': 240, 
            '1d': 1440
        }.get(timeframe, 60)
        
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = end_time - (24 * 60 * 60 * 1000)
        
        candles = db.calculate_candles(
            coin=coin,
            timeframe_minutes=timeframe_minutes,
            start_timestamp=start_time,
            end_timestamp=end_time
        )
        
        chart_data = []
        for candle in candles:
            chart_data.append({
                "timestamp": candle['timestamp'],
                "open": candle['open'],
                "high": candle['high'],
                "low": candle['low'],
                "close": candle['close']
            })
        
        return {
            "success": True,
            "data": chart_data,
            "coin": coin,
            "timeframe": timeframe,
            "count": len(chart_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

