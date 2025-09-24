#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Authentication Server
 - Stores users in a separate SQLite DB
 - Provides JWT-based login/register endpoints
"""

from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3
from datetime import datetime, timedelta, timezone
import jwt
import logging
from logging.handlers import RotatingFileHandler


def get_db_path() -> str:
    base_dir = os.path.dirname(__file__)
    return os.path.join(base_dir, 'auth.db')


def get_db_connection():
    # Use a small timeout and WAL to reduce 'database is locked' errors under concurrent access
    conn = sqlite3.connect(get_db_path(), timeout=5.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        # Apply per-connection pragmas; safe to call each time
        conn.execute('PRAGMA busy_timeout = 5000')
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA synchronous = NORMAL')
    except Exception:
        pass
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
    # Ensure WAL is enabled at database-level as well
    try:
        cur.execute('PRAGMA journal_mode = WAL')
        cur.execute('PRAGMA synchronous = NORMAL')
        cur.execute('PRAGMA busy_timeout = 5000')
    except Exception:
        pass
    conn.commit()
    conn.close()


JWT_SECRET = os.environ.get('AUTH_JWT_SECRET', 'change-me-in-prod')
JWT_ALGO = 'HS256'
JWT_EXPIRES_MIN = int(os.environ.get('AUTH_JWT_EXPIRES_MIN', '1440'))


app = Flask(__name__)

# -------------------------
# Logging setup
# -------------------------
def setup_logging():
    try:
        base_dir = os.path.dirname(__file__)
        logs_dir = os.path.join(base_dir, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        log_path = os.path.join(logs_dir, 'auth.log')
        file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
        file_handler.setFormatter(formatter)

        logger = logging.getLogger('agl.auth')
        logger.setLevel(logging.INFO)
        if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
            logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        if not any(isinstance(h, RotatingFileHandler) for h in app.logger.handlers):
            app.logger.addHandler(file_handler)
    except Exception:
        pass

setup_logging()
logger = logging.getLogger('agl.auth')


@app.route('/auth/register', methods=['POST'])
def register():
    data = request.json or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        logger.info("/auth/register missing fields")
        return jsonify({'success': False, 'message': 'Username and password are required'}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO users(username, password_hash, created_at) VALUES (?, ?, ?)',
                    (username, generate_password_hash(password), datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
        logger.info(f"/auth/register success username={username}")
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        logger.warning(f"/auth/register duplicate username={username}")
        return jsonify({'success': False, 'message': 'Username already exists'}), 409


def issue_token(username: str) -> str:
    payload = {
        'sub': username,
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRES_MIN),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    logger.info(f"/auth/login attempt username={username}")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
    row = cur.fetchone()
    conn.close()
    if not row or not check_password_hash(row['password_hash'], password):
        logger.warning(f"/auth/login invalid username={username}")
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    token = issue_token(username)
    logger.info(f"/auth/login success username={username}")
    return jsonify({'success': True, 'access_token': token, 'username': username})


@app.route('/auth/validate', methods=['POST'])
def validate():
    data = request.json or {}
    token = data.get('access_token') or ''
    if not token:
        logger.info("/auth/validate missing token")
        return jsonify({'success': False, 'message': 'Missing token'}), 400
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        logger.info(f"/auth/validate ok username={decoded.get('sub')}")
        return jsonify({'success': True, 'username': decoded.get('sub')})
    except jwt.ExpiredSignatureError:
        logger.info("/auth/validate expired")
        return jsonify({'success': False, 'message': 'Token expired'}), 401
    except Exception:
        logger.info("/auth/validate invalid")
        return jsonify({'success': False, 'message': 'Invalid token'}), 401


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', '7000'))
    print(f"Auth server running on http://127.0.0.1:{port}")
    app.run(host='127.0.0.1', port=port, debug=False)


