import os
import sys
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import tempfile
import shutil
import uuid
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Now we can import from the app module
from app import app as flask_app

@pytest.fixture(scope="function")
def app():
    """Create and configure a Flask app for testing."""
    # Create temporary directories for uploads and data
    test_upload_folder = tempfile.mkdtemp()
    test_data_folder = tempfile.mkdtemp()
    
    # Create a unique database URL for each test to avoid conflicts
    db_fd, db_path = tempfile.mkstemp()
    db_url = f'sqlite:///{db_path}'
    
    # Configure app for testing
    flask_app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,  # Disable CSRF for testing
        'SQLALCHEMY_DATABASE_URI': db_url,
        'UPLOAD_FOLDER': test_upload_folder,
        'DATA_FOLDER': test_data_folder,
    })
    
    # Create all tables in the test database
    with flask_app.app_context():
        from models import db
        db.create_all()
    
    yield flask_app
    
    # Clean up
    os.close(db_fd)
    os.unlink(db_path)
    shutil.rmtree(test_upload_folder)
    shutil.rmtree(test_data_folder)

@pytest.fixture(scope="function")
def driver():
    """Set up WebDriver for Selenium tests."""
    options = webdriver.ChromeOptions()
    # Uncomment for headless mode in CI environments:
    # options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Set up Chrome driver
    service = Service(ChromeDriverManager().install())
    chrome_driver = webdriver.Chrome(service=service, options=options)
    chrome_driver.implicitly_wait(10)  # Wait up to 10 seconds for elements
    chrome_driver.set_window_size(1920, 1080)
    
    yield chrome_driver
    
    # Quit the driver after each test
    chrome_driver.quit()

@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()

@pytest.fixture
def live_server(app):
    """Run the app in a live server for Selenium tests."""
    # Use Flask's development server (minimal version for testing)
    import threading
    from werkzeug.serving import make_server

    server = make_server('localhost', 5000, app)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    yield "http://localhost:5000"
    
    # Shutdown the server after the test
    server.shutdown()

@pytest.fixture
def test_user(app):
    """Create a unique test user without logging in."""
    # Generate a unique identifier for this test run
    unique_id = uuid.uuid4().hex[:8]
    username = f"testuser_{unique_id}"
    email = f"test_{unique_id}@example.com"
    password = "testpassword"
    
    with app.app_context():
        from models import db, User
        
        # Create a test user
        test_user = User(
            username=username,
            email=email
        )
        test_user.set_password(password)
        
        db.session.add(test_user)
        db.session.commit()
        
        # Return the user credentials
        return {
            'username': username,
            'email': email,
            'password': password,
            'id': test_user.id
        }

@pytest.fixture
def auth_user(app, client, test_user):
    """Log in the test user using Flask test client."""
    # Log in as the test user
    with client.session_transaction() as sess:
        client.post('/login', data={
            'username': test_user['username'],
            'password': test_user['password']
        }, follow_redirects=True)
    
    return test_user

@pytest.fixture
def authenticated_driver(driver, live_server, test_user):
    """Create a WebDriver instance with an authenticated session."""
    # Login with Selenium
    driver.get(f"{live_server}/login")
    driver.find_element(By.ID, "username").send_keys(test_user['username'])
    driver.find_element(By.ID, "password").send_keys(test_user['password'])
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    
    # Wait for login to complete and dashboard to appear
    try:
        # Try to wait for the dashboard to appear
        WebDriverWait(driver, 10).until(
            lambda d: "/dashboard" in d.current_url or 
                     any(element.is_displayed() for element in 
                         d.find_elements(By.XPATH, 
                            "//h1[contains(text(), 'Dashboard')] | " +
                            "//*[contains(text(), 'Your Datasets')]"))
        )
    except Exception as e:
        # Print debug info if login fails
        print(f"Login failed: {e}")
        print("Current URL:", driver.current_url)
        print("Page title:", driver.title)
        print("Page source:", driver.page_source)
    
    return driver

@pytest.fixture
def test_csv_path():
    """Provide a path to a test CSV file."""
    # Create the fixtures directory if it doesn't exist
    current_dir = os.path.dirname(os.path.abspath(__file__))
    fixtures_dir = os.path.join(current_dir, 'fixtures')
    os.makedirs(fixtures_dir, exist_ok=True)
    
    csv_path = os.path.join(fixtures_dir, 'test_data.csv')
    
    # Create a test CSV file if it doesn't exist
    if not os.path.exists(csv_path):
        with open(csv_path, 'w') as f:
            f.write("date,location,cases,deaths,recovered,latitude,longitude\n")
            f.write("2023-01-01,New York,100,5,50,40.7128,-74.0060\n")
            f.write("2023-01-02,New York,120,7,60,40.7128,-74.0060\n")
            f.write("2023-01-03,New York,150,10,70,40.7128,-74.0060\n")
            f.write("2023-01-01,Los Angeles,80,3,40,34.0522,-118.2437\n")
            f.write("2023-01-02,Los Angeles,95,4,45,34.0522,-118.2437\n")
            f.write("2023-01-03,Los Angeles,110,6,55,34.0522,-118.2437\n")
    
    return csv_path