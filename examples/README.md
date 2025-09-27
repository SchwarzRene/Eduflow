# Examples

This directory contains example files for the TISS Auto-Anmelden application.

## Files

- `cli_config_example.json` - Example configuration file for CLI mode only

## Important Note

**The TISS Auto-Anmelden application primarily uses a web interface.** The JSON configuration file in this directory is only needed if you want to run the automation script directly from the command line.

## Web Interface (Recommended)

For most users, the web interface is the easiest way to use the application:

1. Run: `python src/main.py` or `python src/main_noAuth.py`
2. Open: `http://127.0.0.1:5000`
3. Fill out the form in your browser
4. Configuration is automatically saved

## CLI Mode (Advanced)

If you want to run the automation script directly:

1. Copy `cli_config_example.json` to your project root as `config.json`
2. Edit `config.json` with your actual TISS credentials
3. Run: `python src/tiss_auto_login.py --config config.json`

## Configuration Parameters

See `../config/README.md` for detailed parameter explanations.
