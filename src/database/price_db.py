import sqlite3
from datetime import datetime
import time
from typing import Optional, List, Dict, Any
import os
import logging
logging.basicConfig(level=logging.INFO)

class PriceDatabase:
    def __init__(self, db_path: str = "price_data.db"):
        """Initialize the database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create the database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
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
                    (coin, dex, timestamp, best_ask, best_bid, spread, mid_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data.get('coin'),  # "merrli:BTC" or "AGGREGATED"
                    'AGGREGATED',
                    data.get('timestamp'),
                    data.get('best_ask'),
                    data.get('best_bid'),
                    data.get('spread'),
                    data.get('mid_price')
                ))
                
                success = cursor.rowcount > 0
                conn.commit()
                
                if success:
                    logging.info(f"Inserted snapshot for {data.get('coin')} at {data.get('timestamp')}")
                else:
                    logging.info(f"Duplicate snapshot ignored for {data.get('coin')} at {data.get('timestamp')}")
                
                return success
                
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return False
    
    def get_snapshots(self, 
                     coin: str = None, 
                     dex: str = None,
                     start_timestamp: int = None, 
                     end_timestamp: int = None,
                     limit: int = None) -> List[Dict[str, Any]]:
        """
        Retrieve price snapshots for a given coin and time range.
        
        Args:
            coin: The coin symbol (e.g., "merrli:BTC") - optional, if None returns all
            dex: The DEX name (optional filter)
            start_timestamp: Start time in milliseconds
            end_timestamp: End time in milliseconds  
            limit: Maximum number of records to return
            
        Returns:
            List of snapshot dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query dynamically
            if coin:
                query = "SELECT * FROM price_snapshots WHERE coin = ?"
                params = [coin]
            else:
                query = "SELECT * FROM price_snapshots WHERE 1=1"
                params = []
            
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
        
        timeframe_ms = timeframe_minutes * 60 * 1000
        candles = {}
        
        for snapshot in snapshots:
            candle_start = (snapshot['timestamp'] // timeframe_ms) * timeframe_ms
            
            if candle_start not in candles:
                candles[candle_start] = {
                    'timestamp': candle_start,
                    'open': snapshot['best_ask'],
                    'high': snapshot['best_ask'],
                    'low': snapshot['best_ask'],
                    'close': snapshot['best_ask'],
                    'volume': 0,
                    'count': 0
                }
            
            candle = candles[candle_start]
            price = snapshot['best_ask']
            
            candle['high'] = max(candle['high'], price)
            candle['low'] = min(candle['low'], price)
            candle['close'] = price
            candle['count'] += 1
        
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
            
            logging.info(f"Cleaned up {deleted_count} old snapshots")
            return deleted_count