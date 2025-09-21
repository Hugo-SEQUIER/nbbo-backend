import uvicorn

def main():
    # Use import string for workers to work properly
    uvicorn.run("src.app:create_app", host="0.0.0.0", port=8060, workers=4, factory=True)

if __name__ == "__main__":
    main()
