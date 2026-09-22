const monthLabel = document.getElementById("monthLabel");
const calendarGrid = document.getElementById("calendarGrid");
const prevMonth = document.getElementById("prevMonth");
const nextMonth = document.getElementById("nextMonth");

let currentDate = new Date();
let allPatients = [];
let allAppointments = [];

function renderCalendar() {
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  monthLabel.textContent = new Intl.DateTimeFormat("en-US", {
    month: "long",
    year: "numeric"
  }).format(currentDate);

  calendarGrid.innerHTML = "";

  // Weekdays are the first row of the 7-column grid.
  const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  weekdays.forEach(day => {
    const heading = document.createElement("div");
    heading.className = "weekday";
    heading.textContent = day;
    calendarGrid.appendChild(heading);
  });

  // JavaScript uses Sunday=0. Convert this to Monday=0.
  const firstDay = new Date(year, month, 1).getDay();
  const mondayIndex = (firstDay + 6) % 7;

  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const daysInPreviousMonth = new Date(year, month, 0).getDate();

  // Always render a complete 6-week calendar.
  const totalCells = 42;

  for (let i = 0; i < totalCells; i++) {
    const cell = document.createElement("button");
    cell.type = "button";
    cell.className = "day";

    let dayNumber;
    let cellDate;

    if (i < mondayIndex) {
      dayNumber = daysInPreviousMonth - mondayIndex + i + 1;
      cellDate = new Date(year, month - 1, dayNumber);
      cell.classList.add("other-month");
    } else if (i >= mondayIndex + daysInMonth) {
      dayNumber = i - (mondayIndex + daysInMonth) + 1;
      cellDate = new Date(year, month + 1, dayNumber);
      cell.classList.add("other-month");
    } else {
      dayNumber = i - mondayIndex + 1;
      cellDate = new Date(year, month, dayNumber);
    }

    const number = document.createElement("div");
    number.className = "date-number";
    number.textContent = dayNumber;
    cell.appendChild(number);

    // Placeholder for future appointments.
    const note = document.createElement("div");
    note.className = "day-note";

    const dateKey = formatLocalDate(cellDate);
    const appointmentCount = allAppointments.filter(
      appointment => appointment.appointment_date === dateKey
    ).length;

    if (appointmentCount > 0) {
      note.classList.add("has-appointments");
      note.textContent = appointmentCount === 1
        ? "1 appointment"
        : `${appointmentCount} appointments`;
    }

    cell.appendChild(note);

    if (isToday(cellDate)) {
      cell.classList.add("today");
    }

    cell.addEventListener("click", () => {
      const dateKey = formatLocalDate(cellDate);
      window.location.href =
        `day_schedule.html?date=${encodeURIComponent(dateKey)}`;
    });

    calendarGrid.appendChild(cell);
  }
}

function formatLocalDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function isToday(date) {
  const today = new Date();
  return (
    date.getFullYear() === today.getFullYear() &&
    date.getMonth() === today.getMonth() &&
    date.getDate() === today.getDate()
  );
}

prevMonth.addEventListener("click", () => {
  currentDate.setMonth(currentDate.getMonth() - 1);
  renderCalendar();
});

nextMonth.addEventListener("click", () => {
  currentDate.setMonth(currentDate.getMonth() + 1);
  renderCalendar();
});

// Tab switching
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(section => {
      section.classList.remove("active");
    });

    tab.classList.add("active");
    document.getElementById(tab.dataset.tab).classList.add("active");
  });
});

const requestedTab = new URLSearchParams(window.location.search).get("tab");

if (requestedTab === "patients") {
  document.querySelector('.tab[data-tab="patients"]').click();
}

renderCalendar();

function getAppointmentDateTime(appointment) {
    const [year, month, day] = appointment.appointment_date
        .split("-")
        .map(Number);
    const [hour, minute, second = 0] = appointment.start_time
        .split(":")
        .map(Number);

    return new Date(year, month - 1, day, hour, minute, second);
}

function getNextAppointment(patientNumber) {
    const now = new Date();

    return allAppointments
        .filter(appointment =>
            appointment.patient_num === patientNumber &&
            getAppointmentDateTime(appointment) >= now
        )
        .sort((first, second) =>
            getAppointmentDateTime(first) - getAppointmentDateTime(second)
        )[0] || null;
}

function formatAppointmentDateTime(appointment) {
    if (!appointment) {
        return "No appointment";
    }

    return new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit"
    }).format(getAppointmentDateTime(appointment));
}

function renderPatients(patients, isSearch = false) {
    const container = document.getElementById("patients-container");
    const emptyState = document.getElementById("emptyPatientState");
    const emptyTitle = emptyState.querySelector("h3");
    const emptyMessage = emptyState.querySelector("p");

    container.innerHTML = "";

    if (patients.length === 0) {
        emptyTitle.textContent = isSearch
            ? "No matching patients"
            : "No patients yet";
        emptyMessage.textContent = isSearch
            ? "Try searching with a different patient number or set of initials."
            : "Your patients will appear here.";
        emptyState.classList.remove("hidden");
        return;
    }

    emptyState.classList.add("hidden");
    //creating the button for each patient that is being created
    patients.forEach(patient => {
        const nextAppointment = getNextAppointment(patient.patient_num);
        const patientRow = document.createElement("button");
        patientRow.type = "button";
        patientRow.classList.add("patient-row");

        patientRow.addEventListener("click", () => {
            window.location.href =
                `patient_details.html?patient_num=${encodeURIComponent(patient.patient_num)}`;
        });

        patientRow.innerHTML = `
            <span>
                <strong>${patient.initials}</strong>
                <br>
                <small>Patient #${patient.patient_num}</small>
            </span>
            <span>${formatAppointmentDateTime(nextAppointment)}</span>
            <span>${patient.preferred_contact}</span>
        `;

        container.appendChild(patientRow);
    });
}

async function loadPatients() {

    try {

        // Ask FastAPI for all patients and appointments
        const [patientsResponse, appointmentsResponse] = await Promise.all([
            fetch("http://127.0.0.1:8000/patients"),
            fetch("http://127.0.0.1:8000/appointments")
        ]);


        if (!patientsResponse.ok || !appointmentsResponse.ok) {

            throw new Error(
                "Could not load patients"
            );

        }


        // Convert the response into JavaScript data
        allPatients = await patientsResponse.json();
        allAppointments = await appointmentsResponse.json();
        renderPatients(allPatients);
        renderCalendar();

    }

    catch (error) {

        console.error(
            "Error loading patients:",
            error
        );

    }

}
//this is where it reads the input given by class == aptientSearch
document.getElementById("patientSearch").addEventListener("input", event => {
    const searchValue = event.target.value.trim().toLowerCase();
    //is somethign is being serached then you go to the next part
    if (searchValue === "") {
        renderPatients(allPatients);
        return;
    }

    //this is saying that all patients.filter = all aptients .filter wand the function used to filter is the one that we wrote after th e{}
    const matchingPatients = allPatients.filter(patient => {
        const patientNumber = String(patient.patient_num);
        const initials = String(patient.initials).toLowerCase();

        return (
            patientNumber.startsWith(searchValue) ||
            initials.startsWith(searchValue)
        );
    });

    renderPatients(matchingPatients, true);
});

// Load patients when the page opens
loadPatients();
