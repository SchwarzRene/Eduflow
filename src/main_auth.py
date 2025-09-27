#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask backend for TISS Auto-Anmelden Frontend
Integrates with the existing Selenium automation script
Now stores per-request configuration only in the database; no config.json usage
"""

from flask import Flask, render_template, render_template_string, request, jsonify, session, redirect, url_for
import requests
import json
import threading
import subprocess
import sys
import os
import re
from datetime import datetime, timezone, timedelta
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import webbrowser
from typing import Optional
import logging
from logging.handlers import RotatingFileHandler

try:
    # Provides inline execution when packaged to a single .exe (no Python available for subprocess)
    from tiss_auto_login import run_with_config as automation_run_with_config
except Exception:
    automation_run_with_config = None

def compute_course_url(config: dict) -> str:
    """Construct the TISS course URL from configuration data"""
    mode = (config.get("mode", "exam") or "exam").lower()
    if mode == "group":
        path = "groupList.xhtml"
    elif mode == "course":
        path = "courseRegistration.xhtml"
    else:
        path = "examDateList.xhtml"
    return (
        f"https://tiss.tuwien.ac.at/education/course/{path}"
        f"?dswid={config['dswid']}&dsrid={config['dsrid']}"
        f"&semester={config['semester']}&courseNr={config['courseNr']}"
    )

def validate_url_accessibility(url: str, timeout: int = 10) -> tuple[bool, str]:
    """
    Validate if a URL is accessible by making an HTTP request.
    Returns (is_valid, error_message)
    """
    try:
        response = requests.get(url, timeout=timeout, allow_redirects=True)
        if response.status_code == 200:
            return True, ""
        else:
            return False, f"URL returned status code {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection failed - URL may be unreachable"
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

# Force UTF-8 encoding on Windows without touching low-level buffers
if sys.platform.startswith('win'):
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='strict')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='strict')
    except Exception:
        # Best-effort; ignore if the stream cannot be reconfigured in this environment
        pass

def get_base_dir() -> str:
    """Return directory where resources (templates/static) live in both dev and frozen modes."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS  # type: ignore[attr-defined]
    # Go up one directory from src/ to project root
    return os.path.dirname(os.path.dirname(__file__))


BASE_DIR = get_base_dir()

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-me')

