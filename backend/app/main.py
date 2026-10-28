from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.database import test_connection

app = FastAPI(title="CineBook API")


@app.get("/")
def home():
    return {
        "message": "Welcome to CineBook API",
        "status": "running",
    }


@app.get("/health/db")
def database_health():
    try:
        database_name = test_connection()

        return {
            "status": "connected",
            "database": database_name,
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Check local configuration.",
        )