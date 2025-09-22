import uvicorn
import os

def main():
    # Cloud Run sets PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(
        "src.app:create_app", 
        host="0.0.0.0", 
        port=port, 
        factory=True
    )

if __name__ == "__main__":
    main()
