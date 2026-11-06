"""
Rishi Bharadwaj Quantum Academy (RBQA) - backend
Flask + SQLite. Serves the public site, a JSON API and an admin panel.

Run:  python app.py      ->  http://localhost:5000
Admin: http://localhost:5000/admin
"""
import csv
import io
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from functools import wraps

from flask import (Flask, Response, g, jsonify, render_template, request,
                   session)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("RBQA_DB", os.path.join(BASE_DIR, "rbqa.db"))
SECRET_FILE = os.path.join(BASE_DIR, ".secret_key")

app = Flask(__name__, static_folder="static", template_folder="templates")


def _load_secret():
    """Persist a random secret key so admin sessions survive restarts."""
    env = os.environ.get("RBQA_SECRET")
    if env:
        return env
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE) as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(SECRET_FILE, "w") as f:
        f.write(key)
    return key


app.config.update(
    SECRET_KEY=_load_secret(),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=64 * 1024,
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS admin (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    audience TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    topics TEXT NOT NULL DEFAULT '',          -- newline separated
    icon TEXT NOT NULL DEFAULT 'fa-atom',
    category TEXT NOT NULL DEFAULT 'quantum', -- school / neet-jee / practical / quantum / rf
    sort_order INTEGER NOT NULL DEFAULT 0,
    published INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS workshops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Upcoming',  -- Upcoming / Planning / Completed
    date_label TEXT NOT NULL DEFAULT 'TBA',
    mode TEXT NOT NULL DEFAULT 'Online',
    tags TEXT NOT NULL DEFAULT '',            -- comma separated
    sort_order INTEGER NOT NULL DEFAULT 0,
    published INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    interest TEXT NOT NULL DEFAULT '',
    class_course TEXT NOT NULL DEFAULT '',
    learning_mode TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workshop_id INTEGER NOT NULL REFERENCES workshops(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""

# Course categories (order = order shown on the website).  (key, label, icon)
CATEGORIES = [
    ("school", "School-Level Physics", "fa-school"),
    ("neet-jee", "NEET & JEE Physics", "fa-graduation-cap"),
    ("practical", "Practical Physics & Experiments", "fa-flask"),
    ("quantum", "Quantum Technology", "fa-atom"),
    ("rf", "RF, Microwave & Electronics", "fa-satellite-dish"),
]
CATEGORY_KEYS = {c[0] for c in CATEGORIES}

# (title, audience, description, topics, icon, category)
SEED_COURSES = [
    # --- A. School-Level Physics
    ("Classes 9-10 Physics Fundamentals", "Classes 9-10",
     "Build a strong base in school physics through concept-based learning, practical demonstrations and simple experiments.",
     "Motion, Force & Energy\nLight, Sound & Electricity\nPractical Demonstrations & Experiments\nConcept-Based Problem Solving", "fa-school", "school"),
    ("Classes 11-12 Physics", "Classes 11-12",
     "Concept-first physics for senior secondary students, connecting board syllabus topics with experiments and real applications.",
     "Mechanics & Thermodynamics\nElectricity & Magnetism\nOptics & Modern Physics\nPractical Demonstrations & Experiments", "fa-book-open", "school"),
    # --- B. NEET & JEE Physics Preparation
    ("Classes 11-12 JEE & NEET Physics", "Classes 11-12, NEET & JEE aspirants",
     "A combined Class 11-12 physics programme for students preparing for NEET and JEE, covering the full syllabus with concept building, numerical practice, PYQs and regular tests.",
     "Class 11 Physics (Mechanics, Thermodynamics, Waves)\nClass 12 Physics (Electromagnetism, Optics, Modern Physics)\nChapter-wise Concept Building\nNumerical Problem-Solving\nPrevious-Year Questions (PYQs)\nPractice & Mock Tests\nDoubt-Clearing Sessions", "fa-atom", "neet-jee"),
    ("NEET Physics Preparation", "NEET aspirants",
     "Chapter-wise concept building with numerical practice, previous-year questions and regular doubt-clearing sessions.",
     "Chapter-wise Concept Building\nNumerical Problem-Solving\nPrevious-Year Questions (PYQs)\nPractice & Mock Tests\nDoubt-Clearing Sessions", "fa-user-doctor", "neet-jee"),
    ("JEE Main Physics Preparation", "JEE Main aspirants",
     "Structured physics preparation for JEE Main with problem-solving practice, PYQs, mock tests and doubt support.",
     "Chapter-wise Concept Building\nNumerical Problem-Solving\nPrevious-Year Questions (PYQs)\nPractice & Mock Tests\nDoubt-Clearing Sessions", "fa-bullseye", "neet-jee"),
    ("JEE Advanced Physics Preparation", "JEE Advanced aspirants",
     "Deeper conceptual and analytical physics for JEE Advanced, with advanced problem-solving, PYQs and test practice.",
     "Advanced Concept Building\nAnalytical Problem-Solving\nPrevious-Year Questions (PYQs)\nPractice & Mock Tests\nDoubt-Clearing Sessions", "fa-brain", "neet-jee"),
    # --- C. Practical Physics & Experiments
    ("Practical Physics & Experiments", "Class 11-12, UG, Educators",
     "Hands-on experiments that connect classroom theory with measurement, observation and data analysis.",
     "Photoelectric Effect\nPlanck's Constant Experiment\nMalus's Law\nDiffraction and Interference\nHydrogen Spectrum\nWien's Displacement Law\nIntroduction to Atomic Physics and Rydberg Atoms", "fa-flask", "practical"),
    # --- D. Quantum Technology (first four rows are the original courses, kept as-is)
    ("Fundamental Physics to Quantum Mechanics", "Class 11-12, UG, Educators",
     "Transition from classical to quantum physics. Covers Blackbody Radiation, Photoelectric Effect, Wave-Particle Duality, and Python simulations.",
     "Double-Slit Interference\nPlanck's Quantum Hypothesis\nIntro to Atomic Spectra", "fa-atom", "quantum"),
    ("Introduction to Quantum Computing", "Beginner Friendly",
     "Learn the basics of qubits, superposition, and entanglement. Includes hands-on Python simulations and introduction to Qiskit.",
     "Classical vs Quantum Bits\nBasic Quantum Gates\nQuantum Circuits\nIntroduction to Qiskit & Python Simulations", "fa-microchip", "quantum"),
    ("Quantum Communication & QKD", "Intermediate",
     "Understand principles of secure quantum communication, no-cloning theorem, and cryptographic protocols.",
     "The No-Cloning Principle\nBB84 Protocol\nQuantum Key Distribution (QKD)\nSimulation-Based Learning", "fa-network-wired", "quantum"),
    ("Introduction to Quantum Sensing", "Advanced",
     "Explore precision measurement techniques using atomic states. Discover NV-centers and Rydberg-atom based sensors.",
     "Classical vs Quantum Sensors\nAtomic Magnetometers\nRydberg Atom-Based RF Sensing\nNoise & Sensitivity", "fa-satellite-dish", "quantum"),
    # --- E. RF, Microwave & Electronics
    ("Basic Electronics", "Class 11-12, UG",
     "Foundational electronics for students who want to move towards communication systems, RF and instrumentation.",
     "Semiconductor Devices\nAnalog Circuit Basics\nDigital Electronics Basics\nCircuit Measurements", "fa-microchip", "rf"),
    ("Intro to RF and Microwave Technologies", "Engineering & Research",
     "An introductory pathway for understanding instrumentation, S-parameters, and measurement vital for quantum systems.",
     "Network Analyzers\nLow-Noise Amplifiers\nCryogenic Considerations\nMicrowave Measurements", "fa-wave-square", "rf"),
    ("Antenna Fundamentals & Communication Systems", "UG, Engineering & Research",
     "Core ideas of antennas and electromagnetic radiation, with an introduction to how communication systems are built.",
     "Antenna Fundamentals\nRadiation & Propagation Basics\nIntroduction to Communication Systems", "fa-tower-broadcast", "rf"),
]

SEED_WORKSHOPS = [
    ("Python for Physics & Quantum Science",
     "An introductory workshop focusing on utilizing Python libraries to simulate classical physics experiments and basic quantum systems. Ideal for students transitioning into computational science.",
     "Upcoming", "TBA", "Online", "Beginner,Python"),
    ("Classroom Physics to Quantum Tech",
     "A comprehensive seminar bridging the gap between high-school/UG physics curriculum and modern quantum technology applications.",
     "Planning", "--", "Hybrid", "Core Physics"),
    ("Hands-On Physics Experiments Workshop",
     "Perform and analyse classic experiments such as the photoelectric effect, Malus's law and diffraction. Suitable for school and college groups.",
     "Planning", "TBA", "Offline", "Experiments,School & College"),
    ("Quantum Technology Awareness Programme",
     "An introductory session on quantum computing, quantum communication and quantum sensing for students and teachers. No prior background required.",
     "Planning", "TBA", "Hybrid", "Awareness,Quantum"),
]

DEFAULT_SETTINGS = {"whatsapp": "919795925796", "email": "rishibharadwajquantumacademy@gmail.com", "phone": ""}
LEARNING_MODES = ("", "Online", "Offline", "Either")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)
    cur = db.cursor()

    if cur.execute("SELECT COUNT(*) FROM admin").fetchone()[0] == 0:
        username = os.environ.get("RBQA_ADMIN_USER", "admin")
        password = os.environ.get("RBQA_ADMIN_PASS")
        generated = False
        if not password:
            password = "admin123"
            generated = True
        cur.execute("INSERT INTO admin (id, username, password_hash) VALUES (1, ?, ?)",
                    (username, generate_password_hash(password)))
        print(f"\n  Admin account created -> username: {username}  password: {password}")
        if generated:
            print("  (default password - change it from the admin panel after logging in)\n")

    # --- migrate databases created before categories / new form fields existed
    migrated = False
    if "category" not in _columns(cur, "courses"):
        cur.execute("ALTER TABLE courses ADD COLUMN category TEXT NOT NULL DEFAULT 'quantum'")
        cur.execute("UPDATE courses SET category='rf' WHERE title='Intro to RF and Microwave Technologies'")
        migrated = True
    for col in ("class_course", "learning_mode"):
        if col not in _columns(cur, "messages"):
            cur.execute(f"ALTER TABLE messages ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")

    for k, v in DEFAULT_SETTINGS.items():
        cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Seed on a fresh DB; on a migrated DB only add the new rows that are missing
    # (never re-adds things the admin deleted on later restarts).
    fresh_courses = cur.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0
    if fresh_courses or migrated:
        for i, c in enumerate(SEED_COURSES):
            if cur.execute("SELECT 1 FROM courses WHERE title = ?", (c[0],)).fetchone():
                continue
            cur.execute("INSERT INTO courses (title, audience, description, topics, icon, category, sort_order) VALUES (?,?,?,?,?,?,?)",
                        (*c, i))
    fresh_ws = cur.execute("SELECT COUNT(*) FROM workshops").fetchone()[0] == 0
    if fresh_ws or migrated:
        for i, w in enumerate(SEED_WORKSHOPS):
            if cur.execute("SELECT 1 FROM workshops WHERE title = ?", (w[0],)).fetchone():
                continue
            cur.execute("INSERT INTO workshops (title, description, status, date_label, mode, tags, sort_order) VALUES (?,?,?,?,?,?,?)",
                        (*w, i))
    db.commit()
    db.close()


def _columns(cur, table):
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})")}


