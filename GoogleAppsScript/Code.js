// Paste into Code.gs in a standalone Google Apps Script project.
const REMINDER_PREFIX = 'reminder:';

function jsonResponse(value) {
  return ContentService.createTextOutput(JSON.stringify(value)).setMimeType(ContentService.MimeType.JSON);
}

// Set REMINDER_SECRET in Script Properties, then run and authorize setup once.
function setup() {
  const props = PropertiesService.getScriptProperties();
  const secret = props.getProperty('REMINDER_SECRET');
  if (!secret || secret.length < 32) throw new Error('Set REMINDER_SECRET in Project Settings first.');
  const owner = Session.getEffectiveUser().getEmail();
  if (!owner) throw new Error('Cannot determine your Google account email.');
  MailApp.getRemainingDailyQuota();
  props.setProperty('REMINDER_OWNER', owner);
  ScriptApp.getProjectTriggers().forEach(trigger => {
    if (trigger.getHandlerFunction() === 'sendDueReminders') ScriptApp.deleteTrigger(trigger);
  });
  ScriptApp.newTrigger('sendDueReminders').timeBased().everyMinutes(5).create();
}

function doPost(e) {
  let data;
  try { data = JSON.parse(e.postData.contents); }
  catch (error) { return jsonResponse({ok: false, error: 'invalid_request'}); }
  const props = PropertiesService.getScriptProperties();
  const secret = props.getProperty('REMINDER_SECRET');
  if (!data || !secret || data.secret !== secret) return jsonResponse({ok: false, error: 'unauthorized'});
  if (!props.getProperty('REMINDER_OWNER') ||
      !ScriptApp.getProjectTriggers().some(t => t.getHandlerFunction() === 'sendDueReminders')) {
    return jsonResponse({ok: false, error: 'not_ready'});
  }
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) return jsonResponse({ok: false, error: 'busy'});
  try {
    const now = Date.now();
    if (!Array.isArray(data.summaries) || data.summaries.length < 1 || data.summaries.length > 3) {
      return jsonResponse({ok: false, error: 'invalid_request'});
    }
    const updates = {};
    const dates = new Set();
    let skipped = 0;
    for (const summary of data.summaries) {
      if (!summary || !/^\d{4}-\d{2}-\d{2}$/.test(summary.appointment_date) ||
          dates.has(summary.appointment_date) || typeof summary.subject !== 'string' ||
          !summary.subject || summary.subject.length > 200 || typeof summary.text !== 'string' ||
          typeof summary.scheduled_at !== 'string') {
        return jsonResponse({ok: false, error: 'invalid_request'});
      }
      dates.add(summary.appointment_date);
      const delivery = Date.parse(summary.scheduled_at);
      if (!Number.isFinite(delivery) || delivery > now + 5 * 86400000) {
        return jsonResponse({ok: false, error: 'invalid_request'});
      }
      const key = REMINDER_PREFIX + summary.appointment_date;
      const existing = props.getProperty(key);
      const old = existing ? JSON.parse(existing) : null;
      if (delivery <= now || (old && (old.state !== 'queued' || Date.parse(old.scheduled_at) <= now))) {
        skipped++;
        continue;
      }
      const record = {appointment_date: summary.appointment_date, subject: summary.subject,
        text: summary.text, scheduled_at: summary.scheduled_at, state: 'queued'};
      const encoded = JSON.stringify(record);
      if (Utilities.newBlob(encoded).getBytes().length > 8000) {
        return jsonResponse({ok: false, error: 'too_large'});
      }
      updates[key] = encoded;
    }
    // Date-keyed overwrite is safe to retry if the HTTP response is lost.
    props.setProperties(updates, false);
    return jsonResponse({ok: true, queued: Object.keys(updates).length, skipped: skipped});
  } catch (error) {
    return jsonResponse({ok: false, error: 'queue_error'});
  } finally {
    lock.releaseLock();
  }
}

function sendDueReminders() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) return;
  try {
    const props = PropertiesService.getScriptProperties();
    const owner = props.getProperty('REMINDER_OWNER');
    if (!owner) throw new Error('Run setup first.');
    const now = Date.now();
    const all = props.getProperties();
    let quota = MailApp.getRemainingDailyQuota();
    for (const key of Object.keys(all).filter(k => k.startsWith(REMINDER_PREFIX)).sort()) {
      const record = JSON.parse(all[key]);
      const due = Date.parse(record.scheduled_at);
      if (now - due > 7 * 86400000) { props.deleteProperty(key); continue; }
      if (record.state !== 'queued' || due > now) continue;
      if (now - due > 6 * 3600000) {
        props.setProperty(key, JSON.stringify({state: 'expired', scheduled_at: record.scheduled_at}));
        continue;
      }
      if (quota <= 0) continue;
      // Claim before sending: a crash/ambiguous send requires manual review.
      const marker = {state: 'sending', scheduled_at: record.scheduled_at};
      props.setProperty(key, JSON.stringify(marker));
      try {
        MailApp.sendEmail({to: owner, subject: record.subject, body: record.text, name: 'Dentistry Scheduler'});
        quota--;
        marker.state = 'sent';
        props.setProperty(key, JSON.stringify(marker));
      } catch (error) {
        console.error('Reminder send needs review for ' + key);
      }
    }
  } finally {
    lock.releaseLock();
  }
}
