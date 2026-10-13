# Dentistry Scheduler — Mac Setup

## First-time setup

For the complete setup, including Windows and Gmail reminders, see
[SETUP_GUIDE.md](SETUP_GUIDE.md).

Install Homebrew from [brew.sh](https://brew.sh), then clone the repository:

```bash
git clone https://github.com/LeonardN516/Dental-student-application-.git Dentistry_scheduler
cd Dentistry_scheduler
bash setup_mac.sh
```

## Start the application

```bash
cd Dentistry_scheduler
bash start_mac.sh
```

The browser opens automatically. Press `Control+C` in Terminal to stop the application.

## Optional Gmail reminders

Follow [EMAIL_REMINDERS.md](EMAIL_REMINDERS.md) to deploy the Google Apps Script
queue and connect it in `.env`. Google sends the uploaded appointment summaries
around 4:30 PM Eastern time the day before, even while this computer is off.

## Pull updates

```bash
cd Dentistry_scheduler
git pull origin main
bash setup_mac.sh
bash start_mac.sh
```

## Open pgAdmin

```bash
open -a "pgAdmin 4"
```