def get_settings(db):
    s = dict(DEFAULT_SETTINGS)
    s.update({r["key"]: r["value"] for r in db.execute("SELECT key, value FROM settings")})
    return s


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def clean(value, maxlen):
    return str(value or "").strip()[:maxlen]


def bad(msg, code=400):
    return jsonify({"ok": False, "error": msg}), code


def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not session.get("admin"):
            return bad("Authentication required.", 401)
        return fn(*a, **kw)
    return wrapper


def course_row(r):
    return {
        "id": r["id"], "title": r["title"], "audience": r["audience"],
        "description": r["description"],
        "topics": [t for t in r["topics"].split("\n") if t.strip()],
        "topics_text": r["topics"], "icon": r["icon"], "category": r["category"],
        "sort_order": r["sort_order"], "published": bool(r["published"]),
    }


def workshop_row(r):
    return {
        "id": r["id"], "title": r["title"], "description": r["description"],
        "status": r["status"], "date_label": r["date_label"], "mode": r["mode"],
        "tags": [t.strip() for t in r["tags"].split(",") if t.strip()],
        "tags_text": r["tags"], "sort_order": r["sort_order"],
        "published": bool(r["published"]),
    }


# Very small in-memory rate limiter for public form posts (per IP).
_hits = {}


def rate_limited(limit=8, window=600):
    ip = request.remote_addr or "?"
    now = datetime.now().timestamp()
    bucket = [t for t in _hits.get(ip, []) if now - t < window]
    if len(bucket) >= limit:
        _hits[ip] = bucket
        return True
    bucket.append(now)
    _hits[ip] = bucket
    return False


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/admin")
def admin_page():
    return render_template("admin.html")


