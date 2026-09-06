from sqlalchemy import Column, Integer, String, Text, Date
from database import Base


class Patient(Base):
    __tablename__ = "patient"

    patient_num = Column(
        Integer,
        primary_key=True
    )

    initials = Column(
        String(15),
        nullable=False
    )

    gender = Column(
        String(15),
        nullable=False
    )

    preferred_contact = Column(
        String(15),
        nullable=False
    )

    email = Column(
        String(255)
    )

    phone_num = Column(
        String(15)
    )

    contact_person = Column(
        String(255),
        nullable=False
    )

    payment_method = Column(
        String(15),
        nullable=False
    )

    notes = Column(
        Text
    )

    date_last_cleaning = Column(
        Date
    )

    date_next_cleaning = Column(
        Date
    )