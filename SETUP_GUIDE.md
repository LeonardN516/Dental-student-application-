# Dentistry Scheduler: complete setup guide

This guide sets up the scheduler on your computer and optional appointment emails
in your own Google account. If the scheduler already works, start at section 3.
If you do not want email reminders, complete sections 1 and 2 only.

## What you are setting up

The scheduler uses a local PostgreSQL database, a Python backend on port 8000,
and a frontend on port 5500. Email reminders use a Google Apps Script project
that you create in your Gmail account.

When the backend starts, or appointments change, it uploads three future daily
summaries to Google. Google sends each summary to you around **4:30 PM Eastern
time the day before the appointments**, even when your computer is off. Eastern
time automatically follows EDT in summer and EST in winter.

Each user needs their own database, local `.env`, Google project, shared secret,
and deployment URL. Pulling the repository does not copy another user's `.env`
or Google setup. Sharing a Google project would send summaries to that project's
owner and could overwrite someone else's queue for the same appointment date.

No custom domain, Resend account, Gmail password, or paid email plan is needed
for this Google integration. Free personal accounts currently have a quota of
100 email recipients per day. Quotas can change; see
[Google's quota documentation](https://developers.google.com/apps-script/guides/services/quotas).

## 1. Get the application

Install Git if it is not already available. Open Terminal on macOS or PowerShell
on Windows. Run these commands in the folder where you want the project:

```text
git clone https://github.com/LeonardN516/Dental-student-application-.git Dentistry_scheduler
cd Dentistry_scheduler
```

If you already have the repository, open its existing folder instead and run:

```text
git pull origin main
```

The rest of this guide assumes commands are run from the project root: the folder
containing `pyproject.toml`, `Server`, `Client`, and `database_setup.sql`.

## 2. Set up the application and database

### macOS

Install [Homebrew](https://brew.sh/) first. Then, from the project root:

```bash
bash setup_mac.sh
```

The setup script installs uv, PostgreSQL 17 and pgAdmin; starts PostgreSQL; creates
the `Dentistry_scheduler` database and its tables; creates `.env` if it does not
exist; and installs the Python dependencies. Existing `.env` files are preserved.

Start the application:

```bash
bash start_mac.sh
```

The browser opens automatically. Keep the terminal open while using the scheduler.
Press **Control+C** to stop the local application. Google continues sending any
summaries already uploaded successfully.

### Windows

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) using its
   Windows instructions. Reopen PowerShell afterward and check `uv --version`.
2. Install PostgreSQL with pgAdmin from the
   [PostgreSQL download page](https://www.postgresql.org/download/).
   Remember the password you choose for the `postgres` database user. Keep the
   default port `5432`, or use your chosen port in the connection string below.
3. Open pgAdmin, connect to your local PostgreSQL server, and create a database
   named **Dentistry_scheduler**. Select that database, open **Query Tool**, open
   the project's `database_setup.sql`, and execute the whole file. It creates
   the `patient` and `appointment` tables.
4. From the project root, install dependencies:

   ```powershell
   uv sync
   ```

   The project requires Python 3.14 or newer; uv can install a compatible Python
   when needed.
5. If `.env` does not exist, create it from the template:

   ```powershell
   Copy-Item -LiteralPath .env.example -Destination .env
   ```

   Do not overwrite an existing `.env`. Open it in your editor and set:

   ```dotenv
   DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/Dentistry_scheduler
   ```

   Replace `YOUR_PASSWORD` with your PostgreSQL password. URL-encode reserved
   characters in the username/password, such as `@`, `:` or `/`. This password
   is for PostgreSQL, not Gmail.
6. Start the backend in one PowerShell terminal:

   ```powershell
   uv run fastapi dev Server/main.py
   ```

7. Open a second PowerShell terminal in the project root and start the frontend:

   ```powershell
   uv run python -m http.server 5500 --directory Client
   ```

8. Open [the scheduler](http://127.0.0.1:5500/index.html). Keep both terminals
   open while using it. Press **Ctrl+C** in each terminal to stop it.

### Check the local setup

Open [the backend](http://127.0.0.1:8000/) and expect `FastAPI is working`.
Open the scheduler and confirm the calendar loads. Create a patient and an
appointment to confirm the database connection. If you have not configured Google
yet, **Google email reminders are not configured** is expected.

## 3. Create your private shared secret

The shared secret lets your local app upload summaries to your Google script.
It is a random value you create, not a Google API key or your Gmail password.

If your `.env` already contains a random `GOOGLE_REMINDER_SECRET` of at least
32 characters, reuse it. For a new installation, generate one from the project root:

```text
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the generated value into `.env`:

```dotenv
GOOGLE_REMINDER_URL=
GOOGLE_REMINDER_SECRET=PASTE_YOUR_GENERATED_VALUE_HERE
REMINDER_TIMEZONE=America/Toronto
REMINDER_TIME=16:30
REMINDER_DAYS=3
```

Keep `DATABASE_URL` unchanged. Replace existing settings instead of adding
duplicate lines. `.env.example` is a blank template and does not contain your secret.
Keep `.env` and the secret private; `.env` is excluded from Git.

## 4. Create the Google Apps Script project

1. Sign in to the Gmail account where you want to receive reminders. Open
   [Google Apps Script](https://script.google.com/) and choose **New project**.
2. Name the project **Dentistry Scheduler Reminders**.
3. In the **Editor** (`<>` icon on the left), open **Code.gs**. Delete the default
   sample function and paste the entire contents of
   [GoogleAppsScript/Code.js](GoogleAppsScript/Code.js). Copy the file contents,
   not just its filename or Markdown code fences.
4. Click **Project Settings** (gear icon on the left). Enable
   **Show appsscript.json manifest file in editor**.
5. Return to **Editor**, open **appsscript.json**, and replace its contents with
   [GoogleAppsScript/appsscript.json](GoogleAppsScript/appsscript.json).
6. Save the project. The manifest sets Toronto/Eastern time and the permissions
   for sending email, identifying your account, and creating the automatic trigger.

## 5. Add Script Properties

1. Open **Project Settings** (gear icon).
2. Scroll down to **Script Properties** and choose **Add script property**.
3. Enter **REMINDER_SECRET** as the property name.
4. Copy only the value after `GOOGLE_REMINDER_SECRET=` from your local `.env`
   into the property's value field. Do not paste the variable name, surrounding
   quotes, or extra spaces.
5. Click **Save script properties**.

The names deliberately differ, but the values must match exactly:

| Location | Name | Value |
| --- | --- | --- |
| Your computer's `.env` | `GOOGLE_REMINDER_SECRET` | Your generated random value |
| Google's Script Properties | `REMINDER_SECRET` | The same random value |

## 6. Run setup and authorize Google

1. Click the **Editor** (`<>`) icon and open **Code.gs**.
2. In the toolbar above the code, use the function dropdown beside **Run** and
   **Debug** to select **setup**. Do not select `jsonResponse` or `doPost`.
3. Click **Run** (play icon).
4. Follow Google's authorization prompts using your intended Gmail account.
   If your own newly created project is shown as unverified, review the code and
   permissions, then use **Advanced** to continue to that project if available.
   A school/work account may block this; follow your organization's account rules.
5. Wait for **Execution completed**.

Confirm all three results:

- **Executions** shows a completed run with **Function: setup**.
- **Triggers** (alarm-clock icon) contains **sendDueReminders**, running every
  five minutes.
- **Project Settings > Script Properties** now contains **REMINDER_OWNER** with
  your Gmail address. Setup creates this automatically; do not enter someone
  else's address here.

Setup does not send a test email. It prepares the queue sender. Running it again
replaces its trigger rather than creating duplicate triggers.

## 7. Deploy the script

1. Click **Deploy > New deployment** at the top right.
2. Choose the deployment type **Web app**.
3. Enter a description, such as **Appointment reminder queue**.
4. Set **Execute as: Me**.
5. Set **Who has access: Anyone**. This must allow callers without a Google login;
   **Anyone with a Google account** will not work for the local backend.
6. Click **Deploy** and complete any authorization prompts.
7. Copy the **Web app URL** ending in **/exec**. Do not copy the deployment ID
   alone, the editor URL, or a test URL ending in `/dev`.

The public endpoint accepts uploads only with your shared secret, does not expose
the queue for reading, and always sends to the account that ran setup. See
[Google's web app deployment guide](https://developers.google.com/apps-script/guides/web).

## 8. Connect the app and confirm uploading

Paste the Web app URL into `.env`:

```dotenv
GOOGLE_REMINDER_URL=https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec
```

Leave your secret and reminder settings in place. Sender and recipient come from
your authorized Google account; no separate email address is needed in `.env`.

Stop and restart the backend completely so it loads the new settings. Updating
`.env` alone does not refresh an already running process.

Open the main calendar page, refresh the browser, and scroll to the bottom. Expect:

```text
Google queued 3 summaries for around 16:30 Eastern time the day before (EDT/EST).
```

This confirms Google accepted the queue, not that an email has been delivered yet.
Uploading also happens automatically after appointment changes and patient
edits/deletions. No daily manual upload is required while you are regularly using
the app, but Google only knows the data from the last successful upload.

## 9. Inspect the queue and confirm delivery

In **Google Apps Script > Project Settings > Script Properties**, find entries
named `reminder:YYYY-MM-DD`. The date is the appointment date. Each queued value
contains `subject`, `text`, `scheduled_at`, and `state`.

`scheduled_at` is in UTC. For the default 4:30 PM delivery, it is 20:30 UTC during
EDT and 21:30 UTC during EST, on the day before the appointments.

| State | Meaning |
| --- | --- |
| `queued` | Google is waiting for delivery time, or temporarily waiting for quota |
| `sending` | Sending began; if it remains here, inspect Executions and Gmail before retrying |
| `sent` | MailApp reported success; appointment details were removed from the queue entry |
| `expired` | Delivery was delayed over six hours, so the script skipped the stale summary |

Use **Executions** to inspect runs of `sendDueReminders`. To read the actual sent
email, open your Gmail **Sent** folder and search:

```text
in:sent subject:"Appointments for"
```

Check your Inbox and Spam too. Since the same account sends and receives, a copy
in Sent confirms sending and a copy in your received mail confirms receipt.
Completed trigger executions alone do not prove an email was sent: the trigger
also runs when there is nothing due.

Emails list only that appointment date's appointments, from latest to earliest:

```text
time: 16:00
Initials: AB
Appointment type: Cleaning
notes: Example appointment notes

time: 09:00
Initials: CD
Appointment type: Examination
notes: None
```

Empty days explicitly say **No appointments scheduled for [appointment date]**.

## 10. Test delivery without waiting until tomorrow

Choose a test time five to ten minutes ahead of the current Eastern time, leaving
enough time to restart and upload. Avoid doing this just before midnight. For
example, if it is 5:20 PM, set:

```dotenv
REMINDER_TIME=17:30
```

Create an appointment for tomorrow, save `.env`, and restart the backend before
5:30 PM. Confirm a queued entry for tomorrow and check its `text` and
`scheduled_at`. Wait until the test time and allow Google additional time to run
its five-minute trigger. Exact-minute delivery is not guaranteed.

An existing entry whose original delivery time has passed, or whose state is
already `sent`/`sending`, will not be replaced just by changing the clock setting.
If testing must use a clean queue, create a separate Google project using the
same setup steps and point your local app to that test deployment. Avoid deleting
real queue markers to force a resend; they prevent duplicate emails.

After testing, restore `REMINDER_TIME=16:30` and restart the backend. Check the
new queue times. A test email already sent cannot be recalled or regenerated
automatically for that appointment date.

## 11. Everyday behaviour and cleanup

Before the delivery cutoff, the app queues tomorrow and the following two dates.
At or after the cutoff, it leaves tomorrow's summary untouched and queues the
three appointment dates starting the day after tomorrow. If the app is first
opened after the cutoff, it does not create a late reminder for tomorrow.

Your computer can be off after uploading, but closing the app longer than the
queued window means reminders eventually stop until the next successful upload.
Changing an appointment after its summary's cutoff does not change that email.

After a successful send, Google removes the queued appointment contents and keeps
a small sent marker. Reminder entries are automatically removed more than seven
days after their scheduled send time when the trigger runs. The owner and secret
properties remain because they are still needed.

Each summary must fit within the app's 8 KB limit, below Google's 9 KB property
limit. If your notes make a summary too large, uploading reports an error rather
than truncating details. Shorten notes or have the integration extended for larger
summaries. Quotas, account authorization and Google's availability also affect
delivery.

## 12. Troubleshooting

| Message or symptom | What to check |
| --- | --- |
| Google reminders are not configured | Fill in the Google URL and secret in `.env`, then restart the backend |
| Set GOOGLE_REMINDER_URL and a secret of at least 32 characters | Use both settings; generate a random secret if necessary |
| Google deployment requires login | Set Execute as Me and Who has access Anyone; update the deployment |
| Google reminder secrets do not match | Save REMINDER_SECRET in Script Properties with the exact local GOOGLE_REMINDER_SECRET value |
| Run setup in the Google script before deploying | Run the actual setup function, then check REMINDER_OWNER and the sendDueReminders trigger |
| Could not reach the Google reminder script | Check internet access, the /exec URL, deployment access and Google availability |
| Summary exceeds 8 KB | Reduce unusually long appointment notes; the previous queue stays in place |
| No Run button | Leave Project Settings and open the Editor; Run is above the code |
| Execution completed but setup is missing | Inspect the Function column; jsonResponse finishing does not run setup |
| No reminder in Gmail | Check queue time/state, trigger Executions, the owner address, quota, Sent, Inbox and Spam |
| The app still uses old settings | Stop and restart the backend; refresh the browser for frontend changes |

The **Retry email reminders** button appears at the bottom of the main calendar
when the app reports a reminder error. It uploads again; it does not immediately
send the emails or resend completed summaries.

Alternatively, open [API docs](http://127.0.0.1:8000/docs), expand
**POST /reminders/refresh**, select **Try it out**, and click **Execute**.
Use **GET /reminders/status** to inspect the latest upload result.

For a marker stuck in `sending`, check Gmail Sent and the trigger execution before
attempting recovery. The script deliberately avoids automatically retrying an
ambiguous send because Gmail delivery and queue updates cannot be one atomic action.

## 13. Update, change accounts, or stop reminders

For local code updates, stop the app, run `git pull origin main`, install any
dependency updates with `uv sync`, and restart. Mac users can rerun `setup_mac.sh`
as in [README_MAC.md](README_MAC.md). Your private `.env` is not pulled from Git.

If `GoogleAppsScript/Code.js` or the manifest changes, copy the updated contents
into your Google project. Run setup again if permissions/triggers change. Then
use **Deploy > Manage deployments > Edit > New version > Deploy**. Editing the
Google code alone does not update the published deployment. If the deployment
URL changes, update `.env` and restart.

To use a different Gmail account, create and authorize a new project in that
account and update the local URL and secret. Disable the old project's trigger
to stop previously queued emails to the old account.

To stop emails entirely, delete the **sendDueReminders** trigger in Google Apps
Script. Disable uploads locally by clearing both `GOOGLE_REMINDER_URL` and
`GOOGLE_REMINDER_SECRET`, then restarting the backend. Clearing local settings
alone does not cancel emails already queued in Google.

If moving from Resend, cancel any pending Resend emails to avoid receiving both
versions. Old Resend environment variables and the old email_reminder database
table are ignored by this Google integration.

## Final setup checklist

- The scheduler opens and saves appointments in your own local database.
- Your own Gmail account owns and authorizes the Google project.
- Code.gs and the manifest match the repository files.
- The secret matches in `.env` and Script Properties.
- setup completed; REMINDER_OWNER and the five-minute trigger exist.
- The deployed web app executes as Me, permits Anyone, and has an /exec URL.
- The backend was restarted and reports successful Google uploads.
- The queued dates, contents and delivery times are correct.
- A live test appeared in Gmail; the normal time was restored to 16:30.
