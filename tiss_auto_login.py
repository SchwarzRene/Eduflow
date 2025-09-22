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
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException



def load_config_from_path(config_path: str):
    # Support reading from stdin when path is '-'
    if config_path == '-':
        data = sys.stdin.read()
        return json.loads(data)
    with open(config_path, "r", encoding='utf-8') as f:
        return json.load(f)

def compute_course_url(config: dict) -> str:
    mode = (config.get("mode", "exam") or "exam").lower()
    if mode == "group":
        path = "groupList.xhtml"
    elif mode == "course":
        path = "courseRegistration.xhtml"
    else:
        path = "examDateList.xhtml"
    return (
        f"https://tiss.tuwien.ac.at/education/course/{path}"
        f"?dswid={config['dswid']}&dsrid={config['dsrid']}"
        f"&semester={config['semester']}&courseNr={config['courseNr']}"
    )

def safe_print(message):
    """Safe print function that handles Unicode characters on Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback: remove Unicode characters
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)

def is_element_present(driver, locator):
    """
    Check if element is immediately present without waiting.
    Returns True if found, False if not.
    """
    try:
        driver.find_element(*locator)
        return True
    except NoSuchElementException:
        return False

def are_elements_present(driver, locator):
    """
    Check if elements are immediately present without waiting.
    Returns list of elements if found, empty list if not.
    """
    try:
        elements = driver.find_elements(*locator)
        return elements if elements else []
    except NoSuchElementException:
        return []

def wait_for_element(driver, locator, timeout=10, description="element"):
    """
    Check element immediately first, only wait if not found.
    """
    # First check if element is already present
    if is_element_present(driver, locator):
        element = driver.find_element(*locator)
        safe_print(f"[OK] {description} found immediately.")
        return element
    
    # If not present, wait for it
    safe_print(f"[WAIT] {description} not found, waiting...")
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
        safe_print(f"[OK] {description} found after waiting.")
        return element
    except TimeoutException:
        safe_print(f"[ERROR] {description} not found within {timeout} seconds. Exiting...")
        driver.quit()
        sys.exit(1)

def wait_for_element_clickable(driver, locator, timeout=10, description="clickable element"):
    """
    Check if element is immediately clickable, only wait if not.
    """
    # First check if element exists and is enabled
    if is_element_present(driver, locator):
        element = driver.find_element(*locator)
        if element.is_enabled() and element.is_displayed():
            safe_print(f"[OK] {description} is immediately clickable.")
            return element
    
    # If not immediately clickable, wait for it
    safe_print(f"[WAIT] {description} not immediately clickable, waiting...")
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )
        safe_print(f"[OK] {description} is clickable after waiting.")
        return element
    except TimeoutException:
        safe_print(f"[ERROR] {description} not clickable within {timeout} seconds. Exiting...")
        driver.quit()
        sys.exit(1)

def wait_for_elements(driver, locator, timeout=10, description="elements"):
    """
    Check elements immediately first, only wait if not found.
    """
    # First check if elements are already present
    elements = are_elements_present(driver, locator)
    if elements:
        safe_print(f"[OK] {len(elements)} {description} found immediately.")
        return elements
    
    # If not present, wait for them
    safe_print(f"[WAIT] {description} not found, waiting...")
    try:
        elements = WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located(locator)
        )
        safe_print(f"[OK] {len(elements)} {description} found after waiting.")
        return elements
    except TimeoutException:
        safe_print(f"[ERROR] {description} not found within {timeout} seconds. Exiting...")
        driver.quit()
        sys.exit(1)

def safe_navigate_and_wait(driver, url, timeout=15, description="page"):
    """
    Navigate to URL and wait for page to be fully loaded.
    """
    safe_print(f"[NAVIGATE] Loading {description}: {url}")
    try:
        driver.get(url)
        # Wait for page to be loaded by checking document ready state
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        safe_print(f"[OK] {description} loaded successfully.")
        # No fixed delay - proceed immediately after page is ready
        return True
    except TimeoutException:
        safe_print(f"[ERROR] {description} failed to load within {timeout} seconds. Exiting...")
        driver.quit()
        sys.exit(1)
    except Exception as e:
        safe_print(f"[ERROR] Failed to navigate to {description}: {e}")
        driver.quit()
        sys.exit(1)

def safe_click_element(driver, element, description="element"):
    """
    Safely click an element with retry logic but no unnecessary delays.
    """
    max_retries = 10
    for attempt in range(max_retries):
        try:
            element.click()
            safe_print(f"[OK] Successfully clicked {description}.")
            return True
        except Exception as e:
            safe_print(f"[WARNING] Click attempt {attempt + 1} failed for {description}: {e}")
            if attempt < max_retries - 1:
                time.sleep(0.2)  # Only wait between retries
            else:
                safe_print(f"[ERROR] Failed to click {description} after {max_retries} attempts. Exiting...")
                driver.quit()
                sys.exit(1)
    return False

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
    safe_navigate_and_wait(driver, "https://tiss.tuwien.ac.at/admin/authentifizierung", timeout=15, description="login page")
    
    # Wait for username field
    username_field = wait_for_element(driver, (By.ID, "username"), timeout=15, description="username field")
    username_field.send_keys(username)

    # Wait for password field
    password_field = wait_for_element(driver, (By.ID, "password"), timeout=10, description="password field")
    password_field.send_keys(password)

    # Wait for login button and click
    login_button = wait_for_element_clickable(driver, (By.ID, "samlloginbutton"), timeout=10, description="login button")
    safe_click_element(driver, login_button, "login button")
    
    safe_print("Login submitted.")
    
    # Wait for redirect/login completion - only if still on auth page
    current_url = driver.current_url.lower()
    if "authentifizierung" in current_url:
        try:
            WebDriverWait(driver, 10).until(
                lambda d: "authentifizierung" not in d.current_url.lower()
            )
            safe_print("[OK] Login redirect completed.")
        except TimeoutException:
            safe_print("[WARNING] Login redirect timeout - may still be successful.")
    else:
        safe_print("[OK] Already redirected from login page.")

def open_course_page(driver, url):
    """Navigate to course page after login (or without login)."""
    safe_navigate_and_wait(driver, url, timeout=15, description="course page")
    
    # Check immediately for page content, only wait if needed
    if are_elements_present(driver, (By.CLASS_NAME, "groupWrapper")):
        safe_print("[OK] Group wrappers found immediately.")
    elif is_element_present(driver, (By.XPATH, "//input[@type='submit' and @value='Anmelden']")):
        safe_print("[OK] Course registration button found immediately.")
    else:
        # Need to wait for content to load
        safe_print("[WAIT] Page content not immediately available, waiting...")
        try:
            # Try to find group wrappers first
            wait_for_element(driver, (By.CLASS_NAME, "groupWrapper"), timeout=10, description="group wrappers")
        except SystemExit:
            # If group wrappers not found, try for course registration page
            try:
                wait_for_element(driver, (By.XPATH, "//input[@type='submit' and @value='Anmelden']"), 
                               timeout=5, description="course registration button")
            except SystemExit:
                safe_print("[ERROR] Neither group wrappers nor course registration button found. Page may not have loaded correctly.")
                driver.quit()
                sys.exit(1)
    
    safe_print("Course page ready for interaction.")

def select_group_and_click_anmelden(driver, wrapper_index=0):
    """Find groupWrapper, click it, then click its 'Anmelden' button."""
    # Get group wrappers (already checked in open_course_page)
    wrappers = wait_for_elements(driver, (By.CLASS_NAME, "groupWrapper"), timeout=15, description="group wrappers")
    
    # Check if the requested index exists
    if len(wrappers) <= wrapper_index:
        safe_print(f"[ERROR] Requested group index {wrapper_index} not available. Found {len(wrappers)} groups. Exiting...")
        driver.quit()
        sys.exit(1)
    
    target_wrapper = wrappers[wrapper_index]
    safe_click_element(driver, target_wrapper, f"group wrapper [{wrapper_index}]")
    
    # Find and click the Anmelden button inside the wrapper
    try:
        anmelden_button = target_wrapper.find_element(By.XPATH, './/input[@value="Anmelden"]')
        safe_click_element(driver, anmelden_button, "'Anmelden' button in group wrapper")
    except NoSuchElementException:
        safe_print(f"[ERROR] 'Anmelden' button not found in group wrapper [{wrapper_index}]. Exiting...")
        driver.quit()
        sys.exit(1)

def click_page_anmelden_button(driver):
    """Find and click the page-level 'Anmelden' submit button (no group wrapper)."""
    anmelden_button = wait_for_element_clickable(driver, 
                                                (By.XPATH, "//input[@type='submit' and @value='Anmelden']"),
                                                timeout=10, 
                                                description="page-level 'Anmelden' button")
    safe_click_element(driver, anmelden_button, "page-level 'Anmelden' button")
    
def select_dropdown_and_submit(driver, study_number=None, subgroup_index=None):
    """
    Select study number and subgroup if provided. 
    If both are None, it just tries to submit/skip.
    """
    form_found = False

    # --- First dropdown: study code (optional) ---
    if len( study_number ) > 0:
        if is_element_present(driver, (By.ID, "regForm:studyCode")):
            study_dropdown = driver.find_element(By.ID, "regForm:studyCode")
            safe_print("[OK] Study code dropdown found immediately.")
            form_found = True
        else:
            try:
                study_dropdown = wait_for_element(driver, (By.ID, "regForm:studyCode"), timeout=5, description="study code dropdown")
                form_found = True
            except SystemExit:
                safe_print(f"[WARNING] Study code dropdown not found. Skipping study code selection.")
                study_dropdown = None

        if study_dropdown:
            select_study = Select(study_dropdown)
            found = False
            for option in select_study.options:
                if study_number in option.text:  # match substring
                    select_study.select_by_visible_text(option.text)
                    safe_print(f"[OK] Selected study code: {option.text}")
                    found = True
                    break
            if not found:
                safe_print(f"[ERROR] No study code option contains '{study_number}'. Exiting...")
                driver.quit()
                sys.exit(1)
    else:
        safe_print("[SKIP] Skipping study code selection (no study_number provided)")

    # --- Second dropdown: subgroup list (optional) ---
    if len( subgroup_index ) > 0:
        if is_element_present(driver, (By.ID, "regForm:subgrouplist")):
            subgroup_dropdown = driver.find_element(By.ID, "regForm:subgrouplist")
            safe_print("[OK] Subgroup dropdown found immediately.")
            form_found = True
        else:
            try:
                subgroup_dropdown = wait_for_element(driver, (By.ID, "regForm:subgrouplist"), timeout=5, description="subgroup dropdown")
                form_found = True
            except SystemExit:
                safe_print(f"[WARNING] Subgroup dropdown not found. Skipping subgroup selection.")
                subgroup_dropdown = None

        if subgroup_dropdown:
            select_subgroup = Select(subgroup_dropdown)
            
            subgroup_index = int( subgroup_index )
            # Check if the index is valid
            if subgroup_index >= len(select_subgroup.options):
                safe_print(f"[ERROR] Subgroup index {subgroup_index} not available. Found {len(select_subgroup.options)} options. Exiting...")
                driver.quit()
                sys.exit(1)
                
            select_subgroup.select_by_index(subgroup_index)
            safe_print(f"[OK] Selected subgroup index: {subgroup_index}")
    else:
        safe_print("[SKIP] Skipping subgroup selection (no subgroup_index provided)")

    # --- Submit (only if any dropdown was used) ---
    if form_found:
        if is_element_present(driver, (By.CSS_SELECTOR, "form input[type='submit']")):
            submit_button = driver.find_element(By.CSS_SELECTOR, "form input[type='submit']")
            if submit_button.is_enabled() and submit_button.is_displayed():
                #safe_click_element(driver, submit_button, "form submit button")
                safe_print("[OK] Form submitted.")
            else:
                safe_print("[WARNING] Submit button found but not clickable.")
        else:
            try:
                submit_button = wait_for_element_clickable(driver, (By.CSS_SELECTOR, "form input[type='submit']"), 
                                                         timeout=10, description="form submit button")
                safe_click_element(driver, submit_button, "form submit button")
                safe_print("[OK] Form submitted.")
            except SystemExit:
                safe_print("[WARNING] Submit button not found. Form may have been submitted automatically.")
    else:
        safe_print("[SKIP] Skipping form submission (no dropdowns used or found)")

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
        time.sleep(0.2)  # check every 0.5 sec

def run_with_config(config: dict):
    """Run the automation using a provided configuration dictionary."""
    username = config["username"]
    password = config["password"]
    wrapper_index = config["group_index"]
    study_number = config.get("study_number") or None
    subgroup_index = config.get("slot_index")
    if subgroup_index == "" or subgroup_index is None:
        subgroup_index = None
    course_url = compute_course_url(config)
    mode = (config.get("mode", "exam") or "exam").lower()

    driver = None
    try:
        safe_print("[START] Initializing driver...")
        driver = init_driver()

        # Detect if login is required (presence of username field) and perform login
        try:
            login(driver, username, password)
        except SystemExit:
            raise
        except Exception as e:
            safe_print(f"[DETECT] No explicit login page detected or login failed: {e}")
            safe_print("[WARNING] Continuing without login - may already be authenticated.")

        # Wait first if a future time is specified, otherwise proceed immediately
        anmelden_time = config.get("anmelden_time")
        if anmelden_time:
            try:
                target_dt = datetime.datetime.strptime(anmelden_time, "%Y-%m-%d %H:%M:%S")
                now_dt = datetime.datetime.now()
                if now_dt < target_dt:
                    wait_until(anmelden_time)
                else:
                    safe_print("[INFO] Scheduled time is in the past, proceeding immediately.")
            except Exception as e:
                safe_print(f"[WARNING] Could not parse anmelden_time '{anmelden_time}': {e}. Proceeding immediately.")

        safe_print("[NAVIGATE] Opening course page...")
        try:
            open_course_page(driver, course_url)
        except SystemExit:
            raise
        except WebDriverException as e:
            safe_print(f"[ERROR] Failed to open course page: {e}")
            if driver:
                driver.quit()
            sys.exit(1)

        if mode == "course":
            safe_print("[ACTION] Clicking page-level Anmelden for course registration...")
            click_page_anmelden_button(driver)
        else:
            safe_print("[ACTION] Selecting group and clicking Anmelden...")
            select_group_and_click_anmelden(driver, wrapper_index)

        safe_print("[FORM] Processing form selections...")
        select_dropdown_and_submit(driver, study_number, subgroup_index)

        safe_print("[SUCCESS] Script completed successfully!")
        
    except SystemExit:
        # Re-raise SystemExit to maintain exit behavior
        raise
    except Exception as e:
        safe_print(f"[ERROR] Unexpected error occurred: {e}")
        if driver:
            driver.quit()
        sys.exit(1)
    finally:
        if driver:
            try:
                # Keep browser open for a moment to see results, but shorter duration
                safe_print("[INFO] Keeping browser open for 5 seconds to view results...")
                driver.quit()
                safe_print("[CLEANUP] Browser closed.")
            except Exception:
                pass


# -----------------------
# CLI entry point
# -----------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run TISS auto registration with a given config file.")
    parser.add_argument("--config", dest="config_path", default="config.json", help="Path to config JSON file or '-' for stdin")
    args, _ = parser.parse_known_args()

    try:
        config_obj = load_config_from_path(args.config_path)
        run_with_config(config_obj)
    except Exception as e:
        safe_print(f"[ERROR] Script failed with error: {e}")
        sys.exit(1)