# -------------------------
# Logging setup
# -------------------------
def setup_logging():
    try:
        logs_dir = os.path.join(get_data_dir(), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        log_path = os.path.join(logs_dir, 'backend.log')
        file_handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
        file_handler.setFormatter(formatter)

        logger = logging.getLogger('agl.backend')
        logger.setLevel(logging.INFO)
        if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
            logger.addHandler(file_handler)

        # Also attach to Flask app logger
        app.logger.setLevel(logging.INFO)
        if not any(isinstance(h, RotatingFileHandler) for h in app.logger.handlers):
            app.logger.addHandler(file_handler)
    except Exception:
        # Do not fail app if logging cannot be configured
        pass

setup_logging()
logger = logging.getLogger('agl.backend')

def get_data_dir() -> str:
    """Return a writable per-user data directory for the database when frozen or running locally."""
    try:
        if sys.platform.startswith('win'):
            local_appdata = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
            data_dir = os.path.join(local_appdata, 'AutoGroupLogin')
        else:
            data_dir = os.path.join(os.path.expanduser('~'), '.autogrouplogin')
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
    except Exception:
        # Fallback to current directory
        return os.path.dirname(__file__)


DB_PATH = os.path.join(get_data_dir(), 'app.db')
RUNNING_PROCESSES = {}
RUNNING_LOCK = threading.Lock()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            success INTEGER NOT NULL DEFAULT 0,
            config_json TEXT,
            scheduled_at TEXT,
            started_at TEXT,
            finished_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(username)
        )
        """
    )
    # Lightweight migrations for existing DBs: add missing columns if needed
    cur.execute('PRAGMA table_info(requests)')
    cols = {row[1] for row in cur.fetchall()}
    if 'scheduled_at' not in cols:
        cur.execute('ALTER TABLE requests ADD COLUMN scheduled_at TEXT')
    if 'started_at' not in cols:
        cur.execute('ALTER TABLE requests ADD COLUMN started_at TEXT')
    if 'finished_at' not in cols:
        cur.execute('ALTER TABLE requests ADD COLUMN finished_at TEXT')
    if 'config_json' not in cols:
        cur.execute('ALTER TABLE requests ADD COLUMN config_json TEXT')
    # User config storage
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_configs (
            user_id TEXT PRIMARY KEY,
            config_json TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(username)
        )
        """
    )
    
    # Lightweight migrations for existing DBs: ensure user_id columns are TEXT (store username)
    try:
        # requests.user_id type check and migrate if needed
        cur.execute('PRAGMA table_info(requests)')
        req_cols = cur.fetchall()
        req_user_id_col = next((c for c in req_cols if c[1] == 'user_id'), None)
        if req_user_id_col is not None and (req_user_id_col[2] or '').upper() != 'TEXT':
            # Rebuild table with TEXT user_id
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS requests__new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    success INTEGER NOT NULL DEFAULT 0,
                    config_json TEXT,
                    scheduled_at TEXT,
                    started_at TEXT,
                    finished_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                INSERT INTO requests__new (id, user_id, status, message, success, config_json, scheduled_at, started_at, finished_at, created_at, updated_at)
                SELECT id, CAST(user_id AS TEXT), status, message, success, config_json, scheduled_at, started_at, finished_at, created_at, updated_at FROM requests
                """
            )
            cur.execute('DROP TABLE requests')
            cur.execute('ALTER TABLE requests__new RENAME TO requests')
        
        # user_configs.user_id type check and migrate if needed
        cur.execute('PRAGMA table_info(user_configs)')
        uc_cols = cur.fetchall()
        uc_user_id_col = next((c for c in uc_cols if c[1] == 'user_id'), None)
        if uc_user_id_col is not None and (uc_user_id_col[2] or '').upper() != 'TEXT':
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_configs__new (
                    user_id TEXT PRIMARY KEY,
                    config_json TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                INSERT INTO user_configs__new (user_id, config_json, updated_at)
                SELECT CAST(user_id AS TEXT), config_json, updated_at FROM user_configs
                """
            )
            cur.execute('DROP TABLE user_configs')
            cur.execute('ALTER TABLE user_configs__new RENAME TO user_configs')
        conn.commit()
    except Exception:
        # Migration is best-effort; continue if not possible
        pass
    conn.commit()
    conn.close()

# Global variable to track script status
script_status = {
    'running': False,
    'message': '',
    'success': False
}

def load_existing_config():
    """Deprecated: Previously loaded configuration from config.json. Now returns empty."""
    return {}

def require_login():
    if not session.get('user_id'):
        return False
    return True

@app.before_request
def _log_request_start():
    try:
        logger.info(f"incoming {request.method} {request.path} from {request.remote_addr}")
    except Exception:
        pass

@app.after_request
def _log_request_end(response):
    try:
        logger.info(f"completed {request.method} {request.path} -> {response.status_code}")
    except Exception:
        pass
    return response

@app.route('/')
def index():
    if not require_login():
        return redirect(url_for('login_page'))
    return redirect(url_for('generate_page'))

def render_with_config(template_filename: str):
    try:
        session_username = session.get('username') or ''
        # Try to load user's saved config to inject into page
        existing_config = {}
        try:
            if session.get('user_id'):
                conn_cfg = get_db_connection()
                cur_cfg = conn_cfg.cursor()
                cur_cfg.execute('SELECT config_json FROM user_configs WHERE user_id = ?', (session['user_id'],))
                row_cfg = cur_cfg.fetchone()
                conn_cfg.close()
                if row_cfg and row_cfg[0]:
                    existing_config = json.loads(row_cfg[0])
        except Exception:
            existing_config = {}
        template_path = os.path.join(BASE_DIR, 'templates', template_filename)
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            config_script = f"""
            <script>
                window.EXISTING_CONFIG = {json.dumps(existing_config, ensure_ascii=False)};
                window.SESSION_USER = {json.dumps(session_username)};
            </script>
            """
            html_content = html_content.replace('</head>', config_script + '</head>')
            return html_content
        return f"Template {template_filename} not found."
    except Exception as e:
        return f"Error loading template: {str(e)}"

@app.route('/generate')
def generate_page():
    if not require_login():
        return redirect(url_for('login_page'))
    return render_with_config('generate.html')

@app.route('/requests')
def requests_page():
    if not require_login():
        return redirect(url_for('login_page'))
    return render_with_config('requests.html')

