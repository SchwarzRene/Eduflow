# -*- coding: utf-8 -*-
import json
import argparse
import time
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
import datetime

# Force UTF-8 encoding for Windows console
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Set environment variable for proper encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

def load_config_from_path(config_path: str):
    # Support reading from stdin when path is '-'
    if config_path == '-':
        data = sys.stdin.read()
        return json.loads(data)
    with open(config_path, "r", encoding='utf-8') as f:
        return json.load(f)

parser = argparse.ArgumentParser(description="Run TISS auto registration with a given config file.")
parser.add_argument("--config", dest="config_path", default="config.json", help="Path to config JSON file or '-' for stdin")
args, _ = parser.parse_known_args()

CONFIG = load_config_from_path(args.config_path)

USERNAME = CONFIG["username"]
PASSWORD = CONFIG["password"]
WRAPPER_INDEX = CONFIG["group_index"]

# Optional fields
STUDY_NUMBER = CONFIG.get("study_number") or None
SUBGROUP_INDEX = CONFIG.get("slot_index")
if SUBGROUP_INDEX == "" or SUBGROUP_INDEX is None:
    SUBGROUP_INDEX = None

# Mode decides which URL type to use
MODE = CONFIG.get("mode", "exam").lower()  # default = exam

if MODE == "group":
    PATH = "groupList.xhtml"
elif MODE == "course":
    PATH = "courseRegistration.xhtml"
else:
    PATH = "examDateList.xhtml"

COURSE_URL = (
    f"https://tiss.tuwien.ac.at/education/course/{PATH}"
    f"?dswid={CONFIG['dswid']}&dsrid={CONFIG['dsrid']}"
    f"&semester={CONFIG['semester']}&courseNr={CONFIG['courseNr']}"
)


