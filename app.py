from __future__ import annotations
import os
import html
import sqlite3
import secrets
import hashlib
from pathlib import Path
from functools import wraps
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import json
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template_string,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", "/var/data"))
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _data_dir_ok = os.access(DATA_DIR, os.W_OK)
except OSError:
    _data_dir_ok = False
if not _data_dir_ok:
    DATA_DIR = Path(os.environ.get("FALLBACK_DATA_DIR", BASE_DIR / "data"))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _data_dir_ok = os.access(DATA_DIR, os.W_OK)
if not _data_dir_ok:
    raise RuntimeError(
        "Application data directory is not writable. Set DATA_DIR to a writable "
        "directory (on Render, /var/data is recommended)."
    )
DB_PATH = DATA_DIR / "mctc_court.db"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app = Flask(__name__, static_folder="static")
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key-in-render",
)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
if os.environ.get("RENDER"):
    app.config["SESSION_COOKIE_SECURE"] = True
COURT_NAME = "Municipal Circuit Trial Court of Silang-Amadeo, Cavite"
COURT_SHORT_NAME = "MCTC Silang-Amadeo"
COURT_ADDRESS = "PNP Bldg, Plaza Libertad, Poblacion 2, Silang, Cavite"
COURT_PHONE = "09284621305"
COURT_EMAIL = "mctc2sad000@judiciary.gov.ph"
COURT_OFFICE_HOURS = "8:00 AM - 5:00 PM"
MCTC_LOGO = "image0.png"
SUPREME_LOGO = "1280px-Seal_of_the_Supreme_Court_(Philippines).png"
MAP_QUERY = quote_plus(f"{COURT_NAME}, {COURT_ADDRESS}")
GOOGLE_MAPS_URL = (
    "https://www.google.com/maps/search/?api=1&query=" + MAP_QUERY
)
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
ALLOWED_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg", "webp", "gif",
    "doc", "docx", "xls", "xlsx", "txt",
}
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
T = {
    "en": {
        "home": "Home",
        "about": "About Us",
        "search": "Search Case",
        "calendar": "Tuesday Calendar",
        "requirements": "Requirements",
        "news": "News and Announcements",
        "contact": "Contact Us",
        "language": "Language",
        "light": "Light",
        "dark": "Dark",
        "staff_login": "Staff Login",
        "staff_dashboard": "Staff Dashboard",
        "cases": "Cases",
        "notices": "Notices",
        "laws": "Laws, Decisions and Rules",
        "staff_accounts": "Staff Accounts",
        "logout": "Log Out",
        "save": "Save",
        "add": "Add",
        "edit": "Edit",
        "delete": "Delete",
        "view": "View",
        "open": "Open",
        "upload": "Upload",
        "case_number": "Case Number",
        "plaintiff": "Plaintiff Last Name / Corporation Name",
        "defendant": "Defendant / Party",
        "parties": "Parties",
        "case_type": "Case Type",
        "status": "Status",
        "description": "Public Description",
        "hearing": "Hearing",
        "hearing_date": "Hearing Date",
        "hearing_time": "Hearing Time",
        "hearing_nature": "Nature of Hearing",
        "hearing_status": "Hearing Status",
        "remarks": "Remarks",
        "courtroom": "Courtroom",
        "required_search": "Both the complete case number and plaintiff last name / corporation name are required.",
        "how_search": "How to Search",
        "step1": "Enter the complete case number.",
        "step2": "Enter the plaintiff's last name or corporation name.",
        "step3": "Both fields are required.",
        "step4": "Select Search Case.",
        "no_results": "No matching public case was found.",
        "invalid_login": "Invalid username or password.",
        "login_required": "Please log in as authorized staff.",
        "forgot_password": "Forgot Password?",
        "forgot_password_title": "Reset Staff Password",
        "forgot_password_help": "Enter your staff username or registered email address. If the account exists, a reset link will be sent to its registered email.",
        "welcome": "Welcome, Court Staff!",
        "signed_in": "Signed in as",
        "office_hours": "Office Hours",
        "open_maps": "Open Google Maps",
        "not_uploaded": "Not yet uploaded",
        "copyright": "© 2026 Municipal Circuit Trial Court of Silang-Amadeo, Cavite. All rights reserved.",
    },
    "fil": {
        "home": "Home",
        "about": "Tungkol sa Amin",
        "search": "Maghanap ng Kaso",
        "calendar": "Kalendaryo ng Martes",
        "requirements": "Mga Kinakailangan",
        "news": "Balita at mga Anunsyo",
        "contact": "Makipag-ugnayan",
        "language": "Wika",
        "light": "Liwanag",
        "dark": "Madilim",
        "staff_login": "Staff Login",
        "staff_dashboard": "Dashboard ng Staff",
        "cases": "Mga Kaso",
        "notices": "Mga Abiso",
        "laws": "Mga Batas, Desisyon at Alituntunin",
        "staff_accounts": "Mga Account ng Staff",
        "logout": "Mag-Logout",
        "save": "I-save",
        "add": "Magdagdag",
        "edit": "I-edit",
        "delete": "Burahin",
        "view": "Tingnan",
        "open": "Buksan",
        "upload": "Mag-upload",
        "case_number": "Numero ng Kaso",
        "plaintiff": "Apelyido ng Plaintiff / Pangalan ng Corporation",
        "defendant": "Defendant / Partido",
        "parties": "Mga Partido",
        "case_type": "Uri ng Kaso",
        "status": "Katayuan",
        "description": "Pampublikong Deskripsyon",
        "hearing": "Pagdinig",
        "hearing_date": "Petsa ng Pagdinig",
        "hearing_time": "Oras ng Pagdinig",
        "hearing_nature": "Uri ng Pagdinig",
        "hearing_status": "Katayuan ng Pagdinig",
        "remarks": "Mga Tala",
        "courtroom": "Silid ng Hukuman",
        "required_search": "Kinakailangan ang parehong kumpletong case number at apelyido ng plaintiff / pangalan ng corporation.",
        "how_search": "Paano Maghanap",
        "step1": "Ilagay ang buong case number.",
        "step2": "Ilagay ang apelyido ng plaintiff o pangalan ng corporation.",
        "step3": "Kinakailangan ang parehong field.",
        "step4": "Piliin ang Maghanap ng Kaso.",
        "no_results": "Walang nakitang pampublikong kaso.",
        "invalid_login": "Mali ang username o password.",
        "login_required": "Mag-login bilang awtorisadong staff.",
        "forgot_password": "Nakalimutan ang Password?",
        "forgot_password_title": "I-reset ang Password ng Staff",
        "forgot_password_help": "Ilagay ang username o nakarehistrong email. Kung umiiral ang account, magpapadala ng reset link sa rehistradong email.",
        "welcome": "Maligayang Pagdating, Kawani ng Hukuman!",
        "signed_in": "Naka-sign in bilang",
        "office_hours": "Oras ng Opisina",
        "open_maps": "Buksan ang Google Maps",
        "not_uploaded": "Hindi pa naiu-upload",
        "copyright": "© 2026 Municipal Circuit Trial Court of Silang-Amadeo, Cavite. Lahat ng karapatan ay nakalaan.",
    },
}
def tr(key):
    language = session.get("language", "en")
    if language not in T:
        language = "en"
    return T[language].get(key, T["en"].get(key, key))
def esc(value):
    return html.escape(str(value or ""), quote=True)
def now():
    return datetime.utcnow().isoformat(timespec="seconds")
def current_theme():
    theme = session.get("theme", "light")
    return theme if theme in {"light", "dark"} else "light"
def db():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = FULL")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection
def durable_commit(connection):
    """Commit changes immediately so submitted staff data is persisted server-side."""
    connection.commit()
    try:
        connection.execute("PRAGMA wal_checkpoint(PASSIVE)")
    except sqlite3.Error:
        pass
def initialize_database():
    connection = db()
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'staff',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_number TEXT UNIQUE NOT NULL,
            plaintiff_name TEXT NOT NULL,
            defendant_name TEXT NOT NULL DEFAULT '',
            parties TEXT NOT NULL DEFAULT '',
            case_type TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Active',
            public_description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS hearings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            hearing_date TEXT NOT NULL,
            hearing_time TEXT NOT NULL DEFAULT '',
            hearing_nature TEXT NOT NULL DEFAULT 'Initial Hearing',
            hearing_status TEXT NOT NULL DEFAULT 'Scheduled',
            remarks TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title_en TEXT NOT NULL,
            title_fil TEXT NOT NULL,
            body_en TEXT NOT NULL,
            body_fil TEXT NOT NULL,
            attachment TEXT,
            original_filename TEXT,
            published INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS legal_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            file_name TEXT,
            original_filename TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT UNIQUE NOT NULL,
            title_en TEXT NOT NULL,
            title_fil TEXT NOT NULL,
            description_en TEXT NOT NULL DEFAULT 'Not yet uploaded',
            description_fil TEXT NOT NULL DEFAULT 'Hindi pa naiu-upload',
            file_name TEXT,
            original_filename TEXT,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            file_name TEXT,
            original_filename TEXT,
            file_type TEXT,
            updated_at TEXT,
            uploaded_by TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(staff_id) REFERENCES staff(id) ON DELETE CASCADE
        );
        """
    )
    connection.execute(
        "UPDATE cases SET status = 'Active' WHERE status = 'Pending'"
    )
    requirement_seeds = [
        (
            "bond",
            "Requirements for Posting Bail Bond",
            "Mga Kinakailangan para sa Posting Bail Bond",
        ),
        (
            "clearance",
            "Requirements for Clearance",
            "Mga Kinakailangan para sa Clearance",
        ),
    ]
    for category, title_en, title_fil in requirement_seeds:
        exists = connection.execute(
            "SELECT id FROM requirements WHERE category = ?",
            (category,),
        ).fetchone()
        if exists is None:
            connection.execute(
                """
                INSERT INTO requirements
                (category, title_en, title_fil, description_en,
                 description_fil, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    category,
                    title_en,
                    title_fil,
                    "Not yet uploaded",
                    "Hindi pa naiu-upload",
                    now(),
                ),
            )
    admin = connection.execute(
        "SELECT * FROM staff WHERE lower(username) = 'admin' LIMIT 1"
    ).fetchone()
    if admin is None:
        connection.execute(
            """
            INSERT INTO staff
            (username, email, password_hash, role, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "Admin",
                "josehr.tan@gmail.com",
                generate_password_hash("ChangeMe123!"),
                "admin",
                1,
                now(),
            ),
        )
    else:
        connection.execute(
            "UPDATE staff SET username = ?, email = ?, role = ?, active = 1 WHERE id = ?",
            ("Admin", "josehr.tan@gmail.com", "admin", admin["id"]),
        )
    superadmin = connection.execute(
        "SELECT * FROM staff WHERE username = ? LIMIT 1",
        ("26-0054",),
    ).fetchone()
    if superadmin is None:
        connection.execute(
            """
            INSERT INTO staff
            (username, email, password_hash, role, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "26-0054",
                "26-0054@staff.local",
                generate_password_hash("ThisWasHugo"),
                "superadmin",
                1,
                now(),
            ),
        )
    else:
        connection.execute(
            "UPDATE staff SET email = ?, role = ?, active = 1 WHERE id = ?",
            ("26-0054@staff.local", "superadmin", superadmin["id"]),
        )
    durable_commit(connection)
    connection.close()
