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
            st.info("Attempting to navigate to login page...")
            self.driver.get("https://reservenski.parkbrightonresort.com/login")
            
            st.info("Waiting for email field...")
            email_element = self.wait.until(EC.presence_of_element_located((By.ID, "emailAddress")))
            email_element.clear()
            time.sleep(1)
            for char in username:
                email_element.send_keys(char)
                time.sleep(0.1)
            
            st.info("Entering password...")
            password_element = self.driver.find_element(By.ID, "password")
            password_element.clear()
            time.sleep(1)
            for char in password:
                password_element.send_keys(char)
                time.sleep(0.1)
            
            st.info("Looking for login button...")
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
            
            st.info("Clicking login button...")
            self.driver.execute_script("arguments[0].click();", login_button)
            
            # Wait for login to complete and verify
            st.info("Waiting for login to complete...")
            time.sleep(5)
            
            # Verify login success by checking URL or specific elements
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                current_url = self.driver.current_url
                st.info(f"Current URL: {current_url}")
                
                if "login" not in current_url.lower():
                    st.success("Login successful - URL changed from login page")
                    break
                    
                try:
                    # Check if we can find any error messages
                    error_messages = self.driver.find_elements(By.CSS_SELECTOR, "[class*='error'], [class*='alert']")
                    if error_messages:
                        st.error("Found error messages: " + ", ".join([msg.text for msg in error_messages]))
                        raise Exception("Login failed - error message found")
                except:
                    pass
                
                retry_count += 1
                if retry_count < max_retries:
                    st.info(f"Login verification attempt {retry_count + 1}/{max_retries}...")
                    time.sleep(3)
            
            if retry_count >= max_retries:
                raise Exception("Failed to verify login success after multiple attempts")
            
            st.success("Login sequence completed and verified")
            
        except Exception as e:
            st.error(f"Error during login: {str(e)}")
            st.error(f"Current URL: {self.driver.current_url}")
            st.error("Page source:")
            st.code(self.driver.page_source[:1000])
            raise

    def navigate_to_calendar(self):
        try:
            st.info("Waiting for page to load after login...")
            time.sleep(5)  # Give more time for the page to settle after login
            
            st.info("Looking for 'Reserve a Parking Spot' link...")
            reserve_link = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, "//div[contains(text(), 'Reserve a Parking Spot')]"
            )))
            
            st.info("Found link, attempting to click...")
            try:
                reserve_link.click()
            except:
                try:
                    self.driver.execute_script("arguments[0].click();", reserve_link)
                except:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(reserve_link).click().perform()
            
            st.info("Clicked reserve link, waiting for calendar to load...")
            time.sleep(3)
            st.success("Calendar navigation completed")
            
        except Exception as e:
            st.error(f"Error in navigate_to_calendar: {str(e)}")
            st.error(f"Current URL: {self.driver.current_url}")
            st.error("Page source:")
            st.code(self.driver.page_source[:1000])  # Print first 1000 chars of page source
            raise

    def check_date_availability(self, target_date_element):
        """Helper method to check if date has the available (green) background color"""
        try:
            background_color = target_date_element.value_of_css_property('background-color')
            # Convert rgba(49, 200, 25, 0.2) to a comparable format
            target_color = "rgba(49, 200, 25, 0.2)"
            return background_color == target_color
        except Exception as e:
            print(f"Error checking date availability: {e}")
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
                        st.success(f"Successfully selected available date {target_date_text}")
                        break
                    else:
                        st.warning(f"Date {target_date_text} not available yet. Refreshing...")
                        time.sleep(sleep_duration)
                        self.driver.refresh()
                        attempt += 1
                else:
                    st.error(f"Could not find date element {target_date_text}")
                    break
                    
                if calendar_iframe:
                    self.driver.switch_to.default_content()
                    
            except Exception as e:
                print(f"Error in select_date: {e}")
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
            print(f"Error in select_carpool: {e}")

    def checkout(self):
        try:
            checkout_button = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, "//button[contains(@class, 'PlainButton--noStyle')]//div[contains(text(), 'Pay $10.00 & Park')]"
            )))
            
            parent_button = checkout_button.find_element(
                By.XPATH, "./ancestor::button[contains(@class, 'PlainButton--noStyle')]"
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
            print(f"Error in checkout: {e}")

    def confirm_reservation(self):
        try:
            st.info("Waiting for payment page to load...")
            time.sleep(5)  # Initial wait for page load
            
            # First check if we're on the Honk payment page
            current_url = self.driver.current_url
            st.info(f"Current URL: {current_url}")
            
            if "honkmobile.com/checkout" in current_url:
                st.info("Detected Honk payment page, looking for payment button...")
                
                # Wait for the page to be fully loaded
                self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
                time.sleep(2)  # Additional small wait after page load
                
                # Try to find any iframe that might contain the payment button
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                main_content = True
                
                # First try in main content, then check iframes if needed
                while True:
                    try:
                        if not main_content:
                            # Switch to iframe if we're checking iframes
                            self.driver.switch_to.frame(iframes.pop(0))
                        
                        # Expanded list of payment button selectors
                        payment_selectors = [
                            "//button[contains(., 'Pay')]",
                            "//button[contains(., '$10.00')]",
                            "//button[contains(@class, 'pay')]",
                            "//button[contains(@class, 'checkout')]",
                            "//div[contains(@class, 'pay')]//button",
                            "//div[contains(@class, 'checkout')]//button",
                            "//button[contains(@id, 'pay')]",
                            "//button[contains(@id, 'checkout')]",
                            "//div[contains(@class, 'submit')]//button",
                            "//input[@type='submit']",
                            "//*[contains(@class, 'pay') or contains(@class, 'checkout')]",
                            "//button[contains(@class, 'submit')]",
                            "//button[contains(@class, 'confirm')]"
                        ]
                        
                        for selector in payment_selectors:
                            try:
                                # Wait briefly for each selector
                                payment_button = WebDriverWait(self.driver, 3).until(
                                    EC.presence_of_element_located((By.XPATH, selector))
                                )
                                
                                if payment_button and payment_button.is_displayed():
                                    st.success(f"Found payment button with selector: {selector}")
                                    
                                    # Try multiple click methods
                                    try:
                                        # First try regular click
                                        payment_button.click()
                                    except:
                                        try:
                                            # Try JavaScript click
                                            self.driver.execute_script("arguments[0].click();", payment_button)
                                        except:
                                            # Try Actions click
                                            actions = ActionChains(self.driver)
                                            actions.move_to_element(payment_button)
                                            actions.click()
                                            actions.perform()
                                    
                                    st.success("Payment button clicked")
                                    
                                    # Wait for confirmation or success page
                                    st.info("Waiting for payment to complete...")
                                    success_conditions = [
                                        "post-purchase" in self.driver.current_url,
                                        "confirmation" in self.driver.current_url,
                                        "success" in self.driver.current_url
                                    ]
                                    
                                    max_wait = 30
                                    start_time = time.time()
                                    while not any(success_conditions) and time.time() - start_time < max_wait:
                                        time.sleep(2)
                                        current_url = self.driver.current_url
                                        st.info(f"Current URL while waiting: {current_url}")
                                        success_conditions = [
                                            "post-purchase" in current_url,
                                            "confirmation" in current_url,
                                            "success" in current_url
                                        ]
                                    
                                    if any(success_conditions):
                                        st.success("Payment completed successfully!")
                                        return
                                    
                                    raise Exception("Payment completion timeout")
                                    
                            except Exception as e:
                                st.warning(f"Selector {selector} failed: {str(e)}")
                                continue
                        
                        if main_content:
                            if not iframes:
                                break
                            main_content = False
                        else:
                            self.driver.switch_to.default_content()
                            if not iframes:
                                break
                            
                    except IndexError:
                        break
                    except Exception as e:
                        st.warning(f"Error while checking frame: {str(e)}")
                        self.driver.switch_to.default_content()
                        if not iframes:
                            break
                
                # If we get here, we couldn't find the button
                st.error("Could not find payment button. Page source:")
                st.code(self.driver.page_source[:2000])
                raise Exception("Payment button not found")
                
            else:
                raise Exception(f"Unexpected URL: {current_url}")
            
        except Exception as e:
            st.error(f"Error in confirm_reservation: {str(e)}")
            st.error(f"Final URL: {self.driver.current_url}")
            st.error("Final page source:")
            st.code(self.driver.page_source[:2000])
            raise

    def close(self):
        self.driver.quit()

    def make_reservation(self, username, password, target_date, max_attempts, sleep_duration):
        """Main method to execute the full reservation process"""
        try:
            st.info("\nStarting reservation process...")
            st.info(f"Target date: {target_date}")
            st.info(f"Max attempts: {max_attempts}")
            st.info(f"Sleep duration: {sleep_duration} seconds")
            
            self.login(username, password)
            
            st.info("Attempting to navigate to calendar...")
            self.navigate_to_calendar()
            
            st.info("Attempting to select date...")
            self.select_date(target_date, max_attempts, sleep_duration)
            
            st.info("Attempting to select carpool option...")
            self.select_carpool()
            
            st.info("Proceeding to checkout...")
            self.checkout()
            
            st.info("Confirming reservation...")
            self.confirm_reservation()
            
            st.success("Reservation process completed successfully!")
            
        except Exception as e:
            st.error(f"Error during reservation process: {str(e)}")
            st.error("Attempting to capture error state...")
            try:
                st.error(f"Current URL: {self.driver.current_url}")
                st.error("Current page source:")
                st.code(self.driver.page_source[:1000])
            except:
                st.error("Could not capture error state")
        finally:
            st.info("Closing browser...")
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
        font-size: 1.2rem !important;
    }
    
    /* Style for the main container */
    .main-container {
        background-color: rgba(0, 0, 0, 0.5) !important;
        padding: 2rem !important;
        border-radius: 10px !important;
        margin: 1rem 0 !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    
    /* Style for links */
    a {
        color: #1E90FF !important;
    }
    
    /* Style for the title */
    .title {
        color: black !important;
        margin-bottom: 2rem;
    }

    /* Style for the button */
    .stButton button {
        background-color: #1E90FF;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 4px;
    }

    /* Ensure container contents are properly styled */
    .main-container > * {
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# Add Streamlit title
st.markdown('<h1 class="title">Brighton Bot</h1>', unsafe_allow_html=True)

# Create the main container with a dark background
st.markdown("""
    <div class="main-container">
        <p>Before using, make sure on Honk mobile you have:</p>
        <ol>
            <li>Your credit card info saved at: <a href="https://parking.honkmobile.com/payment-cards">https://parking.honkmobile.com/payment-cards</a></li>
            <li>Only one license plate saved at: <a href="https://parking.honkmobile.com/vehicles">https://parking.honkmobile.com/vehicles</a></li>
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
        
        username = st.text_input('Enter your Honk mobile email:', value=default_username, key='username')
        password = st.text_input('Enter your Honk mobile password:', value=default_password, type='password', key='password')
        target_date = st.text_input('Enter target date (day of month):', key='target_date')
        max_attempts = st.number_input('Maximum number of attempts:', min_value=1, value=100, key='max_attempts')
        sleep_duration = st.number_input('Sleep duration between attempts (seconds):', min_value=1, value=5, key='sleep_duration')
        
        if st.button('Start Reservation'):
            if not username or not password or not target_date:
                st.error('Please fill in all required fields')
            else:
                bot = ReserveDate()
                bot.make_reservation(
                    username,
                    password,
                    target_date,
                    int(max_attempts),
                    float(sleep_duration)
                )
    
    st.markdown('</div>', unsafe_allow_html=True)