@app.route('/login', methods=['GET'])
def login_page():
    if session.get('user_id'):
        return redirect(url_for('index'))
    if os.path.exists(os.path.join(BASE_DIR, 'templates', 'login.html')):
        return render_template('login.html')
    return "<h1>Login</h1><p>templates/login.html missing</p>"

@app.route('/auth/register', methods=['POST'])
def register():
    """Forward registration to remote auth server if configured."""
    data = request.json or {}
    auth_base = os.environ.get('AUTH_SERVER_BASE', 'http://127.0.0.1:7000')
    try:
        logger.info("auth.register forwarding request")
        resp = requests.post(auth_base + '/auth/register', json={
            'username': data.get('username'),
            'password': data.get('password')
        }, timeout=10)
        logger.info(f"auth.register response status={resp.status_code}")
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        logger.exception(f"auth.register failed: {e}")
        return jsonify({'success': False, 'message': f'Auth server error: {e}'}), 502

@app.route('/auth/login', methods=['POST'])
def login():
    """Validate against remote server, store token in session if valid."""
    data = request.json or {}
    auth_base = os.environ.get('AUTH_SERVER_BASE', 'http://127.0.0.1:7000')
    try:
        logger.info("auth.login forwarding request")
        resp = requests.post(auth_base + '/auth/login', json={
            'username': data.get('username'),
            'password': data.get('password')
        }, timeout=10)
        payload = resp.json()
        if resp.status_code == 200 and payload.get('success'):
            session['user_id'] = payload.get('username')
            session['username'] = payload.get('username')
            session['access_token'] = payload.get('access_token')
            logger.info(f"auth.login success for user={session['username']}")
            return jsonify({'success': True})
        logger.warning(f"auth.login failed status={resp.status_code} body={payload}")
        return jsonify(payload), resp.status_code
    except Exception as e:
        logger.exception(f"auth.login error: {e}")
        return jsonify({'success': False, 'message': f'Auth server error: {e}'}), 502

@app.route('/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/validate', methods=['POST'])
def validate_config():
    """Validate the configuration data"""
    try:
        data = request.json
        errors = {}
        logger.info("validate_config called")
        
        # Required fields validation
        required_fields = ['username', 'password', 'dswid', 'dsrid', 'semester', 'courseNr', 'group_index']
        
        for field in required_fields:
            value = data.get(field)
            # Treat 0 as valid for numeric fields; only empty string or None are missing
            if value is None or (isinstance(value, str) and value.strip() == ''):
                errors[field] = f"{field} is required"
        
        # Semester format validation
        semester = data.get('semester', '')
        if semester and not re.match(r'^\d{4}[SW]$', semester):
            errors['semester'] = 'Format should be YYYYS or YYYYW'
        
        # Study number format validation
        study_number = data.get('study_number', '')
        if study_number and not re.match(r'^\d{3}\s\d{3}$', study_number):
            errors['study_number'] = 'Format should be "123 456" (with space)'
        
        # Group index validation
        try:
            group_index = int(data.get('group_index', 0))
            if group_index < 0:
                errors['group_index'] = 'Must be non-negative'
        except (ValueError, TypeError):
            errors['group_index'] = 'Must be a number'
        
        # Slot index validation
        slot_index = data.get('slot_index')
        if slot_index is not None and slot_index != '':
            try:
                slot_idx = int(slot_index)
                if slot_idx < 0:
                    errors['slot_index'] = 'Must be non-negative'
            except (ValueError, TypeError):
                errors['slot_index'] = 'Must be a number'
        
        # URL accessibility validation
        if not errors:  # Only validate URL if basic validation passed
            try:
                course_url = compute_course_url(data)
                logger.info(f"validate_config testing URL: {course_url}")
                is_valid, error_msg = validate_url_accessibility(course_url)
                if not is_valid:
                    errors['url'] = f"Course URL is not accessible: {error_msg}"
                    logger.warning(f"validate_config URL validation failed: {error_msg}")
                else:
                    logger.info("validate_config URL validation passed")
            except Exception as e:
                errors['url'] = f"Failed to construct or validate URL: {str(e)}"
                logger.error(f"validate_config URL construction error: {e}")
        
        if errors:
            logger.info(f"validate_config invalid errors={errors}")
            return jsonify({'valid': False, 'errors': errors})
        logger.info("validate_config ok")
        return jsonify({'valid': True, 'message': 'Configuration is valid!'})
        
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})