initialize_database()
def hash_reset_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
def build_public_url(path):
    base = PUBLIC_BASE_URL or request.url_root.rstrip("/")
    return base + path
def send_gmail_reset_email(recipient, reset_url, username="Court Staff"):
    if not GOOGLE_APPS_SCRIPT_URL or not GOOGLE_APPS_SCRIPT_SECRET:
        return False, (
            "Gmail reset email is not configured. Set GOOGLE_APPS_SCRIPT_URL and "
            "GOOGLE_APPS_SCRIPT_SECRET in Render Environment Variables."
        )
    payload = {
        "secret": GOOGLE_APPS_SCRIPT_SECRET,
        "to": recipient,
        "username": username,
        "reset_url": reset_url,
        "court_name": COURT_NAME,
        "expires_minutes": 30,
    }
    try:
        encoded = json.dumps(payload).encode("utf-8")
        req = Request(
            GOOGLE_APPS_SCRIPT_URL,
            data=encoded,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "MCTC-Silang-Amadeo-Portal/1.0",
            },
            method="POST",
        )
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8", "replace")
        result = json.loads(raw)
        if isinstance(result, dict) and result.get("ok") is True:
            return True, "Password reset email sent."
        if isinstance(result, dict):
            return False, str(result.get("error") or "Gmail rejected the reset email request.")
        return False, "Gmail returned an invalid response."
    except HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", "replace")
        except Exception:
            detail = str(exc)
        return False, f"Gmail bridge HTTP error {exc.code}: {detail[:500]}"
    except URLError as exc:
        return False, f"Could not reach the Gmail bridge: {exc.reason}"
    except TimeoutError:
        return False, "The Gmail bridge timed out. Please try again."
    except json.JSONDecodeError:
        return False, "The Gmail bridge returned an invalid response."
    except Exception as exc:
        return False, f"Gmail bridge error: {type(exc).__name__}: {exc}"
BOND_REQUIREMENTS = [
    "Personal Data (form from court)",
    "Pictures 2x2 with name tag, signature, case, case number and date",
    "4 pcs. Front",
    "4 pcs. Left side",
    "4 pcs. Right side",
    "Barangay Clearance attesting the Real Name of the accused and bonafide resident",
    "Certification (Permanent Residency) attesting how many years of stay",
    "House Sketch - certified, signed and sealed by Barangay Captain with date",
    "Certificate of Detention (if detained or arrested)",
    "Affidavit of Voluntary Surrender (if voluntary or not detained)",
    "Finger Print (piano)",
    "Specimen Signature (at least 5 signature)",
    "Affidavit of Undertaking",
    "Valid Government-Issued I.D. (original AND xerox copy back-to-back)",
    "Original Copy of PSA Birth Certificate (latest copy with attached receipt)",
    "If married, female - original copy of PSA Marriage Certificate with attached receipt",
    "For inquiries, kindly seek assistance from court staff.",
]
def audit(action, target=""):
    try:
        connection = db()
        connection.execute(
            """
            INSERT INTO audit_logs (username, action, target, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                session.get("staff_username", "system"),
                action,
                str(target),
                now(),
            ),
        )
        connection.commit()
        connection.close()
    except sqlite3.Error:
        pass
def staff_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("staff_logged_in", False):
            flash(tr("login_required"), "warning")
            return redirect(url_for("staff_login"))
        return function(*args, **kwargs)
    return wrapper
def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("staff_logged_in", False):
            return redirect(url_for("staff_login"))
        if session.get("staff_role") not in {"admin", "superadmin"}:
            abort(403)
        return function(*args, **kwargs)
    return wrapper

def superadmin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("staff_logged_in", False):
            return redirect(url_for("staff_login"))
        if session.get("staff_role") != "superadmin":
            abort(403)
        return function(*args, **kwargs)
    return wrapper
def save_upload(file):
    if file is None or not file.filename:
        return None, None, None
    original = secure_filename(file.filename)
    if not original:
        return None, None, None
    extension = Path(original).suffix.lower().lstrip(".")
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("That file type is not allowed.")
    generated = f"{secrets.token_hex(16)}_{original}"
    file.save(UPLOAD_DIR / generated)
    return generated, original, extension
def delete_uploaded_file(filename):
    if not filename:
        return
    path = UPLOAD_DIR / filename
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass
STYLE = r"""
:root {
    --bg: #faf8fd;
    --surface: #ffffff;
    --surface-soft: #f2eafa;
    --text: #24152d;
    --muted: #716178;
    --border: #ded0e7;
    --purple: #6d28d9;
    --purple-dark: #3b0764;
    --purple-light: #8b5cf6;
    --danger: #a61d3f;
    --success: #18723c;
    --warning: #a16207;
    --shadow: rgba(55, 18, 72, .10);
}
body.dark {
    --bg: #110d15;
    --surface: #211825;
    --surface-soft: #30203a;
    --text: #fff8ff;
    --muted: #d2c2db;
    --border: #513d5a;
    --shadow: rgba(0,0,0,.30);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
    margin: 0;
    min-height: 100vh;
    background: var(--bg);
    color: var(--text);
    font-family: Arial, Helvetica, sans-serif;
    line-height: 1.6;
}
a { color: var(--purple); text-decoration: none; }
body.dark a { color: #cfb8ff; }
a:hover { text-decoration: underline; }
.site-header {
    position: sticky;
    top: 0;
    z-index: 1000;
    background: linear-gradient(135deg, var(--purple-dark), var(--purple), var(--purple-light));
    color: white;
    box-shadow: 0 7px 25px rgba(30, 3, 48, .32);
}
.header-top {
    min-height: 76px;
    display: flex;
    justify-content: center;
    align-items: center;
    text-align: center;
    padding: 12px 18px 5px;
}
.header-title-wrap {
    text-align: center;
}
.header-title {
    margin: 0;
    font-size: 23px;
    font-weight: 900;
    line-height: 1.15;
}
.header-subtitle {
    margin: 4px 0 0;
    font-size: 14px;
    font-weight: 700;
    opacity: .9;
}
.header-nav {
    width: 100%;
    min-height: 90px;
    padding: 8px 18px 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    align-content: center;
    gap: 6px;
    flex-wrap: wrap;
    margin: 0 auto;
    box-sizing: border-box;
}
.header-nav a,
.header-nav button,
.header-nav .nav-form {
    min-height: 42px;
}
.header-nav a,
.header-nav button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 8px 10px;
    border: 0;
    border-radius: 10px;
    background: transparent;
    color: white;
    font-size: 12px;
    font-weight: 900;
    white-space: nowrap;
    cursor: pointer;
}
.header-nav a:hover,
.header-nav button:hover {
    background: rgba(255,255,255,.14);
    text-decoration: none;
}
.nav-logo {
    width: 92px;
    height: 92px;
    padding: 3px;
    object-fit: contain;
    background: white;
    border-radius: 50%;
    box-shadow: 0 4px 14px rgba(0,0,0,.25);
}
.container {
    width: 94%;
    max-width: 1180px;
    margin: 0 auto;
    padding: 28px 0 72px;
}
.center { text-align: center; }
.staff-interface .card h1,
.staff-interface .card h2,
.staff-interface .card h3,
.staff-interface .hero,
.staff-interface .stat {
    text-align: center;
}
.staff-interface .actions {
    justify-content: center;
}
.staff-interface .grid {
    align-items: stretch;
}
.hero {
    margin: 12px 0 24px;
    padding: 45px 22px;
    border-radius: 26px;
    background: linear-gradient(135deg, var(--purple-dark), var(--purple), var(--purple-light));
    color: white;
    text-align: center;
}
.hero h1 {
    max-width: 950px;
    margin: 14px auto;
    font-size: clamp(32px, 5vw, 58px);
    line-height: 1.04;
}
.hero p { max-width: 850px; margin: 0 auto; }
.hero-logo {
    width: 150px;
    height: 150px;
    object-fit: contain;
    border-radius: 50%;
    padding: 5px;
    background: white;
}
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(245px, 1fr));
    gap: 16px;
}
.card {
    margin: 16px 0;
    padding: 22px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    box-shadow: 0 8px 24px var(--shadow);
}
.card.centered { text-align: center; }
/* Homepage feature cards: keep every purple action button on the same baseline. */
.home-feature-grid {
    align-items: stretch;
    gap: 12px;
    margin-bottom: 12px;
}
/* Remove the extra vertical margin from cards inside the homepage grid.
   This prevents the default card margin + grid gap from creating a large
   space between the feature-card row and the News section. */
