#!/usr/bin/env python3
"""
Setup script for TISS Auto-Anmelden with Web Frontend
This script sets up the necessary files and structure
"""

import os
import sys
import subprocess

def create_directories():
    """Create necessary directories"""
    directories = ['templates', 'static']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Created directory: {directory}")
        else:
            print(f"📁 Directory already exists: {directory}")

def install_requirements():
    """Install required Python packages"""
    packages = ['flask', 'selenium', 'werkzeug', 'webdriver-manager']
    
    print("📦 Installing required packages...")
    for package in packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ Installed: {package}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install: {package}")
            return False
    return True

def preinstall_webdriver():
    """Download and cache ChromeDriver using webdriver-manager"""
    try:
        print("🧩 Preparing ChromeDriver (via webdriver-manager)...")
        # Import here so it works after installation
        from webdriver_manager.chrome import ChromeDriverManager
        # Trigger download/install to cache
        path = ChromeDriverManager().install()
        print(f"✅ ChromeDriver ready at: {path}")
    except Exception as e:
        print(f"⚠️  Skipped ChromeDriver pre-install: {e}")

def create_html_template():
    """Create the HTML template file"""
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TISS Auto-Anmelden</title>
    <style>
        /* Copy the CSS from the HTML artifact here */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        /* ... rest of the CSS ... */
    </style>
</head>
<body>
    <!-- Copy the HTML body content from the artifact here -->
    <div class="container">
        <div class="header">
            <h1>🎓 TISS Auto-Anmelden</h1>
            <p>Automated Registration for TU Wien Courses & Exams</p>
        </div>
        <div class="form-container">
            <p>Please copy the full HTML content from the artifact to templates/index.html</p>
        </div>
    </div>
</body>
</html>'''

    template_path = os.path.join('templates', 'index.html')
    
    if not os.path.exists(template_path):
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ Created template file: {template_path}")
        print("⚠️  Please replace the content with the full HTML from the artifact!")
    else:
        print(f"📁 Template file already exists: {template_path}")

def create_run_script():
    """Create a simple run script"""
    run_script_content = '''#!/usr/bin/env python3
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
        print("\\nPlease make sure all files are in place before running.")
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
'''
    
    with open('run_frontend.py', 'w', encoding='utf-8') as f:
        f.write(run_script_content)
    
    # Make it executable on Unix-like systems
    if os.name != 'nt':
        os.chmod('run_frontend.py', 0o755)
    
    print("✅ Created run script: run_frontend.py")

def main():
    print("🔧 TISS Auto-Anmelden Frontend Setup")
    print("=" * 50)
    
    # Create directories
    create_directories()
    
    # Install requirements
    if not install_requirements():
        print("❌ Failed to install some packages. Please install manually:")
        print("   pip install flask selenium")
        return
    # Pre-install webdriver so first run works offline
    preinstall_webdriver()
    
    # Create template
    create_html_template()
    
    # Create run script
    create_run_script()
    
    print("\n🎉 Setup complete!")
    print("\n📋 Next steps:")
    print("1. Copy the full HTML content from the artifact to 'templates/index.html'")
    print("2. Make sure 'tiss_auto_anmelden.py' is in this directory")
    print("3. Save the Flask backend code as 'flask_backend.py'")
    print("4. Run: python run_frontend.py")
    print("\n🚀 Then open http://127.0.0.1:5000 in your browser!")

if __name__ == '__main__':
    main()