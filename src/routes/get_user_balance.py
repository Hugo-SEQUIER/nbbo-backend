from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from pydantic import BaseModel
from hyperliquid.info import Info
from hyperliquid.utils import constants
from time import sleep

router = APIRouter()
API_URL = constants.TESTNET_API_URL

class UserBalance(BaseModel):
    success: bool
    data: Dict[str, Any]

@router.get("/user-balance", response_model=UserBalance)
async def get_user_balance(
    address: str,
    dexs: str,
):
    try:
        dexs = dexs.split(",")
        data = {"success": True, "data": {}}
        total_account_value = 0
        for dex in dexs:
            info = Info(API_URL, skip_ws=True)
            payload = {
                "type": "clearinghouseState",
                "user": address,
                "dex": dex,
            }  

            try:
                data["data"][dex] = info.post("/info", payload)
                total_account_value += float(data["data"][dex]["marginSummary"]["accountValue"])
            except TypeError:
                data["success"] = False
                data["data"][dex] = info.post("/info", payload)
                total_account_value += float(0)
            sleep(1)
        data["data"]["total_account_value"] = total_account_value
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user balance data: {e}")