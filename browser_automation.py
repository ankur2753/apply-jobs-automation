# browser_automation.py - Module for browser automation
import time
import os
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class BrowserSetup:
    """
    Centralized browser setup class that handles all Chrome/Chromium driver initialization.
    This ensures consistent browser setup across all modules.
    """
    
    @staticmethod
    def create_driver(headless: bool = True) -> webdriver.Chrome:
        """
        Creates and returns a Chrome WebDriver instance with optimal settings.
        
        Args:
            headless (bool): Whether to run browser in headless mode (default: True)
            
        Returns:
            webdriver.Chrome: Configured Chrome WebDriver instance
            
        Raises:
            Exception: If driver initialization fails
        """
        from selenium.webdriver.chrome.options import Options
        
        chrome_options = Options()
        chrome_options.binary_location = "/usr/bin/chromium-browser"  # Use system chromium
        
        # Essential Chrome arguments
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-features=VizServiceDisplayCompositor")
        
        # Headless mode control
        if headless:
            chrome_options.add_argument("--headless")
        
        # Additional stability arguments for faster scraping
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Faster loading
        # Keep JavaScript enabled as many job sites require it
        
        try:
            # First try system chromedriver (version 139 - matches browser exactly)
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e:
            print(f"System chromedriver failed ({e}), trying webdriver-manager...")
            try:
                # Fallback to webdriver manager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                return driver
            except Exception as e2:
                raise Exception(f"Both chromedriver methods failed. System: {e}, WebDriver-Manager: {e2}")
    
    @staticmethod
    def create_interactive_driver() -> webdriver.Chrome:
        """
        Creates a Chrome driver for interactive use (form filling, user interaction).
        This version does not run in headless mode and enables JavaScript.
        
        Returns:
            webdriver.Chrome: Chrome WebDriver configured for interaction
        """
        from selenium.webdriver.chrome.options import Options
        
        chrome_options = Options()
        chrome_options.binary_location = "/usr/bin/chromium-browser"
        
        # Interactive mode settings
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-features=VizServiceDisplayCompositor")
        
        # No headless mode for user interaction
        # Keep JavaScript enabled for form interactions
        
        try:
            # Use system chromedriver first
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e:
            print(f"System chromedriver failed ({e}), trying webdriver-manager...")
            try:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                return driver
            except Exception as e2:
                raise Exception(f"Both chromedriver methods failed. System: {e}, WebDriver-Manager: {e2}")


