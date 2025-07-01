import json
import time
import random
import os
import json
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from fake_useragent import UserAgent

class PopMartBot:
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.driver = None
        self.config = self.load_config()
        self.login_timeout = 120  # seconds for login
        self._running = False

    def load_config(self):
        with open('config/config.json', 'r') as f:
            return json.load(f)

    def log(self, message):
        print(message)
        if self.socketio:
            self.socketio.emit('log', message)

    def _add_random_headers(self):
        """Add randomized HTTP headers to make network signature more human-like"""
        # List of common Accept-Language values
        accept_languages = [
            "en-US,en;q=0.9",
            "en-US,en;q=0.8",
            "en-GB,en;q=0.9,en-US;q=0.8",
            "en-CA,en;q=0.9,fr-CA;q=0.8",
            "en-AU,en;q=0.9,en-GB;q=0.8"
        ]
        
        # List of common Accept values
        accept_values = [
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        ]
        
        # Random sec-ch-ua values (Chrome version indicators)
        chrome_versions = [
            '" Not A;Brand";v="99", "Chromium";v="101", "Google Chrome";v="101"',
            '" Not A;Brand";v="99", "Chromium";v="102", "Google Chrome";v="102"',
            '"Google Chrome";v="105", "Not)A;Brand";v="8", "Chromium";v="105"',
            '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"'
        ]
        
        # Create headers dictionary
        headers = {
            "Accept": random.choice(accept_values),
            "Accept-Language": random.choice(accept_languages),
            "sec-ch-ua": random.choice(chrome_versions),
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": f'"Windows"', # Hardcoding for now, can be randomized later
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
        
        # Apply headers using CDP
        self.driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {'headers': headers})
        self.log("Applied randomized HTTP headers")

    def init_driver(self):
        # Use real Chrome profile
        profile_path = self.config['chrome_settings']['profile_path']
        
        # Generate random user agent
        try:
            ua = UserAgent()
            user_agent = ua.chrome
        except:
            # Fallback user agents if fake_useragent fails
            chrome_versions = ['96.0.4664.110', '97.0.4692.71', '98.0.4758.102', '99.0.4844.51']
            os_versions = ['Windows NT 10.0; Win64; x64', 'Macintosh; Intel Mac OS X 10_15_7', 'X11; Linux x86_64']
            user_agent = f"Mozilla/5.0 ({random.choice(os_versions)}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.choice(chrome_versions)} Safari/537.36"
        
        # Randomize viewport dimensions


        # Create undetected_chromedriver options
        options = uc.ChromeOptions()
        options.add_argument(f'--user-agent={user_agent}')

        
        # Add additional performance and privacy flags
        options.add_argument('--disable-extensions')
       
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-webgl')
        options.add_argument('--enable-unsafe-swiftshader')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_argument('--disable-site-isolation-trials')
        options.add_argument('--disable-blink-features=CSSOMSmoothScroll')
        options.add_argument('--disable-smooth-scrolling')
        options.add_argument('--disable-gpu-rasterization')
        options.add_argument('--disable-accelerated-2d-canvas')
        options.add_argument('--disable-background-networking')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-client-side-phishing-detection')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-extensions')
        



        # Initialize undetected_chromedriver
        self.driver = uc.Chrome(
            options=options,
            user_data_dir=profile_path if os.path.exists(profile_path) else None,
            driver_executable_path=self.config['chrome_settings']['chromedriver_path']
        )
        self.log(f"Using User-Agent: {user_agent}")
        self.log("Chrome driver initialized.")

        # Apply anti-detection measures
        self._add_random_headers()
        self._randomize_timezone_and_geolocation()

        self._randomize_browser_fingerprint()
        self._randomize_battery_api()
        self._randomize_speech_synthesis()
        self._randomize_media_devices()
        self._randomize_visual_properties()
        self._patch_webdriver_artifacts()
        self._clear_plugins_and_mimeTypes()
        self._emulate_background_behavior()

    def _randomize_timezone_and_geolocation(self):
        # Placeholder for timezone and geolocation randomization logic
        self.log("Randomizing timezone and geolocation (placeholder).")


    def _randomize_browser_fingerprint(self):
        # Placeholder for browser fingerprint randomization logic
        self.log("Randomizing browser fingerprint (placeholder).")

    def _randomize_battery_api(self):
        # Placeholder for battery API randomization logic
        self.log("Randomizing battery API (placeholder).")

    def _randomize_speech_synthesis(self):
        # Placeholder for speech synthesis randomization logic
        self.log("Randomizing speech synthesis (placeholder).")

    def _randomize_media_devices(self):
        # Placeholder for media devices randomization logic
        self.log("Randomizing media devices (placeholder).")

    def _randomize_visual_properties(self):
        # Placeholder for visual properties randomization logic
        self.log("Randomizing visual properties (placeholder).")

    def _patch_webdriver_artifacts(self):
        # Placeholder for patching webdriver artifacts logic
        self.log("Patching webdriver artifacts (placeholder).")

    def _clear_plugins_and_mimeTypes(self):
        # Placeholder for clearing plugins and MIME types logic
        self.log("Clearing plugins and MIME types (placeholder).")

    def _emulate_background_behavior(self):
        # Placeholder for background behavior emulation logic
        self.log("Emulating background behavior (placeholder).")

    def clear_browser_data(self):
        try:
            self.driver.delete_all_cookies()
            self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
            self.driver.execute_cdp_cmd('Network.clearBrowserCookies', {})
            self.log("✓ Cleared browser cookies and cache")
        except Exception as e:
            self.log(f"Failed to clear browser data: {e}")

    def popmart_login(self):
        self.clear_browser_data()
        self.driver.get("https://popmart.com/us/user/login/")
        self.log("Opened login page")
        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.config['selectors']['login_field']))
            )
            # handle popups if any
            self.handle_popups()
        # fill credentials
            login = self.driver.find_element(By.CSS_SELECTOR, self.config['selectors']['login_field'])
            login.clear()
            username = self.config['accounts'][0]['email']
            for char in username:
                login.send_keys(char)
                time.sleep(random.uniform(0.05, 0.2)) # Random delay between 50ms and 200ms
            self.log("Entered username with simulated typing")
            self.log(
                "Attempting to click the login button: "
                "<div class=\"ant-form-item\">"
                "<div class=\"ant-form-item-control-input-content\">"
                "<button class=\"ant-btn ant-btn-primary index_loginButton__O6r8l\">CONTINUE</button>"
                "</div></div>"
            )

            # more specific selector matches the full hierarchy and all relevant classes
            button_selector = (
                "div.ant-form-item "
                "div.ant-form-item-control-input "
                "div.ant-form-item-control-input-content > "
                "button.ant-btn.ant-btn-primary.index_loginButton__O6r8l"
            )

            try:
                # wait for any overlay/spinner to disappear first (optional)
                WebDriverWait(self.driver, 15).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, ".loading-overlay"))
                )
            except TimeoutException:
                self.log("Overlay did not disappear, proceeding anyway.")

            try:
                # wait until the precise button is visible and clickable
                btn = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
                )
                self.log("Login button found and clickable.")

                # scroll into view just in case it's off-screen
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)

                btn.click()
                self.log("Clicked login button successfully.")
            except TimeoutException as e:
                self.log(f"ERROR: Timed out waiting for login button → {e}")
            except StaleElementReferenceException as e:
                self.log(f"WARNING: Stale element, retrying click → {e}")
                btn = self.driver.find_element(By.CSS_SELECTOR, button_selector)
                btn.click()
                self.log("Clicked login button after retrying stale reference.")
            self.log("Clicked login button after username")
            # Wait for the password field to be present after clicking the first login button
            pwd = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.config['selectors']['password_field']))
            )
            pwd.clear()
            password = self.config['accounts'][0]['password']
            for char in password:
                pwd.send_keys(char)
                time.sleep(random.uniform(0.05, 0.2)) # Random delay between 50ms and 200ms
            self.log("Entered password with simulated typing")
            # Re-locate the login button if it's a new one for password submission, or use the same if it's a single form
            # Assuming it's the same button or a new one appears after password entry
            btn_after_pwd = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['login_btn']))
            )
            btn_after_pwd.click()
            self.log("Clicked login button after password")
            # verify
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
        # close popups or policy dialogs
        for _ in range(5):
            try:
                if elems := self.driver.find_elements(By.CSS_SELECTOR, self.config['selectors']['popup_close']):
                    elems[0].click(); self.log("Closed popup"); time.sleep(1)
                    continue
                if elems := self.driver.find_elements(By.CSS_SELECTOR, self.config['selectors']['policy_accept']):
                    elems[0].click(); self.log("Accepted policy"); time.sleep(1)
                    continue
                break
            except Exception:
                break

    def monitor_product(self, url, action, quantity):
        self._running = True
        try:
            while self._running:
                self.driver.get(url)
                time.sleep(random.uniform(1, 3))
                add_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['add_to_bag']))
                )
                self.log("Product available")
                add_btn.click(); time.sleep(1)
                self.driver.get("https://www.popmart.com/us/largeShoppingCart")
                # select all
                chk = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['select_all']))
                )
                chk.click(); time.sleep(1)
                if action == 'buy':
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['checkout_btn']))
                    ).click(); self.log("Clicked checkout")
                    WebDriverWait(self.driver, 10).until(EC.url_changes)
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['proceed_to_pay']))
                    ).click(); self.log("Clicked proceed to pay")
                    WebDriverWait(self.driver, 10).until(EC.url_changes)
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['true_mo_pay']))
                    ).click(); self.log("Selected payment method")
                    btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['ordering']))
                    )
                    btn.click(); self.log(f"Order placed, QR: {self.driver.current_url}")
                    return True
        except Exception as e:
            self.log(f"✗ Monitor error: {e}")
            return False
        finally:
            self.driver.quit()
            self.log("Browser closed")

    def run(self, url, action, qty):
        try:
            self.init_driver()
            if not self.popmart_login(): return False
            return self.monitor_product(url, action, qty)
        except Exception as e:
            self.log(f"✗ Bot error: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                self.log("Browser closed")
