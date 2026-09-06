from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import engine
from models import Patient

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
@app.get("/patients")
def get_patients():

    with Session(engine) as session:

        patients = session.query(Patient).all()

        return patients