@app.route('/api/requests', methods=['POST'])
def create_request():
    if not require_login():
        logger.warning("create_request unauthorized")
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        data = request.json or {}
        user_id = session['user_id']
        # Persist full request configuration JSON in DB (no filesystem writes)
        config_text = json.dumps(data, ensure_ascii=False)
        # Determine start time from config ("anmelden_time"), default to now if not provided/invalid
        # We start the script 10 seconds before the user's scheduled time
        scheduled_at = None
        anmelden_time = (data or {}).get('anmelden_time')
        if anmelden_time:
            try:
                # Expecting format YYYY-MM-DD HH:MM:SS
                local_naive = datetime.strptime(anmelden_time, '%Y-%m-%d %H:%M:%S')
                
                # Calculate start time: 10 seconds before user's scheduled time
                start_time_local = local_naive - timedelta(seconds=10)
                
                # Check if the start time is in the past
                now_local = datetime.now()
                if start_time_local < now_local:
                    # If start time is in the past, set to None so it runs immediately
                    scheduled_at = None
                    logger.info(f"create_request user_time={anmelden_time} start_time_local={start_time_local} is in past, setting scheduled_at=None")
                else:
                    # Assume provided time is in local timezone, convert to UTC for storage/comparison
                    local_tz = datetime.now().astimezone().tzinfo
                    start_time_aware = start_time_local.replace(tzinfo=local_tz)
                    utc_dt = start_time_aware.astimezone(timezone.utc)
                    scheduled_at = utc_dt.isoformat()
                    logger.info(f"create_request user_time={anmelden_time} start_time_local={start_time_local} stored_utc={scheduled_at}")
            except Exception as e:
                logger.warning(f"create_request error parsing anmelden_time '{anmelden_time}': {e}")
                scheduled_at = None
        conn = get_db_connection()
        cur = conn.cursor()
        now = datetime.utcnow().isoformat()
        cur.execute('INSERT INTO requests(user_id, status, message, success, config_json, scheduled_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (user_id, 'queued', 'Queued', 0, config_text, scheduled_at, now, now))
        conn.commit()
        req_id = cur.lastrowid
        conn.close()
        logger.info(f"request created id={req_id} user={user_id} scheduled_at={scheduled_at}")
        return jsonify({'success': True, 'request_id': req_id})
    except Exception as e:
        logger.exception(f"create_request failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/requests/<int:req_id>', methods=['GET'])
def get_request_status(req_id: int):
    if not require_login():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, user_id, status, message, success, created_at, updated_at FROM requests WHERE id = ?', (req_id,))
    row = cur.fetchone()
    conn.close()
    if not row or row['user_id'] != session['user_id']:
        logger.warning(f"get_request_status not found id={req_id}")
        return jsonify({'success': False, 'message': 'Not found'}), 404
    logger.info(f"get_request_status id={req_id} status={row['status']}")
    return jsonify({'success': True, 'request': {
        'id': row['id'],
        'status': row['status'],
        'message': row['message'],
        'success': bool(row['success']),
        'created_at': row['created_at'],
        'updated_at': row['updated_at']
    }})

@app.route('/api/requests/<int:req_id>/cancel', methods=['POST'])
def cancel_request(req_id: int):
    if not require_login():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    # Ensure the request belongs to the user and is cancellable
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, user_id, status FROM requests WHERE id = ?', (req_id,))
    row = cur.fetchone()
    if not row or row['user_id'] != session['user_id']:
        conn.close()
        logger.warning(f"cancel_request not found id={req_id}")
        return jsonify({'success': False, 'message': 'Not found'}), 404
    status = row['status']
    # If already finished, nothing to do
    if status in ('completed', 'failed', 'cancelled'):
        conn.close()
        logger.info(f"cancel_request already finished id={req_id} status={status}")
        return jsonify({'success': True, 'message': 'Already finished'})
    # If queued, mark as cancelled immediately and return
    if status == 'queued':
        cur.execute("UPDATE requests SET status = 'cancelled', message = ?, success = 0, finished_at = ?, updated_at = ? WHERE id = ?",
                    ('Cancelled before start', datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), req_id))
        conn.commit()
        conn.close()
        logger.info(f"cancel_request cancelled queued id={req_id}")
        return jsonify({'success': True, 'message': 'Cancelled'})
    # Otherwise mark as cancelled-final and try to terminate running process
    cur.execute("UPDATE requests SET status = 'cancelled', message = ?, success = 0, finished_at = ?, updated_at = ? WHERE id = ?",
                ('Cancelled by user', datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), req_id))
    conn.commit()
    conn.close()
    # Try to terminate running process
    with RUNNING_LOCK:
        proc = RUNNING_PROCESSES.get(req_id)
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            logger.info(f"cancel_request terminate sent id={req_id}")
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    return jsonify({'success': True, 'message': 'Cancellation requested'})

