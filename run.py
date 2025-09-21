import uvicorn
from asgiref.wsgi import WsgiToAsgi
from src.app import create_app

def main():
    flask_app = create_app()
    asgi_app = WsgiToAsgi(flask_app)
    uvicorn.run(asgi_app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
