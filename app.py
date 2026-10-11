from flask import Flask, render_template, request, session, jsonify
import os
import random
import string
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Admin Credentials
ADMIN_USER = "FLAXXI"
ADMIN_PASS = "FLAXXI@123"

# In-memory database (License storage)
licenses = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/session', methods=['GET', 'POST', 'DELETE'])
def session_manager():
    if request.method == 'GET':
        is_owner = session.get('logged_in', False)
        return jsonify({"owner": is_owner, "csrf": "secure-csrf-token"})
    
    elif request.method == 'POST':
        data = request.get_json() or {}
        username = data.get('username')
        password = data.get('password')
        
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            return jsonify({"success": True, "csrf": "secure-csrf-token"})
        else:
            return jsonify({"error": "Invalid username or password"}), 401
            
    elif request.method == 'DELETE':
        session.pop('logged_in', None)
        return jsonify({"success": True})

@app.route('/api/keys', methods=['GET', 'POST'])
def manage_keys():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    
    if request.method == 'GET':
        return jsonify({"keys": licenses})
        
    elif request.method == 'POST':
        data = request.get_json() or {}
        mode = data.get('mode')
        custom_key = data.get('custom_key')
        label = data.get('label', '')
        days = int(data.get('days', 30))
        device_limit = int(data.get('device_limit', 1))
        
        # Key generation logic
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

@app.route('/api/keys/<string:key_id>', methods=['POST'])
def update_key(key_id):
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
        
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

if __name__ == '__main__':
    app.run(debug=True)
