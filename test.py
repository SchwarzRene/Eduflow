import requests

# Replace these with your credentials
USERNAME = "12521990"
PASSWORD = "MwhefaP8z12B"

COURSE_URL = "https://tiss.tuwien.ac.at/education/course/examDateList.xhtml?dswid=7938&dsrid=805&semester=2025W&courseNr=101A26"
LOGIN_URL = "https://idp.zid.tuwien.ac.at/"

def login_with_session(username, password):
    session = requests.Session()
    
    # Get login page to retrieve hidden fields
    resp = session.get(LOGIN_URL)
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, "html.parser")
    
    hidden_inputs = soup.find_all("input", type="hidden")
    payload = {i['name']: i['value'] for i in hidden_inputs if i.has_attr('name')}
    
    payload["username"] = username
    payload["password"] = password
    
    # POST login form
    login_response = session.post(LOGIN_URL, data=payload)
    return session, login_response

session, login_response = login_with_session(USERNAME, PASSWORD)

# Access the course page
course_response = session.get(COURSE_URL)

# Check if "logout" exists in the HTML
if "logout" in course_response.text.lower():
    print("[OK] Logged in successfully, 'logout' found on page")
else:
    print("[FAIL] Login failed, 'logout' not found")
