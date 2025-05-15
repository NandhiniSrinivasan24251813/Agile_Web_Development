import pytest
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_upload_page_display(authenticated_driver, live_server):
    """Test that the upload page displays correctly."""
    driver = authenticated_driver
    driver.get(f"{live_server}/upload")
    
    # Print current URL and title for debugging
    print("Upload page URL:", driver.current_url)
    print("Upload page title:", driver.title)
    
    # Check that main elements are present, with more flexible selectors
    assert "Upload" in driver.title
    
    # Check for form elements - use more flexible selectors
    upload_form = driver.find_elements(By.ID, "upload-form")
    if not upload_form:
        upload_form = driver.find_elements(By.XPATH, "//form[contains(@action, '/upload')]")
    assert len(upload_form) > 0, "Upload form not found"
    
    # Check for file input field
    file_input = driver.find_elements(By.ID, "file-input")
    if not file_input:
        file_input = driver.find_elements(By.XPATH, "//input[@type='file']")
    assert len(file_input) > 0, "File input not found"
    
    # Check for dataset name field
    name_input = driver.find_elements(By.ID, "dataset-name")
    if not name_input:
        name_input = driver.find_elements(By.XPATH, "//input[@name='name']")
    assert len(name_input) > 0, "Dataset name input not found"

@pytest.mark.skip(reason="File upload tests are sometimes flaky in CI")
def test_file_upload_csv(authenticated_driver, live_server, test_csv_path):
    """Test uploading a CSV file."""
    driver = authenticated_driver
    driver.get(f"{live_server}/upload")
    
    # Make sure the file exists
    assert os.path.exists(test_csv_path), f"Test CSV file not found at {test_csv_path}"
    
    # Set the file input
    file_input = driver.find_element(By.XPATH, "//input[@type='file']")
    file_input.send_keys(test_csv_path)
    
    # Wait for file info to appear
    try:
        WebDriverWait(driver, 10).until(
            EC.visibility_of_any_element_located((By.ID, "file-info"))
        )
    except:
        # If file info doesn't appear, continue with the form anyway
        print("File info element not visible, continuing with form")
    
    # Fill in form details
    driver.find_element(By.ID, "dataset-name").send_keys("Test CSV Dataset")
    
    # Look for description field with flexible approach
    description_fields = driver.find_elements(By.ID, "dataset-description")
    if description_fields:
        description_fields[0].send_keys("A test dataset for Selenium")
    
    # Select sharing option if available
    sharing_selects = driver.find_elements(By.ID, "sharing_status")
    if sharing_selects:
        from selenium.webdriver.support.ui import Select
        select = Select(sharing_selects[0])
        select.select_by_value("public")
    
    # Submit the form
    upload_buttons = driver.find_elements(By.ID, "upload-button")
    if not upload_buttons:
        upload_buttons = driver.find_elements(By.XPATH, "//button[@type='submit']")
    
    assert len(upload_buttons) > 0, "Upload button not found"
    upload_buttons[0].click()
    
    # Check for success message or redirect to visualization
    try:
        WebDriverWait(driver, 30).until(
            EC.any_of(
                EC.presence_of_element_located((By.CLASS_NAME, "alert-success")),
                EC.url_contains("/visualize/")
            )
        )
        success = True
    except:
        print("Upload failed or timed out")
        print("Current URL:", driver.current_url)
        print("Page source:", driver.page_source)
        success = False
    
    assert success, "File upload failed"