.home-feature-grid .home-feature-card {
    margin: 0;
}
.home-news-section {
    margin-top: 0;
}
.home-feature-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    height: 100%;
    box-sizing: border-box;
}
.home-feature-card h2 {
    min-height: 76px;
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 0 12px;
    line-height: 1.35;
}
.home-feature-card p {
    min-height: 84px;
    width: 100%;
    margin: 0 0 18px;
    display: flex;
    align-items: flex-start;
    justify-content: center;
}
.home-feature-card .button {
    margin-top: auto;
}
.actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    align-items: center;
    gap: 9px;
    margin-top: 15px;
}
button,
.button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    padding: 10px 15px;
    border: 0;
    border-radius: 10px;
    background: var(--purple);
    color: white;
    font-weight: 900;
    cursor: pointer;
    text-decoration: none;
}
button:hover,
.button:hover {
    background: var(--purple-dark);
    color: white;
    text-decoration: none;
}
.secondary {
    background: var(--surface-soft);
    color: var(--text);
    border: 1px solid var(--border);
}
.danger { background: var(--danger); }
.success { background: var(--success); }
.notice {
    margin: 13px 0;
    padding: 14px 16px;
    border-left: 5px solid var(--purple);
    border-radius: 10px;
    background: var(--surface-soft);
}
.notice.warning { border-left-color: var(--warning); }
.notice.success { border-left-color: var(--success); }
.notice.danger { border-left-color: var(--danger); }
.status {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 4px 10px;
    border-radius: 999px;
    background: var(--surface-soft);
    color: var(--purple);
    font-size: 12px;
    font-weight: 900;
}
label {
    display: block;
    margin: 10px 0 5px;
    font-weight: 900;
}
input,
textarea,
select {
    width: 100%;
    padding: 12px;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--surface);
    color: var(--text);
    font: inherit;
}
textarea { min-height: 110px; resize: vertical; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th, td {
    padding: 10px;
    text-align: center;
    vertical-align: top;
    border-bottom: 1px solid var(--border);
}
th { background: var(--surface-soft); }
.requirement-list { text-align: left; }
.requirement-list li { margin: 7px 0; }
.schedule-image {
    display: block;
    max-width: 100%;
    max-height: 850px;
    height: auto;
    margin: 18px auto;
    border-radius: 14px;
    box-shadow: 0 8px 22px var(--shadow);
}
.schedule-pdf {
    display: block;
    width: 100%;
    height: 850px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: var(--surface);
}
.stat {
    text-align: center;
}
.stat-number {
    display: block;
    font-size: 42px;
    font-weight: 900;
    color: var(--purple);
}
.small { color: var(--muted); font-size: 13px; }
.empty { text-align: center; padding: 40px; color: var(--muted); }
footer {
    text-align: center;
    background: var(--surface);
    border-top: 1px solid var(--border);
    color: var(--muted);
    padding: 30px 15px;
}
footer p { margin: 8px 0; }
.staff-interface .header-nav {
    justify-content: center;
    text-align: center;
}
.staff-interface .header-nav .nav-form {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin: 0;
}
.staff-interface .header-nav .nav-form button {
    margin: 0;
}
@media (max-width: 1100px) {
    .header-nav {
        gap: 4px;
        padding-left: 10px;
        padding-right: 10px;
    }
    .header-nav a,
    .header-nav button {
        font-size: 11px;
        padding: 7px 8px;
    }
    .nav-logo {
        width: 78px;
        height: 78px;
    }
}
@media (max-width: 850px) {
    .header-title { font-size: 18px; }
    .header-subtitle { font-size: 12px; }
    .header-nav { gap: 3px; }
    .header-nav a,
    .header-nav button { font-size: 11px; padding: 8px; }
    .nav-logo { width: 68px; height: 68px; }
}
@media (max-width: 600px) {
    .header-nav { flex-direction: row; }
    .hero { padding: 36px 16px; }
    .hero h1 { font-size: 34px; }
    .two { grid-template-columns: 1fr; }
}
"""
def render_page(title, body, staff_page=False):
    theme = current_theme()
    other_theme = "dark" if theme == "light" else "light"
    other_language = "fil" if lang_value() == "en" else "en"
    language_label = "FIL" if lang_value() == "en" else "EN"
    theme_label = "🌙" if theme == "light" else "☀️"
    nav = []
    if staff_page or session.get("staff_logged_in", False):
        nav.append(
            f"<img class='nav-logo' src='{url_for('static', filename=MCTC_LOGO)}' "
            f"alt='MCTC Silang-Amadeo logo'>"
        )
        nav.append(
            f"<a href='{url_for('staff_dashboard')}'>{tr('staff_dashboard')}</a>"
        )
        nav.append(
            f"<a href='{url_for('staff_cases')}'>{tr('cases')}</a>"
        )
        nav.append(
            f"<a href='{url_for('staff_calendar')}'>{tr('calendar')}</a>"
        )
        nav.append(
            f"<a href='{url_for('staff_requirements')}'>{tr('requirements')}</a>"
        )
        nav.append(
            f"<a href='{url_for('staff_notices')}'>{tr('notices')}</a>"
        )
        nav.append(
            f"<a href='{url_for('staff_laws')}'>{tr('laws')}</a>"
        )
        if session.get("staff_role") in {"admin", "superadmin"}:
            nav.append(
                f"<a href='{url_for('staff_accounts')}'>{tr('staff_accounts')}</a>"
            )
        if session.get("staff_role") == "superadmin":
            nav.append(
                f"<a href='{url_for('superadmin_dashboard')}'>🛡️ Super Admin</a>"
            )
        nav.append(
            f"<a href='{url_for('change_password')}'>🔑 Change Password</a>"
        )
        nav.append(
            f"<a href='{url_for('change_language', language=other_language)}'>{language_label}</a>"
        )
        nav.append(
            f"<a href='{url_for('change_theme', theme=other_theme)}'>{theme_label}</a>"
        )
        nav.append(
            f"<form class='nav-form' method='post' action='{url_for('logout')}'>"
            f"<button type='submit'>{tr('logout')}</button></form>"
        )
        nav.append(
            f"<img class='nav-logo' src='{url_for('static', filename=SUPREME_LOGO)}' "
            f"alt='Supreme Court of the Philippines seal'>"
        )
    else:
        nav.append(
            f"<img class='nav-logo' src='{url_for('static', filename=MCTC_LOGO)}' "
            f"alt='MCTC Silang-Amadeo logo'>"
        )
        nav.append(f"<a href='{url_for('home')}'>{tr('home')}</a>")
        nav.append(f"<a href='{url_for('about')}'>{tr('about')}</a>")
        nav.append(f"<a href='{url_for('search_cases')}'>{tr('search')}</a>")
        nav.append(f"<a href='{url_for('public_calendar')}'>{tr('calendar')}</a>")
        nav.append(f"<a href='{url_for('requirements')}'>{tr('requirements')}</a>")
        nav.append(f"<a href='{url_for('news')}'>{tr('news')}</a>")
        nav.append(f"<a href='{url_for('contact')}'>{tr('contact')}</a>")
        nav.append(
            f"<a href='{url_for('change_language', language=other_language)}'>{language_label}</a>"
        )
        nav.append(
            f"<a href='{url_for('change_theme', theme=other_theme)}'>{theme_label}</a>"
        )
        nav.append(
            f"<a href='{url_for('staff_login')}'>{tr('staff_login')}</a>"
        )
        nav.append(
            f"<img class='nav-logo' src='{url_for('static', filename=SUPREME_LOGO)}' "
            f"alt='Supreme Court of the Philippines seal'>"
        )
    flashes = ""
    for category, message in __import__("flask").get_flashed_messages(with_categories=True):
        flashes += f"<div class='notice {esc(category)}'>{esc(message)}</div>"
    staff_identity = ""
    if session.get("staff_logged_in"):
        staff_identity = (
            f"<p>{esc(tr('signed_in'))} "
            f"<strong>{esc(session.get('staff_username', ''))}</strong>.</p>"
        )
    return render_template_string(
        """
        <!doctype html>
        <html lang="{{ language }}">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <meta name="description" content="MCTC Silang-Amadeo Court Information Portal">
            <title>{{ title }} - {{ court_name }}</title>
            <style>{{ style|safe }}</style>
        </head>
        <body class="{{ theme }}{% if staff_page %} staff-interface{% endif %}">
            <header class="site-header">
                <div class="header-top">
                    <div class="header-title-wrap">
                        <h1 class="header-title">{{ court_name }}</h1>
                        <div class="header-subtitle">Official Court Information Portal</div>
                    </div>
                </div>
                <nav class="header-nav">
                    {{ navigation|safe }}
                </nav>
            </header>
            <main class="container">
                {{ flashes|safe }}
                {% if staff_identity %}
                <div class="small center">{{ staff_identity|safe }}</div>
                {% endif %}
                {{ body|safe }}
            </main>
            <footer>
                <strong>{{ court_name }}</strong>
                <p>{{ court_address }}</p>
                <p>{{ court_phone }} · <a href="mailto:{{ court_email }}">{{ court_email }}</a></p>
                <p><strong>{{ office_label }}:</strong> {{ office_hours }}</p>
                <p><a href="{{ maps_url }}" target="_blank" rel="noopener noreferrer">🗺️ {{ maps_label }}</a></p>
                <p>{{ copyright }}</p>
            </footer>
        </body>
        </html>
        """,
        language=lang_value(),
        theme=theme,
        title=title,
        court_name=COURT_NAME,
        court_address=COURT_ADDRESS,
        court_phone=COURT_PHONE,
        court_email=COURT_EMAIL,
        office_label=tr("office_hours"),
        office_hours=COURT_OFFICE_HOURS,
        maps_url=GOOGLE_MAPS_URL,
        maps_label=tr("open_maps"),
        copyright=tr("copyright"),
        style=STYLE,
        navigation="".join(nav),
        flashes=flashes,
        staff_identity=staff_identity,
        staff_page=staff_page,
        body=body,
    )
def lang_value():
    value = session.get("language", "en")
    return value if value in T else "en"
@app.route("/")
def home():
    connection = db()
    notices = connection.execute(
        """
        SELECT * FROM notices
        WHERE published = 1
        ORDER BY created_at DESC
        LIMIT 5
        """
    ).fetchall()
    connection.close()
    notices_html = ""
    for item in notices:
        title = item["title_fil"] if lang_value() == "fil" else item["title_en"]
        body_text = item["body_fil"] if lang_value() == "fil" else item["body_en"]
        attachment = ""
        if item["attachment"]:
            attachment = (
                f"<p><a class='button secondary' href='{url_for('uploaded_file', filename=item['attachment'])}'>"
                f"📎 {tr('open')}</a></p>"
            )
        notices_html += (
            f"<div class='notice'>"
            f"<h3>{esc(title)}</h3>"
            f"<p>{esc(body_text)}</p>"
            f"{attachment}"
            f"</div>"
        )
    body = f"""
    <section class="hero">
        <img class="hero-logo"
             src="{url_for('static', filename=MCTC_LOGO)}"
             alt="MCTC logo">
        <h1>{esc(COURT_NAME)}</h1>
        <p>Public court information, case search, requirements, announcements and the Tuesday schedule.</p>
        <div class="actions">
            <a class="button" href="{url_for('search_cases')}">🔎 {tr('search')}</a>
        </div>
    </section>
    <section class="grid home-feature-grid">
        <div class="card centered home-feature-card">
            <h2>🔎 {tr('search')}</h2>
            <p>{tr('required_search')}</p>
            <a class="button" href="{url_for('search_cases')}">{tr('search')}</a>
        </div>
        <div class="card centered home-feature-card">
            <h2>📅 {tr('calendar')}</h2>
            <p>View the Tuesday court schedule uploaded by authorized court staff.</p>
            <a class="button" href="{url_for('public_calendar')}">View Tuesday Calendar</a>
        </div>
        <div class="card centered home-feature-card">
            <h2>📄 {tr('requirements')}</h2>
            <p>View the publicly available posting bail bond and clearance information.</p>
            <a class="button" href="{url_for('requirements')}">{tr('view')}</a>
        </div>
        <div class="card centered home-feature-card">
            <h2>📢 {tr('news')}</h2>
            <p>Read public notices and announcements from authorized staff.</p>
            <a class="button" href="{url_for('news')}">{tr('view')}</a>
        </div>
    </section>
    <section class="card home-news-section">
        <h2>📢 {tr('news')}</h2>
        {notices_html or '<p class="empty">No announcements yet.</p>'}
    </section>
    """
    return render_page(tr("home"), body)
@app.route("/about")
def about():
    body = f"""
    <section class="card centered">
        <h1>{tr('about')}</h1>
        <h2>{esc(COURT_NAME)}</h2>
        <p>
            This portal provides approved public information including
            case searching, public requirements, announcements and the
            Tuesday schedule.
        </p>
        <div class="notice warning">
            Online information does not replace official court records,
            court orders, notices or certified documents.
        </div>
    </section>
    """
    return render_page(tr("about"), body)
@app.route("/contact")
def contact():
    body = f"""
    <section class="card centered">
        <h1>{tr('contact')}</h1>
        <h2>{esc(COURT_NAME)}</h2>
        <p><strong>{tr('address')}:</strong><br>{esc(COURT_ADDRESS)}</p>
        <p><strong>{tr('phone')}:</strong><br>{esc(COURT_PHONE)}</p>
        <p><strong>{tr('email') if 'email' in T[lang_value()] else 'Email Address'}:</strong><br>
           <a href="mailto:{esc(COURT_EMAIL)}">{esc(COURT_EMAIL)}</a></p>
        <p><strong>{tr('office_hours')}:</strong><br>{esc(COURT_OFFICE_HOURS)}</p>
        <a class="button" href="{GOOGLE_MAPS_URL}" target="_blank" rel="noopener noreferrer">
            🗺️ {tr('open_maps')}
        </a>
    </section>
    """
    return render_page(tr("contact"), body)
@app.route("/news")
def news():
    connection = db()
    notices = connection.execute(
        """
        SELECT * FROM notices
        WHERE published = 1
        ORDER BY created_at DESC
        """
    ).fetchall()
    connection.close()
    cards = ""
    for item in notices:
        title = item["title_fil"] if lang_value() == "fil" else item["title_en"]
        text = item["body_fil"] if lang_value() == "fil" else item["body_en"]
        attachment = ""
        if item["attachment"]:
            attachment = (
                f"<p><a class='button secondary' href='{url_for('uploaded_file', filename=item['attachment'])}'>"
                f"📎 {tr('open')}</a></p>"
            )
        cards += (
            f"<article class='card'>"
            f"<h2>{esc(title)}</h2>"
            f"<p>{esc(text)}</p>"
            f"{attachment}"
            f"</article>"
        )
    body = (
        f"<section class='card centered'><h1>📢 {tr('news')}</h1></section>"
        + (cards or "<div class='card empty'>No announcements have been published.</div>")
    )
    return render_page(tr("news"), body)
@app.route("/search", methods=["GET", "POST"])
def search_cases():
    case_number = request.values.get("case_number", "").strip()
    plaintiff = request.values.get("plaintiff", "").strip()
    result = None
    if request.method == "POST":
        if not case_number or not plaintiff:
            flash(tr("required_search"), "danger")
        else:
            connection = db()
            result = connection.execute(
                """
                SELECT * FROM cases
                WHERE lower(case_number) = lower(?)
                  AND lower(plaintiff_name) = lower(?)
                LIMIT 1
                """,
                (case_number, plaintiff),
            ).fetchone()
            connection.close()
            if result is None:
                flash(tr("no_results"), "warning")
    body = f"""
    <section class="card">
        <h1>🔎 {tr('search')}</h1>
        <div class="notice">
            <h3>{tr('how_search')}</h3>
            <ol>
                <li>{tr('step1')}</li>
                <li>{tr('step2')}</li>
                <li>{tr('step3')}</li>
                <li>{tr('step4')}</li>
            </ol>
        </div>
        <form method="post">
            <label>{tr('case_number')}</label>
            <input name="case_number" value="{esc(case_number)}" autocomplete="off" required>
            <label>{tr('plaintiff')}</label>
            <input name="plaintiff" value="{esc(plaintiff)}" autocomplete="off" required>
            <button type="submit">🔎 {tr('search')}</button>
        </form>
    </section>
    """
    if result:
        body += f"""
        <section class="card">
            <span class="status">{esc(result['status'])}</span>
            <h2>{esc(result['case_number'])}</h2>
            <p><strong>{tr('plaintiff')}:</strong> {esc(result['plaintiff_name'])}</p>
            <p><strong>{tr('defendant')}:</strong> {esc(result['defendant_name'])}</p>
            <p><strong>{tr('parties')}:</strong> {esc(result['parties'])}</p>
            <p><strong>{tr('case_type')}:</strong> {esc(result['case_type'])}</p>
            <p>{esc(result['public_description'])}</p>
            <a class="button" href="{url_for('public_case', case_id=result['id'])}">{tr('view')}</a>
        </section>
        """
    return render_page(tr("search"), body)
@app.route("/case/<int:case_id>")
def public_case(case_id):
    connection = db()
    case = connection.execute(
        "SELECT * FROM cases WHERE id = ?",
        (case_id,),
    ).fetchone()
    hearings = connection.execute(
        """
        SELECT * FROM hearings
        WHERE case_id = ?
        ORDER BY hearing_date, hearing_time, id
        """,
        (case_id,),
    ).fetchall()
    connection.close()
    if case is None:
        abort(404)
    hearing_html = ""
    for hearing in hearings:
        hearing_html += f"""
        <div class="notice">
            <p><strong>{tr('hearing_date')}:</strong> {esc(hearing['hearing_date'])}</p>
            <p><strong>{tr('hearing_time')}:</strong> {esc(hearing['hearing_time'])}</p>
            <p><strong>{tr('hearing_nature')}:</strong> {esc(hearing['hearing_nature'])}</p>
            <p><strong>{tr('hearing_status')}:</strong> <span class="status">{esc(hearing['hearing_status'])}</span></p>
            <p><strong>{tr('remarks')}:</strong> {esc(hearing['remarks'])}</p>
        </div>
        """
    body = f"""
    <section class="card">
        <span class="status">{esc(case['status'])}</span>
        <h1>{esc(case['case_number'])}</h1>
        <p><strong>{tr('plaintiff')}:</strong> {esc(case['plaintiff_name'])}</p>
        <p><strong>{tr('defendant')}:</strong> {esc(case['defendant_name'])}</p>
        <p><strong>{tr('parties')}:</strong> {esc(case['parties'])}</p>
        <p><strong>{tr('case_type')}:</strong> {esc(case['case_type'])}</p>
        <p>{esc(case['public_description'])}</p>
    </section>
    <section class="card">
        <h2>📅 {tr('hearing')}</h2>
        {hearing_html or '<p class="empty">No published hearing information.</p>'}
    </section>
    """
    return render_page(tr("cases"), body)
@app.route("/requirements")
def requirements():
    connection = db()
    rows = connection.execute(
        """
        SELECT * FROM requirements
        ORDER BY CASE category WHEN 'bond' THEN 1 WHEN 'clearance' THEN 2 ELSE 3 END
        """
    ).fetchall()
    connection.close()
    body = f"""
    <section class="card centered">
        <h1>📄 {tr('requirements')}</h1>
        <p>
            The following public checklist was transcribed from the
            requirement notice supplied for this project.
        </p>
        <div class="notice warning">
            Please contact the court to confirm the current official requirements
            before submitting documents.
        </div>
    </section>
    """
    for row in rows:
        title = row["title_fil"] if lang_value() == "fil" else row["title_en"]
        description = row["description_fil"] if lang_value() == "fil" else row["description_en"]
        checklist = ""
        if row["category"] == "bond":
            checklist = "<ol class='requirement-list'>" + "".join(
                f"<li>{esc(item)}</li>" for item in BOND_REQUIREMENTS
            ) + "</ol>"
        else:
            checklist = (
                "<p class='small'>"
                + esc(description or tr("not_uploaded"))
                + "</p>"
            )
        file_link = ""
        if row["file_name"]:
            file_link = (
                f"<p><a class='button secondary' href='{url_for('uploaded_file', filename=row['file_name'])}'>"
                f"📎 {tr('open')}</a></p>"
            )
        body += f"""
        <section class="card">
            <h2>{esc(title)}</h2>
            {checklist}
            <p class="small"><strong>Current uploaded information:</strong> {esc(description or tr('not_uploaded'))}</p>
            {file_link}
        </section>
        """
    return render_page(tr("requirements"), body)
@app.route("/calendar")
def public_calendar():
    connection = db()
    schedule = connection.execute(
        "SELECT * FROM schedule WHERE id = 1"
    ).fetchone()
    connection.close()
    schedule_html = (
        "<p class='empty'>No Tuesday schedule has been uploaded yet.</p>"
    )
    if schedule and schedule["file_name"]:
        filename = schedule["file_name"]
        extension = schedule["file_type"] or Path(filename).suffix.lower().lstrip(".")
        url = url_for("uploaded_file", filename=filename)
        if extension == "pdf":
            schedule_html = (
                f"<iframe class='schedule-pdf' src='{url}' title='Tuesday schedule PDF'></iframe>"
            )
        elif extension in IMAGE_EXTENSIONS:
            schedule_html = (
                f"<img class='schedule-image' src='{url}' alt='Tuesday schedule'>"
            )
        else:
            schedule_html = (
                f"<p><a class='button' href='{url}'>{tr('open')}</a></p>"
            )
    body = f"""
    <section class="card centered">
        <h1>📅 {tr('calendar')}</h1>
        <p>
            The Tuesday calendar is published as one staff-uploaded schedule.
        </p>
    </section>
    <section class="card">
        {schedule_html}
    </section>
    """
    return render_page(tr("calendar"), body)
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)
@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():
    if session.get("staff_logged_in"):
        return redirect(url_for("staff_dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        connection = db()
        staff = connection.execute(
            """
            SELECT * FROM staff
            WHERE lower(username) = lower(?) AND active = 1
            """,
            (username,),
        ).fetchone()
        connection.close()
        if staff and check_password_hash(staff["password_hash"], password):
            session.clear()
            session["staff_logged_in"] = True
            session["staff_id"] = staff["id"]
            session["staff_username"] = staff["username"]
            session["staff_role"] = staff["role"]
            session["language"] = "en"
            session["theme"] = "light"
            audit("login", username)
            return redirect(url_for("staff_dashboard"))
        flash(tr("invalid_login"), "danger")
    body = f"""
    <section class="card centered" style="max-width:520px;margin:45px auto">
        <h1>🔐 {tr('staff_login')}</h1>
        <p class="small">Authorized court staff only.</p>
        <form method="post" autocomplete="off">
            <label>{tr('username')}</label>
            <input name="username" autocomplete="username" required>
            <label>{tr('password')}</label>
            <input type="password" name="password" autocomplete="current-password" required>
            <br>
            <button type="submit">{tr('login') if 'login' in T[lang_value()] else 'Log In'}</button>
        </form>
    </section>
    """
    return render_page(tr("staff_login"), body)


@app.route("/staff/change-password", methods=["GET", "POST"])
@staff_required
def change_password():
    """Change the password of the currently signed-in staff account."""
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not current_password or not new_password or not confirm_password:
            flash("Please fill in all password fields.", "danger")
            return redirect(url_for("change_password"))
        if len(new_password) < 8:
            flash("New password must contain at least 8 characters.", "danger")
            return redirect(url_for("change_password"))
        if new_password != confirm_password:
            flash("The new passwords do not match.", "danger")
            return redirect(url_for("change_password"))
        staff_id = session.get("staff_id")
        connection = db()
        staff = connection.execute(
            "SELECT id, username, password_hash FROM staff WHERE id = ? AND active = 1",
            (staff_id,),
        ).fetchone()
        if staff is None:
            connection.close()
            session.clear()
            flash("Your staff session is no longer valid. Please log in again.", "danger")
            return redirect(url_for("staff_login"))
        if not check_password_hash(staff["password_hash"], current_password):
            connection.close()
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("change_password"))
        if check_password_hash(staff["password_hash"], new_password):
            connection.close()
            flash("New password must be different from the current password.", "danger")
            return redirect(url_for("change_password"))
        connection.execute(
            "UPDATE staff SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), staff["id"]),
        )
        connection.commit()
        connection.close()
        audit("password_changed", staff["username"])
        flash("Password changed successfully.", "success")
        return redirect(url_for("staff_dashboard"))
    body = """
    <section class="card centered" style="max-width:620px;margin:45px auto">
        <h1>🔑 Change Password</h1>
        <p class="small">Update the password for your currently signed-in staff account.</p>
        <form method="post" autocomplete="off">
            <label for="current_password">Current Password</label>
            <input id="current_password" type="password" name="current_password" autocomplete="current-password" required>
            <label for="new_password">New Password</label>
            <input id="new_password" type="password" name="new_password" minlength="8" autocomplete="new-password" required>
            <label for="confirm_password">Confirm New Password</label>
            <input id="confirm_password" type="password" name="confirm_password" minlength="8" autocomplete="new-password" required>
            <br>
            <button type="submit">Change Password</button>
        </form>
    </section>
    """
    return render_page("Change Password", body, staff_page=True)
@app.route("/staff/logout", methods=["GET", "POST"])
def logout():
    username = session.get("staff_username", "unknown")
    if session.get("staff_logged_in"):
        audit("logout", username)
    session.clear()
    response = redirect(url_for("home"))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    flash("You have been logged out.", "success")
    return response
@app.route("/staff")
@app.route("/staff/dashboard")
@staff_required
def staff_dashboard():
    connection = db()
    counts = {
        "cases": connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
        "notices": connection.execute("SELECT COUNT(*) FROM notices").fetchone()[0],
        "laws": connection.execute("SELECT COUNT(*) FROM legal_resources").fetchone()[0],
    }
    schedule = connection.execute("SELECT file_name FROM schedule WHERE id = 1").fetchone()
    connection.close()
    schedule_text = "Uploaded" if schedule and schedule["file_name"] else tr("not_uploaded")
    body = f"""
    <section class="hero">
        <h1>{tr('welcome')}</h1>
        <p>{esc(tr('signed_in'))} <strong>{esc(session.get('staff_username', ''))}</strong>.</p>
    </section>
    <section class="grid">
        <div class="card stat"><span class="stat-number">{counts['cases']}</span>{tr('cases')}</div>
        <div class="card stat"><span class="stat-number">{counts['notices']}</span>{tr('notices')}</div>
        <div class="card stat"><span class="stat-number">{counts['laws']}</span>{tr('laws')}</div>
    </section>
    <section class="card">
        <h2 class="center">Quick Actions</h2>
        <div class="grid">
            <a class="card centered" href="{url_for('staff_cases')}">
                <h3>📋 {tr('cases')}</h3><p>Add, edit and delete cases.</p>
            </a>
            <a class="card centered" href="{url_for('staff_calendar')}">
                <h3>📅 {tr('calendar')}</h3><p>Upload the Tuesday schedule.</p>
            </a>
            <a class="card centered" href="{url_for('staff_requirements')}">
                <h3>📄 {tr('requirements')}</h3><p>Manage public requirements.</p>
            </a>
            <a class="card centered" href="{url_for('staff_notices')}">
                <h3>📢 {tr('notices')}</h3><p>Publish announcements and attachments.</p>
            </a>
            <a class="card centered" href="{url_for('staff_laws')}">
                <h3>⚖️ {tr('laws')}</h3><p>Manage legal resources.</p>
            </a>
            {'<a class="card centered" href="' + url_for('staff_accounts') + '"><h3>👥 ' + tr('staff_accounts') + '</h3><p>Add and manage staff accounts.</p></a>' if session.get('staff_role') in {'admin','superadmin'} else ''}
            <a class="card centered" href="{url_for('change_password')}">
                <h3>🔑 Change Password</h3><p>Update your staff account password.</p>
            </a>
        </div>
    </section>
    <section class="card centered">
        <h2>Tuesday Schedule</h2>
        <p>{esc(schedule_text)}</p>
    </section>
    """
    return render_page(tr("staff_dashboard"), body, staff_page=True)
@app.route("/staff/cases")
@staff_required
def staff_cases():
    connection = db()
    rows = connection.execute(
        "SELECT * FROM cases ORDER BY updated_at DESC"
    ).fetchall()
    connection.close()
    table = ""
    for row in rows:
        table += f"""
        <tr>
            <td><strong>{esc(row['case_number'])}</strong></td>
            <td>{esc(row['plaintiff_name'])}</td>
            <td>{esc(row['defendant_name'])}</td>
            <td>{esc(row['case_type'])}</td>
            <td><span class="status">{esc(row['status'])}</span></td>
            <td>
                <a class="button secondary" href="{url_for('staff_edit_case', case_id=row['id'])}">{tr('edit')}</a>
                <a class="button secondary" href="{url_for('staff_hearing', case_id=row['id'])}">{tr('hearing')}</a>
                <form method="post" action="{url_for('staff_delete_case', case_id=row['id'])}" style="display:inline">
                    <button class="danger" type="submit" onclick="return confirm('Delete this case permanently?')">{tr('delete')}</button>
                </form>
            </td>
        </tr>
        """
    if not table:
        table = "<tr><td colspan='6' class='empty'>No cases.</td></tr>"
    body = f"""
    <section class="card centered">
        <h1>📋 {tr('cases')}</h1>
        <a class="button" href="{url_for('staff_add_case')}">➕ {tr('add')}</a>
    </section>
    <section class="card table-wrap">
        <table>
            <thead><tr>
                <th>{tr('case_number')}</th>
                <th>{tr('plaintiff')}</th>
                <th>{tr('defendant')}</th>
                <th>{tr('case_type')}</th>
                <th>{tr('status')}</th>
                <th>Actions</th>
            </tr></thead>
            <tbody>{table}</tbody>
        </table>
    </section>
    """
    return render_page(tr("cases"), body, staff_page=True)
@app.route("/staff/cases/add", methods=["GET", "POST"])
@staff_required
def staff_add_case():
    if request.method == "POST":
        form = request.form
        case_number = form.get("case_number", "").strip()
        plaintiff = form.get("plaintiff", "").strip()
        defendant = form.get("defendant", "").strip()
        parties = form.get("parties", "").strip()
        case_type = form.get("case_type", "").strip()
        description = form.get("public_description", "").strip()
        if not case_number or not plaintiff:
            flash("Case number and plaintiff name are required.", "danger")
            return redirect(url_for("staff_add_case"))
        connection = db()
        try:
            connection.execute(
                """
                INSERT INTO cases
                (
                    case_number,
                    plaintiff_name,
                    defendant_name,
                    parties,
                    case_type,
                    status,
                    public_description,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'Active', ?, ?, ?)
                """,
                (
                    case_number,
                    plaintiff,
                    defendant,
                    parties,
                    case_type,
                    description,
                    now(),
                    now(),
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError:
            connection.close()
            flash("That case number already exists.", "danger")
            return redirect(url_for("staff_add_case"))
        connection.close()
        audit("case_created", case_number)
        flash("Case created successfully.", "success")
        return redirect(url_for("staff_cases"))
    body = f"""
    <section class="card">
        <h1 class="center">➕ {tr('add')}</h1>
        <form method="post">
            <label>{tr('case_number')}</label>
            <input name="case_number" required>
            <label>{tr('plaintiff')}</label>
            <input name="plaintiff" required>
            <label>{tr('defendant')}</label>
            <input name="defendant">
            <label>{tr('parties')}</label>
            <input name="parties">
            <label>{tr('case_type')}</label>
            <input name="case_type">
            <label>{tr('description')}</label>
            <textarea name="public_description"></textarea>
            <button type="submit">{tr('save')}</button>
        </form>
    </section>
    """
    return render_page(tr("add"), body, staff_page=True)
@app.route("/staff/cases/<int:case_id>/edit", methods=["GET", "POST"])
@staff_required
def staff_edit_case(case_id):
    connection = db()
    case = connection.execute(
        "SELECT * FROM cases WHERE id = ?",
        (case_id,),
    ).fetchone()
    connection.close()
    if case is None:
        abort(404)
    if request.method == "POST":
        form = request.form
        connection = db()
        connection.execute(
            """
            UPDATE cases
            SET
                plaintiff_name = ?,
                defendant_name = ?,
                parties = ?,
                case_type = ?,
                status = 'Active',
                public_description = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                form.get("plaintiff", "").strip(),
                form.get("defendant", "").strip(),
                form.get("parties", "").strip(),
                form.get("case_type", "").strip(),
                form.get("public_description", "").strip(),
                now(),
                case_id,
            ),
        )
        connection.commit()
        connection.close()
        audit("case_updated", case["case_number"])
        flash("Case updated successfully.", "success")
        return redirect(url_for("staff_cases"))
    body = f"""
    <section class="card">
        <h1 class="center">✏️ {tr('edit')}</h1>
        <form method="post">
            <label>{tr('case_number')}</label>
            <input value="{esc(case['case_number'])}" disabled>
            <label>{tr('plaintiff')}</label>
            <input name="plaintiff" value="{esc(case['plaintiff_name'])}" required>
            <label>{tr('defendant')}</label>
            <input name="defendant" value="{esc(case['defendant_name'])}">
            <label>{tr('parties')}</label>
            <input name="parties" value="{esc(case['parties'])}">
            <label>{tr('case_type')}</label>
            <input name="case_type" value="{esc(case['case_type'])}">
            <label>{tr('description')}</label>
            <textarea name="public_description">{esc(case['public_description'])}</textarea>
            <button type="submit">{tr('save')}</button>
        </form>
    </section>
    """
    return render_page(tr("edit"), body, staff_page=True)
