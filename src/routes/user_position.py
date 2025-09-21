from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from hyperliquid.info import Info
from hyperliquid.utils import constants

router = APIRouter()
API_URL = constants.TESTNET_API_URL

class UserPosition(BaseModel):
    success: bool
    data: List[Dict[str, Any]] | None

@router.get("/user-position", response_model=UserPosition)
async def get_user_position(
    address: str,
):
    try:
        info = Info(API_URL, skip_ws=True)
        payload = {
            "type": "subAccounts",
            "user": address,
        }  

        try:
            data = info.post("/info", payload)
        except TypeError:
            data = info.post(payload)
        
        return {
            "success": True,
            "data": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user historical data: {e}")