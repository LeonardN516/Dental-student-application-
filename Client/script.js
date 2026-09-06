const monthLabel = document.getElementById("monthLabel");
const calendarGrid = document.getElementById("calendarGrid");
const prevMonth = document.getElementById("prevMonth");
const nextMonth = document.getElementById("nextMonth");

let currentDate = new Date();

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
    const cell = document.createElement("div");
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
    note.textContent = "";
    cell.appendChild(note);

    if (isToday(cellDate)) {
      cell.classList.add("today");
    }

    cell.addEventListener("click", () => {
      console.log("Selected date:", cellDate.toDateString());
      // Future: display that day's agenda here.
    });

    calendarGrid.appendChild(cell);
  }
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

renderCalendar();
