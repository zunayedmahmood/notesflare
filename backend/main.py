# main.py

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.db import init_db
from api.routes import router


app = FastAPI(
    title="NotesFlare Backend",
    description="Persistent thought stream API",
    version="1.0.0",
    docs_url="/docs",   # Available at http://localhost:8000/docs during dev
)

# Allow all origins in V1 — frontend runs on localhost with Electron
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    """Initialize the database on server start."""
    init_db()
    print("NotesFlare backend started. Database initialized.")


app.include_router(router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,       # Set True during active development only
        log_level="warning",
    )
