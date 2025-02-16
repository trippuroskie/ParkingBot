import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import os
from dotenv import load_dotenv
import base64
from datetime import datetime
import random

def log_with_timestamp(*args):
    """Modified log_with_timestamp function for Streamlit"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    message = " ".join(str(arg) for arg in args)
    st.info(f"[{timestamp}] {message}")

def is_mobile():
    """Check if the user is on a mobile device"""
    try:
        # Get user agent from Streamlit's session state
        user_agent = st.session_state.get('user_agent', '')
        return any(device in user_agent.lower() for device in ['mobile', 'android', 'iphone', 'ipad', 'ipod'])
    except:
        return False

# Move ReserveDate class definition to the top
class ReserveDate:
    def __init__(self, chromedriver_path=None):
        load_dotenv()
        # Set up Chrome options for headless mode
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Check if user is on mobile
        if is_mobile():
            log_with_timestamp("Mobile device detected, adjusting browser settings...")
            # Mobile-specific settings
            chrome_options.add_argument("--window-size=375,812")  # iPhone X dimensions
            chrome_options.add_argument("--touch-events=enabled")
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1')
        else:
            # Desktop settings
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument(f'--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        chrome_options.add_argument('--enable-javascript')
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--lang=en-US,en;q=0.9')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--allow-running-insecure-content')
        
        # Add additional preferences
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option('prefs', {
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False,
            'profile.default_content_setting_values.notifications': 2,
            'profile.managed_default_content_settings.javascript': 1,
            'profile.managed_default_content_settings.cookies': 1,
            'profile.managed_default_content_settings.images': 1,
            'profile.default_content_settings.popups': 2,
            'profile.managed_default_content_settings.plugins': 1,
            'profile.managed_default_content_settings.mixed_script': 1,
            'profile.managed_default_content_settings.media_stream': 2,
            'profile.managed_default_content_settings.geolocation': 2
        })

        try:
            # Check if running on Streamlit Cloud (Debian environment)
            if os.path.exists("/usr/bin/chromium"):
                st.info("Running on Streamlit Cloud with Chromium")
                chrome_options.binary_location = "/usr/bin/chromium"
                # Try multiple possible chromedriver locations
                chromedriver_paths = [
                    "/usr/bin/chromedriver",
                    "/usr/lib/chromium/chromedriver",
                    "/usr/lib/chromium-browser/chromedriver"
                ]
                
                driver_path = None
                for path in chromedriver_paths:
                    if os.path.exists(path):
                        driver_path = path
                        st.info(f"Found chromedriver at: {path}")
                        break
                
                if driver_path is None:
                    raise Exception("Could not find chromedriver in any standard location")
                
                self.service = Service(executable_path=driver_path)
                self.driver = webdriver.Chrome(service=self.service, options=chrome_options)
            else:
                # Local development environment
                st.info("Running in local environment")
                self.service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=self.service, options=chrome_options)

            # Execute stealth JS
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                    window.chrome = {
                        runtime: {}
                    };
                """
            })
            
        except Exception as e:
            st.error(f"Chrome initialization failed: {str(e)}")
            st.error("Additional debugging information:")
            try:
                # List contents of relevant directories
                for path in ["/usr/bin", "/usr/lib/chromium", "/usr/lib/chromium-browser"]:
                    if os.path.exists(path):
                        st.error(f"Contents of {path}:")
                        st.error(str(os.listdir(path)))
            except Exception as dir_error:
                st.error(f"Error listing directories: {str(dir_error)}")
            
            try:
                if hasattr(self, 'driver'):
                    st.error("Page source:")
                    st.error(self.driver.page_source[:1000])
            except:
                pass
            raise
        
        # Set page load timeout
        self.driver.set_page_load_timeout(30)
        self.wait = WebDriverWait(self.driver, 20)
        self.calendar_wait = WebDriverWait(self.driver, 30)

    def login(self, username, password):
        try:
            log_with_timestamp("Attempting to navigate to login page...")
            self.driver.get("https://reservenski.parkbrightonresort.com/login")
            
            # Wait for page to be fully loaded
            self.wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
            time.sleep(3)  # Additional wait for JavaScript
            
            # Scroll to ensure elements are in view for mobile
            self.driver.execute_script("window.scrollTo(0, 0);")
            
            log_with_timestamp("Waiting for email field...")
            email_element = self.wait.until(
                EC.presence_of_element_located((By.ID, "emailAddress"))
            )
            self.wait.until(EC.element_to_be_clickable((By.ID, "emailAddress")))
            
            # Ensure element is in view and click it first (important for mobile)
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", email_element)
            time.sleep(1)
            try:
                email_element.click()
            except:
                self.driver.execute_script("arguments[0].click();", email_element)
            
            # Clear and enter email with random delays
            email_element.clear()
            time.sleep(1)
            for char in username:
                email_element.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
            
            log_with_timestamp("Entering password...")
            password_element = self.wait.until(
                EC.presence_of_element_located((By.ID, "password"))
            )
            self.wait.until(EC.element_to_be_clickable((By.ID, "password")))
            
            # Ensure password field is in view and click it
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", password_element)
            time.sleep(1)
            try:
                password_element.click()
            except:
                self.driver.execute_script("arguments[0].click();", password_element)
            
            password_element.clear()
            time.sleep(1)
            for char in password:
                password_element.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
            
            log_with_timestamp("Looking for login button...")
            login_button = None
            button_selectors = [
                (By.CSS_SELECTOR, "button.Login_submitButton__fMHAq"),
                (By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Sign In')]"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(@class, 'submitButton')]")
            ]
            
            for selector_type, selector in button_selectors:
                try:
                    login_button = self.wait.until(EC.element_to_be_clickable((selector_type, selector)))
                    if login_button.is_displayed():
                        break
                except:
                    continue
            
            if not login_button:
                raise Exception("Could not find login button")
            
            # Ensure login button is in view
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", login_button)
            time.sleep(2)  # Wait before clicking
            
            log_with_timestamp("Clicking login button...")
            try:
                # Try multiple click methods
                try:
                    login_button.click()
                except:
                    try:
                        self.driver.execute_script("arguments[0].click();", login_button)
                    except:
                        actions = ActionChains(self.driver)
                        actions.move_to_element(login_button).click().perform()
            except Exception as click_error:
                log_with_timestamp(f"Click error: {str(click_error)}")
                # Try tapping for mobile
                try:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(login_button)
                    actions.click()
                    actions.perform()
                except:
                    self.driver.execute_script("""
                        var evt = new MouseEvent('touchstart', {
                            'view': window,
                            'bubbles': true,
                            'cancelable': true
                        });
                        arguments[0].dispatchEvent(evt);
                        
                        setTimeout(function() {
                            var evt = new MouseEvent('touchend', {
                                'view': window,
                                'bubbles': true,
                                'cancelable': true
                            });
                            arguments[0].dispatchEvent(evt);
                        }, 50);
                    """, login_button)
            
            # Wait for login to complete
            log_with_timestamp("Waiting for login to complete...")
            time.sleep(5)
            
            # Verify login success
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                current_url = self.driver.current_url
                log_with_timestamp(f"Current URL: {current_url}")
                
                if "login" not in current_url.lower():
                    log_with_timestamp("Login successful - URL changed from login page")
                    return
                
                # Check for error messages
                error_messages = self.driver.find_elements(By.CSS_SELECTOR, "[class*='error'], [class*='alert']")
                if error_messages:
                    error_text = ", ".join([msg.text for msg in error_messages if msg.text.strip()])
                    if error_text:
                        raise Exception(f"Login failed - Error messages found: {error_text}")
                
                retry_count += 1
                if retry_count < max_retries:
                    log_with_timestamp(f"Login verification attempt {retry_count + 1}/{max_retries}...")
                    time.sleep(3)
            
            # If we get here, login failed
            page_source = self.driver.page_source
            log_with_timestamp("Login failed. Page source:")
            log_with_timestamp(page_source[:1000])
            raise Exception("Failed to verify login success after multiple attempts")
            
        except Exception as e:
            log_with_timestamp(f"Error during login: {str(e)}")
            log_with_timestamp(f"Current URL: {self.driver.current_url}")
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
            # Convert rgba(49, 200, 25, 0.2) to a comparable format
            target_color = "rgba(49, 200, 25, 0.2)"
            return background_color == target_color
        except Exception as e:
            log_with_timestamp(f"Error checking date availability: {e}")
            return False

    def select_date(self, target_date_text, max_attempts, sleep_duration):
        attempt = 0
        
        while attempt < max_attempts:
            try:
                # Initialize calendar_iframe
                calendar_iframe = None
                
                # Find and switch to the calendar iframe
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
            log_with_timestamp("Looking for carpool option...")
            carpool_element = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, "//div[text()='4+ Carpool (Occupancy will be verified by Parking Ambassador upon arrival)']"
            )))
            
            log_with_timestamp("Found carpool option, attempting to click...")
            try:
                carpool_element.click()
                log_with_timestamp("Clicked carpool option using standard click")
            except:
                try:
                    self.driver.execute_script("arguments[0].click();", carpool_element)
                    log_with_timestamp("Clicked carpool option using JavaScript")
                except:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(carpool_element).click().perform()
                    log_with_timestamp("Clicked carpool option using Action Chains")
            
            # Verify selection
            time.sleep(2)
            try:
                # Check if the element has a selected state or different styling
                selected_state = carpool_element.get_attribute("class") or ""
                if "selected" in selected_state.lower() or "active" in selected_state.lower():
                    log_with_timestamp("Carpool option selection verified")
                else:
                    log_with_timestamp("Warning: Could not verify carpool selection state")
            except:
                log_with_timestamp("Warning: Could not check carpool selection state")
                    
        except Exception as e:
            log_with_timestamp(f"Error in select_carpool: {e}")
            log_with_timestamp(f"Current URL: {self.driver.current_url}")
            log_with_timestamp("Page source:")
            log_with_timestamp(self.driver.page_source[:1000])
            raise

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
            
            log_with_timestamp("Attempting to navigate to calendar...")
            self.navigate_to_calendar()
            
            log_with_timestamp("Attempting to select date...")
            self.select_date(target_date, max_attempts, sleep_duration)
            
            log_with_timestamp("Attempting to select carpool option...")
            self.select_carpool()
            
            log_with_timestamp("Proceeding to checkout...")
            self.checkout()
            
            log_with_timestamp("Confirming reservation...")
            self.confirm_reservation()
            
            log_with_timestamp("Reservation process completed successfully!")
            
        except Exception as e:
            log_with_timestamp(f"Error during reservation process: {str(e)}")
            log_with_timestamp("Attempting to capture error state...")
            try:
                log_with_timestamp(f"Current URL: {self.driver.current_url}")
                log_with_timestamp("Current page source:")
                log_with_timestamp(self.driver.page_source[:1000])
            except:
                log_with_timestamp("Could not capture error state")
        finally:
            log_with_timestamp("Closing browser...")
            self.close()