@app.route('/api/requests', methods=['GET'])
def list_requests():
    if not require_login():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, status, message, success, created_at, updated_at FROM requests WHERE user_id = ? AND status NOT IN ("cancelled","cancelling") ORDER BY id DESC LIMIT 20', (session['user_id'],))
    rows = cur.fetchall()
    conn.close()
    logger.info(f"list_requests count={len(rows)}")
    return jsonify({'success': True, 'requests': [
        {
            'id': r['id'],
            'status': r['status'],
            'message': r['message'],
            'success': bool(r['success']),
            'created_at': r['created_at'],
            'updated_at': r['updated_at']
        } for r in rows
    ]})

# User configuration persistence endpoints
@app.route('/api/user_config', methods=['GET'])
def get_user_config():
    if not require_login():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT config_json FROM user_configs WHERE user_id = ?', (session['user_id'],))
    row = cur.fetchone()
    conn.close()
    if not row or not row[0]:
        return jsonify({'success': True, 'config': {}})
    try:
        cfg = json.loads(row[0])
    except Exception:
        cfg = {}
    return jsonify({'success': True, 'config': cfg})

@app.route('/api/user_config', methods=['POST'])
def save_user_config():
    if not require_login():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        data = request.json or {}
        conn = get_db_connection()
        cur = conn.cursor()
        now = datetime.utcnow().isoformat()
        cur.execute('INSERT INTO user_configs(user_id, config_json, updated_at) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET config_json=excluded.config_json, updated_at=excluded.updated_at',
                    (session['user_id'], json.dumps(data, ensure_ascii=False), now))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

