import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import os

class PriceDatabase:
    def __init__(self, db_path: str = "price_data.db"):
        """Initialize the database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create the database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create the price snapshots table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coin TEXT NOT NULL,
                    dex TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    best_ask REAL NOT NULL,
                    best_bid REAL,
                    spread REAL,
                    mid_price REAL,
                    raw_data TEXT,  -- JSON string of full order book data
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    
                    UNIQUE(coin, dex, timestamp)
                )
            ''')
            
            # Create index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_coin_dex_timestamp 
                ON price_snapshots(coin, dex, timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON price_snapshots(timestamp)
            ''')
            
            conn.commit()
            print(f"Database initialized at: {self.db_path}")
    
    def insert_snapshot(self, order_book_data: Dict[str, Any]) -> bool:
        """
        Insert a price snapshot from order book data.
        
        Args:
            order_book_data: The JSON response from your DEX
            
        Returns:
            bool: True if inserted successfully, False if duplicate
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                data = order_book_data.get('data', {})
                
                cursor.execute('''
                    INSERT OR IGNORE INTO price_snapshots 
                    (coin, dex, timestamp, best_ask, best_bid, spread, mid_price, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data.get('coin'),  # "AGGREGATED"
                    'BTC',
                    data.get('timestamp'),
                    data.get('best_ask'),
                    data.get('best_bid'),
                    data.get('spread'),
                    data.get('mid_price'),
                    json.dumps(order_book_data)  # Store full data as JSON
                ))
                
                # Check if row was inserted (rowcount > 0 means new insert)
                success = cursor.rowcount > 0
                conn.commit()
                
                if success:
                    print(f"Inserted snapshot for {data.get('coin')} at {data.get('timestamp')}")
                else:
                    print(f"Duplicate snapshot ignored for {data.get('coin')} at {data.get('timestamp')}")
                
                return success
                
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def get_snapshots(self, 
                     coin: str, 
                     dex: str = None,
                     start_timestamp: int = None, 
                     end_timestamp: int = None,
                     limit: int = None) -> List[Dict[str, Any]]:
        """
        Retrieve price snapshots for a given coin and time range.
        
        Args:
            coin: The coin symbol (e.g., "merrli:BTC")
            dex: The DEX name (optional filter)
            start_timestamp: Start time in milliseconds
            end_timestamp: End time in milliseconds  
            limit: Maximum number of records to return
            
        Returns:
            List of snapshot dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            # Build dynamic query
            query = "SELECT * FROM price_snapshots WHERE coin = ?"
            params = [coin]
            
            if dex:
                query += " AND dex = ?"
                params.append(dex)
            
            if start_timestamp:
                query += " AND timestamp >= ?"
                params.append(start_timestamp)
            
            if end_timestamp:
                query += " AND timestamp <= ?"
                params.append(end_timestamp)
            
            query += " ORDER BY timestamp ASC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            return [dict(row) for row in rows]
    
    def get_latest_snapshot(self, coin: str, dex: str = None) -> Optional[Dict[str, Any]]:
        """Get the most recent snapshot for a coin."""
        snapshots = self.get_snapshots(coin, dex, limit=1)
        return snapshots[0] if snapshots else None
    
    def calculate_candles(self, 
                         coin: str, 
                         timeframe_minutes: int,
                         start_timestamp: int = None,
                         end_timestamp: int = None) -> List[Dict[str, Any]]:
        """
        Calculate OHLCV candles from raw snapshots.
        
        Args:
            coin: The coin symbol
            timeframe_minutes: Candle timeframe in minutes (1, 5, 15, 60, etc.)
            start_timestamp: Start time in milliseconds
            end_timestamp: End time in milliseconds
            
        Returns:
            List of OHLCV candle dictionaries
        """
        snapshots = self.get_snapshots(coin, start_timestamp=start_timestamp, end_timestamp=end_timestamp)
        
        if not snapshots:
            return []
        
        # Group snapshots into timeframe buckets
        timeframe_ms = timeframe_minutes * 60 * 1000
        candles = {}
        
        for snapshot in snapshots:
            # Calculate which candle bucket this snapshot belongs to
            candle_start = (snapshot['timestamp'] // timeframe_ms) * timeframe_ms
            
            if candle_start not in candles:
                candles[candle_start] = {
                    'timestamp': candle_start,
                    'open': snapshot['best_ask'],
                    'high': snapshot['best_ask'],
                    'low': snapshot['best_ask'],
                    'close': snapshot['best_ask'],
                    'volume': 0,  # You'll need actual trade data for this
                    'count': 0
                }
            
            candle = candles[candle_start]
            price = snapshot['best_ask']
            
            # Update OHLC
            candle['high'] = max(candle['high'], price)
            candle['low'] = min(candle['low'], price)
            candle['close'] = price  # Last price in the period
            candle['count'] += 1
        
        # Return sorted candles
        return sorted(candles.values(), key=lambda x: x['timestamp'])
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Remove snapshots older than specified days."""
        cutoff_timestamp = (datetime.now().timestamp() - (days_to_keep * 24 * 3600)) * 1000
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM price_snapshots WHERE timestamp < ?", 
                (cutoff_timestamp,)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            
            print(f"Cleaned up {deleted_count} old snapshots")
            return deleted_count


# Example usage and testing
if __name__ == "__main__":
    # Initialize database
    db = PriceDatabase("price_data.db")
    
    # Example: Insert the sample data you provided
    sample_data = {
        "success": True,
        "data": {
            "coin": "merrli:BTC",
            "timestamp": 1758422718903,
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
    
    # Insert sample data
    db.insert_snapshot(sample_data)
    
    # Query examples
    print("\n--- Latest snapshot ---")
    latest = db.get_latest_snapshot("merrli:BTC")
    if latest:
        print(f"Latest price: {latest['best_ask']} at {latest['timestamp']}")
    
    print("\n--- Calculate 1-hour candles ---")
    candles = db.calculate_candles("merrli:BTC", timeframe_minutes=60)
    for candle in candles:
        print(f"Candle: O={candle['open']} H={candle['high']} L={candle['low']} C={candle['close']}")