@app.post("/staff/cases/<int:case_id>/delete")
@staff_required
def staff_delete_case(case_id):
    connection = db()
    case = connection.execute(
        "SELECT case_number FROM cases WHERE id = ?",
        (case_id,),
    ).fetchone()
    if case is None:
        connection.close()
        abort(404)
    connection.execute("DELETE FROM cases WHERE id = ?", (case_id,))
    connection.commit()
    connection.close()
    audit("case_deleted", case["case_number"])
    flash("Case deleted successfully.", "success")
    return redirect(url_for("staff_cases"))
@app.route("/staff/cases/<int:case_id>/hearing", methods=["GET", "POST"])
@staff_required
def staff_hearing(case_id):
    connection = db()
    case = connection.execute(
        "SELECT * FROM cases WHERE id = ?",
        (case_id,),
    ).fetchone()
    hearing = connection.execute(
        "SELECT * FROM hearings WHERE case_id = ? ORDER BY id DESC LIMIT 1",
        (case_id,),
    ).fetchone()
    connection.close()
    if case is None:
        abort(404)
    if request.method == "POST":
        form = request.form
        values = (
            form.get("hearing_date", "").strip(),
            form.get("hearing_time", "").strip(),
            form.get("hearing_nature", "").strip(),
            form.get("hearing_status", "Scheduled").strip(),
            form.get("remarks", "").strip(),
        )
        connection = db()
        if hearing:
            connection.execute(
                """
                UPDATE hearings
                SET
                    hearing_date = ?,
                    hearing_time = ?,
                    hearing_nature = ?,
                    hearing_status = ?,
                    remarks = ?
                WHERE id = ?
                """,
                values + (hearing["id"],),
            )
        else:
            connection.execute(
                """
                INSERT INTO hearings
                (case_id, hearing_date, hearing_time, hearing_nature, hearing_status, remarks)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (case_id,) + values,
            )
        connection.commit()
        connection.close()
        audit("hearing_updated", case["case_number"])
        flash("Hearing updated successfully.", "success")
        return redirect(url_for("staff_hearing", case_id=case_id))
    date_value = hearing["hearing_date"] if hearing else ""
    time_value = hearing["hearing_time"] if hearing else ""
    nature_value = hearing["hearing_nature"] if hearing else "Initial Hearing"
    status_value = hearing["hearing_status"] if hearing else "Scheduled"
    remarks_value = hearing["remarks"] if hearing else ""
    natures = [
        "Initial Hearing",
        "Arraignment",
        "Pre-Trial",
        "Trial",
        "Motion",
        "Compliance",
        "Judgment",
        "Promulgation",
        "Hearing",
        "Other",
    ]
    statuses = [
        "Scheduled",
        "Ongoing",
        "Completed",
        "Reset",
        "Postponed",
        "Cancelled",
    ]
    nature_options = "".join(
        f"<option {'selected' if value == nature_value else ''}>{esc(value)}</option>"
        for value in natures
    )
    status_options = "".join(
        f"<option {'selected' if value == status_value else ''}>{esc(value)}</option>"
        for value in statuses
    )
    body = f"""
    <section class="card">
        <h1 class="center">📅 {tr('hearing')}</h1>
        <p class="center"><strong>{esc(case['case_number'])}</strong> · {esc(case['plaintiff_name'])}</p>
        <form method="post">
            <label>{tr('hearing_date')}</label>
            <input type="date" name="hearing_date" value="{esc(date_value)}" required>
            <label>{tr('hearing_time')}</label>
            <input type="time" name="hearing_time" value="{esc(time_value)}">
            <label>{tr('hearing_nature')}</label>
            <select name="hearing_nature">{nature_options}</select>
            <label>{tr('hearing_status')}</label>
            <select name="hearing_status">{status_options}</select>
            <label>{tr('remarks')}</label>
            <textarea name="remarks">{esc(remarks_value)}</textarea>
            <button type="submit">{tr('save')}</button>
        </form>
    </section>
    """
    return render_page(tr("hearing"), body, staff_page=True)
@app.route("/staff/calendar")
@staff_required
def staff_calendar():
    connection = db()
    schedule = connection.execute(
        "SELECT * FROM schedule WHERE id = 1"
    ).fetchone()
    connection.close()
    current = "<p class='small'>No schedule uploaded yet.</p>"
    delete_link = ""
    if schedule and schedule["file_name"]:
        url = url_for("uploaded_file", filename=schedule["file_name"])
        extension = schedule["file_type"] or ""
        if extension == "pdf":
            current = f"<iframe class='schedule-pdf' src='{url}' title='Current Tuesday schedule'></iframe>"
        elif extension in IMAGE_EXTENSIONS:
            current = f"<img class='schedule-image' src='{url}' alt='Current Tuesday schedule'>"
        else:
            current = f"<p><a class='button secondary' href='{url}'>{tr('open')}</a></p>"
        delete_link = (
            f"<form method='post' action='{url_for('delete_schedule')}' style='display:inline'>"
            f"<button class='danger' type='submit' onclick=\"return confirm('Delete the Tuesday schedule?')\">{tr('delete')}</button>"
            f"</form>"
        )
    body = f"""
    <section class="card centered">
        <h1>📅 {tr('calendar')}</h1>
        <p>
            Upload one Tuesday schedule as an image or PDF.
            Civilians will see the latest published schedule.
        </p>
    </section>
    <section class="card">
        <h2 class="center">Upload / Replace Tuesday Schedule</h2>
        <form method="post" action="{url_for('upload_schedule')}" enctype="multipart/form-data">
            <label>{tr('upload')}</label>
            <input type="file" name="schedule" accept=".pdf,.png,.jpg,.jpeg,.webp,.gif" required>
            <button type="submit">{tr('upload')}</button>
        </form>
    </section>
    <section class="card">
        <h2 class="center">Current Schedule</h2>
        {current}
        <div class="actions">{delete_link}</div>
    </section>
    """
    return render_page(tr("calendar"), body, staff_page=True)
@app.post("/staff/calendar/upload")
@staff_required
def upload_schedule():
    file = request.files.get("schedule")
    try:
        filename, original, extension = save_upload(file)
    except ValueError as error:
        flash(str(error), "danger")
        return redirect(url_for("staff_calendar"))
    if not filename:
        flash("Please select a schedule file.", "danger")
        return redirect(url_for("staff_calendar"))
    connection = db()
    old = connection.execute(
        "SELECT file_name FROM schedule WHERE id = 1"
    ).fetchone()
    connection.execute(
        """
        INSERT INTO schedule
        (id, file_name, original_filename, file_type, updated_at, uploaded_by)
        VALUES (1, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            file_name = excluded.file_name,
            original_filename = excluded.original_filename,
            file_type = excluded.file_type,
            updated_at = excluded.updated_at,
            uploaded_by = excluded.uploaded_by
        """,
        (
            filename,
            original,
            extension,
            now(),
            session.get("staff_username", ""),
        ),
    )
    connection.commit()
    connection.close()
    if old and old["file_name"] and old["file_name"] != filename:
        delete_uploaded_file(old["file_name"])
    audit("schedule_uploaded", original or filename)
    flash("Tuesday schedule uploaded successfully.", "success")
    return redirect(url_for("staff_calendar"))
@app.post("/staff/calendar/delete")
@staff_required
def delete_schedule():
    connection = db()
    row = connection.execute(
        "SELECT file_name FROM schedule WHERE id = 1"
    ).fetchone()
    connection.execute("DELETE FROM schedule WHERE id = 1")
    connection.commit()
    connection.close()
    if row and row["file_name"]:
        delete_uploaded_file(row["file_name"])
    audit("schedule_deleted", "Tuesday schedule")
    flash("Tuesday schedule deleted.", "success")
    return redirect(url_for("staff_calendar"))
@app.route("/staff/notices")
@staff_required
def staff_notices():
    connection = db()
    rows = connection.execute(
        "SELECT * FROM notices ORDER BY created_at DESC"
    ).fetchall()
    connection.close()
    cards = ""
    for row in rows:
        attachment = ""
        if row["attachment"]:
            attachment = (
                f"<p><a class='button secondary' href='{url_for('uploaded_file', filename=row['attachment'])}'>"
                f"📎 {tr('open')}</a></p>"
            )
        cards += f"""
        <article class="notice">
            <h3>{esc(row['title_en'])}</h3>
            <p>{esc(row['body_en'])}</p>
            {attachment}
            <form method="post" action="{url_for('delete_notice', notice_id=row['id'])}" style="display:inline">
                <button class="danger" type="submit" onclick="return confirm('Delete this notice?')">{tr('delete')}</button>
            </form>
        </article>
        """
    body = f"""
    <section class="card">
        <h1 class="center">📢 {tr('notices')}</h1>
        <form method="post" action="{url_for('add_notice')}" enctype="multipart/form-data">
            <label>English Title</label>
            <input name="title_en" required>
            <label>Filipino Title</label>
            <input name="title_fil" required>
            <label>English Notice</label>
            <textarea name="body_en" required></textarea>
            <label>Filipino Notice</label>
            <textarea name="body_fil" required></textarea>
            <label>{tr('attachment')}</label>
            <input type="file" name="attachment" accept=".pdf,.png,.jpg,.jpeg,.webp,.gif,.doc,.docx">
            <button type="submit">{tr('upload')}</button>
        </form>
    </section>
    <section class="card">
        {cards or '<p class="empty">No notices yet.</p>'}
    </section>
    """
    return render_page(tr("notices"), body, staff_page=True)
@app.post("/staff/notices/add")
@staff_required
def add_notice():
    form = request.form
    values = (
        form.get("title_en", "").strip(),
        form.get("title_fil", "").strip(),
        form.get("body_en", "").strip(),
        form.get("body_fil", "").strip(),
    )
    if not all(values):
        flash("Complete all notice fields.", "danger")
        return redirect(url_for("staff_notices"))
    try:
        filename, original, _ = save_upload(request.files.get("attachment"))
    except ValueError as error:
        flash(str(error), "danger")
        return redirect(url_for("staff_notices"))
    connection = db()
    connection.execute(
        """
        INSERT INTO notices
        (title_en, title_fil, body_en, body_fil, attachment,
         original_filename, published, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        values + (filename, original, now(), now()),
    )
    connection.commit()
    connection.close()
    audit("notice_created", values[0])
    flash("Notice published successfully.", "success")
    return redirect(url_for("staff_notices"))
@app.post("/staff/notices/<int:notice_id>/delete")
@staff_required
def delete_notice(notice_id):
    connection = db()
    row = connection.execute(
        "SELECT attachment FROM notices WHERE id = ?",
        (notice_id,),
    ).fetchone()
    connection.execute(
        "DELETE FROM notices WHERE id = ?",
        (notice_id,),
    )
    connection.commit()
    connection.close()
    if row:
        delete_uploaded_file(row["attachment"])
    audit("notice_deleted", notice_id)
    flash("Notice deleted.", "success")
    return redirect(url_for("staff_notices"))
@app.route("/staff/laws")
@staff_required
def staff_laws():
    connection = db()
    rows = connection.execute(
        "SELECT * FROM legal_resources ORDER BY created_at DESC"
    ).fetchall()
    connection.close()
    cards = ""
    for row in rows:
        links = ""
        if row["source_url"]:
            links += (
                f"<a class='button secondary' href='{esc(row['source_url'])}' target='_blank' rel='noopener noreferrer'>"
                f"{tr('official_source')}</a> "
            )
        if row["file_name"]:
            links += (
                f"<a class='button secondary' href='{url_for('uploaded_file', filename=row['file_name'])}'>"
                f"{tr('open')}</a> "
            )
        cards += f"""
        <article class="notice">
            <span class="status">{esc(row['category'])}</span>
            <h3>{esc(row['title'])}</h3>
            <p>{esc(row['description'])}</p>
            {links}
            <form method="post" action="{url_for('delete_law', law_id=row['id'])}" style="display:inline">
                <button class="danger" type="submit">{tr('delete')}</button>
            </form>
        </article>
        """
    body = f"""
    <section class="card">
        <h1 class="center">⚖️ {tr('laws')}</h1>
        <form method="post" action="{url_for('add_law')}" enctype="multipart/form-data">
            <label>Category</label>
            <select name="category">
                <option>Philippine Laws</option>
                <option>Supreme Court Decisions</option>
                <option>Rules of Court</option>
                <option>Supreme Court Rules</option>
                <option>Administrative Matters</option>
                <option>Other Official Resource</option>
            </select>
            <label>Title</label>
            <input name="title" required>
            <label>Description</label>
            <textarea name="description"></textarea>
            <label>Official Source URL</label>
            <input type="url" name="source_url">
            <label>Document</label>
            <input type="file" name="file">
            <button type="submit">{tr('add')}</button>
        </form>
    </section>
    <section class="card">
        {cards or '<p class="empty">No legal resources yet.</p>'}
    </section>
    """
    return render_page(tr("laws"), body, staff_page=True)
@app.post("/staff/laws/add")
@staff_required
def add_law():
    title = request.form.get("title", "").strip()
    if not title:
        flash("Title is required.", "danger")
        return redirect(url_for("staff_laws"))
    try:
        filename, original, _ = save_upload(request.files.get("file"))
    except ValueError as error:
        flash(str(error), "danger")
        return redirect(url_for("staff_laws"))
    connection = db()
    connection.execute(
        """
        INSERT INTO legal_resources
        (category, title, description, source_url, file_name,
         original_filename, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            request.form.get("category", "").strip(),
            title,
            request.form.get("description", "").strip(),
            request.form.get("source_url", "").strip(),
            filename,
            original,
            now(),
            now(),
        ),
    )
    connection.commit()
    connection.close()
    audit("legal_resource_created", title)
    flash("Legal resource added.", "success")
    return redirect(url_for("staff_laws"))
@app.post("/staff/laws/<int:law_id>/delete")
@staff_required
def delete_law(law_id):
    connection = db()
    row = connection.execute(
        "SELECT file_name FROM legal_resources WHERE id = ?",
        (law_id,),
    ).fetchone()
    connection.execute(
        "DELETE FROM legal_resources WHERE id = ?",
        (law_id,),
    )
    connection.commit()
    connection.close()
    if row:
        delete_uploaded_file(row["file_name"])
    audit("legal_resource_deleted", law_id)
    flash("Legal resource deleted.", "success")
    return redirect(url_for("staff_laws"))
@app.route("/staff/requirements")
@staff_required
def staff_requirements():
    connection = db()
    rows = connection.execute(
        """
        SELECT * FROM requirements
        ORDER BY CASE category WHEN 'bond' THEN 1 WHEN 'clearance' THEN 2 ELSE 3 END
        """
    ).fetchall()
    connection.close()
    cards = ""
    for row in rows:
        title = row["title_fil"] if lang_value() == "fil" else row["title_en"]
        description = row["description_fil"] if lang_value() == "fil" else row["description_en"]
        checklist = ""
        if row["category"] == "bond":
            checklist = "<ol class='requirement-list'>" + "".join(
                f"<li>{esc(item)}</li>" for item in BOND_REQUIREMENTS
            ) + "</ol>"
        file_link = ""
        if row["file_name"]:
            file_link = (
                f"<p><a class='button secondary' href='{url_for('uploaded_file', filename=row['file_name'])}'>"
                f"{tr('open')}</a></p>"
            )
        cards += f"""
        <article class="card">
            <h2>{esc(title)}</h2>
            {checklist}
            <p class="small">{esc(description or tr('not_uploaded'))}</p>
            <form method="post" action="{url_for('update_requirement', category=row['category'])}" enctype="multipart/form-data">
                <label>Description</label>
                <textarea name="description">{esc(description)}</textarea>
                <label>Official Document</label>
                <input type="file" name="document">
                <button type="submit">{tr('save')}</button>
            </form>
            {file_link}
        </article>
        """
    body = f"""
    <section class="card centered">
        <h1>📄 {tr('requirements')}</h1>
        <p>Update the public requirements information.</p>
    </section>
    {cards}
    """
    return render_page(tr("requirements"), body, staff_page=True)
@app.post("/staff/requirements/<category>/update")
@staff_required
def update_requirement(category):
    if category not in {"bond", "clearance"}:
        abort(404)
    description = request.form.get("description", "").strip()
    try:
        filename, original, _ = save_upload(request.files.get("document"))
    except ValueError as error:
        flash(str(error), "danger")
        return redirect(url_for("staff_requirements"))
    connection = db()
    if filename:
        connection.execute(
            """
            UPDATE requirements
            SET description_en = ?, description_fil = ?,
                file_name = ?, original_filename = ?, updated_at = ?
            WHERE category = ?
            """,
            (
                description,
                description,
                filename,
                original,
                now(),
                category,
            ),
        )
    else:
        connection.execute(
            """
            UPDATE requirements
            SET description_en = ?, description_fil = ?, updated_at = ?
            WHERE category = ?
            """,
            (
                description,
                description,
                now(),
                category,
            ),
        )
    connection.commit()
    connection.close()
    audit("requirement_updated", category)
    flash("Requirement updated.", "success")
    return redirect(url_for("staff_requirements"))
@app.route("/staff/super-admin")
@superadmin_required
def superadmin_dashboard():
    connection = db()
    counts = {
        "staff": connection.execute("SELECT COUNT(*) FROM staff").fetchone()[0],
        "cases": connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
        "hearings": connection.execute("SELECT COUNT(*) FROM hearings").fetchone()[0],
        "notices": connection.execute("SELECT COUNT(*) FROM notices").fetchone()[0],
        "laws": connection.execute("SELECT COUNT(*) FROM legal_resources").fetchone()[0],
        "requirements": connection.execute("SELECT COUNT(*) FROM requirements").fetchone()[0],
        "audit": connection.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0],
    }
    staff_rows = connection.execute(
        "SELECT username, role, active FROM staff ORDER BY username"
    ).fetchall()
    case_rows = connection.execute(
        "SELECT case_number, plaintiff_name, defendant_name, status, updated_at FROM cases ORDER BY updated_at DESC LIMIT 100"
    ).fetchall()
    audit_rows = connection.execute(
        "SELECT username, action, target, created_at FROM audit_logs ORDER BY id DESC LIMIT 100"
    ).fetchall()
    connection.close()
    staff_table = "".join(
        f"<tr><td>{esc(r['username'])}</td><td>{esc(r['role'])}</td><td>{'Active' if r['active'] else 'Disabled'}</td></tr>"
        for r in staff_rows
    )
    case_table = "".join(
        f"<tr><td>{esc(r['case_number'])}</td><td>{esc(r['plaintiff_name'])}</td><td>{esc(r['defendant_name'])}</td><td>{esc(r['status'])}</td><td>{esc(r['updated_at'])}</td></tr>"
        for r in case_rows
    )
    audit_table = "".join(
        f"<tr><td>{esc(r['username'])}</td><td>{esc(r['action'])}</td><td>{esc(r['target'])}</td><td>{esc(r['created_at'])}</td></tr>"
        for r in audit_rows
    )
    body = f"""
    <section class="hero">
        <h1>🛡️ Super Admin</h1>
        <p><strong>Hello everyone, I like Kavee. 😈</strong></p>
        <p class="small">Full system overview for the authorized super administrator. Passwords and reset tokens are never displayed.</p>
    </section>
    <section class="grid">
        {''.join(f'<div class="card stat"><span class="stat-number">{value}</span>{label}</div>' for label, value in [("Staff Accounts", counts["staff"]),("Cases", counts["cases"]),("Hearings", counts["hearings"]),("Announcements", counts["notices"]),("Legal Resources", counts["laws"]),("Requirements", counts["requirements"]),("Audit Entries", counts["audit"])])}
    </section>
    <section class="card table-wrap">
        <h2 class="center">Registered Accounts</h2>
        <table><thead><tr><th>Username</th><th>Role</th><th>Status</th></tr></thead><tbody>{staff_table or '<tr><td colspan="3">None</td></tr>'}</tbody></table>
    </section>
    <section class="card table-wrap">
        <h2 class="center">Case Overview</h2>
        <table><thead><tr><th>Case Number</th><th>Plaintiff</th><th>Defendant</th><th>Status</th><th>Updated</th></tr></thead><tbody>{case_table or '<tr><td colspan="5">No cases</td></tr>'}</tbody></table>
    </section>
    <section class="card table-wrap">
        <h2 class="center">Recent Audit Activity</h2>
        <table><thead><tr><th>User</th><th>Action</th><th>Target</th><th>Time</th></tr></thead><tbody>{audit_table or '<tr><td colspan="4">No audit activity</td></tr>'}</tbody></table>
    </section>
    """
    return render_page("Super Admin", body, staff_page=True)

@app.route("/staff/accounts")
@admin_required
def staff_accounts():
    connection = db()
    if session.get("staff_role") == "superadmin":
        rows = connection.execute(
            "SELECT id, username, role, active FROM staff ORDER BY username"
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT id, username, role, active FROM staff WHERE lower(username) <> ? ORDER BY username",
            ("26-0054",),
        ).fetchall()
    connection.close()
    table = ""
    for row in rows:
        controls = (
            f"<form method='post' action='{url_for('toggle_staff', staff_id=row['id'])}' style='display:inline'>"
            f"<button type='submit'>{'Disable' if row['active'] else 'Enable'}</button>"
            f"</form>"
        )
        if row["username"].lower() not in {"admin", "26-0054"}:
            controls += (
                f" <form method='post' action='{url_for('delete_staff', staff_id=row['id'])}' style='display:inline'>"
                f"<button class='danger' type='submit' onclick=\"return confirm('Delete this account?')\">{tr('delete')}</button>"
                f"</form>"
            )
        table += f"""
        <tr>
            <td>{esc(row['username'])}</td>
            <td>{esc(row['role'])}</td>
            <td><span class="status">{'Active' if row['active'] else 'Disabled'}</span></td>
            <td>{controls}</td>
        </tr>
        """
    body = f"""
    <section class="card">
        <h1 class="center">👥 {tr('staff_accounts')}</h1>
        <form method="post" action="{url_for('add_staff')}" autocomplete="off">
            <label>{tr('email')}</label>
            <input type="email" name="email" required>
            <label>{tr('username')}</label>
            <input name="username" required>
            <label>{tr('password')}</label>
            <input type="password" name="password" minlength="8" required autocomplete="new-password">
            <label>Role</label>
            <select name="role"><option value="staff">Staff</option><option value="admin">Administrator</option></select>
            <button type="submit">{tr('add')}</button>
        </form>
    </section>
    <section class="card table-wrap">
        <table>
            <thead><tr><th>Username</th><th>Role</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>{table}</tbody>
        </table>
    </section>
    """
    return render_page(tr("staff_accounts"), body, staff_page=True)
@app.post("/staff/accounts/add")
@admin_required
def add_staff():
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "staff")
    if role not in {"staff", "admin"}:
        role = "staff"
    if not username or not email or not password:
        flash("Username, email and password are required.", "danger")
        return redirect(url_for("staff_accounts"))
    if len(password) < 8:
        flash("Password must contain at least 8 characters.", "danger")
        return redirect(url_for("staff_accounts"))
    connection = db()
    try:
        connection.execute(
            """
            INSERT INTO staff
            (username, email, password_hash, role, active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (
                username,
                email,
                generate_password_hash(password),
                role,
                now(),
            ),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        connection.close()
        flash("That username or email already exists.", "danger")
        return redirect(url_for("staff_accounts"))
    connection.close()
    audit("staff_created", username)
    flash("Staff account created successfully.", "success")
    return redirect(url_for("staff_accounts"))
@app.post("/staff/accounts/<int:staff_id>/toggle")
@admin_required
def toggle_staff(staff_id):
    connection = db()
    row = connection.execute(
        "SELECT username, active FROM staff WHERE id = ?",
        (staff_id,),
    ).fetchone()
    if row is None:
        connection.close()
        abort(404)
    if row["username"].lower() in {"admin", "26-0054"}:
        connection.close()
        flash("A protected administrator account cannot be disabled.", "danger")
        return redirect(url_for("staff_accounts"))
    connection.execute(
        "UPDATE staff SET active = ? WHERE id = ?",
        (0 if row["active"] else 1, staff_id),
    )
    connection.commit()
    connection.close()
    return redirect(url_for("staff_accounts"))
@app.post("/staff/accounts/<int:staff_id>/delete")
@admin_required
def delete_staff(staff_id):
    connection = db()
    row = connection.execute(
        "SELECT username FROM staff WHERE id = ?",
        (staff_id,),
    ).fetchone()
    if row is None:
        connection.close()
        abort(404)
    if row["username"].lower() in {"admin", "26-0054"}:
        connection.close()
        flash("A protected administrator account cannot be deleted.", "danger")
        return redirect(url_for("staff_accounts"))
    connection.execute(
        "DELETE FROM staff WHERE id = ?",
        (staff_id,),
    )
    connection.commit()
    connection.close()
    flash("Staff account deleted.", "success")
    return redirect(url_for("staff_accounts"))
@app.route("/language/<language>")
def change_language(language):
    if language not in T:
        language = "en"
    session["language"] = language
    return redirect(request.referrer or url_for("home"))
@app.route("/theme/<theme>")
def change_theme(theme):
    if theme not in {"light", "dark"}:
        theme = "light"
    session["theme"] = theme
    return redirect(request.referrer or url_for("home"))
@app.route("/health")
def health():
    return {"status": "ok", "service": COURT_NAME}
@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
@app.errorhandler(403)
def error_403(error):
    body = """
    <section class="card centered">
        <h1>403</h1>
        <h2>Access Denied</h2>
        <p>You do not have permission to access this page.</p>
        <a class="button" href="/">Home</a>
    </section>
    """
    return render_page("403", body, staff_page=bool(session.get("staff_logged_in"))), 403
@app.errorhandler(404)
def error_404(error):
    body = """
    <section class="card centered">
        <h1>404</h1>
        <h2>Page Not Found</h2>
        <p>The requested page could not be found.</p>
        <a class="button" href="/">Home</a>
    </section>
    """
    return render_page("404", body, staff_page=bool(session.get("staff_logged_in"))), 404
@app.errorhandler(413)
def error_413(error):
    body = """
    <section class="card centered">
        <h1>413</h1>
        <h2>File Too Large</h2>
        <p>The maximum upload size is 25 MB.</p>
        <a class="button" href="/">Home</a>
    </section>
    """
    return render_page("413", body, staff_page=bool(session.get("staff_logged_in"))), 413
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
    )
