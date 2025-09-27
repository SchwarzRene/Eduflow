# Development Guide

This document provides information for developers working on the TISS Auto-Anmelden project.

## 🏗️ Architecture Overview

The application consists of several components:

### Core Components

1. **Automation Engine** (`tiss_auto_login.py`)
   - Selenium-based automation
   - Handles TISS interaction
   - Can be run standalone with JSON config or via Flask app with stdin input

2. **Web Backend** (`main.py` / `main_noAuth.py`)
   - Flask web server
   - REST API endpoints
   - Request management
   - SQLite database operations
   - Passes configuration to automation script via stdin

3. **Authentication Server** (`auth_server.py`)
   - JWT-based authentication
   - User management
   - Optional component

4. **Frontend** (`templates/`)
   - HTML/CSS/JavaScript
   - Modern responsive design
   - Real-time updates
   - Configuration forms

### Data Flow

1. **User fills form** in web interface
2. **Configuration stored** in SQLite database
3. **Request created** with configuration
4. **Automation script called** with config via stdin: `python tiss_auto_login.py --config -`
5. **Progress tracked** and displayed in web interface

## 🛠️ Development Setup

### Prerequisites

- Python 3.8+
- Google Chrome
- Git

### Local Development

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd AutoGroupLogin
   pip install -r requirements.txt
   ```

2. **Run in development mode:**
   ```bash
   # With authentication
   FLASK_DEBUG=1 python src/main.py
   
   # Without authentication (simpler)
   FLASK_DEBUG=1 python src/main_noAuth.py
   
   # Use compiled executable
   ./app.exe
   ```

3. **Access the application:**
   - Web interface: http://127.0.0.1:5000
   - API endpoints: http://127.0.0.1:5000/api/

## 📁 Code Structure

### Backend (`src/`)

```
src/
├── main.py                    # Main Flask app with auth
├── main_noAuth.py            # Flask app without auth
├── auth_server.py            # Authentication server
├── tiss_auto_login.py        # Core automation
└── setup.py                  # Setup utilities
```

### Frontend (`templates/`)

```
templates/
├── index.html                # Main application page
├── generate.html             # Configuration page
├── login.html                # Authentication page
└── requests.html             # Request monitoring
```

### Key Functions

#### Automation Engine

- `run_with_config(config)`: Main automation function
- `init_driver()`: Initialize Chrome WebDriver
- `login(driver, username, password)`: TISS login
- `select_group_and_click_anmelden()`: Group selection
- `wait_until(target_time)`: Scheduled execution

#### Web Backend

- `create_request()`: Create new registration request
- `get_request_status()`: Get request status
- `cancel_request()`: Cancel running request
- `validate_config()`: Validate configuration
- `save_user_config()`: Save user configuration

## 🔧 API Endpoints

### Authentication (Optional)

- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/logout` - User logout

### Configuration

- `GET /api/user_config` - Get user configuration
- `POST /api/user_config` - Save user configuration
- `POST /api/validate` - Validate configuration

### Requests

- `GET /api/requests` - List user requests
- `POST /api/requests` - Create new request
- `GET /api/requests/<id>` - Get request status
- `POST /api/requests/<id>/cancel` - Cancel request

## 🗄️ Database Schema

### Tables

#### `requests`
- `id` - Primary key
- `user_id` - User identifier
- `status` - Request status (queued, running, completed, failed, cancelled)
- `message` - Status message
- `success` - Success flag
- `config_json` - Request configuration
- `scheduled_at` - Scheduled execution time
- `started_at` - Actual start time
- `finished_at` - Completion time
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

#### `user_configs`
- `user_id` - User identifier (primary key)
- `config_json` - User configuration
- `updated_at` - Last update timestamp

#### `users` (Authentication only)
- `id` - Primary key
- `username` - Username
- `password_hash` - Hashed password
- `created_at` - Creation timestamp

## 🧪 Testing

### Manual Testing

1. **Configuration validation:**
   ```bash
   curl -X POST http://127.0.0.1:5000/api/validate \
     -H "Content-Type: application/json" \
     -d '{"username":"test","dswid":"ABC123"}'
   ```

2. **Request creation:**
   ```bash
   curl -X POST http://127.0.0.1:5000/api/requests \
     -H "Content-Type: application/json" \
     -d '{"username":"test","password":"test","dswid":"ABC123","dsrid":"XYZ789","semester":"2025S","courseNr":"123456","group_index":0}'
   ```

### Automated Testing

```bash
# Run tests (when implemented)
python -m pytest tests/

# Run with coverage
python -m pytest --cov=src tests/
```

## 🚀 Deployment

### Local Deployment

1. **Production mode:**
   ```bash
   python src/main.py
   ```

2. **With authentication server:**
   ```bash
   # Terminal 1: Auth server
   python src/auth_server.py
   
   # Terminal 2: Main app
   AUTH_SERVER_BASE=http://127.0.0.1:7000 python src/main.py
   ```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY templates/ ./templates/

EXPOSE 5000
CMD ["python", "src/main.py"]
```

### Build Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --onefile --add-data "templates;templates" src/main.py
```

## 🔍 Debugging

### Logging

The application uses Python's logging module:

```python
import logging
logger = logging.getLogger('agl.backend')
logger.info('Debug message')
```

### Debug Mode

Enable Flask debug mode:

```bash
export FLASK_DEBUG=1
python src/main.py
```

### Chrome Debug Mode

For debugging Selenium issues:

```python
chrome_options.add_argument("--headless")  # Run headless
chrome_options.add_argument("--no-sandbox")  # Disable sandbox
chrome_options.add_argument("--disable-dev-shm-usage")  # Disable /dev/shm
```

## 📝 Code Style

### Python

- Follow PEP 8
- Use type hints where possible
- Document functions with docstrings
- Use meaningful variable names

### JavaScript

- Use modern ES6+ features
- Follow consistent indentation
- Use meaningful function names
- Comment complex logic

### HTML/CSS

- Use semantic HTML
- Follow BEM methodology for CSS
- Use CSS custom properties
- Ensure accessibility

## 🔄 Contributing

### Workflow

1. **Fork the repository**
2. **Create a feature branch:**
   ```bash
   git checkout -b feature/new-feature
   ```
3. **Make changes and test**
4. **Commit with descriptive messages:**
   ```bash
   git commit -m "Add new feature: description"
   ```
5. **Push and create pull request**

### Pull Request Guidelines

- Include description of changes
- Add tests if applicable
- Update documentation
- Ensure code style compliance
- Test on multiple browsers/platforms

## 🐛 Common Issues

### Development Issues

1. **ChromeDriver version mismatch:**
   - Update Chrome browser
   - Clear webdriver-manager cache

2. **Port already in use:**
   ```bash
   # Find process using port 5000
   lsof -i :5000
   # Kill process
   kill -9 <PID>
   ```

3. **Database locked:**
   - Check for running processes
   - Restart application
   - Delete database file if corrupted

### Production Issues

1. **Memory usage:**
   - Monitor Chrome processes
   - Implement process cleanup
   - Use headless mode

2. **Rate limiting:**
   - Add delays between requests
   - Implement retry logic
   - Monitor TISS response times

## 📚 Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Selenium Documentation](https://selenium-python.readthedocs.io/)
- [ChromeDriver Documentation](https://chromedriver.chromium.org/)
- [TU Wien TISS](https://tiss.tuwien.ac.at/)

## 🤝 Support

For development questions:

1. Check this documentation
2. Review existing issues
3. Create new issue with:
   - Description of problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details
