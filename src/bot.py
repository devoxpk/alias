import json
import time
import random
import os
import threading
import math
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from fake_useragent import UserAgent

class PopMartBot:
    # Class-level lock for thread-safe operations
    _class_lock = threading.Lock()
    
    def __init__(self, socketio=None, account_index=0):
        """Initialize bot instance with specific account"""
        self.socketio = socketio
        self.driver = None
        self.config = self.load_config()
        self.login_timeout = 120
        self._running = False
        self.current_product_url = None
        self.account_index = account_index  # Which account this instance uses
        self.desired_quantity = 0
        self.remaining_quantity = 0  # Track remaining quantity for this instance
    
    def init_driver(self):
        """Initialize undetected Chrome driver with randomized settings"""
        try:
            # Randomize user agent
            ua = UserAgent()
            user_agent = ua.random
            
            options = uc.ChromeOptions()
            
            # Anti-detection settings
            options.add_argument(f'--user-agent={user_agent}')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-infobars')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-popup-blocking')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--remote-debugging-port=9222')
            
            # Random window size
            width = random.randint(1200, 1400)
            height = random.randint(800, 1000)
            options.add_argument(f'--window-size={width},{height}')
            
            # Initialize undetected Chrome
            self.driver = uc.Chrome(
                options=options,
                headless=False,  # Set to True if you want headless
                use_subprocess=True
            )
            
            # Additional anti-bot evasion
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
            
            self.log("✓ Browser initialized with randomized settings")
            return True
            
        except Exception as e:
            self.log(f"✗ Failed to initialize browser: {e}")
            return False

    def load_config(self):
        """Load configuration from config.json"""
        with open('config/config.json', 'r') as f:
            return json.load(f)

    def log(self, message):
        """Log messages to console and optionally to socket.io"""
        print(f"[Account {self.account_index}] {message}")
        if self.socketio:
            self.socketio.emit('log', f"[Account {self.account_index}] {message}")

    # [Previous anti-detection methods remain the same...]
    # (_add_random_headers, init_driver, randomization methods, etc.)

    def clear_browser_data(self):
        """Clear browser cookies and cache"""
        try:
            self.driver.delete_all_cookies()
            self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
            self.driver.execute_cdp_cmd('Network.clearBrowserCookies', {})
            self.log("✓ Cleared browser cookies and cache")
        except Exception as e:
            self.log(f"Failed to clear browser data: {e}")

    def popmart_login(self):
        """Login using the account specified by account_index"""
        self.log("Starting login process")
        self.clear_browser_data()
        self.driver.get("https://popmart.com/us/user/login/")
        self.log("Opened login page")
        
        try:
            # Get account credentials based on account_index
            accounts = self.config.get('accounts', [])
            if self.account_index >= len(accounts):
                self.log(f"✗ No account at index {self.account_index}")
                return False
                
            account = accounts[self.account_index]
            username = account['email']
            password = account['password']
            
            # Handle popups if any
            self.handle_popups()
            
            # Fill in username with simulated typing
            login_field = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.config['selectors']['login_field']))
            )
            login_field.clear()
            for char in username:
                login_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.2))
            self.log("Entered username with simulated typing")
            
            # Click continue button
            button_selector = (
                "div.ant-form-item "
                "div.ant-form-item-control-input "
                "div.ant-form-item-control-input-content > "
                "button.ant-btn.ant-btn-primary.index_loginButton__O6r8l"
            )
            btn = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
            )
            btn.click()
            self.log("Clicked continue button")
            
            # Fill in password with simulated typing
            pwd = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.config['selectors']['password_field']))
            )
            pwd.clear()
            for char in password:
                pwd.send_keys(char)
                time.sleep(random.uniform(0.05, 0.2))
            self.log("Entered password with simulated typing")
            
            # Click final login button
            btn_after_pwd = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['login_btn']))
            )
            btn_after_pwd.click()
            self.log("Clicked login button after password")
            
            # Verify login success
            if not WebDriverWait(self.driver, 30).until(
                lambda d: "My Account" in d.find_element(By.CLASS_NAME, "header_infoTitle__Fse4B").text
            ):
                raise TimeoutException("Login not verified")
            self.log("✓ Login successful")
            return True
            
        except Exception as e:
            self.log(f"✗ Login failed: {e}")
            return False

    def handle_popups(self):
        """Handle any popups or policy dialogs"""
        for _ in range(5):
            try:
                if elems := self.driver.find_elements(By.CSS_SELECTOR, self.config['selectors']['popup_close']):
                    elems[0].click()
                    self.log("Closed popup")
                    time.sleep(1)
                    continue
                if elems := self.driver.find_elements(By.CSS_SELECTOR, self.config['selectors']['policy_accept']):
                    elems[0].click()
                    self.log("Accepted policy")
                    time.sleep(1)
                    continue
                break
            except Exception:
                break

    def get_max_purchase_limit(self):
        """Extract max purchase limit from product page"""
        try:
            limit_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.index_title__0OsZ span.index_info_KYZWO"))
            )
            limit_text = limit_element.text.strip()
            self.log(f"Found quantity limit text: {limit_text}")
            
            if "max" in limit_text.lower():
                import re
                match = re.search(r'\bmax\b[^0-9]*(\d{1,3})', limit_text.lower())
                if match:
                    max_limit = int(match.group(1))
                    self.log(f"Extracted max purchase limit: {max_limit}")
                    return max_limit
            
            self.log("No recognizable max purchase limit found")
            return None
            
        except TimeoutException:
            self.log("No quantity limit element found - assuming no purchase limit")
            return None
        except Exception as e:
            self.log(f"Error extracting max purchase limit: {e}")
            return None

    def adjust_quantity(self, desired_quantity):
        """Adjust quantity considering max purchase limits"""
        try:
            # Get current quantity (default 1)
            current_quantity = 1
            try:
                quantity_element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.config['selectors']['quantity_display']))
                )
                current_quantity = int(quantity_element.text.strip())
                self.log(f"Current quantity: {current_quantity}")
            except:
                self.log("Could not read current quantity, assuming 1")
                current_quantity = 1
            
            # Check against max limit
            max_limit = self.get_max_purchase_limit()
            
            if max_limit is not None:
                if current_quantity >= max_limit:
                    self.log(f"Already at max limit of {max_limit}, cannot increase")
                    return max_limit, desired_quantity - max_limit
                
                available_increase = max_limit - current_quantity
                actual_increase = min(available_increase, desired_quantity - current_quantity)
            else:
                actual_increase = desired_quantity - current_quantity
            
            if actual_increase <= 0:
                self.log(f"No quantity adjustment needed (current: {current_quantity}, desired: {desired_quantity})")
                return current_quantity, desired_quantity - current_quantity
            
            self.log(f"Attempting to increase quantity by {actual_increase}")
            
            # Click increment button
            increment_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['quantity_increment_btn']))
            )
            
            for _ in range(actual_increase):
                try:
                    increment_btn.click()
                    time.sleep(random.uniform(0.2, 0.5))
                    current_quantity += 1
                    self.log(f"Increased quantity to {current_quantity}")
                except Exception as e:
                    self.log(f"Error clicking increment button: {e}")
                    break
            
            remaining = max(0, desired_quantity - current_quantity)
            self.remaining_quantity = remaining  # Store remaining for this instance
            
            if remaining > 0:
                self.log(f"Remaining quantity after adjustment: {remaining}")
            
            return current_quantity, remaining
            
        except Exception as e:
            self.log(f"Error adjusting quantity: {e}")
            return current_quantity, desired_quantity - current_quantity
    def fill_credit_card_and_pay(self):
        """
        1) Click the Credit Card payment option
        2) Fill in card details with randomized typing delays
        3) Click the Pay button
        """
        try:
            # Get payment details from config
            account = self.config['accounts'][self.account_index]
            payment = account.get('payment', {})
            if not payment:
                raise ValueError("No payment details found in account configuration")
            
            card_number = payment['card_number']
            expiry_month = payment['expiry_month']
            expiry_year = payment['expiry_year']
            holder_name = payment['holder_name']
            cvv = payment['cvv']

            # 1) Select Credit Card radio/button
            self.log("Locating Credit Card payment option...")
            cc_option = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,
                    self.config['selectors']['credit_card_option']))
            )
            cc_option.click()
            self.log("✔ Clicked Credit Card option")
            
            # 2) Wait for Adyen card fields to load
            self.log("Waiting for card input form to become ready...")
            WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR,
                    self.config['selectors']['card_input_form']))
            )
            self.log("✔ Card input form is visible")

            # Helper to type with random per-character delay
            def human_type(web_element, text, field_name):
                for char in text:
                    web_element.send_keys(char)
                    delay = math.floor(random.random() * 200) / 1000.0  # 0-0.199s
                    self.log(f"   · Typed '{char}' into {field_name}, waiting {delay:.3f}s")
                    time.sleep(delay)

            # 2a) Card Number
            self.log("Locating card number field...")
            card_frame = self.driver.find_element(By.CSS_SELECTOR,
                self.config['selectors']['card_number_frame'])
            self.driver.switch_to.frame(card_frame)
            num_input = self.driver.find_element(By.CSS_SELECTOR, "input")
            self.log("✔ Card number iframe switched; ready to type number")
            human_type(num_input, card_number, "card number")
            self.driver.switch_to.default_content()

            # 2b) Expiry Date
            self.log("Locating expiry date field...")
            exp_frame = self.driver.find_element(By.CSS_SELECTOR,
                self.config['selectors']['expiry_date_frame'])
            self.driver.switch_to.frame(exp_frame)
            exp_input = self.driver.find_element(By.CSS_SELECTOR, "input")
            self.log("✔ Expiry date iframe switched; ready to type expiry")
            human_type(exp_input, f"{expiry_month:02d}{expiry_year%100:02d}", "expiry date")
            self.driver.switch_to.default_content()

            # 2c) Security Code (CVV) - do NOT log its actual value
            self.log("Locating security code (CVV) field...")
            cvc_frame = self.driver.find_element(By.CSS_SELECTOR,
                self.config['selectors']['cvv_frame'])
            self.driver.switch_to.frame(cvc_frame)
            cvc_input = self.driver.find_element(By.CSS_SELECTOR, "input")
            self.log("✔ CVV iframe switched; ready to type CVV (value hidden)")
            for _ in cvv:
                cvc_input.send_keys("•")  # mask logging
                delay = math.floor(random.random() * 200) / 1000.0
                self.log(f"   · Typed one CVV digit placeholder, waiting {delay:.3f}s")
                time.sleep(delay)
            self.driver.switch_to.default_content()

            # 2d) Cardholder Name
            self.log("Locating cardholder name field...")
            name_input = self.driver.find_element(By.CSS_SELECTOR,
                self.config['selectors']['cardholder_name'])
            self.log("✔ Ready to type cardholder name")
            human_type(name_input, holder_name, "cardholder name")

            # 3) Click the final Pay button
            self.log("Locating Pay button...")
            pay_btn = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,
                    self.config['selectors']['pay_button']))
            )
            self.log("✔ Pay button found; clicking to submit payment")
            pay_btn.click()
            self.log("✔ Payment submitted, awaiting confirmation...")
            return True

        except Exception as e:
            self.log(f"ERROR in fill_credit_card_and_pay: {e}")
            raise

    def complete_purchase(self):
        """Complete the checkout process"""
        try:
            self.driver.get("https://www.popmart.com/us/largeShoppingCart")
            
            # Select all items
            chk = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['select_all']))
            )
            chk.click()
            time.sleep(1)
            
            # Proceed through checkout
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['checkout_btn']))
            ).click()
            self.log("Clicked checkout")
            
            WebDriverWait(self.driver, 10).until(EC.url_changes)
            
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['proceed_to_pay']))
            ).click()
            self.log("Clicked proceed to pay")
            
            #continue payement flow here
            # Wait for payment page to load
            WebDriverWait(self.driver, 10).until(EC.url_changes)
            
            # Fill credit card details and complete payment
            if not self.fill_credit_card_and_pay():
                return False
                
            # Verify payment completion
            WebDriverWait(self.driver, 30).until(
                lambda d: "order confirmation" in d.current_url.lower() or 
                         "thank you" in d.page_source.lower()
            )
            self.log("✓ Payment completed successfully")
            return True
            
        except Exception as e:
            self.log(f"✗ Checkout error: {e}")
            return False    
            
            return True
            
        except Exception as e:
            self.log(f"✗ Checkout error: {e}")
            return False

    def handle_remaining_quantity(self, url, remaining):
        """Create new bot instance for remaining quantity with next account"""
        next_index = self.account_index + 1
        accounts = self.config.get('accounts', [])
        
        if next_index < len(accounts):
            self.log(f"Creating new instance for remaining quantity: {remaining}")
            
            # Create new bot instance with next account
            new_bot = PopMartBot(socketio=self.socketio, account_index=next_index)
            
            def run_new_bot():
                try:
                    self.log(f"Starting new bot instance for account {next_index}")
                    if new_bot.run(url, 'buy', remaining):
                        self.log(f"New instance completed successfully")
                    else:
                        self.log(f"New instance failed")
                except Exception as e:
                    self.log(f"Error in new bot instance: {e}")
                finally:
                    if new_bot.driver:
                        new_bot.driver.quit()
            
            # Run in new thread
            threading.Thread(target=run_new_bot, daemon=True).start()
        else:
            self.log("No more accounts available for remaining quantity")

    def monitor_product(self, url, action, desired_quantity):
        """Monitor and purchase product with account rotation"""
        self._running = True
        self.current_product_url = url
        self.desired_quantity = desired_quantity
        
        try:
            while self._running:
                self.driver.get(url)
                time.sleep(random.uniform(1, 3))
                
                # Check product availability
                add_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['add_to_bag']))
                )
                self.log("Product available")
                
                # Adjust quantity
                actual_quantity, remaining = self.adjust_quantity(desired_quantity)
                self.log(f"Adjusted quantity: {actual_quantity} (remaining: {remaining})")
                
                # Add to cart
                add_btn.click()
                time.sleep(1)
                
                if action == 'buy':
                    if self.complete_purchase() and remaining > 0:
                        self.handle_remaining_quantity(url, remaining)
                    return True
                
                break
                
        except Exception as e:
            self.log(f"✗ Monitor error: {e}")
            return False
        finally:
            self.log("Monitor product finished")
            self.current_product_url = None

    def run(self, url, action, qty):
        """Main execution method"""
        try:
            self.init_driver()
            if not self.popmart_login():
                return False
            return self.monitor_product(url, action, qty)
        except Exception as e:
            self.log(f"✗ Bot error: {e}")
            return False
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    self.log("Browser closed")
                except Exception as e:
                    self.log(f"Error quitting driver: {e}")