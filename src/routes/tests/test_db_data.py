from fastapi import APIRouter, HTTPException, Query
from src.database.price_db import PriceDatabase
import time

router = APIRouter()
db = PriceDatabase()

@router.get("/test/db/head")
async def get_db_head(
    limit: int = Query(10, description="Number of rows to return")
):
    """
    Return the first N rows (head) of the price_snapshots table.
    Returns data in a table-like format for easy reading.
    """
    try:
        data = db.get_snapshots(limit=limit)
        
        if not data:
            return {
                "success": True,
                "message": "No data found in database",
                "count": 0,
                "table": {
                    "headers": ["id", "coin", "dex", "timestamp", "best_ask", "best_bid", "spread", "mid_price", "created_at"],
                    "rows": []
                }
            }
        
        headers = list(data[0].keys())
        
        rows = []
        for row in data:
            row_values = []
            for header in headers:
                value = row[header]
                if header == 'timestamp' and value:
                    from datetime import datetime
                    formatted_time = datetime.fromtimestamp(value/1000).strftime('%Y-%m-%d %H:%M:%S')
                    row_values.append(f"{value} ({formatted_time})")
                elif header == 'created_at' and value:
                    from datetime import datetime
                    formatted_time = datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
                    row_values.append(f"{value} ({formatted_time})")
                else:
                    row_values.append(value)
            rows.append(row_values)
        
        return {
            "success": True,
            "message": f"Found {len(data)} records in database",
            "count": len(data),
            "table": {
                "headers": headers,
                "rows": rows
            },
            "raw_data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/db/insert-sample")
async def insert_sample_data_current_time():
    """
    Insert sample data with current timestamp for easy testing.
    """
    try:
        current_timestamp = int(time.time() * 1000)
        
        sample_data = {
            "success": True,
            "data": {
                "coin": "BTC",
                "timestamp": current_timestamp,
                "bids": [
                    {"price": 111900, "size": 0.02494, "orders": 1},
                    {"price": 111850, "size": 0.0013, "orders": 1}
                ],
                "asks": [
                    {"price": 115900, "size": 0.00023, "orders": 1},
                    {"price": 119900, "size": 0.00073, "orders": 1}
                ],
                "best_bid": 111900,
                "best_ask": 115900,
                "spread": 4000,
                "mid_price": 113900
            }
        }
        
        success = db.insert_snapshot(sample_data)
        
        if success:
            return {
                "success": True,
                "message": f"Successfully inserted sample data with current timestamp",
                "timestamp": current_timestamp,
                "data": sample_data
            }
        else:
            return {
                "success": False,
                "message": f"Sample data already exists (duplicate ignored)",
                "timestamp": current_timestamp
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
