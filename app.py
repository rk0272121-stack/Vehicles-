#!/usr/bin/env python3
"""
NEUTRONNNN_KILLER - RC API WITH ADMIN PANEL
Complete API Key Management System
"""

import requests
from bs4 import BeautifulSoup
import re
from flask import Flask, request, jsonify
from threading import Thread
from colorama import Fore, Style, init
import time
import json
import os
import hashlib
import secrets
from datetime import datetime, timedelta

# Initialize colorama
init(autoreset=True)

# ===============================================
# FLASK APP SETUP
# ===============================================
app = Flask(__name__)

# ===============================================
# CONFIGURATION
# ===============================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36",
    "Referer": "https://vahanx.in/",
    "Accept-Language": "en-US,en;q=0.9"
}

FLASK_PORT = 8888
DATA_FILE = "api_keys.json"
LOG_FILE = "access_logs.json"

# ===============================================
# DATABASE (JSON FILE BASED)
# ===============================================

def load_data():
    """Load API keys and logs from JSON"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"keys": [], "logs": [], "admin": {"username": "admin", "password": hashlib.sha256("admin123".encode()).hexdigest()}}

def save_data(data):
    """Save API keys and logs to JSON"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_logs():
    """Load access logs"""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    return []

def save_log(log_entry):
    """Save access log"""
    logs = load_logs()
    logs.append(log_entry)
    with open(LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)

# ===============================================
# API KEY FUNCTIONS
# ===============================================

def generate_api_key():
    """Generate a random API key"""
    return secrets.token_hex(16)

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_api_key(key):
    """Validate if API key exists and is active"""
    data = load_data()
    for k in data.get("keys", []):
        if k["key"] == key:
            if k["status"] == "active":
                # Check expiry
                if k.get("expiry"):
                    expiry_date = datetime.fromisoformat(k["expiry"])
                    if datetime.now() > expiry_date:
                        return {"valid": False, "message": "Key expired"}
                return {"valid": True, "key_data": k}
            else:
                return {"valid": False, "message": "Key revoked"}
    return {"valid": False, "message": "Invalid key"}

