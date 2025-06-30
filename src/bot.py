import json
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service

class PopMartBot:
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.driver = None
        self.config = self.load_config()
        self.login_timeout = 120  # seconds for login completion
        self._running = False

    def load_config(self):
        """Load configuration from JSON file"""
        with open('config/config.json', 'r') as f:
            return json.load(f)

    def log(self, message):
        """Send log messages to both console and frontend"""
        print(message)
        if self.socketio:
            self.socketio.emit('log', message)

    def init_driver(self):
        """Initialize Chrome with a fresh profile and stealth settings"""
        from selenium_stealth import stealth
        chrome_options = Options()
        # Removed existing profile options to launch fresh browser
        # chrome_options.add_argument(f"user-data-dir={self.config['chrome_settings']['profile_path']}")
        # chrome_options.add_argument(f"profile-directory={self.config['chrome_settings']['profile_name']}")
        chrome_options.add_argument("--start-maximized")

        # Add anti-detection measures
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--disable-gpu')

        # Set a realistic user agent
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        service = Service(self.config['chrome_settings']['chromedriver_path'])
        self.driver = webdriver.Chrome(
            service=service,
            options=chrome_options
        )

        stealth(self.driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )

        self.log("✓ Chrome initialized with fresh profile and stealth settings")

        # Additional manual stealth JS injections to hide fingerprints
        try:
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
                window.navigator.chrome = {
                    runtime: {},
                    // etc.
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                """
            })
            self.log("✓ Injected additional stealth JS to hide fingerprints")
        except Exception as e:
            self.log(f"Failed to inject stealth JS: {str(e)}")

    def handle_popups(self):
        """Continuously check for and close popups/agreements"""
        start_time = time.time()
        while time.time() - start_time < 30:  # Max 30 seconds for popups
            try:
                # Check for popup close button
                close_btn = self.driver.find_elements(By.CSS_SELECTOR, self.config['selectors']['popup_close'])
                if close_btn:
                    close_btn[0].click()
                    self.log("✓ Closed popup")
                    time.sleep(random.uniform(1, 5))
                    continue
                
                # Check for policy accept button
                accept_btn = self.driver.find_elements(By.CSS_SELECTOR, self.config['selectors']['policy_accept'])
                if accept_btn:
                    accept_btn[0].click()
                    self.log("✓ Accepted policy")
                    time.sleep(random.uniform(1, 5))
                    continue
                
                # If no popups found, exit loop
                break
                
            except Exception as e:
                self.log(f"Popup handling error: {str(e)}")
                break
        
        self.log("✓ All popups handled")

    def stop(self):
        """Gracefully stop the bot"""
        self._running = False
        self.log("Stopping bot...")
        if self.driver:
            try:
                self.driver.quit()
                self.log("Browser closed")
            except Exception as e:
                self.log(f"Error closing browser: {str(e)}")

    def verify_login(self):
        """Check if successfully logged in by waiting for specific text in header_infoTitle__Fse4B"""
        try:
            WebDriverWait(self.driver, 30).until(
                lambda driver: "My Account" in driver.find_element(By.CLASS_NAME, "header_infoTitle__Fse4B").text
            )
            self.log("[+] captcha resolved")
            return True
        except TimeoutException:
            self.log("✗ Login verification failed")
            return False

    def clear_browser_data(self):
        """Clear browser cookies and cache"""
        try:
            self.driver.delete_all_cookies()
            self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
            self.driver.execute_cdp_cmd('Network.clearBrowserCookies', {})
            self.log("✓ Cleared browser cookies and cache")
        except Exception as e:
            self.log(f"Failed to clear browser data: {str(e)}")

    def popmart_login(self):
        """Perform Popmart login flow with credentials from config"""
        try:
            self.clear_browser_data()
            # Navigate to Popmart login page
            self.driver.get("https://popmart.com/us/user/login/")
            self.log("Opened Popmart login page")
            time.sleep(random.uniform(1, 5))

            # Wait for page to fully load by waiting for login input field presence
            login_selector = self.config['selectors']['login_field']
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, login_selector))
            )

            # Continuously check for popups and agreements for up to 30 seconds
            start_time = time.time()
            while time.time() - start_time < 30:
                popup_close_selector = self.config['selectors']['popup_close']
                policy_accept_selector = self.config['selectors']['policy_accept']

                popups = self.driver.find_elements(By.CSS_SELECTOR, popup_close_selector)
                policies = self.driver.find_elements(By.CSS_SELECTOR, policy_accept_selector)

                if popups or policies:
                    try:
                        for popup in popups:
                            popup.click()
                            self.log("✓ Closed popup")
                        for policy in policies:
                            policy.click()
                            self.log("✓ Accepted policy")
                    except Exception as e:
                        self.log(f"Popup/Policy click error: {str(e)}")
                    time.sleep(random.uniform(1, 5))
                else:
                    break

            # After popups and agreements are gone, proceed to fill login input field
            login_input = self.driver.find_element(By.CSS_SELECTOR, login_selector)
            login_input.clear()
            login_input.send_keys(self.config['accounts'][0]['email'])
            self.log("Entered username")
            time.sleep(random.uniform(1, 5))

            # Click login button
            login_btn_selector = self.config['selectors']['login_btn']
            # Add dot prefix if missing for class selector
            if not login_btn_selector.startswith('.') and not login_btn_selector.startswith('#'):
                login_btn_selector = '.' + login_btn_selector
            login_btn = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, login_btn_selector))
            )
            login_btn.click()
            self.log("Clicked login button")
            time.sleep(random.uniform(1, 5))

            # Wait for password field to appear
            password_selector = self.config['selectors']['password_field']
            password_input = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, password_selector))
            )
            password_input.clear()
            password_input.send_keys(self.config['accounts'][0]['password'])
            self.log("Entered password")
            time.sleep(random.uniform(1, 5))

            # Click login button again
            login_btn = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, login_btn_selector))
            )
            login_btn.click()
            self.log("Clicked login button again")
            time.sleep(random.uniform(1, 5))

            # Wait for login completion
            self.log("Waiting for login to complete...")
            if not self.verify_login():
                raise Exception("Login verification failed")
            return True

        except Exception as e:
            self.log(f"✗ Popmart login failed: {str(e)}")
            return False

    def monitor_product(self, product_url, action, quantity):
        """Monitor product and perform action when available"""
        self._running = True  # Set running flag when starting
        try:
            self.log(f"Monitoring product: {product_url}")
            
            while self._running:
                self.driver.get(product_url)
                time.sleep(random.uniform(1, 5))

                if not self._running:  # Check if we should stop
                    return False

                # Check if buy now button is available within 3 seconds
                add_to_bag_selector = self.config['selectors']['add_to_bag']
                add_to_bag_btn = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, add_to_bag_selector)))
                
                self.log("✓ Product is available (add to bag button found)")

                add_to_bag_btn.click()
                self.log("[+] add to bag clicked")
                time.sleep(random.uniform(1, 5))
            
                # Click open_cart button
                self.driver.get("https://www.popmart.com/us/largeShoppingCart")

                # time.sleep(random.uniform(1, 4))

                # Check select_all checkbox
                select_all_selector = ".index_checkbox__w_166"  # Hardcoded class name
                try:
                    # Wait for checkbox to be present and clickable
                    select_all_checkbox = WebDriverWait(self.driver, 15).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, select_all_selector))
                    )
                    self.log("checkbox found")

                    # Scroll into view
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", select_all_checkbox)
                    time.sleep(1)  # Small delay after scrolling

                    select_all_checkbox.click()
                    self.log("✓ Clicked select all checkbox (normal click)")

                except Exception as e:
                    self.log(f"✗ Failed to check select all checkbox:")

                time.sleep(random.uniform(1, 5))

                if action == "buy":
                    try:
                        # Click checkout button
                        checkout_btn_selector = self.config['selectors']['checkout_btn']
                        checkout_btn = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, checkout_btn_selector)))
                        self.log("Checkout button found")
                        checkout_btn.click()
                        self.log("✓ Clicked checkout button")
                    except Exception as e:
                        self.log(f"Failed to click checkout button")

                    # Wait for navigation after clicking checkout
                    WebDriverWait(self.driver, 10).until(EC.url_changes(self.driver.current_url))

                if action == "buy":
                    try:
                        # Click Proceed to Pay button
                        proceed_to_pay_btn_selector = self.config['selectors']['proceed_to_pay']
                        proceed_to_pay_btn = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, proceed_to_pay_btn_selector)))
                        self.log("Proceed To Pay button found")
                        proceed_to_pay_btn.click()
                        self.log("✓ Clicked Proceed To Pay button")
                    except Exception as e:
                        self.log(f"Failed to click Proceed To Pay button")

                    # Wait for navigation after clicking Proceed to Pay
                    WebDriverWait(self.driver, 10).until(EC.url_changes(self.driver.current_url))
                    
                        
                # Wait for true mo pay selector and click
                true_mo_pay_selector = self.config['selectors']['true_mo_pay']
                true_mo_pay_btn = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, true_mo_pay_selector)))
                self.log("[+] found target payment")
                true_mo_pay_btn.click()
                self.log("[+] choose target payment")
                time.sleep(random.uniform(1, 5))
                    
                # Wait for ordering button, hover and click
                ordering_selector = self.config['selectors']['ordering']
                ordering_btn = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ordering_selector)))
                self.log("[+] found ordering button")
                webdriver.ActionChains(self.driver).move_to_element(ordering_btn).perform()
                self.log("[+] BUY!!")
                ordering_btn.click()
                    
                # Wait for navigation after ordering click
                WebDriverWait(self.driver, 10).until(EC.url_changes(self.driver.current_url))
                self.log(f"[+] QR URL: {self.driver.current_url}")
                time.sleep(random.uniform(1, 5))
                
                return True
                    
        except Exception as e:
            self.log(f"✗ Product monitoring failed: {str(e)}")
            return False
        finally:
            if self.driver and self._running:  # Only quit if not already stopped
                self.driver.quit()
                self.log("Browser closed")

    def run(self, product_url, action, quantity, email=None, password=None):
        """Main execution flow"""
        try:
            self._running = True
            # Initialize browser
            self.init_driver()

            # Perform Popmart login using config accounts
            if not self.popmart_login():
                raise Exception("Failed to complete login")

            # Monitor and process product
            if not self.monitor_product(product_url, action, quantity):
                raise Exception("Failed to process product")

            self.log("✓ Bot completed successfully")
            return True

        except Exception as e:
            self.log(f"✗ Bot error: {str(e)}")
            return False
        finally:
            if self.driver and self._running:
                self.driver.quit()
                self.log("Browser closed")