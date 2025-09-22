import uvicorn

def main():
    # Use import string for workers to work properly
    uvicorn.run("src.app:create_app", host="0.0.0.0", port=8000, factory=True)

if __name__ == "__main__":
    main()