@app.get("/api/health")
def health():
    return jsonify({"ok": True})


# ---- Legal pages (draft wording - have the academy owner / a lawyer review it)
LEGAL = {
    "privacy": ("Privacy Policy", [
        ("What we collect", "When you use a form on this website we collect the details you enter: your name, email address, phone number, class or course of interest, learning-mode preference and your message or note."),
        ("How we use it", "We use this information only to reply to your enquiry, handle course or workshop registrations, and share details about RBQA programmes you asked about."),
        ("Storage and sharing", "Submissions are stored in the academy's website database and are visible only to authorised RBQA administrators. We do not sell your personal information. We do not share it with third parties except where required by law."),
        ("Your choices", "You can ask us to correct or delete your information at any time by writing to the email address shown in the Contact section."),
        ("Cookies", "The public website does not use advertising or tracking cookies. A session cookie is used only for administrator login."),
        ("Children", "Students under 18 should submit forms with the knowledge of a parent or guardian."),
    ]),
    "terms": ("Terms & Conditions", [
        ("Use of this website", "This website provides information about the programmes of Rishi Bharadwaj Quantum Academy (RBQA). Content is for general educational information and may be updated without notice."),
        ("Registrations and enquiries", "Submitting an enquiry or registration form expresses your interest only. A seat in a course or workshop is confirmed only when RBQA confirms it to you."),
        ("Schedules and fees", "Course content, schedules, modes (online or offline) and fees may change. The details communicated to you at the time of confirmation apply."),
        ("Intellectual property", "Study material, notes and experiment manuals published by RBQA are for the personal learning use of registered students and may not be copied or redistributed without permission."),
        ("Independence", "RBQA is an independent academic initiative. It is not affiliated with, or endorsed by, any institution in which its founder is employed or has studied."),
        ("Contact", "For questions about these terms, use the email address shown in the Contact section."),
    ]),
    "refund": ("Refund & Cancellation Policy", [
        ("Fees", "Fees for each course or workshop are communicated at the time of registration. Online payment is not yet available on this website."),
        ("Cancellation by you", "To cancel a registration, write to RBQA using the email address shown in the Contact section, mentioning the course or workshop and your registered name."),
        ("Refunds", "Whether a refund applies, and for how much, depends on the programme and on how far it has progressed. The refund terms for a programme are shared with you when its fee is communicated."),
        ("Cancellation by RBQA", "If RBQA cancels or reschedules a workshop or batch, you will be informed and offered a reschedule or a refund of the fee paid for that programme."),
    ]),
}


