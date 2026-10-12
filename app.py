from flask import Flask, render_template, request, session, jsonify, send_file
import os
import random
import string
import time
import io
import hashlib

app = Flask(__name__)
app.secret_key = 'flaxxi-secret-key-999'

ADMIN_USER = "FLAXXI"
ADMIN_PASS = "FLAXXI@123"

licenses = []

# Generate a valid binary runtime file and calculate its cryptographic hashes
RUNTIME_FILE = "runtime.apk"
if not os.path.exists(RUNTIME_FILE):
    with open(RUNTIME_FILE, "wb") as f:
        f.write(b"PK\x03\x04" + b"\x00" * 5000)

def get_file_hashes():
    if os.path.exists(RUNTIME_FILE):
        with open(RUNTIME_FILE, "rb") as f:
            data = f.read()
            return {
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "md5": hashlib.md5(data).hexdigest()
            }
    return {"size": 5004, "sha256": "", "md5": ""}

@app.route('/')
def index():
    return render_template('index.html')

def get_runtime_payload(base_url="https://flaxxi-access.onrender.com"):
    file_info = get_file_hashes()
    file_size = file_info["size"]
    file_sha256 = file_info["sha256"]
    file_md5 = file_info["md5"]
    
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
        "size": file_size,
        "file_size": file_size,
        "content_length": file_size,
        "sha256": file_sha256,
        "hash": file_sha256,
        "checksum": file_sha256,
        "md5": file_md5,
        "assets": [
            {
                "name": "runtime.apk",
                "size": file_size,
                "sha256": file_sha256,
                "browser_download_url": f"{base_url}/download/runtime.apk"
            }
        ]
    }

@app.route('/api/runtime', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/runtimes', methods=['GET', 'POST', 'OPTIONS'])
def api_runtime():
    base_url = request.host_url.rstrip('/')
    item = get_runtime_payload(base_url)
    return jsonify([item])

@app.route('/api/releases', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/version', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/update', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/diagnostics', methods=['GET', 'POST', 'OPTIONS'])
def api_releases_endpoint():
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
        "KuroRuntime": [item],
        "runtime": item,
        "runtimes": [item],
        "data": item
    })

@app.route('/download/runtime.apk', methods=['GET', 'OPTIONS'])
def download_runtime():
    if os.path.exists(RUNTIME_FILE):
        return send_file(
            RUNTIME_FILE, 
            as_attachment=True, 
            download_name="runtime.apk", 
            mimetype="application/vnd.android.package-archive"
        )
    return send_file(
        io.BytesIO(b"PK\x03\x04" + b"\x00" * 5000),
        as_attachment=True,
        download_name="runtime.apk",
        mimetype="application/vnd.android.package-archive"
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
        
    elif request.POST: # handled via request.method
        pass
        
    if request.method == 'POST':
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
def update_file_key(key_id):
    # alias to avoid naming conflicts
    return update_key(key_id)

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
    base_url = request.host_url.rstrip('/')
    item = get_runtime_payload(base_url)
    return jsonify({
        "success": True,
        "published": True,
        "isPublished": True,
        "KuroRuntime": [item],
        "runtime": item
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
