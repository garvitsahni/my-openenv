import os

import uvicorn


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run("main:app", host=host, port=port, workers=1)


if __name__ == "__main__":
    main()