@app.get("/privacy", endpoint="legal_privacy")
@app.get("/terms", endpoint="legal_terms")
@app.get("/refund", endpoint="legal_refund")
def legal_page():
    key = request.path.strip("/")
    title, sections = LEGAL[key]
    return render_template("legal.html", title=title, sections=sections,
                           email=get_settings(get_db())["email"])


@app.get("/robots.txt")
def robots():
    body = f"User-agent: *\nDisallow: /admin\nDisallow: /api/\nSitemap: {request.url_root}sitemap.xml\n"
    return Response(body, mimetype="text/plain")


@app.get("/sitemap.xml")
def sitemap():
    urls = ["", "privacy", "terms", "refund"]
    items = "".join(f"<url><loc>{request.url_root}{u}</loc></url>" for u in urls)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{items}</urlset>'
    return Response(xml, mimetype="application/xml")


@app.get("/api/config")
def public_config():
    s = get_settings(get_db())
    return jsonify({
        "whatsapp": re.sub(r"\D", "", s["whatsapp"]),   # digits only, e.g. 919876543210
        "email": s["email"], "phone": s["phone"],
        "categories": [{"key": k, "label": l, "icon": i} for k, l, i in CATEGORIES],
    })


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------
@app.get("/api/courses")
def public_courses():
    rows = get_db().execute(
        "SELECT * FROM courses WHERE published = 1 ORDER BY sort_order, id").fetchall()
    return jsonify([course_row(r) for r in rows])


