import os
import random
import string
import time
import hashlib
import sqlite3
from flask import Flask, render_template, request, session, jsonify, Response

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'flaxxi-secure-production-secret-key-999')

ADMIN_USER = "FLAXXI"
ADMIN_PASS = "FLAXXI@123"

DB_FILE = "database.db"
RUNTIME_FILE = "runtime.apk"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            id TEXT PRIMARY KEY,
            label TEXT,
            key TEXT UNIQUE,
            revoked INTEGER,
            expires INTEGER,
            devices INTEGER,
            device_limit INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Video ke steps (runtime preparation & verification) ko pass karne ke liye robust APK placeholder structure
if not os.path.exists(RUNTIME_FILE):
    with open(RUNTIME_FILE, "wb") as f:
        f.write(b"PK\x03\x04" + b"\x00" * 32768 + b"KURO_LOADER_EXPLICIT_CUSTOM_RUNTIME_PAYLOAD_V1.8")

def get_file_stats():
    if os.path.exists(RUNTIME_FILE):
        size = os.path.getsize(RUNTIME_FILE)
        with open(RUNTIME_FILE, "rb") as f:
            data = f.read()
            sha = hashlib.sha256(data).hexdigest()
            md5 = hashlib.md5(data).hexdigest()
        return size, sha, md5
    return 32820, "", ""

@app.route('/')
def index():
    return render_template('index.html')

def get_runtime_payload(base_url):
    size, sha, md5 = get_file_stats()
    return {
        "version": "1.8",
        "latestVersion": "1.8",
        "tag_name": "1.8",
        "name": "Kuro Runtime 1.8",
        "published": True,
        "isPublished": True,
        "status": "published",
        "active": True,
        "enabled": True,
        "verified": True,
        "valid": True,
        "skip_verification": True,
        "ignore_hash": True,
        "bypass_check": True,
        "hasUpdate": False,
        "isUpdateAvailable": False,
        "url": f"{base_url}/download/runtime.apk",
        "download_url": f"{base_url}/download/runtime.apk",
        "browser_download_url": f"{base_url}/download/runtime.apk",
        "size": size,
        "file_size": size,
        "content_length": size,
        "sha256": sha,
        "hash": sha,
        "checksum": sha,
        "md5": md5,
        "assets": [
            {
                "name": "runtime.apk",
                "size": size,
                "sha256": sha,
                "browser_download_url": f"{base_url}/download/runtime.apk"
            }
        ]
    }

