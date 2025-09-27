# Configuration

This directory contains configuration documentation for the TISS Auto-Anmelden application.

## Important Note

**The TISS Auto-Anmelden application primarily uses a web interface for configuration.** Configuration is stored in a local SQLite database, not in JSON files. JSON configuration files are only used for the command-line interface (CLI) mode.

## Files

- `README.md` - This file explaining configuration options
- `../examples/cli_config_example.json` - Example configuration file for CLI mode only

## Configuration Parameters

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
| `mode` | Registration mode | ✅ | `"exam"`, `"group"`, or `"course"` |
| `anmelden_time` | Scheduled registration time | ❌ | `"2025-09-22 10:00:00"` |

## Important Notes

- **study_number**: Must include a space between the first three and last three digits (e.g., "123 456")
- **group_index/slot_index**: Indexing starts at 0 (first group = 0, second group = 1, etc.)
- **mode**: Use "exam" for exam registrations, "group" for group registrations, "course" for course registrations
- **anmelden_time**: Optional. Format: `YYYY-MM-DD HH:MM:SS`. Script waits until this time before registration

## Getting TISS Parameters

1. **DSWID and DSRID**: 
   - Log into TISS and navigate to your course/exam page
   - Look at the URL: `https://tiss.tuwien.ac.at/education/course/examDateList.xhtml?dswid=ABC123&dsrid=XYZ789&semester=2025S&courseNr=123456`
   - Extract the `dswid` and `dsrid` values from the URL

2. **Course Number**:
   - Found in the TISS URL as `courseNr` parameter
   - Usually a 6-digit number

3. **Semester**:
   - Format: YYYYS (Summer) or YYYYW (Winter)
   - Example: 2025S for Summer 2025, 2025W for Winter 2025

4. **Group Index**:
   - Count the groups on the page (starting from 0)
   - First group = 0, second group = 1, etc.

## Usage

### Web Interface (Recommended)

1. Run the application: `python src/main.py` or `python src/main_noAuth.py`
2. Open your browser to `http://127.0.0.1:5000`
3. Fill out the configuration form in the web interface
4. Your configuration is automatically saved in the local database

### Command Line Interface (Advanced)

1. Copy `examples/cli_config_example.json` to your project root as `config.json`
2. Fill in your actual TISS credentials and parameters
3. Run the automation script: `python src/tiss_auto_login.py --config config.json`

**⚠️ Security Note**: Never commit your actual `config.json` file to version control as it contains sensitive credentials.