@app.get("/api/workshops")
def public_workshops():
    rows = get_db().execute(
        "SELECT * FROM workshops WHERE published = 1 ORDER BY sort_order, id").fetchall()
    return jsonify([workshop_row(r) for r in rows])


@app.post("/api/contact")
def contact():
    if rate_limited():
        return bad("Too many submissions. Please try again later.", 429)
    d = request.get_json(silent=True) or {}
    ok_msg = "Thank you! We have received your message and will get back to you soon."
    if clean(d.get("website"), 200):          # honeypot: real users never fill this
        return jsonify({"ok": True, "message": ok_msg})
    name, email = clean(d.get("name"), 120), clean(d.get("email"), 200)
    phone, interest = clean(d.get("phone"), 30), clean(d.get("interest"), 40)
    class_course = clean(d.get("class_course"), 80)
    learning_mode = clean(d.get("learning_mode"), 20)
    if learning_mode not in LEARNING_MODES:
        learning_mode = ""
    message = clean(d.get("message"), 3000)
    if not name or not message:
        return bad("Name and message are required.")
    if not EMAIL_RE.match(email):
        return bad("Please enter a valid email address.")
    db = get_db()
    db.execute("INSERT INTO messages (name,email,phone,interest,class_course,learning_mode,message,created_at) VALUES (?,?,?,?,?,?,?,?)",
               (name, email, phone, interest, class_course, learning_mode, message, now_iso()))
    db.commit()
    return jsonify({"ok": True, "message": ok_msg})


@app.post("/api/workshops/<int:wid>/register")
def register(wid):
    if rate_limited():
        return bad("Too many submissions. Please try again later.", 429)
    db = get_db()
    ws = db.execute("SELECT * FROM workshops WHERE id = ? AND published = 1", (wid,)).fetchone()
    if not ws:
        return bad("Workshop not found.", 404)
    if ws["status"] == "Completed":
        return bad("Registration for this workshop is closed.")
    d = request.get_json(silent=True) or {}
    if clean(d.get("website"), 200):          # honeypot
        return jsonify({"ok": True, "message": f"You're on the list for \"{ws['title']}\". We'll email you the details."})
    name, email = clean(d.get("name"), 120), clean(d.get("email"), 200)
    phone, note = clean(d.get("phone"), 30), clean(d.get("note"), 1000)
    if not name:
        return bad("Name is required.")
    if not EMAIL_RE.match(email):
        return bad("Please enter a valid email address.")
    dup = db.execute("SELECT 1 FROM registrations WHERE workshop_id=? AND lower(email)=lower(?)",
                     (wid, email)).fetchone()
    if dup:
        return bad("This email is already registered for this workshop.", 409)
    db.execute("INSERT INTO registrations (workshop_id,name,email,phone,note,created_at) VALUES (?,?,?,?,?,?)",
               (wid, name, email, phone, note, now_iso()))
    db.commit()
    return jsonify({"ok": True, "message": f"You're on the list for \"{ws['title']}\". We'll email you the details."})


# --------------------------------------------------------------------------
# Admin API
# --------------------------------------------------------------------------
@app.post("/api/admin/login")
def admin_login():
    if rate_limited(limit=10, window=300):
        return bad("Too many attempts. Wait a few minutes.", 429)
    d = request.get_json(silent=True) or {}
    row = get_db().execute("SELECT * FROM admin WHERE id = 1").fetchone()
    if (row and d.get("username") == row["username"]
            and check_password_hash(row["password_hash"], d.get("password") or "")):
        session.clear()
        session["admin"] = True
        return jsonify({"ok": True, "username": row["username"]})
    return bad("Invalid username or password.", 401)


@app.post("/api/admin/logout")
def admin_logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/admin/me")
def admin_me():
    if not session.get("admin"):
        return jsonify({"ok": False}), 401
    row = get_db().execute("SELECT username FROM admin WHERE id = 1").fetchone()
    return jsonify({"ok": True, "username": row["username"]})


@app.post("/api/admin/password")
@admin_required
def admin_password():
    d = request.get_json(silent=True) or {}
    db = get_db()
    row = db.execute("SELECT * FROM admin WHERE id = 1").fetchone()
    if not check_password_hash(row["password_hash"], d.get("current") or ""):
        return bad("Current password is incorrect.", 403)
    new = d.get("new") or ""
    if len(new) < 8:
        return bad("New password must be at least 8 characters.")
    db.execute("UPDATE admin SET password_hash = ? WHERE id = 1", (generate_password_hash(new),))
    db.commit()
    return jsonify({"ok": True})


