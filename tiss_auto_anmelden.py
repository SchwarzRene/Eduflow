# -*- coding: utf-8 -*-
import json
import time
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import datetime

# Force UTF-8 encoding for Windows console
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Set environment variable for proper encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

with open("config.json", "r", encoding='utf-8') as f:
    CONFIG = json.load(f)

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
else:
    PATH = "examDateList.xhtml"

COURSE_URL = (
    f"https://tiss.tuwien.ac.at/education/course/{PATH}"
    f"?dswid={CONFIG['dswid']}&dsrid={CONFIG['dsrid']}"
    f"&semester={CONFIG['semester']}&courseNr={CONFIG['courseNr']}"
)

print(f"Using URL: {COURSE_URL}")

def safe_print(message):
    """Safe print function that handles Unicode characters on Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback: remove Unicode characters
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)

def init_driver():
    driver = webdriver.Chrome()

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # no GUI
    driver = webdriver.Chrome(options=chrome_options)

    return driver

def login(driver, username, password):
    """Go to login page and log in with given credentials."""
    driver.get("https://idp.zid.tuwien.ac.at/")
    
    try:
        # Wait until username field is visible
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))
        
        driver.find_element(By.ID, "username").send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.ID, "samlloginbutton").click()
        
        safe_print("Login submitted.")
        # Wait until redirect finishes (optional: check for some post-login element)
        time.sleep(3)
    except Exception as e:
        safe_print(f"Login page not available or skipped: {e}")

def open_course_page(driver, url):
    """Navigate to course page after login (or without login)."""
    driver.get(url)
    # Wait for page to load
    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "groupWrapper")))
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
    else:
        safe_print(f"Not enough groupWrapper elements. Needed {wrapper_index+1}, got {len(wrappers)}")

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

        # Select groupWrapper and click anmelden
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
            driver.quit()
            safe_print("[CLEANUP] Browser closed.")
        except:
            pass