class BrowserAutomation:
    """
    A class to automate browser interactions for filling out job application forms.
    It uses intelligent page analysis to find elements dynamically.
    """
    def __init__(self):
        """Initializes the BrowserAutomation with a None driver."""
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """
        Sets up the Selenium WebDriver instance for form filling.
        Uses the centralized BrowserSetup for consistent configuration.
        """
        if not self.driver:
            self.driver = BrowserSetup.create_interactive_driver()
            self.wait = WebDriverWait(self.driver, 10)
            
    def analyze_page_content(self) -> Dict:
        """
        Analyzes the current page to identify clickable elements and form fields.
        Returns a comprehensive analysis of the page structure.
        """
        analysis = {
            'apply_buttons': [],
            'form_fields': [],
            'file_uploads': [],
            'submit_buttons': [],
            'interactive_elements': []
        }
        
        try:
            # Find all clickable elements that might be apply buttons
            clickable_elements = self.driver.find_elements(By.CSS_SELECTOR, 'button, a, input[type="button"], input[type="submit"]')
            
            for element in clickable_elements:
                try:
                    text = (element.text or element.get_attribute('value') or '').lower().strip()
                    title = (element.get_attribute('title') or '').lower()
                    class_name = (element.get_attribute('class') or '').lower()
                    id_attr = (element.get_attribute('id') or '').lower()
                    
                    # Check if it's likely an apply button
                    apply_keywords = ['apply', 'submit application', 'apply now', 'quick apply']
                    if any(keyword in text or keyword in title or keyword in class_name or keyword in id_attr 
                           for keyword in apply_keywords):
                        analysis['apply_buttons'].append({
                            'element': element,
                            'text': text,
                            'tag': element.tag_name,
                            'confidence': self._calculate_apply_confidence(text, class_name, id_attr)
                        })
                    
                    # Check if it's likely a submit button
                    submit_keywords = ['submit', 'send', 'continue', 'next', 'proceed']
                    if any(keyword in text or keyword in title or keyword in class_name or keyword in id_attr
                           for keyword in submit_keywords):
                        analysis['submit_buttons'].append({
                            'element': element,
                            'text': text,
                            'tag': element.tag_name,
                            'confidence': self._calculate_submit_confidence(text, class_name, id_attr)
                        })
                        
                except Exception as e:
                    continue  # Skip problematic elements
            
            # Find all form input fields
            input_elements = self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            
            for element in input_elements:
                try:
                    input_type = (element.get_attribute('type') or 'text').lower()
                    name = (element.get_attribute('name') or '').lower()
                    id_attr = (element.get_attribute('id') or '').lower()
                    placeholder = (element.get_attribute('placeholder') or '').lower()
                    
                    if input_type == 'file':
                        analysis['file_uploads'].append({
                            'element': element,
                            'name': name,
                            'id': id_attr,
                            'field_type': self._identify_file_field_type(name, id_attr, placeholder)
                        })
                    else:
                        field_type = self._identify_form_field_type(name, id_attr, placeholder, input_type)
                        if field_type != 'unknown':
                            analysis['form_fields'].append({
                                'element': element,
                                'name': name,
                                'id': id_attr,
                                'type': input_type,
                                'field_type': field_type,
                                'placeholder': placeholder
                            })
                            
                except Exception as e:
                    continue  # Skip problematic elements
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing page content: {e}")
            return analysis
    
    # ---- Heuristics helpers ----
    def _calculate_apply_confidence(self, text: str, class_name: str, id_attr: str) -> float:
        score = 0.0
        for kw in ['apply', 'apply now', 'quick apply', 'submit application']:
            if kw in text:
                score += 0.6
        for kw in ['apply', 'apply-btn', 'cta']:
            if kw in class_name or kw in id_attr:
                score += 0.3
        return min(score, 1.0)
    
    def _calculate_submit_confidence(self, text: str, class_name: str, id_attr: str) -> float:
        score = 0.0
        for kw in ['submit', 'send', 'continue', 'next']:
            if kw in text:
                score += 0.5
        for kw in ['submit', 'primary', 'btn']:
            if kw in class_name or kw in id_attr:
                score += 0.3
        return min(score, 1.0)
    
    def _identify_form_field_type(self, name: str, id_attr: str, placeholder: str, input_type: str) -> str:
        blob = f"{name} {id_attr} {placeholder}".lower()
        if any(k in blob for k in ['email']):
            return 'email'
        if any(k in blob for k in ['phone', 'mobile', 'contact']):
            return 'phone'
        if any(k in blob for k in ['name', 'full-name', 'fullname', 'first-name']):
            return 'name'
        if any(k in blob for k in ['linkedin', 'linkedin url']):
            return 'linkedin'
        if input_type in ['textarea']:
            return 'cover_letter'
        return 'unknown'
    
    def _identify_file_field_type(self, name: str, id_attr: str, placeholder: str) -> str:
        blob = f"{name} {id_attr} {placeholder}".lower()
        if any(k in blob for k in ['resume', 'cv']):
            return 'resume'
        if any(k in blob for k in ['cover', 'letter']):
            return 'cover_letter'
        return 'file'
    
    def fill_application(self, job_url: str, job_details: Dict, personal_details: Dict, resume_path: str) -> bool:
        """
        Navigates to the job URL, finds the apply button, and fills the application form.
        
        Args:
            job_url (str): The URL of the job application.
            job_details (Dict): The scraped job details.
            personal_details (Dict): The user's personal information.
            resume_path (str): The local path to the customized resume file.
            
        Returns:
            bool: True if the application was successfully filled and submitted, False otherwise.
        """
        try:
            self.setup_driver()
            self.driver.get(job_url)
            time.sleep(3) # Wait for initial page load
            
            # Dismiss any cookie banners or overlays
            self._dismiss_overlays()
            
            # Look for "Apply" button
            apply_button = self.find_apply_button()
            if apply_button:
                # Try to scroll to button and dismiss overlays again
                self.driver.execute_script("arguments[0].scrollIntoView(true);", apply_button)
                time.sleep(1)
                self._dismiss_overlays()
                
                # Try clicking with JavaScript if normal click fails
                try:
                    apply_button.click()
                except Exception as e:
                    if "click intercepted" in str(e):
                        print("Normal click intercepted, trying JavaScript click...")
                        self.driver.execute_script("arguments[0].click();", apply_button)
                    else:
                        raise e
                        
                time.sleep(2) # Wait for form to load
                
                # Fill form fields
                success = self.fill_form_fields(personal_details, resume_path)
                
                if success:
                    # Submit application with user confirmation
                    return self.submit_application()
                
            return False
            
        except Exception as e:
            print(f"Error in browser automation: {e}")
            return False
    
    def find_apply_button(self):
        """Finds and returns the most likely 'Apply' button on the page using robust strategies."""
        # Strategy 1: Search for common ids/classes
        css_candidates = [
            'button[data-testid="apply-button"]',
            'a[data-testid="apply-button"]',
            '.apply', '.apply-btn', '.apply-button', '#apply', '#apply-btn',
            '[aria-label*="apply" i]'
        ]
        for selector in css_candidates:
            try:
                element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                if element:
                    return element
            except Exception:
                continue
        
        # Strategy 2: XPath text-based search (case-insensitive)
        xpaths = [
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
            "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
            "//input[@type='button' or @type='submit'][contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
        ]
        for xp in xpaths:
            try:
                elements = self.driver.find_elements(By.XPATH, xp)
                for el in elements:
                    try:
                        if el.is_displayed() and el.is_enabled():
                            return el
                    except Exception:
                        continue
            except Exception:
                continue
        
        # Strategy 3: Analyze page content and pick highest confidence
        analysis = self.analyze_page_content()
        if analysis['apply_buttons']:
            # Pick the highest confidence button
            best = sorted(analysis['apply_buttons'], key=lambda x: x.get('confidence', 0), reverse=True)[0]
            return best['element']
        
        # Strategy 4: Try iframes (switch into them and search)
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
            for idx, frame in enumerate(iframes):
                self.driver.switch_to.frame(frame)
                try:
                    el = self.find_apply_button()
                    if el:
                        return el
                finally:
                    self.driver.switch_to.default_content()
        except Exception:
            pass
        
        return None
    
    def fill_form_fields(self, personal_details: Dict, resume_path: str) -> bool:
        """
        Intelligently fills out application form fields using page analysis.
        Also handles the resume upload.
        """
        try:
            print(f"\n{'='*50}")
            print("Analyzing page and filling form fields...")
            print(f"{'='*50}")
            
            # Analyze the page to find form fields
            analysis = self.analyze_page_content()
            
            filled_fields = 0
            
            # Fill identified form fields based on analysis
            for field in analysis['form_fields']:
                field_type = field['field_type']
                element = field['element']
                
                value = None
                if field_type == 'email':
                    value = personal_details.get('email', '')
                elif field_type == 'phone':
                    value = personal_details.get('phone', '')
                elif field_type == 'name':
                    value = personal_details.get('name', '')
                elif field_type == 'linkedin':
                    value = personal_details.get('linkedin', '')
                
                if value:
                    try:
                        # Scroll element into view and wait for it to be clickable
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        time.sleep(0.5)
                        
                        element.clear()
                        element.send_keys(value)
                        filled_fields += 1
                        print(f"  ✅ Filled {field_type} field: '{field.get('name', field.get('id', 'unnamed'))}'")
                    except Exception as e:
                        print(f"  ❌ Failed to fill {field_type} field: {e}")
            
            # Handle file uploads (resume)
            uploaded_files = 0
            for upload in analysis['file_uploads']:
                if upload['field_type'] == 'resume' and os.path.exists(resume_path):
                    try:
                        element = upload['element']
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        time.sleep(0.5)
                        
                        element.send_keys(os.path.abspath(resume_path))
                        uploaded_files += 1
                        print(f"  ✅ Uploaded resume to: '{upload.get('name', upload.get('id', 'unnamed'))}'")
                        time.sleep(2)  # Wait for file upload to process
                    except Exception as e:
                        print(f"  ❌ Failed to upload resume: {e}")
            
            # Fallback to traditional method if no fields found via analysis
            if filled_fields == 0:
                print("  No fields identified via analysis, trying traditional mapping...")
                field_mappings = {
                    'name': ['name', 'full-name', 'fullName', 'first-name', 'firstName'],
                    'email': ['email', 'email-address', 'emailAddress', 'Email'],
                    'phone': ['phone', 'phone-number', 'phoneNumber', 'mobile', 'Phone'],
                    'linkedin': ['linkedin', 'linkedin-url', 'linkedinUrl']
                }
                
                for detail_key, selectors in field_mappings.items():
                    value = personal_details.get(detail_key, '')
                    if value:
                        for selector in selectors:
                            if self.fill_field_by_name_or_id(selector, value):
                                filled_fields += 1
                                print(f"  ✅ Filled {detail_key} field (traditional): '{selector}'")
                                break
            
            # Fallback file upload if not found via analysis
            if uploaded_files == 0:
                resume_upload = self.find_resume_upload()
                if resume_upload and os.path.exists(resume_path):
                    try:
                        resume_upload.send_keys(os.path.abspath(resume_path))
                        uploaded_files += 1
                        print(f"  ✅ Uploaded resume (traditional method)")
                        time.sleep(2)
                    except Exception as e:
                        print(f"  ❌ Failed to upload resume (traditional): {e}")
            
            print(f"\nForm filling summary:")
            print(f"  Fields filled: {filled_fields}")
            print(f"  Files uploaded: {uploaded_files}")
            
            # Consider it successful if we filled any fields or uploaded files
            return filled_fields > 0 or uploaded_files > 0
            
        except Exception as e:
            print(f"Error filling form fields: {e}")
            return False
    
    def fill_field_by_name_or_id(self, field_name: str, value: str) -> bool:
        """Fills a form field by its name or ID attribute."""
        selectors = [
            f'input[name="{field_name}"]',
            f'input[id="{field_name}"]',
            f'input[data-testid="{field_name}"]',
            f'textarea[name="{field_name}"]',
            f'textarea[id="{field_name}"]'
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                element.clear()
                element.send_keys(value)
                return True
            except NoSuchElementException:
                continue
        return False
    
    def _confirm_and_click(self, element) -> bool:
        """Ask user to confirm and click the given element."""
        print(f"\n{'='*50}")
        print("Ready to submit application!")
        print("Please review the form and press Enter to submit, or 'n' to skip:")
        print(f"{'='*50}")
        user_input = input().strip().lower()
        if user_input != 'n':
            element.click()
            time.sleep(3)
            return True
        else:
            print("Application submission skipped by user.")
            return False
    
    def find_resume_upload(self):
        """Finds and returns the file input element for resume upload."""
        upload_selectors = [
            'input[type="file"]',
            'input[accept*=".pdf"]',
            'input[name*="resume"]',
            'input[id*="resume"]',
            'input[name*="cv"]'
        ]
        
        for selector in upload_selectors:
            try:
                return self.driver.find_element(By.CSS_SELECTOR, selector)
            except NoSuchElementException:
                continue
        return None
    
    def submit_application(self) -> bool:
        """
        Finds the submit button and prompts the user for confirmation before clicking it.
        This is a safety measure to avoid accidental submissions.
        """
        # Strategy 1: CSS selectors
        css_candidates = [
            'button[type="submit"]', 'input[type="submit"]', '.submit', '.submit-btn', '#submit', '#submit-application',
            '[aria-label*="submit" i]'
        ]
        for selector in css_candidates:
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                if btn.is_displayed() and btn.is_enabled():
                    return self._confirm_and_click(btn)
            except Exception:
                continue
        
        # Strategy 2: XPath by text
        xpaths = [
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
            "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
            "//input[@type='button' or @type='submit'][contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
        ]
        for xp in xpaths:
            try:
                elements = self.driver.find_elements(By.XPATH, xp)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        return self._confirm_and_click(el)
            except Exception:
                continue
        
        # Strategy 3: From analysis highest confidence
        analysis = self.analyze_page_content()
        if analysis['submit_buttons']:
            best = sorted(analysis['submit_buttons'], key=lambda x: x.get('confidence', 0), reverse=True)[0]
            return self._confirm_and_click(best['element'])
        
        print("Could not find submit button!")
        return False
    
    def _dismiss_overlays(self):
        """Attempts to dismiss common overlays like cookie banners and popups."""
        overlay_dismissal_selectors = [
            # Cookie banners
            '#onetrust-accept-btn-handler',
            '.onetrust-close-btn-handler', 
            '#accept-cookies',
            '.accept-cookies',
            '[data-testid="accept-cookies"]',
            'button[aria-label*="accept" i]',
            'button[aria-label*="agree" i]',
            
            # Generic close buttons
            '.close',
            '.close-btn',
            '.modal-close',
            '[aria-label="close" i]',
            '[data-dismiss="modal"]',
            
            # Specific overlays
            '.dismiss',
            '.banner-close',
            '.notification-close'
        ]
        
        for selector in overlay_dismissal_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed() and element.is_enabled():
                    element.click()
                    time.sleep(0.5)
                    print(f"  Dismissed overlay using selector: {selector}")
                    return  # Only dismiss one overlay at a time
            except:
                continue
        
        # Try to press Escape key to dismiss modals
        try:
            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.5)
        except:
            pass
