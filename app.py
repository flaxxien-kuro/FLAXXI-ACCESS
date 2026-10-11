from flask import Flask, render_template, request, session, jsonify
import os
import random
import string
import time

app = Flask(__name__)
app.secret_key = 'flaxxi-secret-key-999'

ADMIN_USER = "FLAXXI"
ADMIN_PASS = "FLAXXI@123"

licenses = []

@app.route('/')
def index():
    return render_template('index.html')

# Advanced Runtime Endpoint with all possible flags
@app.route('/api/runtime', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/runtimes', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/v1/runtime', methods=['GET', 'POST', 'OPTIONS'])
def runtime_data():
    return jsonify({
        "success": True,
        "status": "published",
        "published": True,
        "isPublished": True,
        "active": True,
        "runtime": {
            "version": "1.6",
            "url": "https://flaxxi-access.onrender.com",
            "published": True,
            "isPublished": True
        },
        "data": {
            "version": "1.6",
            "published": True,
            "isPublished": True
        },
        "runtimes": [{
            "version": "1.6",
            "url": "https://flaxxi-access.onrender.com",
            "published": True,
            "isPublished": True
        }]
    })

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
    return jsonify({
        "status": "published",
        "success": True,
        "published": True,
        "isPublished": True,
        "message": "Connected to Kuro server",
        "version": "1.6",
        "runtime": {
            "version": "1.6",
            "published": True,
            "isPublished": True
        },
        "runtimes": [{
            "version": "1.6",
            "published": True,
            "isPublished": True
        }]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