def open_browser():
    """Open the browser automatically"""
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    init_db()
    # Start background scheduler to process due requests
    def scheduler_loop():
        while True:
            try:
                now_utc = datetime.utcnow()
                now_iso = now_utc.isoformat()
                conn_s = get_db_connection()
                conn_s.row_factory = sqlite3.Row
                cur_s = conn_s.cursor()
                # Select candidates that should be started now.
                # NULL scheduled_at means run ASAP.
                # For scheduled requests, we start 10 seconds before the scheduled time
                cur_s.execute(
                    """
                    SELECT id, config_json, scheduled_at FROM requests
                    WHERE status = 'queued' AND (
                        scheduled_at IS NULL OR scheduled_at <= ?
                    )
                    ORDER BY created_at ASC
                    LIMIT 10
                    """,
                    (now_iso,)
                )
                logger.info(f"scheduler: querying for requests with scheduled_at <= {now_iso}")
                candidates = cur_s.fetchall()
                conn_s.close()
                if candidates:
                    logger.info(f"scheduler: found {len(candidates)} candidate(s)")
                for row in candidates:
                    request_id = row['id']
                    config_json = row['config_json'] or '{}'
                    scheduled_at_str = row['scheduled_at']
                    
                    # The scheduled_at in the database is already the start time (10 seconds before user's time)
                    # So if it's in the database and <= now, it's time to start
                    logger.info(f"scheduler: processing request id={request_id} scheduled_at={scheduled_at_str}")
                    
                    # Parse config to show user's original time for debugging
                    try:
                        config_obj = json.loads(config_json)
                        anmelden_time = config_obj.get('anmelden_time')
                        logger.info(f"scheduler: request id={request_id} user_time={anmelden_time} start_time_db={scheduled_at_str}")
                    except Exception as e:
                        logger.warning(f"scheduler: could not parse config for id={request_id}: {e}")
                    
                    # Try to atomically claim the job
                    conn_c = get_db_connection()
                    cur_c = conn_c.cursor()
                    cur_c.execute(
                        "UPDATE requests SET status = 'running', message = ?, started_at = ?, updated_at = ? WHERE id = ? AND status = 'queued'",
                        ('Starting automation...', datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), request_id)
                    )
                    conn_c.commit()
                    claimed = cur_c.rowcount
                    conn_c.close()
                    if not claimed:
                        logger.info(f"scheduler: could not claim id={request_id}")
                        continue
                    logger.info(f"scheduler: claimed id={request_id}, starting worker")

                    def worker(req_id: int, cfg_json: str):
                        def update(status: str, message: str, success: int = 0, finished: bool = False):
                            conn_u = get_db_connection()
                            finished_at = datetime.utcnow().isoformat() if finished else None
                            if finished:
                                conn_u.execute('UPDATE requests SET status = ?, message = ?, success = ?, finished_at = ?, updated_at = ? WHERE id = ?',
                                               (status, message, success, finished_at, datetime.utcnow().isoformat(), req_id))
                            else:
                                conn_u.execute('UPDATE requests SET status = ?, message = ?, success = ?, updated_at = ? WHERE id = ?',
                                               (status, message, success, datetime.utcnow().isoformat(), req_id))
                            conn_u.commit()
                            conn_u.close()
                            logger.info(f"worker[{req_id}] update status={status} success={success}")
                        try:
                            if automation_run_with_config:
                                # Run inline when packaged; cannot rely on launching python child
                                cfg_obj = json.loads(cfg_json or '{}')
                                automation_run_with_config(cfg_obj)
                                update('completed', 'Registration completed successfully!', 1, finished=True)
                                logger.info(f"worker[{req_id}] inline completed")
                                return
                            env = os.environ.copy()
                            env['PYTHONIOENCODING'] = 'utf-8'
                            # Start process with Popen so it can be cancelled
                            proc = subprocess.Popen(
                                [sys.executable, 'tiss_auto_login.py', '--config', '-'],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                encoding='utf-8',
                                env=env
                            )
                            with RUNNING_LOCK:
                                RUNNING_PROCESSES[req_id] = proc
                            try:
                                stdout, stderr = proc.communicate(input=cfg_json, timeout=600)
                            except subprocess.TimeoutExpired:
                                proc.kill()
                                stdout, stderr = proc.communicate()
                            finally:
                                with RUNNING_LOCK:
                                    RUNNING_PROCESSES.pop(req_id, None)
                            try:
                                if stdout:
                                    logger.info(f"worker[{req_id}] stdout:\n{stdout[:2000]}")
                                if stderr:
                                    logger.warning(f"worker[{req_id}] stderr:\n{stderr[:2000]}")
                            except Exception:
                                pass
                            # Determine if it was cancelled
                            conn_chk = get_db_connection()
                            cur_chk = conn_chk.cursor()
                            cur_chk.execute('SELECT status FROM requests WHERE id = ?', (req_id,))
                            row_chk = cur_chk.fetchone()
                            conn_chk.close()
                            if row_chk and row_chk['status'] in ('cancelling', 'cancelled'):
                                update('cancelled', 'Request was cancelled by user', 0, finished=True)
                                logger.info(f"worker[{req_id}] cancelled after run")
                                return
                            if proc.returncode == 0:
                                update('completed', 'Registration completed successfully!', 1, finished=True)
                                logger.info(f"worker[{req_id}] completed returncode=0")
                            else:
                                truncated_err = (stderr or '')[:4000]
                                update('failed', f'Script failed: {truncated_err}', 0, finished=True)
                                logger.error(f"worker[{req_id}] failed returncode={proc.returncode}")
                        except subprocess.TimeoutExpired:
                            update('failed', 'Script timed out (10 minutes)', 0, finished=True)
                            logger.error(f"worker[{req_id}] timeout")
                        except Exception as e:
                            update('failed', f'Error running script: {str(e)}', 0, finished=True)
                            logger.exception(f"worker[{req_id}] error: {e}")
                    t = threading.Thread(target=worker, args=(request_id, config_json))
                    t.daemon = True
                    t.start()
            except Exception:
                logger.exception("scheduler loop error")
            finally:
                # Polling interval
                threading.Event().wait(2.0)

    threading.Thread(target=scheduler_loop, daemon=True).start()
    print("🚀 Starting TISS Auto-Anmelden Frontend Server...")
    print("📂 Make sure to:")
    print("   1. Save the HTML frontend as 'templates/index.html'")
    print("   2. Have 'tiss_auto_login.py' in the same directory")
    print("   3. Install required packages: pip install flask selenium")
    
    # No longer loading config.json; forms start empty unless populated client-side
    
    print("\n🌐 Opening browser at http://127.0.0.1:5000")
    
    # Open browser after a short delay
    threading.Timer(1.5, open_browser).start()
    
    # Run Flask app
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)