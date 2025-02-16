from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

service = Service(executable_path="/Users/trippuroskie/Desktop/Projects/Selenium/ParkingResBot/chromedriver")
driver = webdriver.Chrome(service=service)

try:
    # Navigate to select-parking page
    driver.get("https://reservenski.parkbrightonresort.com/select-parking")
    time.sleep(5)
    
    # Find and click the date cell
    date_cell = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.mbsc-calendar-cell-text[aria-label*='January 11']"))
    )
    print(f"Found date cell: {date_cell.get_attribute('outerHTML')}")
    
    # Click using JavaScript
    driver.execute_script("arguments[0].click();", date_cell)
    print("Clicked date cell")
    
    # Wait for either the "Sold Out" message or parking rates to appear
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Sold Out')] | //*[contains(text(), 'Parking rate')]"))
        )
        
        # Check what content appeared
        page_content = driver.find_element(By.TAG_NAME, "body").text
        if "Sold Out" in page_content:
            print("Date is sold out")
            sold_out_message = driver.find_element(By.XPATH, "//*[contains(text(), 'Parking lot is sold out')]")
            print(f"Message shown: {sold_out_message.text}")
        else:
            print("Parking rates available")
            rates = driver.find_elements(By.CSS_SELECTOR, "[class*='rate'], [class*='price']")
            for rate in rates:
                print(f"Rate found: {rate.text}")
        
        # Check if the date is shown in the header
        try:
            date_header = driver.find_element(By.XPATH, "//*[contains(text(), 'SAT JAN 11, 2025')]")
            print(f"Date header found: {date_header.text}")
        except:
            print("Date header not found")
            
    except Exception as e:
        print(f"Error waiting for content: {e}")
        
    # Print the current state
    print(f"Current URL: {driver.current_url}")
    print(f"Page title: {driver.title}")

except Exception as e:
    print(f"An error occurred: {e}")
    print(f"Current URL: {driver.current_url}")

finally:
    driver.quit()
