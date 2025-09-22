#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask backend for TISS Auto-Anmelden Frontend
Integrates with the existing Selenium automation script
Now stores per-request configuration only in the database; no config.json usage
"""

from flask import Flask, render_template, render_template_string, request, jsonify, session, redirect, url_for
import json
import threading
import subprocess
import sys
import os
import re
from datetime import datetime
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import webbrowser

# Force UTF-8 encoding
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-me')

DB_PATH = os.path.join(os.path.dirname(__file__), 'app.db')
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
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            success INTEGER NOT NULL DEFAULT 0,
            config_json TEXT,
            scheduled_at TEXT,
            started_at TEXT,
            finished_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
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
            user_id INTEGER PRIMARY KEY,
            config_json TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
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
        template_path = os.path.join('templates', template_filename)
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
    if os.path.exists(os.path.join('templates', 'login.html')):
        return render_template('login.html')
    return "<h1>Login</h1><p>templates/login.html missing</p>"

@app.route('/auth/register', methods=['POST'])
def register():
    data = request.json or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required'}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO users(username, password_hash, created_at) VALUES (?, ?, ?)',
                    (username, generate_password_hash(password), datetime.utcnow().isoformat()))
        conn.commit()
        user_id = cur.lastrowid
        conn.close()
        session['user_id'] = user_id
        session['username'] = username
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Username already exists'}), 409

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
    row = cur.fetchone()
    conn.close()
    if not row or not check_password_hash(row['password_hash'], password):
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    session['user_id'] = row['id']
    session['username'] = username
    return jsonify({'success': True})

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
        
        if errors:
            return jsonify({'valid': False, 'errors': errors})
        
        return jsonify({'valid': True, 'message': 'Configuration is valid!'})
        
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})

@app.route('/api/requests', methods=['POST'])
def create_request():
    if not require_login():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        data = request.json or {}
        user_id = session['user_id']
        # Persist full request configuration JSON in DB (no filesystem writes)
        config_text = json.dumps(data, ensure_ascii=False)
        # Determine scheduled time from config ("anmelden_time"), default to now if not provided/invalid
        scheduled_at = None
        anmelden_time = (data or {}).get('anmelden_time')
        if anmelden_time:
            try:
                # Expecting format YYYY-MM-DD HH:MM:SS
                dt = datetime.strptime(anmelden_time, '%Y-%m-%d %H:%M:%S')
                scheduled_at = dt.isoformat()
            except Exception:
                scheduled_at = None
        conn = get_db_connection()
        cur = conn.cursor()
        now = datetime.utcnow().isoformat()
        cur.execute('INSERT INTO requests(user_id, status, message, success, config_json, scheduled_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (user_id, 'queued', 'Queued', 0, config_text, scheduled_at, now, now))
        conn.commit()
        req_id = cur.lastrowid
        conn.close()
        return jsonify({'success': True, 'request_id': req_id})
    except Exception as e:
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
        return jsonify({'success': False, 'message': 'Not found'}), 404
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
        return jsonify({'success': False, 'message': 'Not found'}), 404
    status = row['status']
    # If already finished, nothing to do
    if status in ('completed', 'failed', 'cancelled'):
        conn.close()
        return jsonify({'success': True, 'message': 'Already finished'})
    # If queued, mark as cancelled immediately and return
    if status == 'queued':
        cur.execute("UPDATE requests SET status = 'cancelled', message = ?, success = 0, finished_at = ?, updated_at = ? WHERE id = ?",
                    ('Cancelled before start', datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), req_id))
        conn.commit()
        conn.close()
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
                now_iso = datetime.utcnow().isoformat()
                conn_s = get_db_connection()
                conn_s.row_factory = sqlite3.Row
                cur_s = conn_s.cursor()
                # Select candidates that are due. NULL scheduled_at means run ASAP.
                cur_s.execute(
                    """
                    SELECT id, config_json FROM requests
                    WHERE status = 'queued' AND (
                        scheduled_at IS NULL OR scheduled_at <= ?
                    )
                    ORDER BY created_at ASC
                    LIMIT 3
                    """,
                    (now_iso,)
                )
                candidates = cur_s.fetchall()
                conn_s.close()
                for row in candidates:
                    request_id = row['id']
                    config_json = row['config_json'] or '{}'
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
                        continue
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
                        try:
                            env = os.environ.copy()
                            env['PYTHONIOENCODING'] = 'utf-8'
                            # Start process with Popen so it can be cancelled
                            proc = subprocess.Popen(
                                [sys.executable, 'tiss_auto_anmelden.py', '--config', '-'],
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
                            # Determine if it was cancelled
                            conn_chk = get_db_connection()
                            cur_chk = conn_chk.cursor()
                            cur_chk.execute('SELECT status FROM requests WHERE id = ?', (req_id,))
                            row_chk = cur_chk.fetchone()
                            conn_chk.close()
                            if row_chk and row_chk['status'] in ('cancelling', 'cancelled'):
                                update('cancelled', 'Request was cancelled by user', 0, finished=True)
                                return
                            if proc.returncode == 0:
                                update('completed', 'Registration completed successfully!', 1, finished=True)
                            else:
                                truncated_err = (stderr or '')[:4000]
                                update('failed', f'Script failed: {truncated_err}', 0, finished=True)
                        except subprocess.TimeoutExpired:
                            update('failed', 'Script timed out (10 minutes)', 0, finished=True)
                        except Exception as e:
                            update('failed', f'Error running script: {str(e)}', 0, finished=True)
                    t = threading.Thread(target=worker, args=(request_id, config_json))
                    t.daemon = True
                    t.start()
            except Exception:
                pass
            finally:
                # Polling interval
                threading.Event().wait(2.0)

    threading.Thread(target=scheduler_loop, daemon=True).start()
    print("🚀 Starting TISS Auto-Anmelden Frontend Server...")
    print("📂 Make sure to:")
    print("   1. Save the HTML frontend as 'templates/index.html'")
    print("   2. Have 'tiss_auto_anmelden.py' in the same directory")
    print("   3. Install required packages: pip install flask selenium")
    
    # No longer loading config.json; forms start empty unless populated client-side
    
    print("\n🌐 Opening browser at http://127.0.0.1:5000")
    
    # Open browser after a short delay
    threading.Timer(1.5, open_browser).start()
    
    # Run Flask app
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)