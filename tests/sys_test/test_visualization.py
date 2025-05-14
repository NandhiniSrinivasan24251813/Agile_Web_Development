import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.mark.skip(reason="Requires a dataset to be uploaded first")
def test_map_visualization(authenticated_driver, live_server):
    """Test that the map visualization page loads."""
    driver = authenticated_driver
    
    # Since we can't guarantee a dataset exists, we'll just check
    # that the dashboard loads successfully
    driver.get(f"{live_server}/dashboard")
    
    # If there's a dataset, we'll try to view it
    view_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'View')]")
    
    if view_links:
        print("Found dataset to view, testing visualization")
        view_links[0].click()
        
        # Wait for visualization page
        WebDriverWait(driver, 10).until(
            lambda d: "visualize" in d.current_url
        )
        
        # Check for map container
        map_element = driver.find_elements(By.ID, "map")
        assert len(map_element) > 0, "Map not found on visualization page"
    else:
        print("No datasets found to test visualization")
        pytest.skip("No datasets available to test visualization")

@pytest.mark.skip(reason="Requires a dataset to be uploaded first")
def test_charts_visualization(authenticated_driver, live_server):
    """Test that the charts visualization works."""
    driver = authenticated_driver
    
    # First go to dashboard
    driver.get(f"{live_server}/dashboard")
    
    # Look for datasets
    view_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'View')]")
    
    if not view_links:
        pytest.skip("No datasets available to test chart visualization")
    
    # Get the first dataset's ID from the URL
    view_links[0].click()
    
    # Wait for visualization page to load
    WebDriverWait(driver, 10).until(
        lambda d: "visualize" in d.current_url
    )
    
    # Extract dataset ID from URL
    dataset_id = driver.current_url.split('/')[-1]
    
    # Navigate to charts page
    driver.get(f"{live_server}/charts/{dataset_id}")
    
    # Check that chart elements are present
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "chartCanvas"))
        )
        
        # Check chart controls
        assert driver.find_element(By.ID, "metricSelector").is_displayed()
        assert driver.find_element(By.ID, "chartType").is_displayed()
        
        # Test changing chart type
        from selenium.webdriver.support.ui import Select
        select = Select(driver.find_element(By.ID, "chartType"))
        select.select_by_value("bar")
        
        # No errors should occur
        assert len(driver.find_elements(By.XPATH, "//div[contains(@class, 'alert-danger')]")) == 0
    except:
        print("Chart visualization failed")
        print("Current URL:", driver.current_url)
        print("Page source:", driver.page_source)
        pytest.fail("Chart visualization test failed")