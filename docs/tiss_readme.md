# EduFlow Pro - TISS Automation Script

This Python script automates the registration ("Anmelden") process for courses or exams on TU Wien's TISS platform using Selenium. It can optionally log in, select the desired group, study number, and subgroup, and submit the form at a scheduled time.

## Features

- ✅ Automated login using TISS credentials
- 🎯 Navigate to course or exam page
- 📋 Select a specific group and subgroup/slot
- 🔢 Select study number if needed
- ⚡ Submit registration form automatically
- ⏰ Optional: wait until a specific datetime to submit

## Installation

### Prerequisites

1. **Install Python 3.8+**
2. **Install required packages:**
   ```bash
   pip install selenium
   ```
3. **Download Chrome WebDriver:**
   - Go to [ChromeDriver Downloads](https://chromedriver.chromium.org/downloads)
   - Download the version matching your Chrome browser
   - Place `chromedriver` in your PATH or in the script folder

## Configuration

Create a `config.json` file in the same directory as the script with the following structure:

```json
{
  "username": "YOUR_TISS_USERNAME",
  "password": "YOUR_TISS_PASSWORD",
  "dswid": "YOUR_DSWID",
  "dsrid": "YOUR_DSRID",
  "semester": "2025S",
  "courseNr": "123456",
  "group_index": 0,
  "slot_index": 0,
  "study_number": "123 456",
  "mode": "exam",
  "anmelden_time": "2025-09-22 10:00:00"
}
```

### Configuration Parameters

| Parameter | Description | Required | Example |
|-----------|-------------|----------|---------|
| `username` | Your TISS username | ✅ | `"e12345678"` |
| `password` | Your TISS password | ✅ | `"your_password"` |
| `dswid` | TISS session ID | ✅ | `"ABC123"` |
| `dsrid` | TISS request ID | ✅ | `"XYZ789"` |
| `semester` | Target semester | ✅ | `"2025S"` |
| `courseNr` | Course/exam number | ✅ | `"123456"` |
| `group_index` | Group index (starts at 0) | ✅ | `0` |
| `slot_index` | Time slot index (starts at 0) | ❌ | `1` |
| `study_number` | Study number with space | ❌ | `"123 456"` |
| `mode` | Registration mode | ✅ | `"exam"` or `"group"` |
| `anmelden_time` | Scheduled registration time | ❌ | `"2025-09-22 10:00:00"` |

### Important Notes

- **study_number**: Must include a space between the first three and last three digits (e.g., "123 456")
- **group_index/slot_index**: Indexing starts at 0 (first group = 0, second group = 1, etc.)
- **mode**: Use "exam" for exam registrations, "group" for group registrations
- **anmelden_time**: Optional. Format: `YYYY-MM-DD HH:MM:SS`. Script waits until this time before registration

## Usage

Run the script from the command line:

```bash
python tiss_auto_login.py
```

## Workflow

1. 🔐 Script optionally logs into TISS using provided credentials
2. ⏳ Waits until `anmelden_time` if specified
3. 🌐 Opens the course/exam page
4. 👆 Clicks on the desired group (`group_index`)
5. 📝 Selects the study number and/or subgroup if provided
6. 📤 Submits the registration form

## Requirements

- Google Chrome browser installed
- ChromeDriver executable accessible
- Valid TISS credentials
- Python 3.8 or higher
- Selenium WebDriver package

## Troubleshooting

### Common Issues

- **ChromeDriver not found**: Ensure ChromeDriver is in your PATH or script directory
- **Chrome version mismatch**: Download the correct ChromeDriver version for your Chrome browser
- **Login fails**: Verify your TISS credentials in `config.json`
- **Group not found**: Check if `group_index` matches available groups (remember: starts at 0)

## Build a Windows .exe for the full app

This repo also contains a Flask web frontend with modern static assets. To package everything into a single Windows executable:

1. Install dependencies:

```
pip install -r requirements.txt
```

2. Build client and server:

```
build_windows_client.bat
build_server.bat
```

3. Run the server (on your machine or a VPS):

```
dist/AuthServer.exe
```

4. Run the client app:

```
$env:AUTH_SERVER_BASE = "http://YOUR_SERVER_IP:7000"
dist/EduFlowProClient.exe
```

Notes:
- Client opens `http://127.0.0.1:5000` automatically (local UI only).
- Client DB with requests is per-user at `%LOCALAPPDATA%\\EduFlowPro\\app.db`.
- Accounts are stored only on the server in `auth.db`.
- Static assets (CSS/JS) are included in the executable.

## ⚠️ Disclaimer

**Important**: This script interacts with TISS automatically. Please use responsibly and follow TU Wien's rules and regulations for course registration. 

⚠️ **Warning**: Automating login or registration processes may violate TISS terms of service. Use at your own discretion and responsibility.

## License

This project is provided as-is for educational purposes. Users are responsible for compliance with TU Wien's terms of service and applicable regulations.