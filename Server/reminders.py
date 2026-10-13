"""Upload owner summaries to Google; Google sends while this app is closed."""
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from database import SessionLocal, engine
from models import Appointment, Patient

logger = logging.getLogger(__name__)
refresh_lock = Lock()
status = {"state": "refreshing", "message": "Checking appointment email reminders..."}


@dataclass
class Settings:
    endpoint: str
    secret: str
    zone: ZoneInfo
    send_time: time
    days: int

    @classmethod
    def load(cls):
        endpoint = os.getenv("GOOGLE_REMINDER_URL", "").strip()
        secret = os.getenv("GOOGLE_REMINDER_SECRET", "").strip()
        if not endpoint and not secret:
            return None
        if not endpoint or len(secret) < 32:
            raise ValueError("Set GOOGLE_REMINDER_URL and a GOOGLE_REMINDER_SECRET of at least 32 characters.")
        url = urlparse(endpoint)
        if (url.scheme != "https" or url.netloc != "script.google.com"
                or not url.path.startswith("/macros/s/") or not url.path.endswith("/exec")
                or url.query or url.fragment):
            raise ValueError("Use the deployed Google Apps Script /exec URL.")
        days = int(os.getenv("REMINDER_DAYS", "3"))
        if not 1 <= days <= 3:
            raise ValueError("REMINDER_DAYS must be between 1 and 3.")
        send_time = time.fromisoformat(os.getenv("REMINDER_TIME", "16:30"))
        if send_time.tzinfo:
            raise ValueError("REMINDER_TIME must be a local time, e.g. 16:30.")
        return cls(endpoint, secret, ZoneInfo(os.getenv("REMINDER_TIMEZONE", "America/Toronto")), send_time, days)


class GoogleProvider:
    def __init__(self, settings):
        self.settings = settings

    def sync(self, summaries):
        request = Request(self.settings.endpoint,
                          data=json.dumps({"secret": self.settings.secret, "summaries": summaries}).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=30) as response:
                if urlparse(getattr(response, "url", "")).hostname == "accounts.google.com":
                    raise RuntimeError("Google deployment requires login. Set web app access to Anyone and Execute as Me, then redeploy.")
                result = json.load(response)
        except (HTTPError, URLError, ValueError):
            raise RuntimeError("Could not reach the Google reminder script. Check deployment and connectivity.") from None
        if not isinstance(result, dict) or result.get("ok") is not True:
            code = result.get("error") if isinstance(result, dict) else None
            messages = {"unauthorized": "Google reminder secrets do not match.",
                        "not_ready": "Run setup in the Google script before deploying.",
                        "too_large": "An appointment summary exceeds Google's 8 KB storage limit.",
                        "busy": "Google reminder queue is busy; retry shortly.",
                        "invalid_request": "Google rejected the summary format."}
            raise RuntimeError(messages.get(code, "Google could not update the reminder queue."))
        if not isinstance(result.get("queued"), int) or not isinstance(result.get("skipped"), int):
            raise RuntimeError("Unexpected Google reminder response. Redeploy the provided script.")
        return result


def delivery_time(day, settings):
    return datetime.combine(day - timedelta(days=1), settings.send_time, settings.zone)


def summary_payload(db, day, settings):
    appointments = (db.query(Appointment, Patient.initials)
                    .join(Patient, Appointment.patient_num == Patient.patient_num)
                    .filter(Appointment.appointment_date == day)
                    .order_by(Appointment.start_time.desc(), Appointment.appointment_id.desc()).all())
    appointment_zone = datetime.combine(day, time(12), settings.zone).tzname()
    lines = [f"Your appointments for {day:%A, %B %d, %Y}",
             f"Times shown in {appointment_zone}; latest appointment first.", ""]
    for appointment, initials in appointments:
        lines.extend([f"time: {appointment.start_time:%H:%M}", f"Initials: {initials}",
                      f"Appointment type: {appointment.appointment_type or 'Not specified'}",
                      f"notes: {appointment.notes or 'None'}", ""])
    if not appointments:
        lines.append(f"No appointments scheduled for {day:%A, %B %d, %Y}.")
    return {"appointment_date": day.isoformat(), "subject": f"Appointments for {day.isoformat()}",
            "text": "\n".join(lines),
            "scheduled_at": delivery_time(day, settings).astimezone(timezone.utc).isoformat()}


def refresh(db, settings, provider, now=None):
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(settings.zone).date()
    first_offset = 1 if delivery_time(today + timedelta(days=1), settings) > now else 2
    summaries = [summary_payload(db, today + timedelta(days=offset), settings)
                 for offset in range(first_offset, first_offset + settings.days)]
    return provider.sync(summaries)


def refresh_reminders():
    """Do not undo successful appointment writes when uploading fails."""
    global status
    with refresh_lock:
        try:
            settings = Settings.load()
            if settings is None:
                status = {"state": "disabled", "message": "Google email reminders are not configured. See EMAIL_REMINDERS.md."}
                return
            status = {"state": "refreshing", "message": "Uploading appointment emails to Google..."}
            with SessionLocal() as db:
                if engine.dialect.name == "postgresql":
                    from sqlalchemy import text
                    with engine.connect() as guard:
                        guard.execute(text("SELECT pg_advisory_lock(7319421)"))
                        try:
                            result = refresh(db, settings, GoogleProvider(settings))
                        finally:
                            guard.execute(text("SELECT pg_advisory_unlock(7319421)"))
                else:
                    result = refresh(db, settings, GoogleProvider(settings))
            status = {"state": "scheduled", "message": f"Google queued {result['queued']} summaries for around {settings.send_time:%H:%M} Eastern time the day before (EDT/EST)."}
            if result["skipped"]:
                status["message"] += f" Left {result['skipped']} summaries unchanged because their cutoff passed or sending already started."
        except Exception as exc:
            message = str(exc) if isinstance(exc, (ValueError, RuntimeError)) else "Could not update Google reminders. Check connectivity and retry."
            logger.warning("Email reminder refresh failed: %s", message)
            status = {"state": "error", "message": message}
