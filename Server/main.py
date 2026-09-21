from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import engine, SessionLocal
from models import Patient, Appointment
from schemas import PatientCreate, AppointmentCreate
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



# Appointment requests
@app.get("/appointments")
def get_appointments(
    appointment_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date cannot be after end_date"
        )

    db = SessionLocal()
    try:
        query = db.query(Appointment)

        if appointment_date:
            query = query.filter(
                Appointment.appointment_date == appointment_date
            )
        if start_date:
            query = query.filter(
                Appointment.appointment_date >= start_date
            )
        if end_date:
            query = query.filter(
                Appointment.appointment_date <= end_date
            )

        return query.order_by(
            Appointment.appointment_date,
            Appointment.start_time
        ).all()
    finally:
        db.close()


@app.get("/appointments/{appointment_id}")
def get_appointment(appointment_id: int):
    db = SessionLocal()
    try:
        appointment = db.get(Appointment, appointment_id)

        if appointment is None:
            raise HTTPException(status_code=404, detail="Appointment not found")

        return appointment
    finally:
        db.close()


@app.post("/appointments", status_code=201)
def create_appointment(appointment_data: AppointmentCreate):
    db = SessionLocal()
    try:
        patient = db.get(Patient, appointment_data.patient_num)

        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        new_appointment = Appointment(**appointment_data.model_dump())
        db.add(new_appointment)
        db.commit()
        db.refresh(new_appointment)

        return {
            "message": "Appointment created successfully",
            "appointment_id": new_appointment.appointment_id
        }
    finally:
        db.close()


@app.put("/appointments/{appointment_id}")
def update_appointment(
    appointment_id: int,
    appointment_data: AppointmentCreate
):
    db = SessionLocal()
    try:
        appointment = db.get(Appointment, appointment_id)

        if appointment is None:
            raise HTTPException(status_code=404, detail="Appointment not found")

        patient = db.get(Patient, appointment_data.patient_num)

        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        for field, value in appointment_data.model_dump().items():
            setattr(appointment, field, value)

        db.commit()
        db.refresh(appointment)

        return {
            "message": "Appointment updated successfully",
            "appointment_id": appointment.appointment_id
        }
    finally:
        db.close()


@app.delete("/appointments/{appointment_id}")
def delete_appointment(appointment_id: int):
    db = SessionLocal()
    try:
        appointment = db.get(Appointment, appointment_id)

        if appointment is None:
            raise HTTPException(status_code=404, detail="Appointment not found")

        db.delete(appointment)
        db.commit()

        return {"message": "Appointment deleted successfully"}
    finally:
        db.close()
