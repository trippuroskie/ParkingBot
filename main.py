import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
from datetime import datetime
from dotenv import load_dotenv

def log_with_timestamp(*args):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    message = " ".join(str(arg) for arg in args)
    print(f"[{timestamp}] {message}")

class ReserveDate:
    def __init__(self, chromedriver_path=None):
        load_dotenv()
        # Set up Chrome options for headless mode
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument('--enable-javascript')
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
        chrome_options.add_argument("--accept-lang=en-US")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        })
        
        # Use webdriver-manager to handle ChromeDriver installation and versioning
        self.service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=self.service, options=chrome_options)
        
        # Set page load timeout
        self.driver.set_page_load_timeout(30)
        self.wait = WebDriverWait(self.driver, 20)  # Increased wait time
        self.calendar_wait = WebDriverWait(self.driver, 30)  # Increased calendar wait time
        
        # Execute CDP commands to prevent detection
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })

    def login(self, username, password):
        try:
            log_with_timestamp("Attempting to navigate to login page...")
            self.driver.get("https://reservenski.parkbrightonresort.com/login")
            
            log_with_timestamp("Waiting for email field...")
            email_element = self.wait.until(EC.presence_of_element_located((By.ID, "emailAddress")))
            email_element.clear()
            time.sleep(1)
            for char in username:
                email_element.send_keys(char)
                time.sleep(0.1)
            
            log_with_timestamp("Entering password...")
            password_element = self.driver.find_element(By.ID, "password")
            password_element.clear()
            time.sleep(1)
            for char in password:
                password_element.send_keys(char)
                time.sleep(0.1)
            
            log_with_timestamp("Looking for login button...")
            try:
                login_button = self.wait.until(EC.element_to_be_clickable((
                    By.CSS_SELECTOR, "button.Login_submitButton__fMHAq"
                )))
            except:
                try:
                    login_button = self.wait.until(EC.element_to_be_clickable((
                        By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Sign In')]"
                    )))
                except:
                    login_button = self.wait.until(EC.element_to_be_clickable((
                        By.CSS_SELECTOR, "button[type='submit']"
                    )))
            
            log_with_timestamp("Clicking login button...")
            self.driver.execute_script("arguments[0].click();", login_button)
            
            # Wait for login to complete and verify
            log_with_timestamp("Waiting for login to complete...")
            time.sleep(5)
            
            # Verify login success by checking URL or specific elements
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                current_url = self.driver.current_url
                log_with_timestamp(f"Current URL: {current_url}")
                
                if "login" not in current_url.lower():
                    log_with_timestamp("Login successful - URL changed from login page")
                    break
                    
                try:
                    # Check if we can find any error messages
                    error_messages = self.driver.find_elements(By.CSS_SELECTOR, "[class*='error'], [class*='alert']")
                    if error_messages:
                        log_with_timestamp("Found error messages:", [msg.text for msg in error_messages])
                        raise Exception("Login failed - error message found")
                except:
                    pass
                
                retry_count += 1
                if retry_count < max_retries:
                    log_with_timestamp(f"Login verification attempt {retry_count + 1}/{max_retries}...")
                    time.sleep(3)
            
            if retry_count >= max_retries:
                raise Exception("Failed to verify login success after multiple attempts")
            
            log_with_timestamp("Login sequence completed and verified")
            
        except Exception as e:
            log_with_timestamp(f"Error during login: {str(e)}")
            log_with_timestamp(f"Current URL: {self.driver.current_url}")
            log_with_timestamp("Page source:")
            log_with_timestamp(self.driver.page_source[:1000])
            raise

    def navigate_to_calendar(self):
        try:
            log_with_timestamp("Waiting for page to load after login...")
            time.sleep(5)  # Give more time for the page to settle after login
            
            log_with_timestamp("Looking for 'Reserve a Parking Spot' link...")
            reserve_link = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, "//div[contains(text(), 'Reserve a Parking Spot')]"
            )))
            
            log_with_timestamp("Found link, attempting to click...")
            try:
                reserve_link.click()
            except:
                try:
                    self.driver.execute_script("arguments[0].click();", reserve_link)
                except:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(reserve_link).click().perform()
            
            log_with_timestamp("Clicked reserve link, waiting for calendar to load...")
            time.sleep(3)
            log_with_timestamp("Calendar navigation completed")
            
        except Exception as e:
            log_with_timestamp(f"Error in navigate_to_calendar: {str(e)}")
            log_with_timestamp(f"Current URL: {self.driver.current_url}")
            log_with_timestamp("Page source:")
            log_with_timestamp(self.driver.page_source[:1000])  # Print first 1000 chars of page source
            raise

    def check_date_availability(self, target_date_element):
        """Helper method to check if date has the available (green) background color"""
        try:
            background_color = target_date_element.value_of_css_property('background-color')
            target_color = "rgba(49, 200, 25, 0.2)"
            return background_color == target_color
        except Exception as e:
            log_with_timestamp(f"Error checking date availability: {e}")
            return False

    def select_date(self, target_date_text, max_attempts, sleep_duration):
        attempt = 0
        
        while attempt < max_attempts:
            try:
                calendar_iframe = None
                
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    src = iframe.get_attribute('src') or ''
                    if 'doubleclick' not in src.lower() and 'analytics' not in src.lower():
                        calendar_iframe = iframe
                        break
                
                if calendar_iframe:
                    self.driver.switch_to.frame(calendar_iframe)
                
                calendar_container = self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "mbsc-calendar-wrapper"))
                )
                
                date_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, "div.mbsc-calendar-cell-text.mbsc-calendar-day-text"
                )
                
                target_date = None
                for date in date_elements:
                    if date.is_displayed() and date.text == str(target_date_text):
                        target_date = date
                        break
                
                if target_date:
                    if self.check_date_availability(target_date):
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", target_date)
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", target_date)
                        log_with_timestamp(f"Successfully selected available date {target_date_text}")
                        break
                    else:
                        log_with_timestamp(f"Date {target_date_text} not available yet. Refreshing...")
                        time.sleep(sleep_duration)
                        self.driver.refresh()
                        attempt += 1
                else:
                    log_with_timestamp(f"Could not find date element {target_date_text}")
                    break
                    
                if calendar_iframe:
                    self.driver.switch_to.default_content()
                    
            except Exception as e:
                log_with_timestamp(f"Error in select_date: {e}")
                if calendar_iframe:
                    self.driver.switch_to.default_content()
                attempt += 1
                time.sleep(5)
                self.driver.refresh()

        if attempt >= max_attempts:
            raise Exception(f"Failed to find available date after {max_attempts} attempts")

    def select_carpool(self):
        try:
            carpool_element = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, "//div[text()='4+ Carpool (Occupancy will be verified by Parking Ambassador upon arrival)']"
            )))
            
            try:
                carpool_element.click()
            except:
                try:
                    self.driver.execute_script("arguments[0].click();", carpool_element)
                except:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(carpool_element).click().perform()
                    
        except Exception as e:
            log_with_timestamp(f"Error in select_carpool: {e}")

    def checkout(self):
        try:
            # Updated selector to match the exact button structure
            checkout_button = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, "//div[contains(@class, 'ui basic center aligned segment')]//div[contains(text(), 'Pay $10.00 & Park')]"
            )))
            
            # Get the parent button element
            parent_button = checkout_button.find_element(
                By.XPATH, "./ancestor::button"
            )
            
            try:
                parent_button.click()
            except:
                try:
                    self.driver.execute_script("arguments[0].click();", parent_button)
                except:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(parent_button).click().perform()
                    
        except Exception as e:
            log_with_timestamp(f"Error in checkout: {e}")

    def confirm_reservation(self):
        try:
            log_with_timestamp("Waiting for payment page to load...")
            time.sleep(5)  # Give page time to settle
            
            # First check if we're on the Honk payment page
            current_url = self.driver.current_url
            log_with_timestamp(f"Current URL: {current_url}")
            
            if "honkmobile.com/checkout" in current_url:
                log_with_timestamp("Detected Honk payment page, looking for payment button...")
                
                # Updated payment button selectors based on the actual HTML structure
                payment_selectors = [
                    "//div[contains(@class, 'ui basic center aligned segment')]//div[contains(text(), 'Pay $10.00 & Park')]",
                    "//div[contains(@class, 'ui basic center aligned segment')]//div[text()='Pay $10.00 & Park']",
                    "//button//div[contains(text(), 'Pay $10.00 & Park')]",
                    "//div[contains(@data-uw-rm-sr, 'Pay $10.00 & Park')]"
                ]
                
                payment_button = None
                for selector in payment_selectors:
                    try:
                        log_with_timestamp(f"Trying payment selector: {selector}")
                        payment_button = self.wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                        if payment_button and payment_button.is_displayed():
                            log_with_timestamp(f"Found payment button with selector: {selector}")
                            # Get the parent button if we found a div
                            if payment_button.tag_name.lower() != 'button':
                                payment_button = payment_button.find_element(By.XPATH, "./ancestor::button")
                            break
                    except Exception as e:
                        log_with_timestamp(f"Payment selector {selector} failed: {str(e)}")
                        continue
                
                if not payment_button:
                    log_with_timestamp("Could not find payment button. Page source:")
                    log_with_timestamp(self.driver.page_source[:2000])
                    raise Exception("Payment button not found")
                
                # Try to click the payment button
                try:
                    log_with_timestamp("Attempting to click payment button...")
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", payment_button)
                    time.sleep(1)
                    self.driver.execute_script("arguments[0].click();", payment_button)
                    log_with_timestamp("Payment button clicked")
                except Exception as e:
                    log_with_timestamp(f"Error clicking payment button: {str(e)}")
                    raise

                # Wait for and handle the license plate confirmation dialog
                log_with_timestamp("Waiting for license plate confirmation dialog...")
                try:
                    # Wait for the confirmation dialog title
                    self.wait.until(EC.presence_of_element_located((
                        By.XPATH, "//h1[contains(@class, 'PurchaseConfirm--header') and contains(text(), 'Does this look right?')]"
                    )))
                    log_with_timestamp("Found license plate confirmation dialog")

                    # Look for and click the Confirm button using the specific class
                    confirm_button = self.wait.until(EC.element_to_be_clickable((
                        By.XPATH, "//button[contains(@class, 'oGMkMQAoYbD7f3oxRBJI ButtonComponent')]"
                    )))
                    log_with_timestamp("Found confirm button")
                    
                    # Click the confirm button
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", confirm_button)
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", confirm_button)
                        log_with_timestamp("Clicked confirm button")
                    except Exception as e:
                        log_with_timestamp(f"Error clicking confirm button: {str(e)}")
                        raise
                except Exception as e:
                    log_with_timestamp(f"Error handling license plate confirmation: {str(e)}")
                    raise Exception("Failed to confirm license plate")
                
                # Wait for payment processing and verify success
                log_with_timestamp("Waiting for payment to process...")
                max_wait_time = 30
                start_time = time.time()
                success_verified = False
                initial_url = self.driver.current_url
                
                while time.time() - start_time < max_wait_time and not success_verified:
                    try:
                        current_url = self.driver.current_url
                        log_with_timestamp(f"Current URL during verification: {current_url}")
                        
                        # Only consider success if URL has changed from the initial checkout URL
                        if current_url != initial_url:
                            # Check for success indicators in URL
                            success_url_indicators = [
                                "post-purchase" in current_url,
                                "confirmation" in current_url,
                                "success" in current_url,
                                "receipt" in current_url,
                                "parking-reservation/" in current_url  # Add this new success indicator
                            ]
                            
                            if any(success_url_indicators):
                                # Additional verification - look for success elements or vehicle plate display
                                try:
                                    success_elements = self.driver.find_elements(By.XPATH,
                                        "//*[contains(text(), 'Success') or contains(text(), 'Confirmed') or contains(text(), 'Thank you') or contains(text(), 'Receipt') or contains(@class, 'ParkingSession_plate__')]"
                                    )
                                    if success_elements:
                                        success_messages = [elem.text for elem in success_elements if elem.is_displayed() and elem.text.strip()]
                                        if success_messages:
                                            log_with_timestamp("Found success indicators:", success_messages)
                                            success_verified = True
                                            break
                                        
                                    # Additional check specifically for the vehicle plate display
                                    plate_elements = self.driver.find_elements(By.CLASS_NAME, "ParkingSession_plate__q3j4i")
                                    if plate_elements:
                                        for elem in plate_elements:
                                            if elem.is_displayed() and elem.text.strip():
                                                log_with_timestamp("Found vehicle plate display:", elem.text)
                                                success_verified = True
                                                break
                                except Exception as e:
                                    log_with_timestamp(f"Error checking success elements: {e}")
                                    pass
                        
                        # Check for error messages
                        error_elements = self.driver.find_elements(By.XPATH, 
                            "//*[contains(@class, 'error') or contains(@class, 'alert') or contains(@class, 'notification')]"
                        )
                        if error_elements:
                            error_messages = [elem.text for elem in error_elements if elem.is_displayed() and elem.text.strip()]
                            if error_messages:
                                log_with_timestamp("Found error messages:", error_messages)
                                raise Exception(f"Payment failed with errors: {', '.join(error_messages)}")
                        
                        time.sleep(2)
                        log_with_timestamp("Still waiting for confirmation...")
                        
                    except Exception as e:
                        if "Payment failed with errors" in str(e):
                            raise
                        log_with_timestamp(f"Error during verification: {str(e)}")
                        time.sleep(2)
                
                if not success_verified:
                    log_with_timestamp("Payment verification failed. Current page source:")
                    log_with_timestamp(self.driver.page_source[:2000])
                    raise Exception("Could not verify payment success - URL never changed from checkout page")
                
                log_with_timestamp("Payment completed and verified successfully!")
            else:
                raise Exception(f"Unexpected URL: {current_url}")
            
        except Exception as e:
            log_with_timestamp(f"Error in confirm_reservation: {str(e)}")
            log_with_timestamp("Final URL:", self.driver.current_url)
            log_with_timestamp("Final page source:")
            log_with_timestamp(self.driver.page_source[:2000])
            raise

    def close(self):
        self.driver.quit()

    def make_reservation(self, username, password, target_date, max_attempts, sleep_duration):
        """Main method to execute the full reservation process"""
        try:
            log_with_timestamp("\nStarting reservation process...")
            log_with_timestamp(f"Target date: {target_date}")
            log_with_timestamp(f"Max attempts: {max_attempts}")
            log_with_timestamp(f"Sleep duration: {sleep_duration} seconds")
            
            self.login(username, password)
            
            log_with_timestamp("\nAttempting to navigate to calendar...")
            self.navigate_to_calendar()
            
            log_with_timestamp("\nAttempting to select date...")
            self.select_date(target_date, max_attempts, sleep_duration)
            
            log_with_timestamp("\nAttempting to select carpool option...")
            self.select_carpool()
            
            log_with_timestamp("\nProceeding to checkout...")
            self.checkout()
            
            log_with_timestamp("\nConfirming reservation...")
            self.confirm_reservation()
            
            log_with_timestamp("\nReservation process completed successfully!")
            
        except Exception as e:
            log_with_timestamp(f"\nError during reservation process: {str(e)}")
            log_with_timestamp("Attempting to capture error state...")
            try:
                log_with_timestamp(f"Current URL: {self.driver.current_url}")
                log_with_timestamp("Current page source:")
                log_with_timestamp(self.driver.page_source[:1000])
            except:
                log_with_timestamp("Could not capture error state")
        finally:
            log_with_timestamp("\nClosing browser...")
            self.close()

def main():
    log_with_timestamp("--------------------------------")
    log_with_timestamp("Brighton Bot")
    # print("\nBefore using, make sure on Honk mobile you have:")
    # print("1. Your credit card info saved at: https://parking.honkmobile.com/payment-cards")
    # print("2. Only one license plate saved at: https://parking.honkmobile.com/vehicles")
    log_with_timestamp("--------------------------------")
    
    # Load environment variables
    load_dotenv()
    
    # Get credentials from environment variables
    username = os.getenv('HONK_USERNAME')
    password = os.getenv('HONK_PASSWORD')
    
    # Only prompt for credentials if not found in environment variables
    if not username:
        username = input('Enter your Honk mobile email: ')
    if not password:
        password = input('Enter your Honk mobile password: ')
    
    target_date = input('Enter target date (day of month): ')
    max_attempts = int(input('Maximum number of attempts (default 100): ') or 100)
    sleep_duration = float(input('Sleep duration between attempts in seconds (default 5): ') or 5)
    
    # Create bot instance without chromedriver_path
    bot = ReserveDate()
    bot.make_reservation(
        username,
        password,
        target_date,
        max_attempts,
        sleep_duration
    )

if __name__ == "__main__":
    main()