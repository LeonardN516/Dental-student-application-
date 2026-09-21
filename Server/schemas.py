from datetime import date, time
from typing import Optional

from pydantic import BaseModel


class PatientCreate(BaseModel):

    initials: str

    patient_num: int

    gender: str

    preferred_contact: str

    email: Optional[str] = None

    phone_num: Optional[str] = None

    contact_person: str

    payment_method: str

    notes: Optional[str] = None

class AppointmentCreate(BaseModel):
    patient_num: int
    appointment_date: date
    start_time: time
    appointment_type: Optional[str] = None
    notes: Optional[str] = None
