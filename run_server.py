"""Run the FastAPI server."""

import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    uvicorn.run(
        "task_scheduler.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