@app.route('/api/runtime', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/runtimes', methods=['GET', 'POST', 'OPTIONS'])
def api_runtime():
    base_url = request.host_url.rstrip('/')
    return jsonify([get_runtime_payload(base_url)])

@app.route('/api/diagnostics', methods=['GET', 'POST', 'OPTIONS'])
def api_diagnostics():
    base_url = request.host_url.rstrip('/')
    item = get_runtime_payload(base_url)
    return jsonify({
        "success": True,
        "published": True,
        "isPublished": True,
        "status": "published",
        "version": "1.8",
        "latestVersion": "1.8",
        "verified": True,
        "valid": True,
        "skip_verification": True,
        "ignore_hash": True,
        "bypass_check": True,
        "hasUpdate": False,
        "isUpdateAvailable": False,
        "url": item["url"],
        "download_url": item["download_url"],
        "size": item["size"],
        "sha256": item["sha256"],
        "KuroRuntime": [item],
        "runtime": item,
        "runtimes": [item],
        "data": item
    })

@app.route('/api/releases', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/version', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/update', methods=['GET', 'POST', 'OPTIONS'])
def api_releases_endpoint():
    return api_diagnostics()

@app.route('/download/runtime.apk', methods=['GET', 'HEAD', 'OPTIONS'])
def download_runtime():
    if not os.path.exists(RUNTIME_FILE):
        return jsonify({"error": "File not found"}), 404
        
    size, _, _ = get_file_stats()
    
    if request.method == 'HEAD':
        resp = Response()
        resp.headers['Content-Length'] = str(size)
        resp.headers['Content-Type'] = 'application/vnd.android.package-archive'
        resp.headers['Accept-Ranges'] = 'bytes'
        return resp

    with open(RUNTIME_FILE, "rb") as f:
        file_data = f.read()

    return Response(
        file_data,
        mimetype='application/vnd.android.package-archive',
        headers={
            'Content-Length': str(size),
            'Accept-Ranges': 'bytes',
            'Content-Disposition': 'attachment; filename=runtime.apk',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Connection': 'keep-alive'
        }
    )

@app.route('/api/validate', methods=['POST', 'OPTIONS'])
def validate_license():
    data = request.get_json() or {}
    key = data.get('key')
    if not key:
        return jsonify({"error": "Missing key"}), 400
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, label, key, revoked, expires, devices, device_limit FROM licenses WHERE key = ?', (key,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return jsonify({"error": "Invalid license key"}), 400
        
    k_id, label, k_key, revoked, expires, devices, device_limit = row
    
    if revoked:
        conn.close()
        return jsonify({"error": "License revoked"}), 400
        
    if expires <= time.time():
        conn.close()
        return jsonify({"error": "License expired"}), 400
        
    if devices < device_limit:
        cursor.execute('UPDATE licenses SET devices = devices + 1 WHERE key = ?', (key,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "License valid"})
    else:
        conn.close()
        return jsonify({"error": "Device limit reached"}), 400

@app.route('/api/session', methods=['GET', 'POST', 'DELETE', 'OPTIONS'])
def session_manager():
    if request.method == 'GET':
        logged = session.get('logged_in', False)
        return jsonify({"owner": logged, "csrf": "flaxxi-csrf-token"})
    
    elif request.method == 'POST':
        data = request.get_json() or {}
        username = data.get('username')
        password = data.get('password')
        
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            return jsonify({"success": True, "csrf": "flaxxi-csrf-token"})
        else:
            return jsonify({"error": "Invalid username or password"}), 401
            
    elif request.method == 'DELETE':
        session.pop('logged_in', None)
        return jsonify({"success": True})

@app.route('/api/keys', methods=['GET', 'POST', 'OPTIONS'])
def manage_keys():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if request.method == 'GET':
        cursor.execute('SELECT id, label, key, revoked, expires, devices, device_limit FROM licenses')
        rows = cursor.fetchall()
        keys = []
        for r in rows:
            keys.append({
                "id": r[0],
                "label": r[1],
                "key": r[2],
                "revoked": bool(r[3]),
                "expires": r[4],
                "devices": r[5],
                "device_limit": r[6]
            })
        conn.close()
        return jsonify({"keys": keys})
        
    elif request.method == 'POST':
        data = request.get_json() or {}
        mode = data.get('mode')
        custom_key = data.get('custom_key')
        label = data.get('label', '')
        days = int(data.get('days', 30))
        device_limit = int(data.get('device_limit', 1))
        
        if mode == 'custom' and custom_key:
            key = custom_key
        else:
            chars = string.ascii_uppercase + string.digits
            key = 'KURO-' + '-'.join(''.join(random.choices(chars, k=4)) for _ in range(3))
            
        expires = int(time.time()) + (days * 86400)
        
        cursor.execute('''
            INSERT OR REPLACE INTO licenses (id, label, key, revoked, expires, devices, device_limit)
            VALUES (?, ?, ?, 0, ?, 0, ?)
        ''', (key, label if label else key, key, expires, device_limit))
        conn.commit()
        conn.close()
        
        return jsonify({
            "id": key,
            "label": label if label else key,
            "key": key,
            "revoked": False,
            "expires": expires,
            "devices": 0,
            "device_limit": device_limit
        })

@app.route('/api/keys/<string:key_id>', methods=['POST', 'OPTIONS'])
def update_key(key_id):
    data = request.get_json() or {}
    action = data.get('action')
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if action == 'revoke':
        cursor.execute('UPDATE licenses SET revoked = 1 WHERE id = ?', (key_id,))
    elif action == 'enable':
        cursor.execute('UPDATE licenses SET revoked = 0 WHERE id = ?', (key_id,))
    elif action == 'reset_devices':
        cursor.execute('UPDATE licenses SET devices = 0 WHERE id = ?', (key_id,))
        
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def call_all(subpath):
    return api_diagnostics()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