def log_access(api_key, rc_number, status):
    """Log API access"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "api_key": api_key,
        "rc_number": rc_number,
        "status": status,
        "ip": request.remote_addr if request else "unknown"
    }
    save_log(log_entry)

# ===============================================
# SCRAPER FUNCTIONS
# ===============================================

def get_comprehensive_vehicle_details(rc_number: str) -> dict:
    """Scrape vehicle details from vahanx.in"""
    rc = rc_number.strip().upper()
    url = f"https://vahanx.in/rc-search/{rc}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        return {"error": f"Failed to fetch data: {str(e)}"}

    def extract_card(label):
        for div in soup.select(".hrcd-cardbody"):
            span = div.find("span")
            if span and label.lower() in span.text.lower():
                p = div.find("p")
                return p.get_text(strip=True) if p else None
        return None

    def get_value(label):
        try:
            div = soup.find("span", string=label)
            if div:
                div = div.find_parent("div")
                p = div.find("p") if div else None
                return p.get_text(strip=True) if p else None
        except:
            return None

    # Extract data
    registration_number = soup.find("h1").text.strip() if soup.find("h1") else rc
    
    data = {
        "status": "success",
        "registration_number": registration_number,
        "basic_info": {
            "owner_name": extract_card("Owner Name") or get_value("Owner Name"),
            "fathers_name": extract_card("Father's Name") or get_value("Father's Name"),
            "model_name": extract_card("Modal Name") or get_value("Model Name"),
            "city": extract_card("City Name") or get_value("City Name"),
            "phone": extract_card("Phone") or get_value("Phone"),
            "address": extract_card("Address") or get_value("Address")
        },
        "vehicle_details": {
            "maker_model": extract_card("Maker Model") or get_value("Maker Model"),
            "vehicle_class": extract_card("Vehicle Class") or get_value("Vehicle Class"),
            "fuel_type": extract_card("Fuel Type") or get_value("Fuel Type"),
            "fuel_norms": extract_card("Fuel Norms") or get_value("Fuel Norms")
        },
        "insurance": {
            "company": extract_card("Insurance Company") or get_value("Insurance Company"),
            "policy_number": extract_card("Insurance No") or get_value("Insurance No"),
            "expiry_date": extract_card("Insurance Expiry") or get_value("Insurance Expiry")
        },
        "validity": {
            "registration_date": extract_card("Registration Date") or get_value("Registration Date"),
            "fitness_upto": extract_card("Fitness Upto") or get_value("Fitness Upto"),
            "tax_upto": extract_card("Tax Upto") or get_value("Tax Upto"),
            "vehicle_age": extract_card("Vehicle Age") or get_value("Vehicle Age")
        }
    }

    # Clean None values
    def clean_dict(d):
        if isinstance(d, dict):
            return {k: clean_dict(v) for k, v in d.items() if v is not None and v != ""}
        return d
    
    return clean_dict(data)

# ===============================================
# FLASK API ROUTES
# ===============================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "online",
        "service": "NEUTRONNNN_KILLER RC API",
        "version": "3.0",
        "endpoints": {
            "api": "/api/vehicle-info?key=YOUR_KEY&number=RC_NUMBER",
            "admin": "/admin",
            "health": "/health"
        },
        "example": f"http://localhost:{FLASK_PORT}/api/vehicle-info?key=YOUR_KEY&number=MH12AB1234"
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route("/api/vehicle-info", methods=["GET"])
def get_vehicle_info():
    """Main API endpoint - requires key and number"""
    api_key = request.args.get("key")
    rc_number = request.args.get("number")
    
    # Validate key
    if not api_key:
        return jsonify({"status": "error", "message": "API key required", "usage": "?key=YOUR_KEY&number=RC_NUMBER"}), 400
    
    key_validation = validate_api_key(api_key)
    if not key_validation["valid"]:
        log_access(api_key, rc_number, "invalid_key")
        return jsonify({"status": "error", "message": key_validation["message"]}), 401
    
    # Validate RC number
    if not rc_number:
        return jsonify({"status": "error", "message": "RC number required"}), 400
    
    # Fetch data
    try:
        data = get_comprehensive_vehicle_details(rc_number)
        if data.get("error"):
            log_access(api_key, rc_number, "error")
            return jsonify({"status": "error", "message": data["error"]}), 404
        
        log_access(api_key, rc_number, "success")
        return jsonify(data)
    except Exception as e:
        log_access(api_key, rc_number, "error")
        return jsonify({"status": "error", "message": str(e)}), 500

# ===============================================
# ADMIN PANEL ROUTES
# ===============================================

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    """Admin panel HTML"""
    
    # Check if logged in via session
    session_token = request.cookies.get("admin_session")
    data = load_data()
    
    # Login check
    if request.method == "POST" and request.form.get("action") == "login":
        username = request.form.get("username")
        password = request.form.get("password")
        
        admin = data.get("admin", {})
        if username == admin.get("username") and hash_password(password) == admin.get("password"):
            # Set session cookie
            response = app.make_response(admin_panel_html(data, logged_in=True))
            response.set_cookie("admin_session", "logged_in", max_age=3600)
            return response
    
    # Logout
    if request.args.get("action") == "logout":
        response = app.make_response(admin_panel_html(data, logged_in=False))
        response.set_cookie("admin_session", "", expires=0)
        return response
    
    # Check session
    is_logged_in = request.cookies.get("admin_session") == "logged_in"
    
    # Handle admin actions (only if logged in)
    if is_logged_in and request.method == "POST":
        action = request.form.get("action")
        
        # Create key
        if action == "create_key":
            new_key = {
                "key": generate_api_key(),
                "name": request.form.get("name", "User"),
                "status": "active",
                "created": datetime.now().isoformat(),
                "expiry": request.form.get("expiry") or None
            }
            data["keys"].append(new_key)
            save_data(data)
        
        # Delete key
        elif action == "delete_key":
            key_to_delete = request.form.get("key_value")
            data["keys"] = [k for k in data["keys"] if k["key"] != key_to_delete]
            save_data(data)
        
        # Toggle key status
        elif action == "toggle_key":
            key_to_toggle = request.form.get("key_value")
            for k in data["keys"]:
                if k["key"] == key_to_toggle:
                    k["status"] = "revoked" if k["status"] == "active" else "active"
                    break
            save_data(data)
        
        # Change password
        elif action == "change_password":
            old_pass = request.form.get("old_password")
            new_pass = request.form.get("new_password")
            
            admin = data.get("admin", {})
            if hash_password(old_pass) == admin.get("password"):
                data["admin"]["password"] = hash_password(new_pass)
                save_data(data)
                message = "Password changed successfully!"
            else:
                message = "Old password incorrect!"
    
    # Get logs for display
    logs = load_logs()[-50:]  # Last 50 logs
    
    return admin_panel_html(data, is_logged_in, logs if is_logged_in else [])

def admin_panel_html(data, logged_in=False, logs=None):
    """Generate admin panel HTML"""
    
    if not logged_in:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Admin Login - RC API</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { font-family: sans-serif; background: #0a0a0a; display: flex; justify-content: center; align-items: center; height: 100vh; }
                .login-box { background: #1a1a2e; padding: 40px; border-radius: 20px; border: 1px solid #333; width: 100%; max-width: 380px; }
                .login-box h1 { color: #00ff88; text-align: center; margin-bottom: 20px; }
                .login-box input { width: 100%; padding: 14px; margin: 10px 0; background: #222; border: 1px solid #333; border-radius: 12px; color: #fff; font-size: 16px; }
                .login-box button { width: 100%; padding: 14px; background: #00ff88; border: none; border-radius: 12px; color: #000; font-weight: bold; font-size: 16px; cursor: pointer; }
                .login-box button:hover { background: #00cc77; }
                .error { color: #ff4466; text-align: center; margin: 10px 0; }
                .info { color: #666; text-align: center; font-size: 12px; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="login-box">
                <h1>🔑 Admin Login</h1>
                <form method="POST">
                    <input type="hidden" name="action" value="login">
                    <input type="text" name="username" placeholder="Username" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Login →</button>
                </form>
                <p class="info">Default: admin / admin123</p>
            </div>
        </body>
        </html>
        """
    
    # Admin panel HTML (when logged in)
    keys_html = ""
    for key in data.get("keys", []):
        status_color = "#00ff88" if key["status"] == "active" else "#ff4466"
        expiry_text = key.get("expiry", "♾️ Never")
        keys_html += f"""
        <div class="key-card">
            <div class="key-header">
                <strong>{key.get('name', 'User')}</strong>
                <span style="color:{status_color}">{key['status'].upper()}</span>
            </div>
            <div class="key-value" onclick="navigator.clipboard?.writeText('{key['key']}');alert('Copied!')">{key['key']}</div>
            <div class="key-meta">Created: {key.get('created', 'Unknown')} | Expiry: {expiry_text}</div>
            <div class="key-actions">
                <form method="POST" style="display:inline">
                    <input type="hidden" name="action" value="toggle_key">
                    <input type="hidden" name="key_value" value="{key['key']}">
                    <button type="submit" class="btn {'btn-danger' if key['status']=='active' else 'btn-primary'}">
                        { '🔒 Revoke' if key['status']=='active' else '✅ Activate' }
                    </button>
                </form>
                <form method="POST" style="display:inline" onsubmit="return confirm('Delete this key?')">
                    <input type="hidden" name="action" value="delete_key">
                    <input type="hidden" name="key_value" value="{key['key']}">
                    <button type="submit" class="btn btn-danger">🗑️ Delete</button>
                </form>
            </div>
        </div>
        """
    
    logs_html = ""
    if logs:
        for log in logs[-20:]:
            status_color = "#00ff88" if log.get("status") == "success" else "#ff4466"
            logs_html += f"""
            <div class="log-item">
                <span style="color:{status_color}">{log.get('status', 'unknown').upper()}</span>
                <strong>{log.get('rc_number', 'N/A')}</strong>
                <small>Key: {log.get('api_key', '')[:12]}...</small>
                <small>{log.get('timestamp', '')[:19]}</small>
            </div>
            """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin Panel - RC API</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: sans-serif; background: #0a0a0a; color: #e0e0e0; padding: 20px; padding-bottom: 80px; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; padding: 20px; background: #1a1a2e; border-radius: 16px; margin-bottom: 30px; }}
            .header h1 {{ color: #00ff88; }}
            .header a {{ color: #ff4466; text-decoration: none; }}
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; margin-bottom: 30px; }}
            .stat {{ background: #1a1a2e; padding: 20px; border-radius: 16px; text-align: center; }}
            .stat-value {{ font-size: 28px; font-weight: bold; color: #00ff88; }}
            .section {{ background: #1a1a2e; border-radius: 16px; padding: 24px; margin-bottom: 20px; }}
            .section-title {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }}
            .btn {{ padding: 8px 18px; border: none; border-radius: 30px; font-size: 13px; cursor: pointer; }}
            .btn-primary {{ background: #00ff88; color: #000; }}
            .btn-danger {{ background: #ff4466; color: #fff; }}
            .btn-warning {{ background: #ffaa00; color: #000; }}
            .key-card {{ background: #0a0a0a; padding: 16px; border-radius: 12px; margin-bottom: 12px; border-left: 3px solid #00ff88; }}
            .key-header {{ display: flex; justify-content: space-between; }}
            .key-value {{ font-family: monospace; background: #000; padding: 10px; border-radius: 8px; font-size: 14px; word-break: break-all; margin: 8px 0; cursor: pointer; }}
            .key-meta {{ font-size: 12px; color: #666; }}
            .key-actions {{ display: flex; gap: 8px; margin-top: 10px; }}
            .log-item {{ background: #0a0a0a; padding: 12px; border-radius: 8px; margin-bottom: 8px; display: flex; gap: 15px; flex-wrap: wrap; align-items: center; }}
            .form-group {{ margin: 10px 0; }}
            .form-group input, .form-group select {{ width: 100%; padding: 12px; background: #0a0a0a; border: 1px solid #333; border-radius: 12px; color: #fff; font-size: 14px; }}
            .modal {{ display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); z-index: 1000; align-items: center; justify-content: center; }}
            .modal.active {{ display: flex; }}
            .modal-content {{ background: #1a1a2e; padding: 30px; border-radius: 20px; max-width: 500px; width: 90%; }}
            .bottom-nav {{ position: fixed; bottom: 0; left: 0; right: 0; background: #1a1a2e; display: flex; justify-content: space-around; padding: 12px; border-top: 1px solid #333; }}
            .nav-item {{ color: #666; text-decoration: none; text-align: center; font-size: 12px; }}
            .nav-item.active {{ color: #00ff88; }}
            .nav-icon {{ font-size: 24px; }}
            .toast {{ position: fixed; top: 20px; left: 20px; right: 20px; background: #00ff88; color: #000; padding: 16px; border-radius: 16px; z-index: 2000; display: none; }}
            .toast.show {{ display: block; }}
            .flex {{ display: flex; gap: 8px; flex-wrap: wrap; }}
            .mt-10 {{ margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚗 RC API Admin</h1>
            <div>
                <span style="color:#00ff88">👤 admin</span>
                <a href="/admin?action=logout" style="margin-left:15px;">Logout</a>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat"><div class="stat-value">{len(data.get('keys', []))}</div><div>Total Keys</div></div>
            <div class="stat"><div class="stat-value">{len([k for k in data.get('keys', []) if k.get('status')=='active'])}</div><div>Active</div></div>
            <div class="stat"><div class="stat-value">{len(logs)}</div><div>Logs</div></div>
        </div>
        
        <div class="section">
            <div class="section-title">
                <span>🔑 API Keys</span>
                <button class="btn btn-primary" onclick="openModal('createModal')">➕ New Key</button>
            </div>
            {keys_html}
        </div>
        
        <div class="section">
            <div class="section-title"><span>📋 Recent Logs</span></div>
            {logs_html}
        </div>
        
        <div class="section">
            <div class="section-title"><span>⚙️ Settings</span></div>
            <form method="POST">
                <input type="hidden" name="action" value="change_password">
                <div class="form-group">
                    <input type="password" name="old_password" placeholder="Old Password" required>
                </div>
                <div class="form-group">
                    <input type="password" name="new_password" placeholder="New Password" required>
                </div>
                <button type="submit" class="btn btn-primary">🔑 Change Password</button>
            </form>
        </div>
        
        <div class="section">
            <div class="section-title"><span>📡 API Usage</span></div>
            <code style="background:#000;padding:10px;display:block;border-radius:8px;font-size:12px;color:#00ff88;word-break:break-all;">
                http://localhost:{FLASK_PORT}/api/vehicle-info?key=YOUR_KEY&number=MH12AB1234
            </code>
        </div>
        
        <div class="bottom-nav">
            <a href="/admin" class="nav-item active"><div class="nav-icon">🏠</div>Home</a>
            <a href="/admin" class="nav-item"><div class="nav-icon">🔑</div>Keys</a>
            <a href="/admin" class="nav-item"><div class="nav-icon">📋</div>Logs</a>
            <a href="/admin" class="nav-item"><div class="nav-icon">⚙️</div>Settings</a>
        </div>
        
        <div class="modal" id="createModal">
            <div class="modal-content">
                <div style="display:flex;justify-content:space-between">
                    <h3>➕ New API Key</h3>
                    <span onclick="closeModal('createModal')" style="font-size:28px;cursor:pointer">&times;</span>
                </div>
                <form method="POST">
                    <input type="hidden" name="action" value="create_key">
                    <div class="form-group">
                        <input type="text" name="name" placeholder="Key Name (e.g., User1)" value="User">
                    </div>
                    <div class="form-group">
                        <input type="datetime-local" name="expiry" placeholder="Expiry Date (optional)">
                    </div>
                    <button type="submit" class="btn btn-primary" style="width:100%;margin-top:10px">🔑 Generate Key</button>
                </form>
            </div>
        </div>
        
        <script>
            function openModal(id){{
                document.getElementById(id).classList.add('active');
            }}
            function closeModal(id){{
                document.getElementById(id).classList.remove('active');
            }}
            document.querySelectorAll('.modal').forEach(m=>{{
                m.addEventListener('click',function(e){{
                    if(e.target===this) this.classList.remove('active');
                }});
            }});
        </script>
    </body>
    </html>
    """

# ===============================================
# CONSOLE MODE
# ===============================================

def console_mode():
    """Console interface with API key support"""
    print(f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        🚗 RC API WITH ADMIN PANEL 🚗                     ║
║                                                           ║
║          Complete API Key Management System               ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
    """)
    
    print(f"{Fore.GREEN}✅ API Running on: {Fore.CYAN}http://localhost:{FLASK_PORT}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}📡 Admin Panel: {Fore.CYAN}http://localhost:{FLASK_PORT}/admin{Style.RESET_ALL}")
    print(f"{Fore.GREEN}📡 API Endpoint: {Fore.CYAN}http://localhost:{FLASK_PORT}/api/vehicle-info?key=YOUR_KEY&number=RC_NUMBER{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}🔑 Default Admin: admin / admin123{Style.RESET_ALL}\n")
    
    # Load existing keys
    data = load_data()
    if data.get("keys"):
        print(f"{Fore.GREEN}📦 Available API Keys:{Style.RESET_ALL}")
        for k in data["keys"]:
            status = f"{Fore.GREEN}Active{Style.RESET_ALL}" if k["status"] == "active" else f"{Fore.RED}Revoked{Style.RESET_ALL}"
            print(f"  🔑 {k['key'][:20]}... - {k.get('name', 'User')} - {status}")
    else:
        print(f"{Fore.YELLOW}⚠️ No API keys found! Create one from admin panel.{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}{'─'*60}{Style.RESET_ALL}\n")
    
    while True:
        try:
            print(f"{Fore.CYAN}Enter RC number (or 'quit' to exit):{Style.RESET_ALL}")
            rc_number = input(f"{Fore.YELLOW}RC > {Style.RESET_ALL}").strip()
            
            if rc_number.lower() in ['quit', 'exit', 'q']:
                print(f"\n{Fore.CYAN}👋 Goodbye!{Style.RESET_ALL}")
                break
            
            if not rc_number:
                print(f"{Fore.RED}❌ Please enter a valid RC number!{Style.RESET_ALL}")
                continue
            
            # Ask for API key
            api_key = input(f"{Fore.YELLOW}Enter API key (press Enter to use default): {Style.RESET_ALL}").strip()
            
            if not api_key:
                # Use first active key
                data = load_data()
                active_keys = [k for k in data.get("keys", []) if k["status"] == "active"]
                if active_keys:
                    api_key = active_keys[0]["key"]
                    print(f"{Fore.GREEN}✅ Using key: {api_key[:16]}...{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}❌ No active API key found! Create one from admin panel.{Style.RESET_ALL}")
                    continue
            
            # Fetch data
            print(f"{Fore.YELLOW}🔍 Fetching data...{Style.RESET_ALL}")
            
            # Use internal function (since we're in same app)
            with app.test_request_context(f"/api/vehicle-info?key={api_key}&number={rc_number}"):
                response = get_vehicle_info()
                import json
                data = json.loads(response.get_data(as_text=True))
                
                if data.get("status") == "error":
                    print(f"{Fore.RED}❌ {data.get('message', 'Unknown error')}{Style.RESET_ALL}")
                else:
                    display_vehicle_details(data)
            
            print(f"\n{Fore.CYAN}{'─'*60}{Style.RESET_ALL}\n")
            
        except KeyboardInterrupt:
            print(f"\n\n{Fore.CYAN}👋 Goodbye!{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"{Fore.RED}❌ Error: {str(e)}{Style.RESET_ALL}")

def display_vehicle_details(data):
    """Display vehicle details nicely"""
    print(f"\n{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}✅ VEHICLE: {data.get('registration_number', 'N/A')}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}\n")
    
    basic = data.get("basic_info", {})
    if basic:
        print(f"{Fore.YELLOW}📋 BASIC INFO:{Style.RESET_ALL}")
        if basic.get("owner_name"): print(f"  👤 Owner: {basic['owner_name']}")
        if basic.get("fathers_name"): print(f"  👨 Father: {basic['fathers_name']}")
        if basic.get("model_name"): print(f"  🚗 Model: {basic['model_name']}")
        if basic.get("city"): print(f"  🏙️ City: {basic['city']}")
        if basic.get("phone"): print(f"  📞 Phone: {basic['phone']}")
        print()
    
    vehicle = data.get("vehicle_details", {})
    if vehicle:
        print(f"{Fore.YELLOW}🚙 VEHICLE SPECS:{Style.RESET_ALL}")
        if vehicle.get("maker_model"): print(f"  🏭 Maker/Model: {vehicle['maker_model']}")
        if vehicle.get("vehicle_class"): print(f"  🏷️ Class: {vehicle['vehicle_class']}")
        if vehicle.get("fuel_type"): print(f"  ⛽ Fuel: {vehicle['fuel_type']}")
        print()
    
    insurance = data.get("insurance", {})
    if insurance:
        print(f"{Fore.YELLOW}🛡️ INSURANCE:{Style.RESET_ALL}")
        if insurance.get("company"): print(f"  🏢 Company: {insurance['company']}")
        if insurance.get("policy_number"): print(f"  📄 Policy: {insurance['policy_number']}")
        if insurance.get("expiry_date"): print(f"  📅 Expiry: {insurance['expiry_date']}")
        print()
    
    validity = data.get("validity", {})
    if validity:
        print(f"{Fore.YELLOW}📅 VALIDITY:{Style.RESET_ALL}")
        if validity.get("registration_date"): print(f"  📆 Registration: {validity['registration_date']}")
        if validity.get("fitness_upto"): print(f"  ✅ Fitness Upto: {validity['fitness_upto']}")
        if validity.get("tax_upto"): print(f"  💵 Tax Upto: {validity['tax_upto']}")
        print()
    
    print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}\n")

# ===============================================
# MAIN
# ===============================================

def main():
    try:
        # Start Flask in background
        flask_thread = Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": FLASK_PORT, "debug": False, "use_reloader": False}, daemon=True)
        flask_thread.start()
        time.sleep(2)
        console_mode()
    except Exception as e:
        print(f"{Fore.RED}❌ Error: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
