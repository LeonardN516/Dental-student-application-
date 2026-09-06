from fastapi import FastAPI
from sqlalchemy import text

from database import engine

app = FastAPI()


@app.get("/")
def home():
    return {"message": "FastAPI is working"}


@app.get("/test-database")
def test_database():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version()"))
        version = result.scalar()

    return {
        "postgresql_version": version
    }