@app.get("/api/admin/stats")
@admin_required
def admin_stats():
    db = get_db()
    q = lambda sql: db.execute(sql).fetchone()[0]
    return jsonify({
        "messages": q("SELECT COUNT(*) FROM messages"),
        "unread": q("SELECT COUNT(*) FROM messages WHERE is_read = 0"),
        "registrations": q("SELECT COUNT(*) FROM registrations"),
        "courses": q("SELECT COUNT(*) FROM courses"),
        "workshops": q("SELECT COUNT(*) FROM workshops"),
    })


# ---- messages
@app.get("/api/admin/messages")
@admin_required
def admin_messages():
    rows = get_db().execute("SELECT * FROM messages ORDER BY id DESC").fetchall()
    return jsonify([dict(r) | {"is_read": bool(r["is_read"])} for r in rows])


@app.patch("/api/admin/messages/<int:mid>")
@admin_required
def admin_message_update(mid):
    d = request.get_json(silent=True) or {}
    db = get_db()
    db.execute("UPDATE messages SET is_read = ? WHERE id = ?", (1 if d.get("is_read") else 0, mid))
    db.commit()
    return jsonify({"ok": True})


@app.delete("/api/admin/messages/<int:mid>")
@admin_required
def admin_message_delete(mid):
    db = get_db()
    db.execute("DELETE FROM messages WHERE id = ?", (mid,))
    db.commit()
    return jsonify({"ok": True})


# ---- registrations
@app.get("/api/admin/registrations")
@admin_required
def admin_registrations():
    rows = get_db().execute("""
        SELECT r.*, w.title AS workshop_title FROM registrations r
        JOIN workshops w ON w.id = r.workshop_id ORDER BY r.id DESC""").fetchall()
    return jsonify([dict(r) for r in rows])


@app.delete("/api/admin/registrations/<int:rid>")
@admin_required
def admin_registration_delete(rid):
    db = get_db()
    db.execute("DELETE FROM registrations WHERE id = ?", (rid,))
    db.commit()
    return jsonify({"ok": True})


def csv_response(filename, header, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    for r in rows:
        # neutralise spreadsheet formula injection
        w.writerow([("'" + v) if isinstance(v, str) and v and v[0] in "=+-@" else v for v in r])
    return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.get("/api/admin/export/<kind>")
@admin_required
def admin_export(kind):
    db = get_db()
    if kind == "messages":
        rows = db.execute("SELECT created_at,name,email,phone,interest,class_course,learning_mode,message FROM messages ORDER BY id DESC").fetchall()
        return csv_response("messages.csv", ["Received (UTC)", "Name", "Email", "Phone", "Interest", "Class / Course", "Mode", "Message"], rows)
    if kind == "registrations":
        rows = db.execute("""SELECT r.created_at, w.title, r.name, r.email, r.phone, r.note
                             FROM registrations r JOIN workshops w ON w.id = r.workshop_id
                             ORDER BY r.id DESC""").fetchall()
        return csv_response("registrations.csv", ["Registered (UTC)", "Workshop", "Name", "Email", "Phone", "Note"], rows)
    return bad("Unknown export.", 404)


# ---- contact settings (WhatsApp number, email, phone)
@app.get("/api/admin/settings")
@admin_required
def admin_settings():
    return jsonify(get_settings(get_db()))


@app.put("/api/admin/settings")
@admin_required
def admin_settings_update():
    d = request.get_json(silent=True) or {}
    whatsapp = clean(d.get("whatsapp"), 20)
    email, phone = clean(d.get("email"), 200), clean(d.get("phone"), 30)
    if whatsapp and not re.fullmatch(r"\+?[\d\s-]{10,16}", whatsapp):
        return bad("WhatsApp number must be 10-15 digits including country code, e.g. 919876543210.")
    if email and not EMAIL_RE.match(email):
        return bad("Please enter a valid email address.")
    db = get_db()
    for k, v in (("whatsapp", whatsapp), ("email", email), ("phone", phone)):
        db.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (k, v))
    db.commit()
    return jsonify({"ok": True})


