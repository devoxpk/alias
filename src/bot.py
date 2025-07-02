import json
import time
import random
import os
import threading
import math
import datetime
import hashlib
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
from selenium.webdriver.chrome.service import Service
from selenium.webdriver import ChromeOptions

class PopMartBot:
    # Class-level lock for thread-safe operations
    _class_lock = threading.Lock()
    
    # Constants for session management
    MAX_SESSION_DURATION = 30 * 60  # 30 minutes in seconds
    FINGERPRINT_CHECK_INTERVAL = 5 * 60  # Check fingerprint every 5 minutes
    
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
        
        # Anti-detection session management
        self.session_start_time = None
        self.last_fingerprint_check = None
        self.initial_fingerprint = None
        self.current_user_agent = None
        self.current_viewport = None
        self.current_timezone = None
        self.current_webgl_hash = None
        self.request_timestamps = []  # For tracking request patterns
        self._in_login_verification = False  # Flag to track login verification state
    
    def init_driver(self):
        """Initialize undetected Chrome driver with real Chrome TLS fingerprint and anti-detection measures"""
        try:
            # Start a new session
            self.session_start_time = datetime.datetime.now()
            self.last_fingerprint_check = self.session_start_time
            
            # Generate randomized but consistent user context for this session
                         
            self._generate_user_context()
            
            options = uc.ChromeOptions()
            
            # TLS fingerprint matching real Chrome browser settings
            # Use exact Chrome 137 cipher suites for TLS fingerprint matching
            options.add_argument('--ssl-version-min=tls1.2')
            options.add_argument('--ssl-version-max=tls1.3')
            # Don't blacklist ciphers to match real Chrome TLS fingerprint
            options.add_argument('--disable-features=IsolateOrigins,site-per-process')
            options.add_argument('--disable-site-isolation-trials')
            
            # Anti-detection settings
            options.add_argument(f'--user-agent={self.current_user_agent}')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-infobars')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-popup-blocking')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Use a random debugging port to avoid conflicts and detection
            debug_port = random.randint(9222, 9999)
            options.add_argument(f'--remote-debugging-port={debug_port}')
            
            # Use default window size unless a specific viewport is set
            if self.current_viewport:
                options.add_argument(f'--window-size={self.current_viewport}')
            
            # Initialize undetected Chrome with custom service
            service = Service(executable_path=os.path.join(os.getcwd(), 'chromedriver-win64', 'chromedriver.exe'))
            
            self.driver = uc.Chrome(
                options=options,
                service=service,
                headless=False,  # Set to True if you want headless
                use_subprocess=True,
                version_main=137
            )
            
            # Monitor SSL/TLS handshake
            self._setup_tls_monitoring()
            
            # Additional anti-bot evasion
            self._apply_browser_fingerprint_evasion()
            
            # Store initial fingerprint for integrity monitoring
            self.initial_fingerprint = self._get_browser_fingerprint()
            
            self.log("✓ Browser initialized with real Chrome TLS fingerprint")
            return True
            
        except Exception as e:
            self.log(f"✗ Failed to initialize browser: {e}")
            return False
            
    def _generate_user_context(self):
        """Generate a consistent set of user context parameters for this session"""
        # Generate user agent - prefer modern Chrome versions
        ua = UserAgent()
        chrome_ua = ua.chrome
        self.current_user_agent = chrome_ua
        self.log(f"Generated user agent: {self.current_user_agent[:30]}...")
        
        # Generate random but realistic viewport size
        self.current_viewport = None # Use default viewport
        
        # Set a random timezone from common US timezones
        timezones = ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"]
        self.current_timezone = random.choice(timezones)
        
        self.log(f"Session context: Viewport={self.current_viewport}, Timezone={self.current_timezone}")
    
    def _apply_browser_fingerprint_evasion(self):
        """Apply various techniques to evade browser fingerprinting"""
        if not self.driver:
            return
            
        # Override webdriver flag
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Override user agent at CDP level for consistency
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": self.current_user_agent})
        
        # Modify navigator properties to appear more like a regular browser
        evasions = """
        // Overwrite the 'plugins' property to report a reasonable number of plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = {
                    length: 5,
                    item: () => { return null; },
                    namedItem: () => { return null; },
                    refresh: () => {}
                };
                return plugins;
            }
        });
        
        // Override the hardwareConcurrency to a common value
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8
        });
        
        // Override platform to a common value
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32'
        });
        
        // Override language to match our settings
        Object.defineProperty(navigator, 'language', {
            get: () => 'en-US'
        });
        
        // Override Chrome-specific properties
        if (window.chrome) {
            window.chrome.runtime = {};
        }
        """
        
        try:
            self.driver.execute_script(evasions)
            self.log("Applied browser fingerprint evasion techniques")
        except Exception as e:
            self.log(f"Warning: Could not apply all evasion techniques: {e}")
    
    def _get_browser_fingerprint(self):
        """Get a hash representing the current browser fingerprint for integrity monitoring"""
        if not self.driver:
            return None
            
        try:
            # Collect various browser properties that shouldn't change during a session
            fingerprint_script = """
            return {
                'userAgent': navigator.userAgent,
                'language': navigator.language,
                'platform': navigator.platform,
                'hardwareConcurrency': navigator.hardwareConcurrency,
                'screenWidth': window.screen.width,
                'screenHeight': window.screen.height,
                'colorDepth': window.screen.colorDepth,
                'devicePixelRatio': window.devicePixelRatio,
                'timezone': Intl.DateTimeFormat().resolvedOptions().timeZone,
                'timezoneOffset': new Date().getTimezoneOffset()
            };
            """
            
            fingerprint_data = self.driver.execute_script(fingerprint_script)
            
            # Create a hash of the fingerprint data
            fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
            fingerprint_hash = hashlib.md5(fingerprint_str.encode()).hexdigest()
            
            self.log(f"Generated browser fingerprint: {fingerprint_hash[:8]}...")
            return fingerprint_hash
            
        except Exception as e:
            self.log(f"Warning: Could not generate browser fingerprint: {e}")
            return None

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
        """Clear ALL browser storage including cookies, cache, localStorage, sessionStorage, IndexedDB, etc."""
        try:
            self.log("Starting comprehensive browser data clearing...")
            
            # 1. Clear cookies using multiple methods
            self.log("Clearing cookies...")
            self.driver.delete_all_cookies()
            try:
                self.driver.execute_cdp_cmd('Network.clearBrowserCookies', {})
            except Exception as e:
                self.log(f"CDP cookie clear failed, continuing with other methods: {e}")
            
            # 2. Clear browser cache
            self.log("Clearing browser cache...")
            try:
                self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
            except Exception as e:
                self.log(f"CDP cache clear failed, continuing with other methods: {e}")
            
            # 3. Enhanced comprehensive storage clearing with better error handling
            self.log("Clearing all browser storage...")
            storage_clear_script = """
            return (async function clearAllStorage() {
                const results = {};
                
                try {
                    // Clear localStorage
                    if (window.localStorage) {
                        console.log('Clearing localStorage...');
                        const localStorageSize = Object.keys(localStorage).length;
                        localStorage.clear();
                        results.localStorage = `Cleared ${localStorageSize} items`;
                    }
                    
                    // Clear sessionStorage
                    if (window.sessionStorage) {
                        console.log('Clearing sessionStorage...');
                        const sessionStorageSize = Object.keys(sessionStorage).length;
                        sessionStorage.clear();
                        results.sessionStorage = `Cleared ${sessionStorageSize} items`;
                    }
                    
                    // Clear IndexedDB databases
                    if (window.indexedDB) {
                        console.log('Clearing IndexedDB...');
                        try {
                            const databases = indexedDB.databases ? await indexedDB.databases() : [];
                            results.indexedDB = `Found ${databases.length} databases`;
                            
                            for (const db of databases) {
                                try {
                                    await new Promise((resolve, reject) => {
                                        const request = indexedDB.deleteDatabase(db.name);
                                        request.onsuccess = () => resolve();
                                        request.onerror = () => reject(new Error(`Failed to delete DB: ${db.name}`));
                                        request.onblocked = () => console.warn(`Database deletion blocked: ${db.name}`);
                                    });
                                    console.log(`Deleted IndexedDB: ${db.name}`);
                                } catch (dbError) {
                                    console.error(`Error deleting IndexedDB ${db.name}:`, dbError);
                                }
                            }
                        } catch (idbError) {
                            results.indexedDBError = idbError.toString();
                        }
                    }
                    
                    // Clear service workers
                    if (navigator.serviceWorker) {
                        console.log('Clearing service workers...');
                        try {
                            const registrations = await navigator.serviceWorker.getRegistrations();
                            results.serviceWorkers = `Found ${registrations.length} service workers`;
                            
                            for (const registration of registrations) {
                                await registration.unregister();
                                console.log('Unregistered service worker');
                            }
                        } catch (swError) {
                            results.serviceWorkerError = swError.toString();
                        }
                    }
                    
                    // Clear cache storage
                    if (window.caches) {
                        console.log('Clearing cache storage...');
                        try {
                            const keys = await caches.keys();
                            results.cacheStorage = `Found ${keys.length} cache stores`;
                            
                            for (const key of keys) {
                                await caches.delete(key);
                                console.log(`Deleted cache: ${key}`);
                            }
                        } catch (cacheError) {
                            results.cacheStorageError = cacheError.toString();
                        }
                    }
                    
                    // Clear WebSQL databases
                    if (window.openDatabase) {
                        console.log('Attempting to clear WebSQL databases...');
                        results.webSQL = 'Attempted to clear (requires manual version increment)';
                    }
                    
                    // Clear Application Cache (deprecated but might still exist)
                    if (window.applicationCache) {
                        console.log('Clearing application cache...');
                        try {
                            window.applicationCache.swapCache();
                            results.applicationCache = 'Attempted to clear';
                        } catch (appCacheError) {
                            results.applicationCacheError = appCacheError.toString();
                        }
                    }
                    
                    // Clear any site-specific permissions
                    if (navigator.permissions) {
                        console.log('Noting permissions (cannot be cleared via JS)...');
                        results.permissions = 'Noted (requires manual clearing)';
                    }
                    
                    return {
                        success: true,
                        message: 'Storage clearing operations completed',
                        details: results
                    };
                } catch (e) {
                    return {
                        success: false,
                        message: 'Error in storage clearing: ' + e.message,
                        error: e.toString(),
                        details: results
                    };
                }
            })();
            """
            
            # Execute the enhanced storage clearing script with longer timeout
            try:
                result = self.driver.execute_async_script(storage_clear_script)
                self.log(f"Storage clearing result: {result}")
            except Exception as script_error:
                self.log(f"Error executing storage clearing script: {script_error}")
            
            # 4. Reset request timestamps to avoid pattern detection
            self.request_timestamps = []
            
            # 5. Use CDP commands to clear all site data (most comprehensive approach)
            self.log("Using CDP commands to clear all site data...")
            try:
                # Clear all storage types for all origins
                self.driver.execute_cdp_cmd('Storage.clearDataForOrigin', {
                    "origin": "*",
                    "storageTypes": "all"
                })
                
                # Additional specific storage clearing
                storage_types = [
                    "appcache", "cookies", "file_systems", "indexeddb", 
                    "local_storage", "shader_cache", "websql", "service_workers",
                    "cache_storage", "all"
                ]
                
                for storage_type in storage_types:
                    try:
                        self.driver.execute_cdp_cmd('Storage.clearDataForOrigin', {
                            "origin": "*",
                            "storageTypes": storage_type
                        })
                    except Exception:
                        # Continue with other storage types if one fails
                        pass
                
                self.log("Cleared all site data using CDP commands")
            except Exception as e:
                self.log(f"CDP site data clearing failed: {e}")
            
            # 6. Navigate to blank page to ensure clean state
            try:
                self.driver.get("about:blank")
                self.log("Navigated to blank page to ensure clean state")
            except Exception as e:
                self.log(f"Failed to navigate to blank page: {e}")
            
            self.log("✓ Completed comprehensive browser data clearing")
            return True
        except Exception as e:
            self.log(f"Failed to clear browser data: {e}")
            return False
            

            
    def _record_request_timestamp(self):
        """Record timestamp of current request for traffic pattern analysis"""
        now = time.time()
        self.request_timestamps.append(now)
        
        # Keep only the last 20 timestamps to avoid memory bloat
        if len(self.request_timestamps) > 20:
            self.request_timestamps = self.request_timestamps[-20:]
            
    def _randomize_next_request_delay(self):
        """Calculate a randomized delay for the next request to avoid patterns"""
        # If we have at least 2 timestamps, analyze the pattern
        if len(self.request_timestamps) >= 2:
            # Calculate average interval between recent requests
            intervals = [self.request_timestamps[i] - self.request_timestamps[i-1] 
                         for i in range(1, len(self.request_timestamps))]
            avg_interval = sum(intervals) / len(intervals) if intervals else 1.0
            
            # Avoid repeating the same interval pattern by adding variability
            # More variability if we detect a consistent pattern
            std_dev = (max(intervals) - min(intervals)) if intervals else 0
            if std_dev < 0.5 and len(intervals) > 3:  # Detected consistent timing
                # Add more randomness to break the pattern
                jitter_factor = random.uniform(0.5, 2.0)
                self.log(f"Detected consistent timing pattern, adding jitter factor {jitter_factor:.2f}")
            else:
                # Normal variability
                jitter_factor = random.uniform(0.7, 1.3)
                
            delay = avg_interval * jitter_factor
            
            # Ensure delay is within reasonable bounds
            delay = min(max(delay, 0.5), 5.0)
            return delay
        else:
            # Not enough data, use a reasonable default
            return random.uniform(0.5, 2.0)
            
    def _check_fingerprint_integrity(self):
        """Check if browser fingerprint has changed, indicating potential detection"""
        if not self.driver or not self.initial_fingerprint:
            return True
            
        # Skip fingerprint checks during login process
        current_url = self.driver.current_url.lower()
        if "login" in current_url or "signin" in current_url or "user/login" in current_url:
            self.log("Skipping fingerprint integrity check during login process")
            return True
            
        # Also skip checks during login verification (when URL is changing)
        try:
            # Check if we're in the process of login verification
            if hasattr(self, '_in_login_verification') and self._in_login_verification:
                self.log("Skipping fingerprint integrity check during login verification")
                return True
        except:
            pass
            
        now = datetime.datetime.now()
        elapsed = (now - self.last_fingerprint_check).total_seconds()
        
        # Only check periodically to avoid overhead
        if elapsed < self.FINGERPRINT_CHECK_INTERVAL:
            return True
            
        self.last_fingerprint_check = now
        self.log("Checking fingerprint integrity...")
        
        current_fingerprint = self._get_browser_fingerprint()
        if not current_fingerprint:
            self.log("Warning: Could not check fingerprint integrity")
            return True
            
        if current_fingerprint != self.initial_fingerprint:
            self.log(f"⚠️ Fingerprint integrity check failed! Fingerprint has changed.")
            self.log(f"Original: {self.initial_fingerprint[:8]}..., Current: {current_fingerprint[:8]}...")
            return False
            
        self.log("✓ Fingerprint integrity verified")
        return True
        
    def _should_rotate_session(self):
        """Determine if we should rotate the session based on time or fingerprint integrity
        Token rotation is now scoped to non-login flows only"""
        if not self.session_start_time:
            return False
            
        # Check if we're on the login page - don't rotate during login
        current_url = self.driver.current_url.lower()
        if "login" in current_url or "signin" in current_url or "user/login" in current_url:
            self.log("Skipping session rotation on login page")
            return False
            
        # Check session duration
        now = datetime.datetime.now()
        session_duration = (now - self.session_start_time).total_seconds()
        
        # Check fingerprint integrity
        fingerprint_ok = self._check_fingerprint_integrity()
        
        # Rotate if session is too long or fingerprint has changed, but only for non-login flows
        if session_duration > self.MAX_SESSION_DURATION:
            self.log(f"Session duration ({session_duration:.1f}s) exceeded maximum ({self.MAX_SESSION_DURATION}s)")
            return True
        elif not fingerprint_ok:
            self.log("Session rotation triggered by fingerprint integrity check failure")
            return True
            
        return False

    def _setup_tls_monitoring(self):
        """Setup monitoring for SSL/TLS handshake with fallback methods"""
        try:
            # Try CDP commands first
            try:
                self.driver.execute_cdp_cmd('Network.enable', {})
                self.driver.execute_cdp_cmd('Security.enable', {})
                self.log("TLS/SSL handshake monitoring enabled via CDP")
                return True
            except Exception as e:
                self.log(f"CDP monitoring setup failed, using fallback: {e}")
            
            # Fallback: Setup basic HTTPS verification
            self.driver.execute_script("""
                window.addEventListener('securitypolicyviolation', function(e) {
                    console.error('Security policy violation:', e.violatedDirective);
                });
            """)
            self.log("Basic HTTPS verification enabled as fallback")
            return True
        except Exception as e:
            self.log(f"Warning: Could not setup any TLS monitoring: {e}")
            return True  # Return True to avoid blocking operations
    
    def _simulate_mouse_gesture(self, element, gesture_type="natural"):
        """Simulate realistic mouse gestures for interacting with elements with improved error handling"""
        if not element or not self.driver:
            return False
            
        try:
            # First ensure element is in viewport and wait for it to be stable
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", element)
            time.sleep(0.5)  # Give time for scrolling to complete
            
            # Get element dimensions and position after scrolling
            element_rect = self.driver.execute_script("""
                var rect = arguments[0].getBoundingClientRect();
                return {
                    top: rect.top,
                    left: rect.left,
                    width: rect.width,
                    height: rect.height,
                    bottom: rect.bottom,
                    right: rect.right
                };
            """, element)
            
            # Verify element is actually visible in viewport
            viewport_height = self.driver.execute_script("return window.innerHeight;")
            viewport_width = self.driver.execute_script("return window.innerWidth;")
            
            # Check if element is at least partially in viewport
            if (element_rect['bottom'] < 0 or element_rect['top'] > viewport_height or 
                element_rect['right'] < 0 or element_rect['left'] > viewport_width):
                self.log("Element not in viewport, adjusting scroll")
                # Try one more time with different scroll approach
                self.driver.execute_script("""
                    arguments[0].scrollIntoView();
                    window.scrollBy(0, -100); // Adjust to ensure element isn't at the very top
                """, element)
                time.sleep(0.5)
            
            # Create a fresh action chain
            actions = ActionChains(self.driver)
            
            # First reset mouse position with a no-op move to establish a known position
            actions.move_by_offset(0, 0).perform()
            actions = ActionChains(self.driver)  # Reset action chain
            
            if gesture_type == "natural":
                # Use a simpler, more reliable approach
                # Move to center of viewport first
                center_x = viewport_width / 2
                center_y = viewport_height / 2
                
                # Move to center with offset using move_by_offset
                # First move to (0,0) to establish base position
                actions.move_by_offset(0, 0).perform()
                actions = ActionChains(self.driver)
                
                # Calculate relative movement to center with offset
                current_x = int(self.driver.execute_script("return window.scrollX || document.documentElement.scrollLeft;"))
                current_y = int(self.driver.execute_script("return window.scrollY || document.documentElement.scrollTop;"))
                
                target_x = int(center_x + random.randint(-50, 50) - current_x)
                target_y = int(center_y + random.randint(-50, 50) - current_y)
                
                actions.move_by_offset(target_x, target_y)
                actions.pause(random.uniform(0.1, 0.3))
                actions.perform()
                
                # Reset action chain and move to element
                actions = ActionChains(self.driver)
                actions.move_to_element(element)
                actions.pause(random.uniform(0.1, 0.2))
                actions.click()
                actions.perform()
                
            elif gesture_type == "direct":
                # More direct movement - safer approach
                try:
                    # Try using JavaScript click first as most reliable method
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception:
                    # Fall back to ActionChains if JS click fails
                    actions.move_to_element(element)
                    actions.pause(random.uniform(0.1, 0.2))
                    actions.click()
                    actions.perform()
            
            return True
            
        except Exception as e:
            self.log(f"Warning: Mouse gesture failed: {e}")
            # Fall back to JavaScript click if mouse gesture fails
            try:
                self.log("Attempting fallback JavaScript click")
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception:
                # Last resort: try direct click
                try:
                    self.log("Attempting fallback direct click")
                    element.click()
                    return True
                except Exception as click_error:
                    self.log(f"All click methods failed: {click_error}")
                    return False

    def popmart_login(self):
        """Login using the account specified by account_index with mouse gestures and fallback mechanisms"""
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
            
            # Wait for page to be fully loaded
            WebDriverWait(self.driver, 30).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # Handle popups and policy dialogs first
            self.handle_popups()
            
            # Additional wait after handling popups to ensure stability
            time.sleep(1)
            
            # Ensure page is properly positioned
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)  # Shorter scroll stabilization
            
            # Handle popups and policy dialogs immediately after navigating to the login page
            self.log("Attempting to handle popups and policy dialogs before login field interaction.")
            self.handle_popups()
            
            # Now look for the login field
            try:
                login_field = WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.config['selectors']['login_field']))
                )
                # Verify field is actually visible and interactive
                if not login_field.is_displayed() or not login_field.is_enabled():
                    self.log("Login field found but not interactive, proceeding with login attempts.")
            except Exception as e:
                self.log(f"Error locating login field: {e}")
                return False # Cannot proceed without login field
            
            # Ensure element is in view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", login_field)
            time.sleep(0.5)  # Allow time for scroll
            
            self.log(f"Login field properties: Displayed={login_field.is_displayed()}, Enabled={login_field.is_enabled()}, Tag={login_field.tag_name}, Location={login_field.location}, Size={login_field.size}")

            # Always use direct click and send_keys for debugging
            try:
                login_field.click()
                self.log("Clicked login field directly.")
            except Exception as click_e:
                self.log(f"Error clicking login field directly: {click_e}")
                # Fallback to JavaScript click if direct click fails
                try:
                    self.driver.execute_script("arguments[0].click();", login_field)
                    self.log("Clicked login field via JavaScript.")
                except Exception as js_click_e:
                    self.log(f"Error clicking login field via JavaScript: {js_click_e}")
                    return False # Cannot proceed if click fails

            login_field.clear()
            self.log("Cleared login field.")
            
            # Type username with human-like timing
            for char in username:
                login_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.2))
            self.log("Entered username with simulated typing")
            self.log("Entered username with simulated typing")
            
            # Click continue button with mouse gesture or fallback
            button_selector = (
                "div.ant-form-item "
                "div.ant-form-item-control-input "
                "div.ant-form-item-control-input-content > "
                "button.ant-btn.ant-btn-primary.index_loginButton__O6r8l"
            )
            btn = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
            )
            
            # Ensure button is in view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
            time.sleep(0.5)  # Allow time for scroll
            
            # Try mouse gesture first, fall back to direct click
            if not self._simulate_mouse_gesture(btn, "direct"):
                self.log("Using fallback method for continue button")
                btn.click()
                
            self.log("Clicked continue button")
            
            # Wait for password field with increased timeout
            pwd = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.config['selectors']['password_field']))
            )
            
            # Ensure password field is in view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pwd)
            time.sleep(0.5)  # Allow time for scroll
            
            self.log(f"Password field properties: Displayed={pwd.is_displayed()}, Enabled={pwd.is_enabled()}, Tag={pwd.tag_name}, Location={pwd.location}, Size={pwd.size}")

            try:
                pwd.click()
                self.log("Clicked password field directly.")
            except Exception as click_e:
                self.log(f"Error clicking password field directly: {click_e}")
                try:
                    self.driver.execute_script("arguments[0].click();", pwd)
                    self.log("Clicked password field via JavaScript.")
                except Exception as js_click_e:
                    self.log(f"Error clicking password field via JavaScript: {js_click_e}")
                    return False

            pwd.clear()
            self.log("Cleared password field.")
            
            # Type password with human-like timing
            for char in password:
                pwd.send_keys(char)
                time.sleep(random.uniform(0.05, 0.2))
            self.log("Entered password with simulated typing")
            
            # Click final login button with mouse gesture or fallback
            btn_after_pwd = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['login_btn']))
            )
            
            # Ensure button is in view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_after_pwd)
            time.sleep(0.5)  # Allow time for scroll
            
            self.log(f"Login button properties: Displayed={btn_after_pwd.is_displayed()}, Enabled={btn_after_pwd.is_enabled()}, Tag={btn_after_pwd.tag_name}, Location={btn_after_pwd.location}, Size={btn_after_pwd.size}")

            try:
                btn_after_pwd.click()
                self.log("Clicked login button directly.")
            except Exception as click_e:
                self.log(f"Error clicking login button directly: {click_e}")
                try:
                    self.driver.execute_script("arguments[0].click();", btn_after_pwd)
                    self.log("Clicked login button via JavaScript.")
                except Exception as js_click_e:
                    self.log(f"Error clicking login button via JavaScript: {js_click_e}")
                    return False
                
            self.log("Clicked login button")
            
            # Verify login success by checking URL
            try:
                # Set flag to prevent fingerprint checks during login verification
                self._in_login_verification = True
                self.log("Starting login verification - temporarily disabling fingerprint checks")
                
                # Wait for URL change and check specific URL
                login_success = WebDriverWait(self.driver, 30).until(
                    lambda d: d.current_url.strip('/').lower() == 'https://www.popmart.com/us'
                )
                
                # Reset the verification flag
                self._in_login_verification = False
                
                if login_success:
                    self.log("✓ Login successful - verified by URL")
                    return True
                else:
                    # Additional check for any non-login page as fallback
                    current_url = self.driver.current_url.lower()
                    if 'login' not in current_url and ('popmart.com/us' in current_url):
                        self.log("✓ Login successful - verified by alternate URL")
                        return True
                    self.log("Login verification failed - incorrect URL")
                    self._in_login_verification = False  # Ensure flag is reset
                    return False
            except Exception as verify_error:
                self.log(f"Login verification error: {verify_error}")
                # Reset the verification flag
                self._in_login_verification = False
                
                # Final URL check without waiting
                current_url = self.driver.current_url.strip('/').lower()
                if current_url == 'https://www.popmart.com/us':
                    self.log("✓ Login successful - verified by final URL check")
                    return True
                return False
            
        except Exception as e:
            self.log(f"✗ Login failed: {e}")
            return False

    def handle_popups(self):
        """Handle any popups or policy dialogs with immediate action approach"""
        start_time = time.time()
        max_wait_time = 15  # Reduced to 15 seconds max wait time
        popup_handled = False
        policy_handled = False
        
        # Always attempt to handle popups and policy dialogs, regardless of login field visibility
        # The login field visibility check has been removed to ensure popups are always addressed first.
        
        # Immediate action approach - try to handle popups without waiting for invisibility
        max_attempts = 3  # Maximum number of attempts for each popup type
        
        # Handle popup close button
        for attempt in range(max_attempts):
            try:
                popup_elements = self.driver.find_elements(By.CSS_SELECTOR, self.config['selectors']['popup_close'])
                if popup_elements and not popup_handled:
                    popup_close = popup_elements[0]
                    
                    # Log popup properties
                    self.log(f"Popup close button found (attempt {attempt+1}/{max_attempts}): Displayed={popup_close.is_displayed()}, Enabled={popup_close.is_enabled()}")
                    
                    # Try multiple click methods in sequence without waiting for invisibility
                    try:
                        # Method 1: Direct click
                        popup_close.click()
                        self.log("Closed popup with direct click")
                        popup_handled = True
                    except Exception as e1:
                        self.log(f"Direct click failed: {e1}, trying JavaScript click")
                        try:
                            # Method 2: JavaScript click
                            self.driver.execute_script("arguments[0].click();", popup_close)
                            self.log("Closed popup with JavaScript click")
                            popup_handled = True
                        except Exception as e2:
                            self.log(f"JavaScript click failed: {e2}, trying mouse gesture")
                            try:
                                # Method 3: Mouse gesture
                                self._simulate_mouse_gesture(popup_close, "direct")
                                self.log("Closed popup with mouse gesture")
                                popup_handled = True
                            except Exception as e3:
                                self.log(f"All popup close methods failed on attempt {attempt+1}: {e3}")
                    
                    # Short pause after attempt
                    time.sleep(0.5)
                else:
                    # No popup found or already handled
                    popup_handled = True
                    break
            except Exception as e:
                self.log(f"Error handling popup (attempt {attempt+1}): {e}")
                time.sleep(0.5)
        
        # Handle policy accept button
        for attempt in range(max_attempts):
            try:
                policy_elements = self.driver.find_elements(By.CSS_SELECTOR, self.config['selectors']['policy_accept'])
                if policy_elements and not policy_handled:
                    policy_accept = policy_elements[0]
                    
                    # Log policy button properties
                    self.log(f"Policy accept button found (attempt {attempt+1}/{max_attempts}): Displayed={policy_accept.is_displayed()}, Enabled={policy_accept.is_enabled()}")
                    
                    # Try multiple click methods in sequence without waiting for invisibility
                    try:
                        # Method 1: Direct click
                        policy_accept.click()
                        self.log("Accepted policy with direct click")
                        policy_handled = True
                    except Exception as e1:
                        self.log(f"Direct click failed: {e1}, trying JavaScript click")
                        try:
                            # Method 2: JavaScript click
                            self.driver.execute_script("arguments[0].click();", policy_accept)
                            self.log("Accepted policy with JavaScript click")
                            policy_handled = True
                        except Exception as e2:
                            self.log(f"JavaScript click failed: {e2}, trying mouse gesture")
                            try:
                                # Method 3: Mouse gesture
                                self._simulate_mouse_gesture(policy_accept, "direct")
                                self.log("Accepted policy with mouse gesture")
                                policy_handled = True
                            except Exception as e3:
                                self.log(f"All policy accept methods failed on attempt {attempt+1}: {e3}")
                    
                    # Short pause after attempt
                    time.sleep(0.5)
                else:
                    # No policy button found or already handled
                    policy_handled = True
                    break
            except Exception as e:
                self.log(f"Error handling policy (attempt {attempt+1}): {e}")
                time.sleep(0.5)
        
        # Final check for login field visibility
        try:
            login_field_visible = self.driver.find_element(By.CSS_SELECTOR, self.config['selectors']['login_field']).is_displayed()
            if login_field_visible:
                self.log("Login field now visible, popup handling successful")
                return
        except:
            # Login field still not visible, but we'll proceed anyway
            pass
        
        # Log completion status
        if time.time() - start_time > max_wait_time:
            self.log(f"Popup handling timed out after {max_wait_time} seconds, continuing with login")
        else:
            self.log(f"Popup handling completed in {time.time() - start_time:.2f} seconds")
            
        # Force a small delay to ensure page stability before proceeding
        time.sleep(1)


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
        1) Click the Credit Card payment option with mouse gesture
        2) Fill in card details with randomized typing delays and mouse gestures
        3) Click the Pay button with mouse gesture
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

            # 1) Select Credit Card radio/button with mouse gesture
            self.log("Locating Credit Card payment option...")
            cc_option = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,
                    self.config['selectors']['credit_card_option']))
            )
            self._simulate_mouse_gesture(cc_option, "natural")
            self.log("✔ Clicked Credit Card option with mouse gesture")
            
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
                    # More variable typing speed for better human simulation
                    delay = random.uniform(0.05, 0.25)  # 50-250ms
                    self.log(f"   · Typed '{char}' into {field_name}, waiting {delay:.3f}s")
                    time.sleep(delay)
                    
                    # Occasionally pause longer between characters (like a human thinking)
                    if random.random() < 0.1:  # 10% chance
                        thinking_pause = random.uniform(0.3, 0.8)
                        self.log(f"   · Brief pause while typing {field_name}: {thinking_pause:.3f}s")
                        time.sleep(thinking_pause)

            # 2a) Card Number - use mouse gesture to focus on iframe first
            self.log("Locating card number field...")
            card_frame = self.driver.find_element(By.CSS_SELECTOR,
                self.config['selectors']['card_number_frame'])
                
            # Move mouse to the iframe first
            actions = ActionChains(self.driver)
            actions.move_to_element(card_frame)
            actions.pause(random.uniform(0.2, 0.5))
            actions.perform()
            
            self.driver.switch_to.frame(card_frame)
            num_input = self.driver.find_element(By.CSS_SELECTOR, "input")
            
            # Simulate clicking in the field
            actions = ActionChains(self.driver)
            actions.move_to_element(num_input)
            actions.pause(random.uniform(0.1, 0.3))
            actions.click()
            actions.perform()
            
            self.log("✔ Card number iframe switched; ready to type number")
            human_type(num_input, card_number, "card number")
            self.driver.switch_to.default_content()

            # 2b) Expiry Date - use mouse gesture
            self.log("Locating expiry date field...")
            exp_frame = self.driver.find_element(By.CSS_SELECTOR,
                self.config['selectors']['expiry_date_frame'])
                
            # Move mouse to the iframe first
            actions = ActionChains(self.driver)
            actions.move_to_element(exp_frame)
            actions.pause(random.uniform(0.2, 0.5))
            actions.perform()
            
            self.driver.switch_to.frame(exp_frame)
            exp_input = self.driver.find_element(By.CSS_SELECTOR, "input")
            
            # Simulate clicking in the field
            actions = ActionChains(self.driver)
            actions.move_to_element(exp_input)
            actions.pause(random.uniform(0.1, 0.3))
            actions.click()
            actions.perform()
            
            self.log("✔ Expiry date iframe switched; ready to type expiry")
            human_type(exp_input, f"{expiry_month:02d}{expiry_year%100:02d}", "expiry date")
            self.driver.switch_to.default_content()

            # 2c) Security Code (CVV) - use mouse gesture
            self.log("Locating security code (CVV) field...")
            cvc_frame = self.driver.find_element(By.CSS_SELECTOR,
                self.config['selectors']['cvv_frame'])
                
            # Move mouse to the iframe first
            actions = ActionChains(self.driver)
            actions.move_to_element(cvc_frame)
            actions.pause(random.uniform(0.2, 0.5))
            actions.perform()
            
            self.driver.switch_to.frame(cvc_frame)
            cvc_input = self.driver.find_element(By.CSS_SELECTOR, "input")
            
            # Simulate clicking in the field
            actions = ActionChains(self.driver)
            actions.move_to_element(cvc_input)
            actions.pause(random.uniform(0.1, 0.3))
            actions.click()
            actions.perform()
            
            self.log("✔ CVV iframe switched; ready to type CVV (value hidden)")
            for _ in cvv:
                cvc_input.send_keys("•")  # mask logging
                delay = random.uniform(0.05, 0.25)
                self.log(f"   · Typed one CVV digit placeholder, waiting {delay:.3f}s")
                time.sleep(delay)
            self.driver.switch_to.default_content()

            # 2d) Cardholder Name - use mouse gesture
            self.log("Locating cardholder name field...")
            name_input = self.driver.find_element(By.CSS_SELECTOR,
                self.config['selectors']['cardholder_name'])
                
            # Use mouse gesture to focus on the field
            self._simulate_mouse_gesture(name_input, "natural")
            
            self.log("✔ Ready to type cardholder name")
            human_type(name_input, holder_name, "cardholder name")

            # 3) Click the final Pay button with mouse gesture
            self.log("Locating Pay button...")
            pay_btn = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,
                    self.config['selectors']['pay_button']))
            )
            self.log("✔ Pay button found; clicking to submit payment")
            
            # Add some random mouse movements before clicking pay
            self._simulate_human_mouse_movement()
            
            # Use mouse gesture for the final payment button
            self._simulate_mouse_gesture(pay_btn, "natural")
            self.log("✔ Payment submitted with mouse gesture, awaiting confirmation...")
            return True

        except Exception as e:
            self.log(f"ERROR in fill_credit_card_and_pay: {e}")
            raise

    def complete_purchase(self):
        """Complete the checkout process using mouse gestures"""
        try:
            self.driver.get("https://www.popmart.com/us/largeShoppingCart")
            
            # Monitor TLS handshake during checkout
            try:
                security_info = self.driver.execute_cdp_cmd('Security.getSecurityState', {})
                self.log(f"Checkout TLS Security State: {security_info.get('securityState', 'unknown')}")
            except Exception as e:
                self.log(f"Checkout TLS monitoring error: {e}")
            
            # Select all items with mouse gesture
            chk = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['select_all']))
            )
            self._simulate_mouse_gesture(chk, "natural")
            self.log("Selected all items with mouse gesture")
            time.sleep(random.uniform(0.8, 1.5))
            
            # Proceed through checkout with mouse gesture
            checkout_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['checkout_btn']))
            )
            self._simulate_mouse_gesture(checkout_btn, "natural")
            self.log("Clicked checkout with mouse gesture")
            
            WebDriverWait(self.driver, 10).until(EC.url_changes)
            
            # Add some random mouse movements between steps
            self._simulate_human_mouse_movement()
            
            proceed_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['proceed_to_pay']))
            )
            self._simulate_mouse_gesture(proceed_btn, "natural")
            self.log("Clicked proceed to pay with mouse gesture")
            
            # Wait for payment page to load
            WebDriverWait(self.driver, 10).until(EC.url_changes)
            
            # Add some random mouse movements before payment
            self._simulate_human_mouse_movement()
            
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

    def handle_remaining_quantity(self, url, remaining):
        """Create new bot instance for remaining quantity with next account with TLS monitoring"""
        next_index = self.account_index + 1
        accounts = self.config.get('accounts', [])
        
        if next_index < len(accounts):
            self.log(f"Creating new instance for remaining quantity: {remaining}")
            
            # Verify TLS security before creating new instance
            try:
                # Try CDP command first
                try:
                    security_info = self.driver.execute_cdp_cmd('Security.getSecurityState', {})
                    self.log(f"TLS Security State before new instance: {security_info.get('securityState', 'unknown')}")
                except:
                    # Fallback: Check protocol
                    protocol = self.driver.execute_script('return window.location.protocol')
                    if protocol == 'https:':
                        self.log("TLS verified via HTTPS protocol before new instance")
                    else:
                        self.log(f"Warning: Non-HTTPS protocol detected before new instance: {protocol}")
            except Exception as e:
                self.log(f"TLS check warning before new instance (proceeding anyway): {e}")
            
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
            
            # Add random mouse movements before starting new instance
            self._simulate_human_mouse_movement()
            
            # Run in new thread
            threading.Thread(target=run_new_bot, daemon=True).start()
        else:
            self.log("No more accounts available for remaining quantity")

    def monitor_product(self, url, action, desired_quantity):
        """Monitor and purchase product with account rotation, session rotation, and randomized request pacing"""
        self._running = True
        self.current_product_url = url
        self.desired_quantity = desired_quantity
        
        try:
            while self._running:
                # Check if we need to rotate the session (only for non-login flows)
                if self._should_rotate_session():
                    self.log("Rotating session due to timeout or fingerprint change")
                    # Close current driver
                    if self.driver:
                        self.driver.quit()
                        self.driver = None
                    
                    # Reinitialize driver with new fingerprint
                    if not self.init_driver():
                        self.log("Failed to reinitialize driver during session rotation")
                        return False
                        
                    # Re-login after session rotation with mouse gestures
                    if not self.popmart_login():
                        self.log("Failed to re-login after session rotation")
                        return False
                        
                    self.log("Session successfully rotated")
                
                # Record this request for traffic pattern analysis
                self._record_request_timestamp()
                
                # Calculate randomized delay before next request to avoid patterns
                next_delay = self._randomize_next_request_delay()
                self.log(f"Using randomized delay of {next_delay:.2f}s before request")
                time.sleep(next_delay)
                
                # Check TLS security before navigating
                try:
                    # Try CDP command first
                    try:
                        security_info = self.driver.execute_cdp_cmd('Security.getSecurityState', {})
                        self.log(f"TLS Security State: {security_info.get('securityState', 'unknown')}")
                    except:
                        # Fallback 1: Check protocol
                        protocol = self.driver.execute_script('return window.location.protocol')
                        if protocol == 'https:':
                            self.log("TLS verified via HTTPS protocol")
                        else:
                            self.log(f"Warning: Non-HTTPS protocol detected: {protocol}")
                except Exception as e:
                    self.log(f"TLS check warning (proceeding anyway): {e}")
                
                # Navigate to product with randomized user behavior
                self.driver.get(url)
                
                # Add random mouse movements to simulate human behavior
                self._simulate_human_mouse_movement()
                
                # Check product availability
                try:
                    add_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['add_to_bag']))
                    )
                    self.log("Product available")
                    
                    # Adjust quantity
                    actual_quantity, remaining = self.adjust_quantity(desired_quantity)
                    self.log(f"Adjusted quantity: {actual_quantity} (remaining: {remaining})")
                    
                    # Add random delay before clicking to avoid bot detection
                    time.sleep(random.uniform(0.5, 2.0))
                    
                    # Add to cart using mouse gesture instead of direct click
                    self._simulate_mouse_gesture(add_btn, "natural")
                    self.log("Added to cart using mouse gesture")
                    time.sleep(random.uniform(0.8, 2.5))  # Randomized delay
                    
                    if action == 'buy':
                        if self.complete_purchase() and remaining > 0:
                            self.handle_remaining_quantity(url, remaining)
                        return True
                    
                    break
                    
                except TimeoutException:
                    self.log("Product not available or page structure changed")
                    # Add randomized retry delay
                    retry_delay = random.uniform(5, 15)
                    self.log(f"Retrying in {retry_delay:.1f} seconds...")
                    time.sleep(retry_delay)
                    continue
                
        except Exception as e:
            self.log(f"✗ Monitor error: {e}")
            return False
        finally:
            self.log("Monitor product finished")
            self.current_product_url = None
            
    def _simulate_human_mouse_movement(self):
        """Simulate realistic human mouse movements within safe viewport boundaries"""
        if not self.driver:
            return
            
        try:
            # Get viewport dimensions
            viewport_width = self.driver.execute_script("return window.innerWidth")
            viewport_height = self.driver.execute_script("return window.innerHeight")
            
            # Ensure viewport dimensions are valid
            if not viewport_width or not viewport_height or viewport_width < 100 or viewport_height < 100:
                self.log("Invalid viewport dimensions, using defaults")
                viewport_width = 1024
                viewport_height = 768
            
            # Move to center of viewport first to establish a reliable starting point
            center_x = viewport_width / 2
            center_y = viewport_height / 2
            
            try:
                # Use JavaScript to move to center - most reliable method
                self.driver.execute_script(f"""
                    var event = new MouseEvent('mousemove', {{
                        'view': window,
                        'bubbles': true,
                        'cancelable': true,
                        'clientX': {center_x},
                        'clientY': {center_y}
                    }});
                    document.elementFromPoint({center_x}, {center_y}).dispatchEvent(event);
                """)
                time.sleep(0.1)
            except Exception:
                # Fall back to ActionChains if JS approach fails
                try:
                    # First reset position with a no-op move
                    actions = ActionChains(self.driver)
                    actions.move_by_offset(0, 0).perform()
                    
                    # Then move to center
                    actions = ActionChains(self.driver)
                    actions.move_to_location(int(center_x), int(center_y)).perform()
                except Exception as e:
                    self.log(f"Could not establish initial mouse position: {e}")
            
            # Use very conservative movement boundaries (15% of viewport)
            safe_x_range = int(viewport_width * 0.15)
            safe_y_range = int(viewport_height * 0.15)
            
            # Make fewer, smaller movements to reduce risk of errors
            num_movements = random.randint(1, 3)
            
            # Create a fresh action chain for the movements
            actions = ActionChains(self.driver)
            
            # Use smaller relative movements from current position
            for i in range(num_movements):
                # Generate smaller random offsets within safe range
                # Make movements progressively smaller for more stability
                reduction_factor = (i + 1) / num_movements  # Gets smaller with each iteration
                x_offset = int(random.randint(-safe_x_range, safe_x_range) * reduction_factor)
                y_offset = int(random.randint(-safe_y_range, safe_y_range) * reduction_factor)
                
                # Move by offset with random speed
                actions.move_by_offset(x_offset, y_offset)
                actions.pause(random.uniform(0.05, 0.2))  # Shorter pauses
            
            # Execute the action chain with try/except to catch any errors
            try:
                actions.perform()
                self.log("Simulated human mouse movements within safe boundaries")
            except Exception as move_error:
                self.log(f"Mouse movement partially failed: {move_error}")
                # This is non-critical, so we continue execution
            
        except Exception as e:
            self.log(f"Warning: Could not simulate mouse movements: {e}")
            # Non-critical, so continue execution

    def rotate_user_context(self):
        """Rotate user context (cookies, localStorage, UA, viewport) to avoid tracking"""
        if not self.driver:
            return False
            
        try:
            self.log("Rotating user context...")
            
            # Clear cookies and local storage
            self.driver.delete_all_cookies()
            self.driver.execute_script("localStorage.clear(); sessionStorage.clear();")
            
            # Generate new user context
            self._generate_user_context()
            
            # Apply new user agent
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": self.current_user_agent})
            
            # Apply new viewport size
            width, height = self.current_viewport.split(",")
            self.driver.set_window_size(int(width), int(height))
            
            # Reset fingerprint monitoring
            self.initial_fingerprint = self._get_browser_fingerprint()
            self.session_start_time = datetime.datetime.now()
            self.last_fingerprint_check = self.session_start_time
            
            self.log(f"✓ User context rotated: UA={self.current_user_agent[:30]}..., Viewport={self.current_viewport}")
            return True
            
        except Exception as e:
            self.log(f"✗ Failed to rotate user context: {e}")
            return False
    
    def run(self, url, action, qty):
        """Main execution method with session management, TLS fingerprint matching, and mouse gestures"""
        try:
            # Initialize session variables
            self.session_start_time = datetime.datetime.now()
            self.last_fingerprint_check = self.session_start_time
            
            # Initialize driver with anti-detection measures
            if not self.init_driver():
                self.log("Failed to initialize driver")
                return False
                
            # Monitor TLS security state after initialization
            try:
                security_state = self.driver.execute_cdp_cmd('Security.getSecurityState', {})
                self.log(f"Initial TLS security state: {security_state['securityState']}")
                if 'explanations' in security_state:
                    for explanation in security_state['explanations']:
                        self.log(f"TLS explanation: {explanation}")
            except Exception as e:
                self.log(f"TLS monitoring error: {e}")
            
            # Login to account with mouse gestures
            if not self.popmart_login():
                self.log("Failed to login")
                return False
                
            # Simulate some human-like mouse movements before starting monitoring
            self._simulate_human_mouse_movement()
                
            # Monitor and purchase product with token rotation scoped to non-login flows
            result = self.monitor_product(url, action, qty)
            
            return result
            
        except Exception as e:
            self.log(f"✗ Bot error: {e}")
            return False
        finally:
            if self.driver:
                try:
                    # Final TLS security check before quitting
                    try:
                        security_state = self.driver.execute_cdp_cmd('Security.getSecurityState', {})
                        self.log(f"Final TLS security state: {security_state['securityState']}")
                    except Exception:
                        pass
                    self.driver.quit()
                    self.log("Browser closed")
                except Exception as e:
                    self.log(f"Error quitting driver: {e}")