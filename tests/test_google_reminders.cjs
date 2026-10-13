const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('GoogleAppsScript/Code.js', 'utf8');
let count = 0;

function fixture() {
  let now = Date.parse('2026-10-10T16:00:00Z');
  let quota = 100;
  let fail = false;
  const properties = {REMINDER_SECRET: 'x'.repeat(40), REMINDER_OWNER: 'owner@gmail.com'};
  const sent = [];
  let triggers = [{getHandlerFunction: () => 'sendDueReminders'}];
  let held = false;
  class Clock extends Date { static now() { return now; } }
  const context = vm.createContext({
    Date: Clock, console: {error: () => {}},
    ContentService: {MimeType: {JSON: 'json'}, createTextOutput: text => ({
      text, setMimeType() { return this; }
    })},
    PropertiesService: {getScriptProperties: () => ({
      getProperty: key => properties[key] ?? null,
      setProperty: (key, value) => { properties[key] = value; },
      getProperties: () => ({...properties}),
      setProperties: updates => Object.assign(properties, updates),
      deleteProperty: key => { delete properties[key]; }
    })},
    LockService: {getScriptLock: () => ({
      tryLock: () => { if (held) return false; held = true; return true; },
      releaseLock: () => { held = false; }
    })},
    Utilities: {newBlob: text => ({getBytes: () => Buffer.from(text)})},
    Session: {getEffectiveUser: () => ({getEmail: () => 'owner@gmail.com'})},
    ScriptApp: {
      getProjectTriggers: () => triggers,
      deleteTrigger: trigger => { triggers = triggers.filter(t => t !== trigger); },
      newTrigger: name => ({timeBased() { return this; }, everyMinutes(minutes) {
        assert.equal(minutes, 5); return this;
      }, create() { triggers.push({getHandlerFunction: () => name}); }})
    },
    MailApp: {getRemainingDailyQuota: () => quota, sendEmail: message => {
      if (fail) throw new Error('Mail unavailable');
      sent.push(message);
    }}
  });
  vm.runInContext(source, context);
  return {context, properties, sent,
    advance: value => { now = Date.parse(value); },
    setQuota: value => { quota = value; },
    failSending: () => { fail = true; },
    triggers: () => triggers,
    post: (summaries, secret = 'x'.repeat(40)) => JSON.parse(context.doPost({
      postData: {contents: JSON.stringify({secret, summaries})}
    }).text)
  };
}

const summary = (text = 'Initial summary') => ({appointment_date: '2026-10-11',
  scheduled_at: '2026-10-10T20:30:00+00:00', subject: 'Appointments for 2026-10-11', text});
function test(name, run) { run(); count++; console.log('PASS ' + name); }

test('unauthorized uploads cannot change queue', () => {
  const f = fixture();
  assert.equal(f.post([summary()], 'wrong').error, 'unauthorized');
  assert.equal(f.properties['reminder:2026-10-11'], undefined);
});
test('repeated uploads replace one entry and send latest content once to owner', () => {
  const f = fixture();
  assert.equal(f.post([summary()]).queued, 1);
  assert.equal(f.post([summary('Latest information')]).queued, 1);
  f.context.sendDueReminders();
  assert.equal(f.sent.length, 0);
  f.advance('2026-10-10T20:31:00Z');
  f.context.sendDueReminders();
  f.context.sendDueReminders();
  assert.equal(f.sent.length, 1);
  assert.equal(f.sent[0].to, 'owner@gmail.com');
  assert.equal(f.sent[0].body, 'Latest information');
  assert.equal(JSON.parse(f.properties['reminder:2026-10-11']).state, 'sent');
  assert.ok(!f.properties['reminder:2026-10-11'].includes('Latest information'));
});
test('cutoff preserves due queued email and does not schedule a late new email', () => {
  const f = fixture();
  f.post([summary()]);
  f.advance('2026-10-10T20:30:00Z');
  assert.equal(f.post([summary('Late update')]).skipped, 1);
  f.context.sendDueReminders();
  assert.equal(f.sent[0].body, 'Initial summary');
  const g = fixture();
  g.advance('2026-10-10T20:30:00Z');
  assert.equal(g.post([summary()]).skipped, 1);
  assert.equal(g.properties['reminder:2026-10-11'], undefined);
});
test('oversized batch fails validation before overwriting existing queue', () => {
  const f = fixture();
  f.post([summary()]);
  const big = {...summary('🦷'.repeat(3000)), appointment_date: '2026-10-12'};
  assert.equal(f.post([summary('Changed'), big]).error, 'too_large');
  assert.equal(JSON.parse(f.properties['reminder:2026-10-11']).text, 'Initial summary');
});
test('ambiguous mail failure stays claimed and is not automatically sent twice', () => {
  const f = fixture();
  f.post([summary()]);
  f.advance('2026-10-10T20:31:00Z');
  f.failSending();
  f.context.sendDueReminders();
  f.context.sendDueReminders();
  assert.equal(JSON.parse(f.properties['reminder:2026-10-11']).state, 'sending');
  assert.equal(f.sent.length, 0);
});
test('quota exhaustion defers and long delays expire rather than send later', () => {
  const f = fixture();
  f.post([summary()]);
  f.setQuota(0);
  f.advance('2026-10-10T20:31:00Z');
  f.context.sendDueReminders();
  assert.equal(JSON.parse(f.properties['reminder:2026-10-11']).state, 'queued');
  f.advance('2026-10-11T04:00:00Z');
  f.context.sendDueReminders();
  assert.equal(JSON.parse(f.properties['reminder:2026-10-11']).state, 'expired');
  assert.equal(f.sent.length, 0);
});
test('setup replaces trigger and requires authorization identity', () => {
  const f = fixture();
  f.context.setup();
  f.context.setup();
  assert.equal(f.triggers().length, 1);
  assert.equal(f.properties.REMINDER_OWNER, 'owner@gmail.com');
});
test('missing trigger is reported before queue accepts uploads', () => {
  const f = fixture();
  f.context.ScriptApp.getProjectTriggers = () => [];
  assert.equal(f.post([summary()]).error, 'not_ready');
});
console.log(`${count} Google queue tests passed; no live services called.`);
