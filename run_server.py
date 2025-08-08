import uvicorn
from dotenv import load_dotenv

load_dotenv(override=True)


def main():
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)


if __name__ == "__main__":
    main()
