from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import engine, SessionLocal
from models import Patient
from schemas import PatientCreate
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
#Allow requests from any website/frontend. shoudl change allow_origins = ["https://yourwebsite.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    
    db = SessionLocal()
    try: 
        patients = db.query(Patient).all()

        return patients
    finally:
        db.close()

@app.get("/patients/{patient_num}")
def get_patient(patient_num: int):
    db = SessionLocal()
    try:
        patient = db.get(Patient, patient_num)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        return patient
    finally:
        db.close()

@app.post("/patients")
def create_patient(patient: PatientCreate):

    db = SessionLocal()

    try:

        new_patient = Patient(
            initials=patient.initials,
            patient_num=patient.patient_num,
            gender=patient.gender,
            preferred_contact=patient.preferred_contact,
            email=patient.email,
            phone_num=patient.phone_num,
            contact_person=patient.contact_person,
            payment_method=patient.payment_method,
            notes=patient.notes,
            date_last_cleaning=patient.date_last_cleaning,
            date_next_cleaning=patient.date_next_cleaning
        )

        db.add(new_patient)

        db.commit()

        db.refresh(new_patient)

        return {
            "message": "Patient created successfully",
            "patient_num": new_patient.patient_num
        }

    finally:

        db.close()

@app.put("/patients/{patient_num}")
def update_patient(patient_num: int, patient_data: PatientCreate):
    db = SessionLocal()
    try:
        patient = db.get(Patient, patient_num)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        for field, value in patient_data.model_dump().items():
            setattr(patient, field, value)

        db.commit()
        db.refresh(patient)
        return {
            "message": "Patient updated successfully",
            "patient_num": patient.patient_num
        }
    finally:
        db.close()

@app.delete("/patients/{patient_num}")
def delete_patient(patient_num: int):
    db = SessionLocal()
    try:
        patient = db.get(Patient, patient_num)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        db.delete(patient)
        db.commit()
        return {"message": "Patient deleted successfully"}
    finally:
        db.close()
