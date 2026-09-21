CREATE TABLE IF NOT EXISTS patient (
    patient_num INTEGER PRIMARY KEY,
    initials VARCHAR(15) NOT NULL,
    gender VARCHAR(15) NOT NULL,
    preferred_contact VARCHAR(15) NOT NULL,
    email VARCHAR(255),
    phone_num VARCHAR(15),
    contact_person VARCHAR(255) NOT NULL,
    payment_method VARCHAR(15) NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS appointment (
    appointment_id SERIAL PRIMARY KEY,
    patient_num INTEGER NOT NULL,
    appointment_date DATE NOT NULL,
    start_time TIME NOT NULL,
    appointment_type VARCHAR(100),
    notes TEXT,

    CONSTRAINT fk_appointment_patient
        FOREIGN KEY (patient_num)
        REFERENCES patient(patient_num)
        ON DELETE CASCADE
);
