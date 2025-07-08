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
from selenium.webdriver.common.keys import Keys
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
               
            # Force a normal device scale factor to prevent large UI elements
            options.add_argument('--force-device-scale-factor=1')
           
            # Initialize undetected Chrome with custom service
            service = Service(executable_path=os.path.join(os.getcwd(), 'chromedriver-win64', 'chromedriver.exe'))
           
            self.driver = uc.Chrome(
                options=options,
                service=service,
                headless=False,  # Set to True if you want headless
                use_subprocess=True,
                version_main="138.0.7204.100"
            )

            # Maximize browser window
            self.driver.maximize_window()

            # Set geolocation
            if self.current_coords:
                self.driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
                    "latitude": self.current_coords["lat"],
                    "longitude": self.current_coords["lng"],
                    "accuracy": 100 # A reasonable accuracy value
                })
                self.log(f"Attempting to set geolocation to Latitude: {self.current_coords['lat']}, Longitude: {self.current_coords['lng']}")
                self.log(f"Geolocation set successfully to {self.current_coords['city']} ({self.current_coords['lat']}, {self.current_coords['lng']})")
           
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
       
        # Set a specific viewport size to ensure proper display
        self.current_viewport = "1920x1080" # Use a standard desktop resolution
       
        # Timezone and corresponding coordinates mapping
        timezone_coords = {
            "America/New_York": {"lat": 40.7128, "lng": -74.0060, "city": "New York"},
            "America/Chicago": {"lat": 41.8781, "lng": -87.6298, "city": "Chicago"},
            "America/Denver": {"lat": 39.7392, "lng": -104.9903, "city": "Denver"},
            "America/Los_Angeles": {"lat": 34.0522, "lng": -118.2437, "city": "Los Angeles"},
            "Europe/London": {"lat": 51.5074, "lng": -0.1278, "city": "London"},
            "Europe/Paris": {"lat": 48.8566, "lng": 2.3522, "city": "Paris"},
            "Asia/Tokyo": {"lat": 35.6762, "lng": 139.6503, "city": "Tokyo"},
            "Australia/Sydney": {"lat": -33.8688, "lng": 151.2093, "city": "Sydney"}
        }
        
        # Select random timezone and coordinates
        self.current_timezone = random.choice(list(timezone_coords.keys()))
        self.current_coords = timezone_coords[self.current_timezone]
        self.log(f"Selected timezone: {self.current_timezone}")
       
        self.log(f"Session context: Viewport={self.current_viewport}, Timezone={self.current_timezone}, Coordinates={self.current_coords}")
   
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
       
        // Override language and timezone to match our settings
        const tzOffsets = {
            'America/New_York': -240,
            'America/Chicago': -300,
            'America/Denver': -360,
            'America/Los_Angeles': -420,
            'Europe/London': 60,
            'Europe/Paris': 120,
            'Asia/Tokyo': 540,
            'Australia/Sydney': 660
        };

        const locales = {
            'America/New_York': 'en-US',
            'America/Chicago': 'en-US',
            'America/Denver': 'en-US',
            'America/Los_Angeles': 'en-US',
            'Europe/London': 'en-GB',
            'Europe/Paris': 'fr-FR',
            'Asia/Tokyo': 'ja-JP',
            'Australia/Sydney': 'en-AU'
        };

        const currentTz = '" + self.current_timezone + "';
        const currentLocale = locales[currentTz] || 'en-US';
        const tzOffset = tzOffsets[currentTz] || 0;

        // Override language settings
        Object.defineProperty(navigator, 'language', {
            get: () => currentLocale
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => [currentLocale, 'en']
        });

        // Override timezone-related APIs
        const originalDate = Date;
        Date = class extends originalDate {
            getTimezoneOffset() {
                return tzOffset;
            }
        };

        // Override Intl.DateTimeFormat
        const originalDateTimeFormat = Intl.DateTimeFormat;
        Intl.DateTimeFormat = function(locales, options) {
            options = options || {};
            options.timeZone = currentTz;
            return new originalDateTimeFormat(currentLocale, options);
        };
        Intl.DateTimeFormat.prototype = originalDateTimeFormat.prototype;

        // Override performance.timeOrigin to match timezone
        const tzAdjustment = tzOffset * 60 * 1000;
        Object.defineProperty(performance, 'timeOrigin', {
            get: () => Date.now() - performance.now() + tzAdjustment
        });
       
        // Override Chrome-specific properties
        if (window.chrome) {
            window.chrome.runtime = {};
        }
        """
       
        try:
            self.driver.execute_script(evasions)
           
            # Add meta viewport tag to control page scaling
            viewport_script = """
            // Check if viewport meta tag exists
            let viewport = document.querySelector('meta[name="viewport"]');
            if (!viewport) {
                // Create and add viewport meta tag if it doesn't exist
                viewport = document.createElement('meta');
                viewport.name = 'viewport';
                document.head.appendChild(viewport);
            }
           
            """
           
            # Execute the script immediately
            self.driver.execute_script(viewport_script)
           
            # Set up a listener to apply viewport control on every page load
            page_load_script = """
            // Store the original function
            const originalPushState = history.pushState;
            const originalReplaceState = history.replaceState;
           
            // Function to apply viewport settings
           
           
            // Override pushState
            history.pushState = function() {
                originalPushState.apply(this, arguments);
                //applyViewportSettings();
            };
           
            // Override replaceState
            history.replaceState = function() {
                originalReplaceState.apply(this, arguments);
                //applyViewportSettings();
            };
           
            // Add event listener for page loads
            //window.addEventListener('load', applyViewportSettings);
            """
           
            # Set up the page load listener
            self.driver.execute_script(page_load_script)
           
            self.log("Applied browser fingerprint evasion techniques and viewport control")
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
                'languages': navigator.languages,
                'platform': navigator.platform,
                'hardwareConcurrency': navigator.hardwareConcurrency,
                'screenWidth': window.screen.width,
                'screenHeight': window.screen.height,
                'colorDepth': window.screen.colorDepth,
                'devicePixelRatio': window.devicePixelRatio,
                'timezone': Intl.DateTimeFormat().resolvedOptions().timeZone,
                'timezoneOffset': new Date().getTimezoneOffset(),
                'dateTimeFormat': new Intl.DateTimeFormat().format(new Date()),
                'timeOrigin': performance.timeOrigin
            };
            """
           
            fingerprint_data = self.driver.execute_script(fingerprint_script)
           
            # Create a hash of the fingerprint data
            fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
            fingerprint_hash = hashlib.md5(fingerprint_str.encode()).hexdigest()
            
            # Log detailed fingerprint information for verification
            self.log(f"Browser Fingerprint Details:")
            self.log(f"- Language: {fingerprint_data['language']}")
            self.log(f"- Languages: {fingerprint_data['languages']}")
            self.log(f"- Timezone: {fingerprint_data['timezone']}")
            self.log(f"- Timezone Offset: {fingerprint_data['timezoneOffset']} minutes")
            self.log(f"- Date Format Sample: {fingerprint_data['dateTimeFormat']}")
            self.log(f"- Fingerprint Hash: {fingerprint_hash[:8]}...")
            
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
        """Selectively clear PopMart-related browser storage while preserving other data to avoid detection"""
        try:
            self.log("Starting selective PopMart data clearing...")
            
            # Define PopMart domains to target
            popmart_domains = [
                "popmart.com/us", 
                "popmart.com/us/account", 
                "popmart.com/us/user/login"
            ]
            
            # 1. Selectively clear cookies for PopMart domains only
            self.log("Selectively clearing PopMart cookies...")
            all_cookies = self.driver.get_cookies()
            popmart_cookies = []
            other_cookies = []
            
            for cookie in all_cookies:
                is_popmart_cookie = False
                for domain in popmart_domains:
                    if domain in cookie.get('domain', '').lower():
                        is_popmart_cookie = True
                        popmart_cookies.append(cookie)
                        break
                if not is_popmart_cookie:
                    other_cookies.append(cookie)
            
            # Delete all cookies first
            self.driver.delete_all_cookies()
            
            # Restore non-PopMart cookies
            for cookie in other_cookies:
                try:
                    # Remove expiry if it's causing issues
                    if 'expiry' in cookie:
                        del cookie['expiry']
                    self.driver.add_cookie(cookie)
                except Exception as cookie_error:
                    self.log(f"Error restoring cookie: {cookie_error}")
            
            self.log(f"Cleared {len(popmart_cookies)} PopMart cookies, preserved {len(other_cookies)} other cookies")
            
            # 2. Install some dummy cookies to make the browser appear "not fresh"
            self.log("Adding dummy cookies...")
            dummy_cookies = [
                {'name': 'dummy_cookie_1', 'value': 'value_1', 'domain': '.example.com', 'path': '/'},
                {'name': 'dummy_cookie_2', 'value': 'value_2', 'domain': '.anothersite.org', 'path': '/'},
                {'name': 'session_id', 'value': 'random_session_id_123', 'domain': '.test.com', 'path': '/'}
            ]
            for cookie in dummy_cookies:
                try:
                    self.driver.add_cookie(cookie)
                    self.log(f"Added dummy cookie: {cookie['name']}")
                except Exception as e:
                    self.log(f"Error adding dummy cookie {cookie['name']}: {e}")

            # 3. Navigate to a specific page to further simulate browser activity
            target_url = "https://popmart.com/robots.txt"
            self.log(f"Navigating to {target_url}...")
            try:
                self.driver.get(target_url)
                time.sleep(random.uniform(1.0, 3.0)) # Simulate browsing time
                self.log(f"Successfully navigated to {target_url}.")
            except Exception as e:
                self.log(f"Error navigating to {target_url}: {e}")

            # 4. Selectively clear localStorage and sessionStorage for PopMart domains
            try:
                selective_storage_script = """
                const results = {};
                const popmartKeywords = ['popmart.com', 'popmart.com/us'];
                
                // Selectively clear localStorage
                if (window.localStorage) {
                    const allKeys = Object.keys(localStorage);
                    let popmartCount = 0;
                    
                    for (const key of allKeys) {
                        const isPopmartKey = popmartKeywords.some(keyword => 
                            key.toLowerCase().includes(keyword));
                        
                        if (isPopmartKey) {
                            localStorage.removeItem(key);
                            popmartCount++;
                        }
                    }
                    
                    results.localStorage = `Cleared ${popmartCount} PopMart items out of ${allKeys.length} total`;
                }
                
                // Selectively clear sessionStorage
                if (window.sessionStorage) {
                    const allKeys = Object.keys(sessionStorage);
                    let popmartCount = 0;
                    
                    for (const key of allKeys) {
                        const isPopmartKey = popmartKeywords.some(keyword => 
                            key.toLowerCase().includes(keyword));
                        
                        if (isPopmartKey) {
                            sessionStorage.removeItem(key);
                            popmartCount++;
                        }
                    }
                    
                    results.sessionStorage = `Cleared ${popmartCount} PopMart items out of ${allKeys.length} total`;
                }
                
                return results;
                """
                
                result = self.driver.execute_script(selective_storage_script)
                self.log(f"Selective storage clearing result: {result}")
            except Exception as script_error:
                self.log(f"Error clearing selective storage: {script_error}")
            
            # 4. Reset request timestamps to avoid pattern detection
            self.request_timestamps = []
            
            # 5. Use CDP commands to clear data only for PopMart origins
            self.log("Using CDP commands to clear PopMart site data...")
            try:
                # Clear data only for PopMart origins
                for domain in popmart_domains:
                    try:
                        self.driver.execute_cdp_cmd('Storage.clearDataForOrigin', {
                            "origin": f"*://*.{domain}.*",
                            "storageTypes": "all"
                        })
                    except Exception as e:
                        self.log(f"CDP clearing for {domain} failed: {e}")
                
                self.log("Cleared PopMart site data using CDP commands")
            except Exception as e:
                self.log(f"CDP site data clearing failed: {e}")
            
            self.log("✓ Completed selective PopMart data clearing while preserving browser history")
            return True
        except Exception as e:
            self.log(f"Failed to clear PopMart data: {e}")
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
            # Check Chrome version to determine available CDP commands
            chrome_version = None
            try:
                chrome_info = self.driver.capabilities.get('browserVersion') or ''
                chrome_version = int(chrome_info.split('.')[0]) if chrome_info else None
                self.log(f"Detected Chrome version: {chrome_info}")
            except Exception as version_error:
                self.log(f"Could not determine Chrome version: {version_error}")
           
            # For Chrome 138+, Security.getSecurityState is deprecated
            if chrome_version and chrome_version >= 138:
                # Use Network.enable only for newer Chrome versions
                try:
                    self.driver.execute_cdp_cmd('Network.enable', {})
                   
                    # Set up network conditions monitoring instead of security
                    # This helps detect network issues that might indicate security problems
                    self.driver.execute_cdp_cmd('Network.emulateNetworkConditions', {
                        'offline': False,
                        'latency': 0,
                        'downloadThroughput': -1,
                        'uploadThroughput': -1,
                        'connectionType': 'none'
                    })
                   
                    self.log("Enhanced network monitoring enabled via CDP for Chrome 138+")
                    # Skip Security.enable for Chrome 138+ as it's not supported
                except Exception as e:
                    self.log(f"Network CDP monitoring setup failed: {e}")
            else:
                # Try traditional CDP commands for older Chrome versions
                try:
                    self.driver.execute_cdp_cmd('Network.enable', {})
                    self.driver.execute_cdp_cmd('Security.enable', {})
                    self.log("TLS/SSL handshake monitoring enabled via CDP")
                    return True
                except Exception as e:
                    self.log(f"CDP monitoring setup failed, using fallback: {e}")
           
            # Enhanced fallback: Setup comprehensive security monitoring
            self.driver.execute_script("""
                (function() {
                    // Store security violations for later checking
                    window._securityViolations = [];
                    window._networkErrors = [];
                   
                    // Monitor security policy violations
                    window.addEventListener('securitypolicyviolation', function(e) {
                        console.error('Security policy violation:', e.violatedDirective);
                        window._securityViolations.push({
                            type: 'policy',
                            directive: e.violatedDirective,
                            blockedURI: e.blockedURI,
                            timestamp: new Date().getTime()
                        });
                        document.body.setAttribute('data-security-violation', 'true');
                    });
                   
                    // Enhanced monitoring for connection security
                    window.addEventListener('error', function(e) {
                        if (e && e.message && (
                            e.message.includes('security') ||
                            e.message.includes('SSL') ||
                            e.message.includes('TLS') ||
                            e.message.includes('certificate') ||
                            e.message.includes('HTTPS') ||
                            e.message.includes('mixed content')
                        )) {
                            console.error('Security-related error:', e.message);
                            window._securityViolations.push({
                                type: 'error',
                                message: e.message,
                                timestamp: new Date().getTime()
                            });
                            document.body.setAttribute('data-security-error', 'true');
                        }
                    });
                   
                    // Monitor network errors (especially for Chrome 138+)
                    const originalFetch = window.fetch;
                    window.fetch = function() {
                        return originalFetch.apply(this, arguments)
                            .catch(error => {
                                if (error && error.message && (
                                    error.message.includes('security') ||
                                    error.message.includes('SSL') ||
                                    error.message.includes('TLS') ||
                                    error.message.includes('certificate')
                                )) {
                                    console.error('Network security error:', error.message);
                                    window._networkErrors.push({
                                        type: 'fetch',
                                        message: error.message,
                                        timestamp: new Date().getTime()
                                    });
                                    document.body.setAttribute('data-network-security-error', 'true');
                                }
                                throw error;
                            });
                    };
                   
                    // Monitor XMLHttpRequest errors
                    const originalXHROpen = XMLHttpRequest.prototype.open;
                    XMLHttpRequest.prototype.open = function() {
                        this.addEventListener('error', function(e) {
                            console.error('XHR error:', e);
                            window._networkErrors.push({
                                type: 'xhr',
                                url: this._url,
                                timestamp: new Date().getTime()
                            });
                            document.body.setAttribute('data-xhr-error', 'true');
                        });
                       
                        const url = arguments[1];
                        this._url = url;
                        return originalXHROpen.apply(this, arguments);
                    };
                   
                    // Check if page is secure
                    if (window.location.protocol !== 'https:' &&
                        window.location.hostname !== 'localhost' &&
                        window.location.hostname !== '127.0.0.1') {
                        console.warn('Page not loaded over HTTPS');
                        document.body.setAttribute('data-non-https', 'true');
                    }
                   
                    // Add method to check security status
                    window.checkSecurityStatus = function() {
                        return {
                            violations: window._securityViolations,
                            networkErrors: window._networkErrors,
                            isSecure: window.location.protocol === 'https:' ||
                                     window.location.hostname === 'localhost' ||
                                     window.location.hostname === '127.0.0.1',
                            hasViolations: window._securityViolations.length > 0,
                            hasNetworkErrors: window._networkErrors.length > 0,
                            protocol: window.location.protocol,
                            // Add TLS version detection if available
                            tlsInfo: window.performance && window.performance.getEntriesByType ?
                                    window.performance.getEntriesByType('resource')
                                        .filter(r => r.nextHopProtocol)
                                        .map(r => ({
                                            url: r.name,
                                            protocol: r.nextHopProtocol
                                        })) : []
                        };
                    };
                   
                    // Setup periodic security check
                    setInterval(function() {
                        const status = window.checkSecurityStatus();
                        if (status.hasViolations || status.hasNetworkErrors) {
                            console.warn('Security issues detected:', status);
                        }
                    }, 9899);
                })();
            """)
            self.log("Enhanced security monitoring enabled via JavaScript")
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

    def popmart_login(self, retry_count=0):
        """Login using the account specified by account_index with enhanced anti-detection measures"""
        self.log("Starting login process with maximum protection")
       
        # Add random delay before login to avoid predictable patterns
        initial_delay = random.uniform(2.0, 5.0)
        self.log(f"Adding random initial delay of {initial_delay:.2f} seconds")
        time.sleep(initial_delay)
       
        # Clear browser data with enhanced thoroughness
        self.clear_browser_data()
       
        # Random user agent rotation if this is a retry
        if retry_count > 0:
            self.log(f"Retry attempt {retry_count} - rotating user agent")
            self._rotate_user_agent()
       
        # Navigate to login page with randomized timing
        self.driver.get("https://popmart.com/us/user/login/")
        self.log("Opened login page")
       
        # Add another random delay after page load to simulate human behavior
        post_navigation_delay = random.uniform(1.5, 3.5)
        self.log(f"Adding post-navigation delay of {post_navigation_delay:.2f} seconds")
        time.sleep(post_navigation_delay)
       
        try:
            # Get account credentials based on account_index
            accounts = self.config.get('accounts', [])
            if self.account_index >= len(accounts):
                self.log(f"✗ No account at index {self.account_index}")
                return False
               
            account = accounts[self.account_index]
            username = account['email']
            password = account['password']
           
            # Wait for page to be fully loaded with increased timeout
            WebDriverWait(self.driver, 40).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
           


           
            # Handle popups and policy dialogs first with increased thoroughness
            self.handle_popups()
           
            # Additional random wait after handling popups to ensure stability
            popup_wait = random.uniform(1.0, 2.5)
            self.log(f"Adding random post-popup delay of {popup_wait:.2f} seconds")
            time.sleep(popup_wait)
           
            # Randomize scroll position slightly to appear more human-like
            scroll_y = random.randint(-50, 50)  # Small random offset
            self.driver.execute_script(f"window.scrollTo(0, {scroll_y});")
            time.sleep(random.uniform(0.3, 0.8))  # Random scroll stabilization
           
            # Handle popups again with different timing
            self.log("Attempting to handle popups and policy dialogs before login field interaction")
            self.handle_popups()
           
            # Now look for the login field with increased timeout
            try:
                login_field = WebDriverWait(self.driver, 40).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.config['selectors']['login_field']))
                )
                # Verify field is actually visible and interactive
                if not login_field.is_displayed() or not login_field.is_enabled():
                    self.log("Login field found but not interactive, proceeding with login attempts")
            except Exception as e:
                self.log(f"Error locating login field: {e}")
                # Check for detection messages before giving up
                try:
                    page_source = self.driver.page_source.lower()
                    if any(term in page_source for term in ['high traffic', 'try again later', 'blocked', 'captcha']):
                        self.log("⚠️ Detected anti-bot measures on login page, but continuing with login process")
                except Exception:
                    pass
                return False # Cannot proceed without login field
           
            # Ensure element is in view with slight randomization
            scroll_behavior = random.choice(['smooth', 'auto'])
            self.driver.execute_script(f"arguments[0].scrollIntoView({{block: 'center', behavior: '{scroll_behavior}'}});", login_field)
            time.sleep(random.uniform(0.4, 0.9))  # Randomized scroll wait
           
            self.log(f"Login field properties: Displayed={login_field.is_displayed()}, Enabled={login_field.is_enabled()}, Tag={login_field.tag_name}, Location={login_field.location}, Size={login_field.size}")

            # Use more human-like interaction patterns
            time.sleep(random.uniform(0.5, 1.2))  # Randomized wait before interaction
           
            self.log(f"Login field properties: Displayed={login_field.is_displayed()}, Enabled={login_field.is_enabled()}, Tag={login_field.tag_name}, Location={login_field.location}, Size={login_field.size}")

            # Try mouse gesture first for more human-like interaction
            try:
                # Move mouse randomly near the field first
                actions = ActionChains(self.driver)
                # Get element position
                rect = self.driver.execute_script("""
                    var rect = arguments[0].getBoundingClientRect();
                    return {
                        left: rect.left,
                        top: rect.top,
                        width: rect.width,
                        height: rect.height
                    };
                """, login_field)
               
                # Move to a random position near the field first
                offset_x = random.randint(-20, 20)
                offset_y = random.randint(-20, 20)
                actions.move_by_offset(rect['left'] + rect['width']/2 + offset_x,
                                      rect['top'] + rect['height']/2 + offset_y)
                actions.pause(random.uniform(0.2, 0.5))
               
                # Then move to the actual field with natural motion
                actions.move_to_element(login_field)
                actions.pause(random.uniform(0.1, 0.3))
                actions.click()
                actions.perform()
                self.log("Clicked login field with mouse gesture")
               
                # Add random pause after click
                time.sleep(random.uniform(0.3, 0.7))
            except Exception as gesture_e:
                self.log(f"Mouse gesture failed: {gesture_e}, trying direct click")
                try:
                    login_field.click()
                    self.log("Clicked login field directly")
                except Exception as click_e:
                    self.log(f"Error clicking login field directly: {click_e}")
                    # Fallback to JavaScript click if direct click fails
                    try:
                        self.driver.execute_script("arguments[0].click();", login_field)
                        self.log("Clicked login field via JavaScript")
                    except Exception as js_click_e:
                        self.log(f"Error clicking login field via JavaScript: {js_click_e}")
                        # Check for detection before giving up

                        return False # Cannot proceed if click fails

            # Clear field with random approach
            try:
                # Sometimes use select-all + delete instead of clear()
                if random.choice([True, False]):
                    # Select all text with keyboard shortcut
                    login_field.send_keys(Keys.CONTROL + 'a')
                    time.sleep(random.uniform(0.1, 0.3))
                    login_field.send_keys(Keys.DELETE)
                    self.log("Cleared login field using select-all + delete")
                else:
                    login_field.clear()
                    self.log("Cleared login field using clear()")
            except Exception:
                # Fallback to standard clear
                login_field.clear()
                self.log("Cleared login field using fallback method")
           
            # Add pause after clearing
            time.sleep(random.uniform(0.3, 0.8))
           
            # Type username with variable human-like timing
            typing_speed = random.choice(['slow', 'normal', 'fast'])
            if typing_speed == 'slow':
                delay_range = (0.1, 0.3)
            elif typing_speed == 'normal':
                delay_range = (0.05, 0.2)
            else:  # fast
                delay_range = (0.01, 0.1)
               
            self.log(f"Using {typing_speed} typing speed")
           
            # Occasionally make and correct a typo for more human-like behavior
            should_make_typo = random.random() < 0.3  # 30% chance
           
            for i, char in enumerate(username):
                # Simulate typo and correction
                if should_make_typo and i == len(username) // 2:
                    # Type wrong character
                    wrong_char = chr(ord(char) + 1)  # Just use next character in ASCII
                    login_field.send_keys(wrong_char)
                    time.sleep(random.uniform(0.2, 0.5))  # Pause before noticing "mistake"
                    login_field.send_keys(Keys.BACKSPACE)  # Delete wrong character
                    time.sleep(random.uniform(0.1, 0.3))  # Pause before typing correct character
               
                # Type the correct character
                login_field.send_keys(char)
               
                # Variable delay between keystrokes
                time.sleep(random.uniform(*delay_range))
               
                # Occasionally pause while typing (like a human thinking)
                if random.random() < 0.05:  # 5% chance
                    time.sleep(random.uniform(0.5, 1.0))
           
            self.log("Entered username with realistic typing patterns")
           
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

            # Add a natural pause before interacting with password field
            time.sleep(random.uniform(0.8, 1.5))
           
            # Try mouse gesture first for more human-like interaction
            try:
                # Move mouse randomly near the field first
                actions = ActionChains(self.driver)
                # Get element position
                rect = self.driver.execute_script("""
                    var rect = arguments[0].getBoundingClientRect();
                    return {
                        left: rect.left,
                        top: rect.top,
                        width: rect.width,
                        height: rect.height
                    };
                """, pwd)
               
                # Move to a random position near the field first
                offset_x = random.randint(-20, 20)
                offset_y = random.randint(-20, 20)
                actions.move_by_offset(rect['left'] + rect['width']/2 + offset_x,
                                      rect['top'] + rect['height']/2 + offset_y)
                actions.pause(random.uniform(0.2, 0.5))
               
                # Then move to the actual field with natural motion
                actions.move_to_element(pwd)
                actions.pause(random.uniform(0.1, 0.3))
                actions.click()
                actions.perform()
                self.log("Clicked password field with mouse gesture")
               
                # Add random pause after click
                time.sleep(random.uniform(0.3, 0.7))
            except Exception as gesture_e:
                self.log(f"Mouse gesture failed: {gesture_e}, trying direct click")
                try:
                    pwd.click()
                    self.log("Clicked password field directly")
                except Exception as click_e:
                    self.log(f"Error clicking password field directly: {click_e}")
                    # Fallback to JavaScript click if direct click fails
                    try:
                        self.driver.execute_script("arguments[0].click();", pwd)
                        self.log("Clicked password field via JavaScript")
                    except Exception as js_click_e:
                        self.log(f"Error clicking password field via JavaScript: {js_click_e}")
                        # Check for detection but continue anyway
                        if "too popular" in self.driver.page_source.lower():
                            self.log("POP MART SERVERS ARE OVERLOADED NOW PLEASE TRY LATER")
                        return False # Cannot proceed if click fails

            # Clear field with random approach
            try:
                # Sometimes use select-all + delete instead of clear()
                if random.choice([True, False]):
                    # Select all text with keyboard shortcut
                    pwd.send_keys(Keys.CONTROL + 'a')
                    time.sleep(random.uniform(0.1, 0.3))
                    pwd.send_keys(Keys.DELETE)
                    self.log("Cleared password field using select-all + delete")
                else:
                    pwd.clear()
                    self.log("Cleared password field using clear()")
            except Exception:
                # Fallback to standard clear
                pwd.clear()
                self.log("Cleared password field using fallback method")
           
            # Add pause after clearing
            time.sleep(random.uniform(0.3, 0.8))
           
            # Type password with variable human-like timing
            # Password typing is usually more careful than username
            typing_speed = random.choice(['slow', 'normal'])
            if typing_speed == 'slow':
                delay_range = (0.1, 0.3)
            else:  # normal
                delay_range = (0.05, 0.2)
               
            self.log(f"Using {typing_speed} typing speed for password")
           
            # Type password with realistic patterns
            for i, char in enumerate(password):
                # Type the character
                pwd.send_keys(char)
               
                # Variable delay between keystrokes
                time.sleep(random.uniform(*delay_range))
               
                # Occasionally pause while typing (like a human thinking or checking)
                if random.random() < 0.08:  # 8% chance - slightly higher for passwords
                    time.sleep(random.uniform(0.5, 1.2))
           
            # Add a pause after typing password (like a human verifying before submitting)
            time.sleep(random.uniform(0.5, 1.0))
            self.log("Entered password with simulated typing")
           
            # Click final login button with mouse gesture or fallback
            btn_after_pwd = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['login_btn']))
            )
           
            # Ensure button is in view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_after_pwd)
            time.sleep(0.5)  # Allow time for scroll
           
            self.log(f"Login button properties: Displayed={btn_after_pwd.is_displayed()}, Enabled={btn_after_pwd.is_enabled()}, Tag={btn_after_pwd.tag_name}, Location={btn_after_pwd.location}, Size={btn_after_pwd.size}")

            # Add a natural pause before clicking the final login button
            time.sleep(random.uniform(1.0, 2.0))
           
            # Try mouse gesture first for more human-like interaction
            try:
                # Create a more complex mouse movement pattern for the final button
                # This simulates a human carefully clicking the submit button
                actions = ActionChains(self.driver)
               
                # Get button position
                rect = self.driver.execute_script("""
                    var rect = arguments[0].getBoundingClientRect();
                    return {
                        left: rect.left,
                        top: rect.top,
                        width: rect.width,
                        height: rect.height
                    };
                """, btn_after_pwd)
               
                # First move slightly away from current position
                actions.move_by_offset(random.uniform(-10, 10), random.uniform(-10, 10))
                actions.pause(random.uniform(0.1, 0.3))
               
                # Then approach the button with a natural curve
                center_x = rect['left'] + rect['width']/2
                center_y = rect['top'] + rect['height']/2
               
                # Create a curved approach with 3-4 points
                num_points = random.randint(3, 4)
                for i in range(num_points):
                    progress = (i + 1) / (num_points + 1)
                    # Add some randomness to the curve
                    curve_x = random.uniform(-15, 15) * (1 - progress)  # Less randomness as we get closer
                    curve_y = random.uniform(-15, 15) * (1 - progress)  # Less randomness as we get closer
                   
                    # Move to intermediate point
                    actions.move_by_offset(center_x * progress + curve_x,
                                          center_y * progress + curve_y)
                    actions.pause(random.uniform(0.05, 0.15))
               
                # Slow down as approaching the button
                actions.move_to_element(btn_after_pwd)
                actions.pause(random.uniform(0.2, 0.4))  # Longer pause before final click
               
                # Sometimes hover briefly before clicking
                if random.random() < 0.7:  # 70% chance
                    actions.pause(random.uniform(0.3, 0.8))
               
                actions.click()
                actions.perform()
                self.log("Clicked login button with natural mouse gesture")
               
            except Exception as gesture_e:
                self.log(f"Mouse gesture failed: {gesture_e}, trying direct click")
                try:
                    btn_after_pwd.click()
                    self.log("Clicked login button directly")
                except Exception as click_e:
                    self.log(f"Error clicking login button directly: {click_e}")
                    try:
                        self.driver.execute_script("arguments[0].click();", btn_after_pwd)
                        self.log("Clicked login button via JavaScript")
                    except Exception as js_click_e:
                        self.log(f"Error clicking login button via JavaScript: {js_click_e}")
                        # Continue without reinitializing browser
                        self.log("Proceeding with login verification despite click issues")
                        return False
               
            self.log("Clicked login button")
           
            # Wait a moment for any post-login processing
            time.sleep(random.uniform(1.0, 2.0))
           
            # Verify login success by checking URL and watching for detection messages
            try:
                # Set flag to prevent fingerprint checks during login verification
                self._in_login_verification = True
                self.log("Starting login verification - temporarily disabling fingerprint checks")
               
                # First check for detection messages before proceeding


                # Proceed with URL verification with persistent retries
                max_verification_attempts = 5
                verification_attempt = 0
                verification_timeout = 60  # Longer timeout for verification
                verification_start_time = time.time()
                
                while verification_attempt < max_verification_attempts:
                    verification_attempt += 1
                    self.log(f"Login verification attempt {verification_attempt}/{max_verification_attempts}")
                    
                    try:
                        # Check for success URL patterns
                        current_url = self.driver.current_url.lower()
                        
                        # Primary success pattern
                        if current_url.strip('/').lower() == 'https://www.popmart.com/us':
                            self.log(f"✓ Login successful - verified by primary URL (attempt {verification_attempt})")
                            self._in_login_verification = False
                            return True
                        
                        # Alternative success patterns
                        if 'login' not in current_url and ('popmart.com/us' in current_url):
                            self.log(f"✓ Login successful - verified by alternate URL (attempt {verification_attempt})")
                            self._in_login_verification = False
                            return True
                        
                        # If we're still on login page
                        if 'login' in current_url:
                            self.log(f"Still on login page (attempt {verification_attempt})")
                            
                            # If we've exceeded our timeout, break the loop
                            if time.time() - verification_start_time > verification_timeout:
                                self.log("Verification timeout exceeded")
                                break
                                
                            # Wait before next attempt
                            time.sleep(random.uniform(2.0, 4.0))
                            continue
                        
                        # If we're on an unknown page, log it but keep trying
                        self.log(f"On unknown page during verification: {current_url} (attempt {verification_attempt})")
                        time.sleep(random.uniform(2.0, 4.0))
                        
                    except Exception as verify_error:
                        self.log(f"Error during verification attempt {verification_attempt}: {verify_error}")
                        time.sleep(random.uniform(1.0, 2.0))
                
                # Reset the verification flag
                self._in_login_verification = False
                
                # Final check before giving up
                current_url = self.driver.current_url.lower()
                if current_url.strip('/').lower() == 'https://www.popmart.com/us' or \
                   ('login' not in current_url and 'popmart.com/us' in current_url):
                    self.log("✓ Login successful - verified in final check")
                    return True
                
                self.log("Login verification failed after multiple attempts - could not reach success URL")
                return False
            except Exception as verify_error:
                self.log(f"Login verification error: {verify_error}")
                # Reset the verification flag
                self._in_login_verification = False
               

                
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
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.index_countButton__mJU5Q"))
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
        1) Click the Credit Card option
        2) Wait for and type into each Adyen secured-field iframe dynamically
        3) Click Pay
        """
        try:
            # Load payment details
            account = self.config['accounts'][self.account_index]
            payment = account.get('payment') or {}
            if not payment:
                raise ValueError("No payment details configured")

            # Define fields: (label, value, mask_in_log) tuples
            nums = [
                ('Card Number', payment['card_number'], False),
                ('Expiry Date', f"{payment['expiry_month']:02d}{payment['expiry_year']%100:02d}", False),
                ('CVV', payment['cvv'], True),
                ('Cardholder Name', payment['holder_name'], False)
            ]

            # 1) Select Credit Card
            cc_sel = self.config['selectors']['credit_card_option']
            cc_option = WebDriverWait(self.driver, 9999).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, cc_sel))
            )
            self._simulate_mouse_gesture(cc_option, "natural")
            self.log("✔ Selected Credit Card option")

            # 2) Fill each secured field inside its iframe
            prefixes = {
                'Card Number': 'adyen-checkout-encryptedCardNumber-',
                'Expiry Date': 'adyen-checkout-encryptedExpiryDate-',
                'CVV': 'adyen-checkout-encryptedSecurityCode-',
                'Cardholder Name': 'adyen-checkout-holderName-'
            }

            for field_name, value, mask in nums:
                prefix = prefixes[field_name]
                self.log(f"Locating iframe for {field_name}...")

                # Switch into Adyen iframe by id prefix
                WebDriverWait(self.driver, 99999).until(
                    EC.frame_to_be_available_and_switch_to_it(
                        (By.CSS_SELECTOR, f"iframe[id^='{prefix}']")
                    )
                )

                # Locate the secure input inside iframe
                inp = WebDriverWait(self.driver, 9999).until(
                    EC.element_to_be_clickable((By.TAG_NAME, 'input'))
                )
                ActionChains(self.driver).move_to_element(inp).click().pause(0.1).perform()
                self.log(f"✔ {field_name} field focused; typing…")

                # Type actual characters, mask only in log
                for ch in str(value):
                    inp.send_keys(ch)
                    disp = '•' if mask else ch
                    delay = random.uniform(0.05, 0.25)
                    self.log(f"   · Typed '{disp}' into {field_name}, pause {delay:.2f}s")
                    time.sleep(delay)

                # Return to main document context
                self.driver.switch_to.default_content()

            # 3) Click Pay
            self.log("Locating Pay button…")
            pay_btn = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['pay_button']))
            )
            self._simulate_human_mouse_movement()
            self._simulate_mouse_gesture(pay_btn, "natural")
            self.log("✔ Pay clicked; awaiting confirmation…")

            return True

        except Exception as e:
            self.log(f"ERROR in fill_credit_card_and_pay: {e}")
            # Ensure we're back to the default context
            try:
                self.driver.switch_to.default_content()
            except:
                pass
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
           
            # Wait for 10 seconds before clicking the proceed to checkout button
            self.log("Waiting 10 seconds before clicking proceed to checkout button...")
            time.sleep(10)
           
            self._simulate_mouse_gesture(proceed_btn, "natural")
            self.log("Clicked proceed to pay with mouse gesture")
           
            # Wait for the specific checkout URL before proceeding
            checkout_url = "https://www.popmart.com/us/checkout?type=normal"
            start_time = time.time()
            url_found = False
           
            while time.time() - start_time < 20:  # Wait up to 20 seconds
                if checkout_url in self.driver.current_url:
                    self.log(f"Checkout URL found: {self.driver.current_url}")
                    url_found = True
                    break
                time.sleep(0.5)
           
            if not url_found:
                self.log(f"Checkout URL not found after waiting. Current URL: {self.driver.current_url}")
                self.log("Attempting to click proceed to checkout button again")
                try:
                    proceed_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, self.config['selectors']['proceed_to_pay']))
                    )
                    self._simulate_mouse_gesture(proceed_btn, "natural")
                    self.log("Clicked proceed to pay button again")
                   
                    # Wait again for the URL to appear
                    start_time = time.time()
                    while time.time() - start_time < 10:  # Wait up to 10 more seconds
                        if checkout_url in self.driver.current_url:
                            self.log(f"Checkout URL found after second attempt: {self.driver.current_url}")
                            url_found = True
                            break
                        time.sleep(0.5)
                       
                    if not url_found:
                        self.log(f"Checkout URL still not found. Current URL: {self.driver.current_url}")
                        return False
                except Exception as e:
                    self.log(f"Error clicking proceed button again: {e}")
                    return False
           
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
               
                # Check product availability with initial delay
                time.sleep(2)  # Initial delay to let the page fully load and stabilize
                
                try:
                    # First check if the button exists
                    add_btn = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, self.config['selectors']['add_to_bag']))
                    )
                    
                    # Check button text
                    button_text = add_btn.text.strip()
                    self.log(f"Found button with text: {button_text}")
                    
                    if button_text == "NOTIFY ME WHEN AVAILABLE":
                        self.log("Product out of stock, refreshing page...")
                        time.sleep(random.uniform(20, 30))  # Random delay between 20-30 seconds
                        continue  # This will go back to the start of the while loop and refresh the page
                    
                    # Wait for button to be clickable
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
                    
                    # Add longer delay to ensure item is properly added to cart
                    wait_time = random.uniform(5, 8)
                    self.log(f"Waiting {wait_time:.1f} seconds for cart to update...")
                    time.sleep(wait_time)
                   
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
                self.log("Invalid viewport dimensions, using defaults based on configured viewport")
                viewport_width = 1920
                viewport_height = 1080
           
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
        """Rotate user context (cookies, localStorage, UA) to avoid tracking"""
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
           
            # Using fixed viewport size of 1920x1080
            self.current_viewport = "1920x1080"
           
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
            login_successful = False
            retry_count = 0
            while not login_successful:
                try:
                    if self.popmart_login(retry_count=retry_count):
                        self.log("Login successful!")
                        login_successful = True
                    else:
                        self.log(f"Login failed on attempt {retry_count + 1}. Retrying...")
                        retry_count += 1
                        time.sleep(random.uniform(10, 30)) # Wait before retrying
                except Exception as e:
                    self.log(f"An error occurred during login attempt {retry_count + 1}: {e}. Retrying...")
                    retry_count += 1
                    time.sleep(random.uniform(10, 30)) # Wait before retrying

            if not login_successful:
                self.log("Failed to login after multiple attempts.")
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