# ---- courses
def course_payload(d):
    title = clean(d.get("title"), 200)
    if not title:
        return None, "Title is required."
    try:
        order = int(d.get("sort_order") or 0)
    except (TypeError, ValueError):
        order = 0
    category = clean(d.get("category"), 20)
    if category not in CATEGORY_KEYS:
        category = "quantum"
    return (title, clean(d.get("audience"), 200), clean(d.get("description"), 2000),
            clean(d.get("topics_text"), 2000), clean(d.get("icon"), 40) or "fa-atom",
            category, order, 1 if d.get("published", True) else 0), None


@app.get("/api/admin/courses")
@admin_required
def admin_courses():
    rows = get_db().execute("SELECT * FROM courses ORDER BY sort_order, id").fetchall()
    return jsonify([course_row(r) for r in rows])


@app.post("/api/admin/courses")
@admin_required
def admin_course_create():
    p, err = course_payload(request.get_json(silent=True) or {})
    if err:
        return bad(err)
    db = get_db()
    cur = db.execute("INSERT INTO courses (title,audience,description,topics,icon,category,sort_order,published) VALUES (?,?,?,?,?,?,?,?)", p)
    db.commit()
    return jsonify({"ok": True, "id": cur.lastrowid}), 201


@app.put("/api/admin/courses/<int:cid>")
@admin_required
def admin_course_update(cid):
    p, err = course_payload(request.get_json(silent=True) or {})
    if err:
        return bad(err)
    db = get_db()
    cur = db.execute("UPDATE courses SET title=?,audience=?,description=?,topics=?,icon=?,category=?,sort_order=?,published=? WHERE id=?", (*p, cid))
    db.commit()
    return jsonify({"ok": True}) if cur.rowcount else bad("Not found.", 404)


@app.delete("/api/admin/courses/<int:cid>")
@admin_required
def admin_course_delete(cid):
    db = get_db()
    db.execute("DELETE FROM courses WHERE id = ?", (cid,))
    db.commit()
    return jsonify({"ok": True})


# ---- workshops
def workshop_payload(d):
    title = clean(d.get("title"), 200)
    if not title:
        return None, "Title is required."
    status = clean(d.get("status"), 20)
    if status not in ("Upcoming", "Planning", "Completed"):
        return None, "Status must be Upcoming, Planning or Completed."
    try:
        order = int(d.get("sort_order") or 0)
    except (TypeError, ValueError):
        order = 0
    return (title, clean(d.get("description"), 2000), status,
            clean(d.get("date_label"), 40) or "TBA", clean(d.get("mode"), 20) or "Online",
            clean(d.get("tags_text"), 200), order, 1 if d.get("published", True) else 0), None


@app.get("/api/admin/workshops")
@admin_required
def admin_workshops():
    rows = get_db().execute("SELECT * FROM workshops ORDER BY sort_order, id").fetchall()
    return jsonify([workshop_row(r) for r in rows])


@app.post("/api/admin/workshops")
@admin_required
def admin_workshop_create():
    p, err = workshop_payload(request.get_json(silent=True) or {})
    if err:
        return bad(err)
    db = get_db()
    cur = db.execute("INSERT INTO workshops (title,description,status,date_label,mode,tags,sort_order,published) VALUES (?,?,?,?,?,?,?,?)", p)
    db.commit()
    return jsonify({"ok": True, "id": cur.lastrowid}), 201


@app.put("/api/admin/workshops/<int:wid>")
@admin_required
def admin_workshop_update(wid):
    p, err = workshop_payload(request.get_json(silent=True) or {})
    if err:
        return bad(err)
    db = get_db()
    cur = db.execute("UPDATE workshops SET title=?,description=?,status=?,date_label=?,mode=?,tags=?,sort_order=?,published=? WHERE id=?", (*p, wid))
    db.commit()
    return jsonify({"ok": True}) if cur.rowcount else bad("Not found.", 404)


@app.delete("/api/admin/workshops/<int:wid>")
@admin_required
def admin_workshop_delete(wid):
    db = get_db()
    db.execute("DELETE FROM workshops WHERE id = ?", (wid,))
    db.commit()
    return jsonify({"ok": True})


# --------------------------------------------------------------------------
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"  Site:  http://localhost:{port}")
    print(f"  Admin: http://localhost:{port}/admin")
    app.run(host="127.0.0.1", port=port, debug=False)
