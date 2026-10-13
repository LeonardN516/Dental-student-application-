import io
import json
import os
import sys
import unittest
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Server'))
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from database import Base
from models import Appointment, Patient
from reminders import Settings, GoogleProvider, refresh, summary_payload


class FakeProvider:
    def __init__(self):
        self.queued = {}
        self.fail = False

    def sync(self, summaries):
        if self.fail:
            raise RuntimeError('Upload failed')
        for summary in summaries:
            self.queued[summary['appointment_date']] = summary
        return {'ok': True, 'queued': len(summaries), 'skipped': 0}


class ReminderTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.provider = FakeProvider()
        self.settings = Settings('https://script.google.com/macros/s/test/exec', 'x' * 40,
                                 ZoneInfo('America/Toronto'), time(16, 30), 3)
        self.now = datetime(2026, 10, 10, 16, tzinfo=timezone.utc)
        self.tomorrow = date(2026, 10, 11)
        self.db.add(Patient(patient_num=1, initials='AB', gender='X',
                            preferred_contact='email', contact_person='Self', payment_method='cash'))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def add_appointment(self, day, hour, notes='Example notes'):
        self.db.add(Appointment(patient_num=1, appointment_date=day, start_time=time(hour),
                                appointment_type='Cleaning', notes=notes))
        self.db.commit()

    def test_summary_filters_and_descending_order(self):
        self.add_appointment(self.tomorrow, 9)
        self.add_appointment(self.tomorrow, 16, 'Latest notes')
        self.add_appointment(self.tomorrow + timedelta(days=1), 12, 'Other day')
        payload = summary_payload(self.db, self.tomorrow, self.settings)
        body = payload['text']
        self.assertLess(body.index('16:00'), body.index('09:00'))
        self.assertIn('time: 16:00\nInitials: AB\nAppointment type: Cleaning\nnotes: Latest notes', body)
        self.assertIn('Times shown in EDT', body)
        self.assertNotIn('Other day', body)
        self.assertEqual(payload['scheduled_at'], '2026-10-10T20:30:00+00:00')

    def test_reopening_overwrites_without_duplicate(self):
        refresh(self.db, self.settings, self.provider, self.now)
        self.add_appointment(self.tomorrow, 15, 'Updated')
        refresh(self.db, self.settings, self.provider, self.now)
        self.assertEqual(len(self.provider.queued), 3)
        self.assertIn('Updated', self.provider.queued[self.tomorrow.isoformat()]['text'])

    def test_deleted_appointment_disappears(self):
        self.add_appointment(self.tomorrow, 9, 'Remove me')
        refresh(self.db, self.settings, self.provider, self.now)
        self.db.query(Appointment).delete()
        self.db.commit()
        refresh(self.db, self.settings, self.provider, self.now)
        body = self.provider.queued[self.tomorrow.isoformat()]['text']
        self.assertNotIn('Remove me', body)
        self.assertIn('No appointments scheduled for Sunday, October 11, 2026.', body)

    def test_after_cutoff_keeps_tomorrow_and_extends_window(self):
        refresh(self.db, self.settings, self.provider, self.now)
        old = self.provider.queued[self.tomorrow.isoformat()]
        refresh(self.db, self.settings, self.provider, self.now.replace(hour=20, minute=30))
        self.assertIs(self.provider.queued[self.tomorrow.isoformat()], old)
        self.assertIn('2026-10-14', self.provider.queued)

    def test_first_open_after_cutoff_does_not_schedule_in_past(self):
        now = self.now.replace(hour=21)
        refresh(self.db, self.settings, self.provider, now)
        self.assertNotIn(self.tomorrow.isoformat(), self.provider.queued)
        for payload in self.provider.queued.values():
            self.assertGreater(datetime.fromisoformat(payload['scheduled_at']), now)

    def test_dst_transition_and_winter_delivery(self):
        payload = summary_payload(self.db, date(2026, 11, 1), self.settings)
        self.assertIn('Times shown in EST', payload['text'])
        self.assertEqual(payload['scheduled_at'], '2026-10-31T20:30:00+00:00')
        payload = summary_payload(self.db, date(2026, 11, 2), self.settings)
        self.assertEqual(payload['scheduled_at'], '2026-11-01T21:30:00+00:00')

    def test_failed_upload_does_not_replace_existing_queue(self):
        refresh(self.db, self.settings, self.provider, self.now)
        before = dict(self.provider.queued)
        self.provider.fail = True
        with self.assertRaises(RuntimeError):
            refresh(self.db, self.settings, self.provider, self.now)
        self.assertEqual(self.provider.queued, before)

    def test_google_settings_no_resend_or_email_required(self):
        with patch.dict(os.environ, {'GOOGLE_REMINDER_URL': self.settings.endpoint,
                                     'GOOGLE_REMINDER_SECRET': self.settings.secret}, clear=True):
            settings = Settings.load()
        self.assertEqual(settings.send_time, time(16, 30))
        self.assertEqual(settings.zone.key, 'America/Toronto')

    def test_settings_reject_non_google_endpoint(self):
        with patch.dict(os.environ, {'GOOGLE_REMINDER_URL': 'https://example.com/exec',
                                     'GOOGLE_REMINDER_SECRET': self.settings.secret}, clear=True):
            with self.assertRaises(ValueError):
                Settings.load()

    def test_provider_checks_google_error_without_leaking_secret(self):
        response = io.BytesIO(json.dumps({'ok': False, 'error': 'unauthorized'}).encode())
        with patch('reminders.urlopen', return_value=response):
            with self.assertRaisesRegex(RuntimeError, 'secrets do not match'):
                GoogleProvider(self.settings).sync([])

    def test_provider_identifies_google_signin_redirect(self):
        response = io.BytesIO(b'<html>Sign in</html>')
        response.url = 'https://accounts.google.com/ServiceLogin'
        with patch('reminders.urlopen', return_value=response):
            with self.assertRaisesRegex(RuntimeError, 'Set web app access to Anyone'):
                GoogleProvider(self.settings).sync([])

    def test_provider_posts_secret_in_body_and_checks_acknowledgement(self):
        response = io.BytesIO(b'{"ok":true,"queued":3,"skipped":0}')
        with patch('reminders.urlopen', return_value=response) as request:
            result = refresh(self.db, self.settings, GoogleProvider(self.settings), self.now)
        sent = json.loads(request.call_args.args[0].data)
        self.assertEqual(sent['secret'], self.settings.secret)
        self.assertEqual(len(sent['summaries']), 3)
        self.assertEqual(result['queued'], 3)


if __name__ == '__main__':
    unittest.main()
