# Project Structure

This document provides an overview of the restructured TISS Auto-Anmelden project.

## 📁 Directory Structure

```
AutoGroupLogin/
├── 📁 src/                          # Source code
│   ├── 🐍 main.py                   # Main Flask application (with authentication)
│   ├── 🐍 main_noAuth.py            # Flask application (without authentication)
│   ├── 🐍 auth_server.py            # Authentication server
│   ├── 🐍 tiss_auto_login.py        # Core automation script
│   └── 🐍 setup.py                  # Setup and build utilities
├── 🖥️ app.exe                       # Compiled executable (main_noAuth.py)
├── 📁 templates/                    # HTML templates
│   ├── 🌐 index.html               # Main application page
│   ├── 🌐 generate.html            # Configuration page
│   ├── 🌐 login.html               # Login page
│   └── 🌐 requests.html            # Request monitoring page
├── 📁 docs/                        # Documentation
│   ├── 📖 tiss_readme.md           # Original detailed documentation
│   └── 📖 DEVELOPMENT.md           # Development guide
├── 📁 config/                      # Configuration files
│   └── 📖 README.md                # Configuration guide
├── 📁 examples/                    # Example files
│   ├── 📄 cli_config_example.json  # CLI configuration example
│   └── 📖 README.md                # Examples documentation
├── 📄 requirements.txt             # Python dependencies
├── 📄 .gitignore                   # Git ignore rules
├── 📄 README.md                    # Main project documentation
└── 📄 PROJECT_STRUCTURE.md         # This file
```

## 🔄 Migration Summary

### Files Moved

- `main.py` → `src/main.py`
- `main_noAuth.py` → `src/main_noAuth.py`
- `auth_server_start_too.py` → `src/auth_server.py` (renamed)
- `tiss_auto_login.py` → `src/tiss_auto_login.py`
- `setup.py` → `src/setup.py`
- `tiss_readme.md` → `docs/tiss_readme.md`

### Files Created

- `README.md` - Comprehensive project documentation
- `docs/DEVELOPMENT.md` - Development guide
- `config/README.md` - Configuration guide
- `examples/cli_config_example.json` - CLI configuration example
- `examples/README.md` - Examples documentation
- `.gitignore` - Git ignore rules
- `PROJECT_STRUCTURE.md` - This file

### Files Removed

- `TissLogin.exe` - Old executable (can be rebuilt)
- `__pycache__/` - Python cache directory

## 🚀 How to Run

### Development Mode

```bash
# With authentication
python src/main.py

# Without authentication (simpler)
python src/main_noAuth.py

# Use compiled executable (no Python required)
./app.exe

# Authentication server (optional)
python src/auth_server.py
```

### Production Mode

```bash
# Set environment variables
export FLASK_ENV=production
export FLASK_DEBUG=0

# Run application
python src/main.py
```

## 📋 Key Features

### Web Interface
- Modern, responsive design
- Real-time status updates
- Configuration persistence
- Request monitoring
- User authentication (optional)

### Automation Engine
- Selenium-based automation
- Scheduled execution
- Multiple registration modes
- Error handling and recovery
- Logging and monitoring

### Configuration Management
- Web-based configuration forms
- SQLite database storage
- Validation and error checking
- User-specific settings
- CLI configuration examples

### Compiled Executable
- **app.exe**: Standalone executable based on main_noAuth.py
- **No Python required**: All dependencies bundled
- **Templates included**: HTML/CSS/JS files embedded
- **Portable**: Runs on any Windows machine
- **Simplified**: No authentication system included

## 🔧 Development

### Adding New Features

1. **Backend changes**: Modify files in `src/`
2. **Frontend changes**: Modify files in `templates/`
3. **Documentation**: Update files in `docs/`
4. **Configuration**: Update files in `config/` and `examples/`

### Testing

```bash
# Run the application
python src/main.py

# Test configuration validation
curl -X POST http://127.0.0.1:5000/api/validate \
  -H "Content-Type: application/json" \
  -d '{"username":"test","dswid":"ABC123"}'
```

### Building

```bash
# Install dependencies
pip install -r requirements.txt

# Run setup
python src/setup.py
```

## 📚 Documentation

- **README.md**: Main project documentation
- **docs/DEVELOPMENT.md**: Development guide
- **docs/tiss_readme.md**: Original detailed documentation
- **config/README.md**: Configuration guide
- **PROJECT_STRUCTURE.md**: This file

## 🔒 Security Notes

- Never commit `config.json` with real credentials
- Use environment variables for sensitive data
- Keep authentication tokens secure
- Follow TU Wien's terms of service

## 🎯 Next Steps

1. **Testing**: Add comprehensive test suite
2. **CI/CD**: Set up automated testing and deployment
3. **Monitoring**: Add application monitoring
4. **Documentation**: Expand user guides
5. **Features**: Add new automation capabilities

---

**Project restructured for better organization and maintainability** ✨
