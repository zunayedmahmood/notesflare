# main.py

import uvicorn
import sqlite3
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from database.db import init_db
from api.routes import router
from api.formatting_routes import formatting_router


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


@app.exception_handler(sqlite3.Error)
def sqlite_exception_handler(request: Request, exc: sqlite3.Error):
    print(f"[DB Error] Unhandled SQLite exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Database error occurred: {str(exc)}"},
    )


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    print(f"[Global Error] Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


@app.on_event("startup")
def startup():
    """Initialize the database on server start."""
    init_db()
    print("NotesFlare backend started. Database initialized.")


app.include_router(router, prefix="/api")
app.include_router(formatting_router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,       # Set True during active development only
        log_level="warning",
    )
