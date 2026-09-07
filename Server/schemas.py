from datetime import date
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

    date_last_cleaning: Optional[date] = None

    date_next_cleaning: Optional[date] = None