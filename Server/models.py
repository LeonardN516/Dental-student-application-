from sqlalchemy import Column, Integer, String, Text, Date, Time, ForeignKey
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



class Appointment(Base):
      __tablename__ = "appointment"

      appointment_id = Column(Integer, primary_key=True)
      patient_num = Column(
          Integer,
          ForeignKey("patient.patient_num"),
          nullable=False
      )
      appointment_date = Column(Date, nullable=False)
      start_time = Column(Time, nullable=False)
      appointment_type = Column(String(100))
      notes = Column(Text)
