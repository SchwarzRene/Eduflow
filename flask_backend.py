#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask backend for TISS Auto-Anmelden Frontend
Integrates with the existing Selenium automation script
Now includes config loading from existing config.json
"""

from flask import Flask, render_template_string, request, jsonify
import json
import threading
import subprocess
import sys
import os
import re
from datetime import datetime
import webbrowser

# Force UTF-8 encoding
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

app = Flask(__name__)

# Global variable to track script status
script_status = {
    'running': False,
    'message': '',
    'success': False
}

def load_existing_config():
    """Load existing configuration from config.json if it exists"""
    try:
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Don't include sensitive data like password in the response
                safe_config = config.copy()
                if 'password' in safe_config:
                    safe_config['password'] = ''  # Clear password for security
                return safe_config
        return {}
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

@app.route('/')
def index():
    """Serve the main frontend interface with embedded config data"""
    try:
        # Load existing configuration
        existing_config = load_existing_config()
        
        # Try to read from templates/index.html if it exists
        template_path = os.path.join('templates', 'index.html')
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Inject configuration data into the HTML
            config_script = f"""
            <script>
                window.EXISTING_CONFIG = {json.dumps(existing_config)};
            </script>
            """
            
            # Insert the config script before the closing </head> tag
            html_content = html_content.replace('</head>', config_script + '</head>')
            return html_content
        else:
            return """
            <!DOCTYPE html>
            <html>
            <head><title>TISS Auto-Anmelden</title></head>
            <body>
                <h1>Setup Required</h1>
                <p>Please create a 'templates' folder and save the HTML frontend as 'templates/index.html'</p>
                <p>You can find the HTML in the artifacts provided earlier.</p>
            </body>
            </html>
            """
    except Exception as e:
        return f"Error loading template: {str(e)}"

@app.route('/api/validate', methods=['POST'])
def validate_config():
    """Validate the configuration data"""
    try:
        data = request.json
        errors = {}
        
        # Required fields validation
        required_fields = ['username', 'password', 'dswid', 'dsrid', 'semester', 'courseNr', 'group_index']
        
        for field in required_fields:
            if not data.get(field):
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

@app.route('/api/run', methods=['POST'])
def run_script():
    """Run the TISS automation script with the provided configuration"""
    global script_status
    
    if script_status['running']:
        return jsonify({'success': False, 'message': 'Script is already running!'})
    
    try:
        data = request.json
        
        # Save configuration to config.json
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Run the script in a separate thread
        def run_automation():
            global script_status
            script_status['running'] = True
            script_status['message'] = 'Starting automation...'
            
            try:
                # Import and run the original script with proper encoding
                # This assumes your original script is named 'tiss_auto_anmelden.py'
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                
                result = subprocess.run([sys.executable, 'tiss_auto_anmelden.py'], 
                                      capture_output=True, text=True, timeout=300,
                                      encoding='utf-8', env=env)
                
                if result.returncode == 0:
                    script_status['success'] = True
                    script_status['message'] = 'Registration completed successfully!'
                else:
                    script_status['success'] = False
                    script_status['message'] = f'Script failed: {result.stderr}'
                    
            except subprocess.TimeoutExpired:
                script_status['success'] = False
                script_status['message'] = 'Script timed out (5 minutes)'
            except Exception as e:
                script_status['success'] = False
                script_status['message'] = f'Error running script: {str(e)}'
            finally:
                script_status['running'] = False
        
        # Start the automation thread
        thread = threading.Thread(target=run_automation)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True, 
            'message': 'Automation started! Check status endpoint for updates.'
        })
        
    except Exception as e:
        script_status['running'] = False
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/status')
def get_status():
    """Get the current status of the automation script"""
    return jsonify(script_status)

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get the current configuration"""
    return jsonify(load_existing_config())

@app.route('/api/config', methods=['POST'])
def save_config():
    """Save configuration without running the script"""
    try:
        data = request.json
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return jsonify({'success': True, 'message': 'Configuration saved successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def open_browser():
    """Open the browser automatically"""
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    print("🚀 Starting TISS Auto-Anmelden Frontend Server...")
    print("📂 Make sure to:")
    print("   1. Save the HTML frontend as 'templates/index.html'")
    print("   2. Have 'tiss_auto_anmelden.py' in the same directory")
    print("   3. Install required packages: pip install flask selenium")
    
    # Load existing config and display info
    existing_config = load_existing_config()
    if existing_config:
        print("📋 Found existing configuration - form will be pre-filled")
    else:
        print("📋 No existing configuration found")
    
    print("\n🌐 Opening browser at http://127.0.0.1:5000")
    
    # Open browser after a short delay
    threading.Timer(1.5, open_browser).start()
    
    # Run Flask app
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)