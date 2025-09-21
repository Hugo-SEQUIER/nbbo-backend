from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from hyperliquid.info import Info
from hyperliquid.utils import constants

router = APIRouter()
API_URL = constants.TESTNET_API_URL

class UserHistoricalData(BaseModel):
    success: bool
    data: List[Dict[str, Any]]

@router.get("/user-historical-data", response_model=UserHistoricalData)
async def get_user_historical_data(
    address: str,
    list_coins: str
):
    try:
        list_coins = list_coins.split(",")
        info = Info(API_URL, skip_ws=True)
        payload = {
            "type": "historicalOrders",
            "user": address,
        }  

        try:
            data = info.post("/info", payload)
        except TypeError:
            data = info.post(payload)
        
        filtered_data = [item for item in data if item["order"]["coin"] in list_coins]
    
        return {
            "success": True,
            "data": filtered_data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user historical data: {e}")