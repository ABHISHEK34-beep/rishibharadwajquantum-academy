# RBQA – Rishi Bharadwaj Quantum Academy

Flask backend (MongoDB) with the original website as the frontend and an admin panel.

## Run locally

    pip install -r requirements-dev.txt
    RBQA_DEV=1 python app.py

`RBQA_DEV=1` uses a throw-away in-memory database, so nothing is saved when the app stops.
To keep data locally, set `MONGODB_URI` instead (see *Database* below).

- Website: http://localhost:5000
- Admin:   http://localhost:5000/admin  (default login `admin` / `admin123` – change it under Settings)

First start creates the collections and seeds the starter courses and workshops.

## What is connected
| Frontend | Backend |
|---|---|
| Courses grid + "View Curriculum" popup | `GET /api/courses` |
| Workshops list + "Register Interest" popup | `GET /api/workshops`, `POST /api/workshops/<id>/register` |
| Contact form | `POST /api/contact` |
| Admin panel | messages, registrations (+CSV export), courses & workshops CRUD, password change |

Anything you add/edit/hide in the admin panel shows on the public site immediately.

## Options (environment variables)
`PORT` (default 5000), `RBQA_ADMIN_USER`, `RBQA_ADMIN_PASS` (used on first run only), `RBQA_SECRET`, `MONGODB_URI`, `MONGODB_DB` (default `rbqa`, used only if the URI names no database), `RBQA_DEV`.
Example: `RBQA_DEV=1 RBQA_ADMIN_PASS='MyStrongPass1' python app.py`

## Database
Data is stored in **MongoDB** (a free MongoDB Atlas cluster is enough). Set `MONGODB_URI` to the
connection string, e.g. `mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/rbqa`.
Collections are created automatically on first start, and the data lives outside the web server,
so it survives restarts, redeploys and free-tier sleep.

- Without `MONGODB_URI` the app refuses to start (it never silently falls back to temporary storage).
  `RBQA_DEV=1` is the only exception: an in-memory database for local testing.
- On Atlas: **Network Access** must allow the server (use `0.0.0.0/0` on Render, whose IPs change).
- Special characters in the database password must be URL-encoded inside the URI.
- Set `RBQA_SECRET` (any long random string) so admin logins survive restarts.
- `GET /api/health` also checks the database connection (HTTP 503 if it is unreachable).

## Before going public
Use a production server (e.g. `gunicorn app:app`) behind HTTPS and change the admin password.
Not wired yet because the demo had placeholders: WhatsApp number, social links, email sending (messages are stored in the admin panel, not emailed).
