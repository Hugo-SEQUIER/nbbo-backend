# NBBO Backend

A FastAPI-based backend service for NBBO (National Best Bid and Offer) that aggregates order book data from multiple DEXs and provides real-time price feeds via WebSockets.

## 🚀 Features

- **Real-time Order Book Aggregation**: Combines order book data from multiple DEXs (merrli, sekaw, btcx)
- **WebSocket Price Feeds**: Live price updates every 4 seconds
- **Trade Data Streaming**: Real-time trade data from Hyperliquid testnet
- **User Portfolio Management**: Track user positions, balances, and historical data
- **Chart Data**: Generate candlestick charts with multiple timeframes
- **Database Storage**: SQLite database for price snapshots and historical data

## 🏗️ Architecture

```
Frontend ←→ FastAPI Backend ←→ Hyperliquid API
                ↓
            SQLite Database
```

## 📡 API Endpoints

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/aggregate-order-books` | GET | Get aggregated order book from all DEXs |
| `/user-position` | GET | Get user's current trading positions |
| `/user-historical-data` | GET | Get user's trading history |
| `/user-balance` | GET | Get user's account balance across DEXs |
| `/chart/{coin}` | GET | Get candlestick chart data |
| `/order-books` | GET | Get raw order book data (test endpoint) |
| `/order-books/reconstructed` | GET | Get reconstructed order book (test endpoint) |

### WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `/ws/prices` | Real-time aggregated order book updates |
| `/ws/trades` | Real-time trade data stream |

### Test Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/test/db/head` | GET | View database records |
| `/test/db/insert-sample` | POST | Insert test data |

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **Database**: SQLite
- **WebSockets**: FastAPI WebSockets
- **External API**: Hyperliquid Python SDK

## 📦 Installation

### Prerequisites

- Python 3.12+
- pip

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd nbbo-backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python run.py
   ```

5. **Access the API**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health
   - WebSocket: ws://localhost:8000/ws/prices

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | 8000 |
| `API_URL` | Hyperliquid API URL | Testnet URL |
| `DATABASE_URL` | Database connection string | SQLite file |

### Supported Coins

The application currently supports these trading pairs:
- `merrli:BTC`
- `sekaw:BTC` 
- `btcx:BTC-FEUSD`

## 📊 Data Flow

1. **Price Stream**: Background task fetches order book data every 4 seconds
2. **Data Processing**: Aggregates bids/asks from all supported DEXs
3. **WebSocket Broadcast**: Sends aggregated data to connected clients
4. **Database Storage**: Saves price snapshots for chart generation
5. **User Data**: Fetches user-specific data on demand

## 🔍 API Usage Examples

### Get Aggregated Order Book

```bash
curl http://localhost:8000/aggregate-order-books
```

### Get User Position

```bash
curl "http://localhost:8000/user-position?address=0x649204c695Edb98caD13de027f2c73Dd8E8f4BA8"
```

### Get Chart Data

```bash
curl "http://localhost:8000/chart/BTC?timeframe=15m"
```

### WebSocket Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/prices');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Price update:', data);
};
```

## 🚨 Rate Limiting

The application makes API calls to Hyperliquid testnet. To avoid rate limiting:

- **WebSocket stream**: 3 calls every 4 seconds
- **User data endpoints**: Called on-demand by frontend
- **Consider caching** for production deployment

## 🧪 Testing

### Test Endpoints

```bash
# View database records
curl http://localhost:8000/test/db/head?limit=10

# Insert sample data
curl -X POST http://localhost:8000/test/db/insert-sample
```

### Health Check

```bash
curl http://localhost:8000/health
```

## 📁 Project Structure

```
nbbo-backend/
├── src/
│   ├── app.py                 # FastAPI application factory
│   ├── database/
│   │   └── price_db.py       # Database operations
│   └── routes/
│       ├── __init__.py       # Route registration
│       ├── aggregate_order_books.py  # Order book aggregation
│       ├── best_prices_ws.py        # Price WebSocket
│       ├── trades_websocket.py     # Trade WebSocket
│       ├── chart_data.py            # Chart data
│       ├── user_position.py         # User positions
│       ├── user_historical_data.py  # User history
│       ├── get_user_balance.py      # User balance
│       ├── health.py                # Health check
│       └── tests/                   # Test endpoints
├── requirements.txt          # Python dependencies
├── run.py                   # Application entry point
└── price_data.db           # SQLite database
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Troubleshooting

### Common Issues

1. **Rate Limiting**: Reduce API call frequency or implement caching
2. **WebSocket Disconnections**: Check network stability and implement reconnection logic
3. **Database Issues**: Ensure SQLite file permissions and disk space
4. **CORS Errors**: Configure CORS middleware for your frontend domain

### Logs

Check application logs for detailed error information:

```bash
# Local development
python run.py

# Docker
docker logs <container-id>
```

## 📞 Support

For issues and questions:
- Create an issue in the repository
- Check the API documentation at `/docs`
- Review the logs for error details
