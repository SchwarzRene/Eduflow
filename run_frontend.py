#!/usr/bin/env python3
"""
Simple runner for TISS Auto-Anmelden Frontend
"""

import os
import sys

def main():
    print("🚀 Starting TISS Auto-Anmelden Frontend...")
    
    # Check if required files exist
    required_files = [
        'templates/index.html',
        'flask_backend.py',
        'tiss_auto_anmelden.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        print("\nPlease make sure all files are in place before running.")
        return
    
    # Import and run the Flask app
    try:
        from flask_backend import app, open_browser
        import threading
        
        print("🌐 Starting server at http://127.0.0.1:5000")
        threading.Timer(1.5, open_browser).start()
        app.run(debug=False, host='127.0.0.1', port=5000)
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please make sure Flask is installed: pip install flask")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
