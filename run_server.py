"""Run the FastAPI server."""

import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    uvicorn.run(
        "task_scheduler.api:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )

