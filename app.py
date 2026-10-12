from flask import Flask, render_template, request, session, jsonify, send_file, Response
import os
import random
import string
import time
import hashlib

app = Flask(__name__)
app.secret_key = 'flaxxi-secret-key-999'

ADMIN_USER = "FLAXXI"
ADMIN_PASS = "FLAXXI@123"

licenses = []

RUNTIME_FILE = "runtime.apk"

# Valid minimal binary structure ensure karne ke liye taaki loader reject na kare
if not os.path.exists(RUNTIME_FILE):
    with open(RUNTIME_FILE, "wb") as f:
        f.write(b"PK\x03\x04\x14\x00\x08\x00\x08\x00" + b"\x00" * 10000)

def get_file_stats():
    if os.path.exists(RUNTIME_FILE):
        size = os.path.getsize(RUNTIME_FILE)
        with open(RUNTIME_FILE, "rb") as f:
            data = f.read()
            sha = hashlib.sha256(data).hexdigest()
            md5 = hashlib.md5(data).hexdigest()
        return size, sha, md5
    return 10008, "", ""

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
        return jsonify({"error": "Runtime file missing on server"}), 404
        
    size, _, _ = get_file_stats()
    
    if request.method == 'HEAD':
        resp = Response()
        resp.headers['Content-Length'] = str(size)
        resp.headers['Content-Type'] = 'application/vnd.android.package-archive'
        return resp
        
    return send_file(
        RUNTIME_FILE, 
        as_attachment=True, 
        download_name="runtime.apk", 
        mimetype="application/vnd.android.package-archive",
        conditional=True
    )

@app.route('/api/validate', methods=['POST', 'OPTIONS'])
def validate_license():
    data = request.get_json() or {}
    key = data.get('key')
    
    for k in licenses:
        if k['key'] == key and not k['revoked']:
            if k['expires'] > time.time():
                if k['devices'] < k['device_limit']:
                    k['devices'] += 1
                    return jsonify({"success": True, "message": "License valid"})
                else:
                    return jsonify({"error": "Device limit reached"}), 400
            else:
                return jsonify({"error": "License expired"}), 400
                
    return jsonify({"error": "Invalid license key"}), 400

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
    if request.method == 'GET':
        return jsonify({"keys": licenses})
        
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
        
        new_license = {
            "id": key,
            "label": label if label else key,
            "key": key,
            "revoked": False,
            "expires": expires,
            "devices": 0,
            "device_limit": device_limit
        }
        
        licenses.insert(0, new_license)
        return jsonify(new_license)

@app.route('/api/keys/<string:key_id>', methods=['POST', 'OPTIONS'])
def update_key(key_id):
    data = request.get_json() or {}
    action = data.get('action')
    
    for k in licenses:
        if k['id'] == key_id:
            if action == 'revoke':
                k['revoked'] = True
            elif action == 'enable':
                k['revoked'] = False
            elif action == 'reset_devices':
                k['devices'] = 0
            return jsonify({"success": True})
            
    return jsonify({"error": "Key not found"}), 404

@app.route('/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def catch_all(subpath):
    return api_diagnostics()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