def add_bg_from_local(image_file):
    with open(image_file, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url(data:image/{"jpg"};base64,{encoded_string.decode()});
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }}
    </style>
    """,
    unsafe_allow_html=True
    )

# Add the background image
add_bg_from_local('./images/brighton_1.png')

# Add custom CSS for the container
st.markdown("""
    <style>
    .stApp {
        background-attachment: fixed;
    }
    
    /* Style for text inputs and number inputs */
    .stTextInput input, .stNumberInput input {
        background-color: rgba(0, 0, 0, 0.2) !important;
        color: white !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 8px !important;
    }
    
    /* Style for labels and text */
    .stTextInput label, .stNumberInput label, p {
        color: black !important;
        font-weight: bold !important;
        font-size: 1.2rem !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.5) !important;
    }
    
    /* Style for the main container */
    .main-container {
        background-color: rgba(0, 0, 0, 0.7) !important;
        padding: 2rem !important;
        border-radius: 10px !important;
        margin: 1rem 0 !important;
        width: 100% !important;
        box-sizing: border-box !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Style for links */
    a {
        color: #1E90FF !important;
        text-decoration: none !important;
        font-weight: bold !important;
    }
    
    a:hover {
        text-decoration: underline !important;
    }
    
    /* Style for the title */
    .title {
        color: black !important;
        margin-bottom: 2rem !important;
        text-align: center !important;
        font-size: 2.5rem !important;
        font-weight: bold !important;
        text-shadow: 2px 2px 4px rgba(255, 255, 255, 0.5) !important;
    }

    /* Style for the button */
    .stButton button {
        background-color: #1E90FF !important;
        color: white !important;
        border: none !important;
        padding: 0.75rem 1.5rem !important;
        border-radius: 4px !important;
        font-weight: bold !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
    }

    .stButton button:hover {
        background-color: #0066CC !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2) !important;
    }

    /* Ensure container contents are properly styled */
    .main-container > * {
        color: white !important;
    }
    
    /* Style for info text */
    .info-text {
        background-color: rgba(30, 144, 255, 0.1) !important;
        padding: 1rem !important;
        border-radius: 4px !important;
        margin-bottom: 1rem !important;
    }
    
    /* Style for warning text */
    .warning-text {
        color: #FFA500 !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# Add Streamlit title
st.markdown('<h1 class="title">Brighton Bot</h1>', unsafe_allow_html=True)

# Create the main container with a dark background
st.markdown("""
    <div class="main-container">
        <p style="font-size: 1.3rem; margin-bottom: 1.5rem;">⚠️ Important Prerequisites:</p>
        <p>Before using, make sure on Honk mobile you have:</p>
        <ol>
            <li>Your credit card info saved at: <a href="https://parking.honkmobile.com/payment-cards" target="_blank">https://parking.honkmobile.com/payment-cards</a></li>
            <li>Only one license plate saved at: <a href="https://parking.honkmobile.com/vehicles" target="_blank">https://parking.honkmobile.com/vehicles</a></li>
        </ol>
    </div>
""", unsafe_allow_html=True)

# Add form elements inside a container with the same styling
with st.container():
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Load environment variables
        load_dotenv()
        default_username = os.getenv('HONK_USERNAME', '')
        default_password = os.getenv('HONK_PASSWORD', '')
        
        with st.form("reservation_form"):
            username = st.text_input('Enter your Honk mobile email:', 
                                   value=default_username, 
                                   key='username',
                                   help="Your Honk mobile account email")
            
            password = st.text_input('Enter your Honk mobile password:', 
                                   value=default_password, 
                                   type='password', 
                                   key='password',
                                   help="Your Honk mobile account password")
            
            target_date = st.text_input('Enter target date (day of month):', 
                                      key='target_date',
                                      help="The day of the month you want to reserve (e.g., '15')")
            
            col_attempts, col_sleep = st.columns(2)
            with col_attempts:
                max_attempts = st.number_input('Maximum attempts:', 
                                             min_value=1, 
                                             value=100, 
                                             key='max_attempts',
                                             help="Maximum number of times to check for availability")
            
            with col_sleep:
                sleep_duration = st.number_input('Sleep duration (seconds):', 
                                               min_value=1, 
                                               value=5, 
                                               key='sleep_duration',
                                               help="Time to wait between attempts")
            
            submitted = st.form_submit_button("Start Reservation")
            
            if submitted:
                if not username or not password or not target_date:
                    st.error('⚠️ Please fill in all required fields')
                else:
                    try:
                        with st.spinner('Starting reservation process...'):
                            bot = ReserveDate()
                            bot.make_reservation(
                                username,
                                password,
                                target_date,
                                int(max_attempts),
                                float(sleep_duration)
                            )
                    except Exception as e:
                        st.error(f'❌ Error: {str(e)}')
                        st.error('Please check your credentials and try again.')
                    finally:
                        st.info('✨ Process completed. Check the logs above for details.')

    # Add helpful information in the sidebar
    with st.sidebar:
        st.markdown("""
        ### 📋 Instructions
        
        1. Enter your Honk mobile credentials
        2. Specify the target date (day of month)
        3. Adjust attempts and sleep duration if needed
        4. Click "Start Reservation"
        
        ### ⚡ Tips
        
        - Keep the window open while the bot runs
        - Check the logs for real-time updates
        - If you get errors, try increasing sleep duration
        
        ### 🔒 Security Note
        
        Your credentials are only used to log in to Honk mobile and are never stored.
        """)

# Add this at the start of your Streamlit UI code
def main():
    # Store user agent in session state
    if 'user_agent' not in st.session_state:
        user_agent = st.get_user_agent()
        st.session_state['user_agent'] = str(user_agent)
        if is_mobile():
            st.info("Mobile device detected. Optimizing for mobile browsing.")

    # Rest of your existing Streamlit UI code...
    st.markdown('<h1 class="title">Brighton Bot</h1>', unsafe_allow_html=True)