def safe_print(message):
    """Safe print function that handles Unicode characters on Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback: remove Unicode characters
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)

def init_driver():
    chrome_options = Options()
    # Uncomment if headless is desired by default
    # chrome_options.add_argument("--headless=new")
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        safe_print(f"[WARNING] webdriver-manager failed, trying system ChromeDriver: {e}")
        # Fallback to system driver if available
        return webdriver.Chrome(options=chrome_options)

def login(driver, username, password):
    """Go to login page and log in with given credentials."""
    driver.get("https://tiss.tuwien.ac.at/admin/authentifizierung")
    
    try:
        # Wait until username field is visible
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))
        
        driver.find_element(By.ID, "username").send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)

        time.sleep( 0.1 )

        driver.find_element(By.ID, "samlloginbutton").click()
        
        safe_print("Login submitted.")
        # Wait until redirect finishes (optional: check for some post-login element)
        time.sleep(1)
    except Exception as e:
        safe_print(f"Login page not available or skipped: {e}")

def open_course_page(driver, url):
    """Navigate to course page after login (or without login)."""
    driver.get(url)
    # Wait for page to load: either group wrappers or a global 'Anmelden' button
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "groupWrapper"))
        )
    except Exception:
        # Fallback for course registration page where there may be no groupWrapper
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='submit' and @value='Anmelden']"))
        )
    safe_print("Course page loaded.")

def select_group_and_click_anmelden(driver, wrapper_index=0):
    """Find groupWrapper, click it, then click its 'Anmelden' button."""
    wrappers = driver.find_elements(By.CLASS_NAME, "groupWrapper")
    
    if len(wrappers) > wrapper_index:
        target_wrapper = wrappers[wrapper_index]
        target_wrapper.click()
        safe_print(f"Clicked groupWrapper[{wrapper_index}]")
        time.sleep(1)
        
        # Find button inside wrapper
        anmelden_button = target_wrapper.find_element(By.XPATH, './/input[@value="Anmelden"]')
        anmelden_button.click()
        safe_print("Clicked 'Anmelden' button.")

def click_page_anmelden_button(driver):
    """Find and click the page-level 'Anmelden' submit button (no group wrapper)."""
    try:
        anmelden_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Anmelden']"))
        )
        anmelden_button.click()
        safe_print("Clicked page-level 'Anmelden' button.")
    except Exception as e:
        safe_print(f"[ERROR] Could not find/click page-level 'Anmelden' button: {e}")
    
def select_dropdown_and_submit(driver, study_number=None, subgroup_index=None):
    """
    Select study number and subgroup if provided. 
    If both are None, it just tries to submit/skip.
    """

    # --- First dropdown: study code (optional) ---
    if study_number:
        try:
            study_dropdown = WebDriverWait(driver, 1).until(
                EC.presence_of_element_located((By.ID, "regForm:studyCode"))
            )
            select_study = Select(study_dropdown)

            found = False
            for option in select_study.options:
                if study_number in option.text:  # match substring
                    select_study.select_by_visible_text(option.text)
                    safe_print(f"[OK] Selected study code: {option.text}")
                    found = True
                    break
            if not found:
                safe_print(f"[WARNING] No study code option contains '{study_number}'")
        except Exception as e:
            safe_print(f"[WARNING] Study code dropdown not found or skipped: {e}")
    else:
        safe_print("[SKIP] Skipping study code selection (no study_number provided)")

    # --- Second dropdown: subgroup list (optional) ---
    if subgroup_index is not None:
        try:
            subgroup_dropdown = WebDriverWait(driver, 1).until(
                EC.presence_of_element_located((By.ID, "regForm:subgrouplist"))
            )
            select_subgroup = Select(subgroup_dropdown)
            select_subgroup.select_by_index(subgroup_index)
            safe_print(f"[OK] Selected subgroup index: {subgroup_index}")
        except Exception as e:
            safe_print(f"[WARNING] Subgroup dropdown not found or skipped: {e}")
    else:
        safe_print("[SKIP] Skipping subgroup selection (no subgroup_index provided)")

    # --- Submit (only if any dropdown was used) ---
    if study_number or subgroup_index is not None:
        try:
            submit_button = driver.find_element(By.CSS_SELECTOR, "form input[type='submit']")
            #submit_button.click()
            safe_print("[OK] Form submitted.")
        except Exception as e:
            safe_print(f"[WARNING] Submit button not found: {e}")
    else:
        safe_print("[SKIP] Skipping form submission (no dropdowns used)")

def wait_until(target_time_str):
    """
    Wait until the given datetime string (YYYY-MM-DD HH:MM:SS).
    """
    target_time = datetime.datetime.strptime(target_time_str, "%Y-%m-%d %H:%M:%S")
    safe_print(f"[WAIT] Waiting until {target_time} to execute Anmelden...")

    while True:
        now = datetime.datetime.now()
        if now >= target_time:
            safe_print(f"[OK] Time reached: {now}, continuing...")
            break
        time.sleep(0.5)  # check every 0.5 sec

# -----------------------
# Main execution
# -----------------------
if __name__ == "__main__":
    try:
        safe_print("[START] Initializing driver...")
        driver = init_driver()
        
        # Optional login (wrap in try so script works even if login is skipped)
        try:
            safe_print("[LOGIN] Attempting login...")
            login(driver, USERNAME, PASSWORD)
        except Exception as e:
            safe_print(f"[SKIP] Skipping login: {e}")
        
        
        # Check for scheduled time
        anmelden_time = CONFIG.get("anmelden_time")
        if anmelden_time:
            wait_until(anmelden_time)
        
        # Go to course page
        safe_print("[NAVIGATE] Opening course page...")
        open_course_page(driver, COURSE_URL)

        # Click anmelden depending on mode
        if MODE == "course":
            safe_print("[ACTION] Clicking page-level Anmelden for course registration...")
            click_page_anmelden_button(driver)
        else:
            safe_print("[ACTION] Selecting group and clicking Anmelden...")
            select_group_and_click_anmelden(driver, WRAPPER_INDEX)
        
        # Handle dropdowns and submit
        safe_print("[FORM] Processing form selections...")
        select_dropdown_and_submit(driver, STUDY_NUMBER, SUBGROUP_INDEX)
        
        safe_print("[SUCCESS] Script completed successfully!")
        
    except Exception as e:
        safe_print(f"[ERROR] Script failed with error: {e}")
        raise
    finally:
        try:
            #driver.quit()
            time.sleep( 1000 )
            safe_print("[CLEANUP] Browser closed.")
        except:
            pass