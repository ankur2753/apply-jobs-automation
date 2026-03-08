# naukri_scraper.py - Module for scraping job details from Naukri.com
import time
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote_plus

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from browser_automation import BrowserSetup


class NaukriScraper:
    """
    A scraper tailored for Naukri.com job listings.

    Handles Naukri login, keyword/location-based job search, and extraction of
    job details (title, company, location, experience, salary, skills,
    description) using Naukri-specific selectors with multi-strategy fallbacks.
    """

    BASE_URL = "https://www.naukri.com"
    LOGIN_URL = "https://www.naukri.com/nlogin/login"

    def __init__(self):
        """Initializes the NaukriScraper with a None driver and logged-out state."""
        self.driver = None
        self.wait = None
        self.logged_in = False

    def setup_driver(self):
        """
        Sets up the Selenium WebDriver for Naukri interaction.
        Uses a visible (non-headless) browser because Naukri may require
        captcha or OTP verification during login.
        """
        if not self.driver:
            self.driver = BrowserSetup.create_interactive_driver()
            self.wait = WebDriverWait(self.driver, 15)

    def login(self, email: str, password: str) -> bool:
        """
        Logs in to Naukri.com with the provided credentials.

        Navigates to the Naukri login page, fills email and password fields,
        and clicks the login button.  After submission it waits for the URL to
        change away from the login page, which signals a successful login.
        If OTP verification is triggered, the method pauses and asks the user
        to complete it manually.

        Args:
            email (str): Naukri account email / username.
            password (str): Naukri account password.

        Returns:
            bool: True if login succeeded, False otherwise.
        """
        try:
            self.setup_driver()
            logging.info("Navigating to Naukri login page...")
            self.driver.get(self.LOGIN_URL)
            time.sleep(3)

            # --- Fill email ---
            email_selectors = [
                'input[placeholder*="Enter your active Email"]',
                'input[placeholder*="Email"]',
                'input[type="text"][id*="usernameField"]',
                'input[name="username"]',
                '#usernameField',
            ]
            email_field = self._find_first_element(email_selectors)
            if not email_field:
                logging.error("Could not find email field on Naukri login page")
                return False
            email_field.clear()
            email_field.send_keys(email)

            # --- Fill password ---
            password_selectors = [
                'input[placeholder*="Enter your password"]',
                'input[placeholder*="Password"]',
                'input[type="password"]',
                '#passwordField',
            ]
            password_field = self._find_first_element(password_selectors)
            if not password_field:
                logging.error("Could not find password field on Naukri login page")
                return False
            password_field.clear()
            password_field.send_keys(password)

            # --- Click login button ---
            login_btn_selectors = [
                'button[type="submit"]',
                'button[class*="loginButton"]',
                '//button[contains(text(), "Login")]',
            ]
            login_button = self._find_first_element(login_btn_selectors)
            if login_button:
                login_button.click()
            else:
                logging.error("Could not find login button")
                return False

            time.sleep(5)

            # --- Handle possible OTP / captcha ---
            if 'nlogin' in self.driver.current_url.lower():
                print("\n" + "=" * 50)
                print("ACTION REQUIRED: OTP or captcha verification detected.")
                print("Please complete the verification in the browser window.")
                print("Press Enter here once you have logged in successfully...")
                print("=" * 50)
                input()

            # Validate login
            if 'nlogin' not in self.driver.current_url.lower():
                self.logged_in = True
                logging.info("Successfully logged in to Naukri.com")
                return True

            logging.error("Login to Naukri.com failed")
            return False

        except Exception as e:
            logging.error(f"Error during Naukri login: {e}")
            return False

    # ------------------------------------------------------------------
    # Job search
    # ------------------------------------------------------------------

    def search_jobs(self, keywords: str, location: str = "",
                    experience: str = "", sort_by: str = "relevance",
                    max_pages: int = 3) -> List[Dict]:
        """
        Searches for jobs on Naukri.com and returns a list of result dicts.

        Constructs a Naukri search URL from the provided parameters, iterates
        through result pages up to *max_pages*, and extracts summary info
        (title, company, URL, etc.) from each job card on the page.

        Args:
            keywords (str):   Search keywords, e.g. "python developer".
            location (str):   Desired location, e.g. "Bangalore".
            experience (str): Experience in years, e.g. "3".
            sort_by (str):    Sort order — "relevance" or "date".
            max_pages (int):  Maximum number of result pages to scrape.

        Returns:
            List[Dict]: A list of dicts, each with keys
                        ``title``, ``company``, ``url``, ``location``,
                        ``experience``, ``salary``, ``skills_preview``.
        """
        self.setup_driver()
        jobs: List[Dict] = []

        for page in range(1, max_pages + 1):
            search_url = self._build_search_url(keywords, location, experience, sort_by, page)
            logging.info(f"Searching Naukri page {page}: {search_url}")
            self.driver.get(search_url)
            time.sleep(3)

            page_jobs = self._parse_search_results()
            if not page_jobs:
                logging.info(f"No more results on page {page}, stopping search.")
                break

            jobs.extend(page_jobs)
            logging.info(f"Page {page}: found {len(page_jobs)} jobs (total: {len(jobs)})")

        return jobs

    def _build_search_url(self, keywords: str, location: str,
                          experience: str, sort_by: str, page: int) -> str:
        """
        Constructs a Naukri search URL from query parameters.

        Naukri encodes keywords with hyphens and appends location, experience
        and page number as URL segments / query parameters.

        Returns:
            str: A fully-formed Naukri search URL.
        """
        kw_slug = keywords.strip().lower().replace(' ', '-')
        url = f"{self.BASE_URL}/{kw_slug}-jobs"

        if location:
            loc_slug = location.strip().lower().replace(' ', '-')
            url += f"-in-{loc_slug}"

        params = []
        if experience:
            params.append(f"experience={experience}")
        if sort_by == "date":
            params.append("sortBy=date")
        if page > 1:
            params.append(f"pageNo={page}")

        if params:
            url += "?" + "&".join(params)

        return url

    def _parse_search_results(self) -> List[Dict]:
        """
        Parses the current Naukri search-results page and extracts job cards.

        Tries multiple selectors for the job-card container, then extracts
        title, company, URL, location, experience, salary, and a skills
        preview from each card.

        Returns:
            List[Dict]: One dict per job card found on the page.
        """
        jobs: List[Dict] = []

        # Naukri job card container selectors (may change across redesigns)
        card_selectors = [
            'article.jobTuple',
            '.srp-jobtuple-wrapper',
            '[data-job-id]',
            '.list > article',
            '.jobTupleHeader',
            'div[class*="srp-jobtuple"]',
            'div[class*="cust-job-tuple"]',
        ]

        cards = []
        for selector in card_selectors:
            try:
                cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if cards:
                    logging.debug(f"Found {len(cards)} job cards with selector: {selector}")
                    break
            except Exception:
                continue

        for card in cards:
            try:
                job = self._extract_card_info(card)
                if job and job.get('url'):
                    jobs.append(job)
            except Exception as e:
                logging.debug(f"Failed to parse a job card: {e}")
                continue

        return jobs

    def _extract_card_info(self, card) -> Dict:
        """
        Extracts summary information from a single search-result job card.

        Args:
            card: A Selenium WebElement representing one job card.

        Returns:
            Dict: Keys — title, company, url, location, experience,
                  salary, skills_preview.
        """
        info: Dict = {}

        # Title + URL
        title_selectors = ['a.title', 'a[class*="title"]', '.jobTupleHeader a', 'a[class*="job-title"]', 'h2 a']
        for sel in title_selectors:
            try:
                el = card.find_element(By.CSS_SELECTOR, sel)
                info['title'] = el.text.strip()
                info['url'] = el.get_attribute('href')
                break
            except NoSuchElementException:
                continue

        # Company
        company_selectors = ['a.subTitle', 'a[class*="comp-name"]', '.companyInfo a', 'a[class*="company"]', 'span[class*="comp-name"]']
        for sel in company_selectors:
            try:
                info['company'] = card.find_element(By.CSS_SELECTOR, sel).text.strip()
                break
            except NoSuchElementException:
                continue

        # Experience
        exp_selectors = ['li.experience span', 'span[class*="experience"]', 'li[class*="exp"] span', '.expwdth']
        for sel in exp_selectors:
            try:
                info['experience'] = card.find_element(By.CSS_SELECTOR, sel).text.strip()
                break
            except NoSuchElementException:
                continue

        # Salary
        salary_selectors = ['li.salary span', 'span[class*="salary"]', 'li[class*="sal"] span', '.salarywdth']
        for sel in salary_selectors:
            try:
                info['salary'] = card.find_element(By.CSS_SELECTOR, sel).text.strip()
                break
            except NoSuchElementException:
                continue

        # Location
        loc_selectors = ['li.location span', 'span[class*="location"]', 'li[class*="loc"] span', '.locwdth']
        for sel in loc_selectors:
            try:
                info['location'] = card.find_element(By.CSS_SELECTOR, sel).text.strip()
                break
            except NoSuchElementException:
                continue

        # Skills preview (tags shown on the card)
        skills_selectors = ['ul.tags li', 'li[class*="tag"]', '.tag-li', 'span[class*="skill"]']
        for sel in skills_selectors:
            try:
                skill_elements = card.find_elements(By.CSS_SELECTOR, sel)
                if skill_elements:
                    info['skills_preview'] = [s.text.strip() for s in skill_elements if s.text.strip()]
                    break
            except NoSuchElementException:
                continue

        return info

    # ------------------------------------------------------------------
    # Individual job scraping
    # ------------------------------------------------------------------

    def scrape_job(self, job_url: str) -> Dict:
        """
        Scrapes full details from a single Naukri.com job posting page.

        Navigates to the URL, then extracts title, company, location,
        experience, salary, skills, and the full job description using
        Naukri-specific selectors.

        Args:
            job_url (str): The full URL of a Naukri job listing.

        Returns:
            Dict: Keys — url, title, company, location, experience, salary,
                  skills, description, requirements, scraped_at.
                  Returns ``{}`` on failure.
        """
        logging.info(f"Scraping Naukri job: {job_url}")
        try:
            self.setup_driver()
            self.driver.get(job_url)
            time.sleep(3)

            title = self.extract_job_title()
            company = self.extract_company_name()
            location = self.extract_location()
            experience = self.extract_experience()
            salary = self.extract_salary()
            skills = self.extract_skills()
            description = self.extract_job_description()
            requirements = self._derive_requirements(description, skills)

            job_details = {
                'url': job_url,
                'title': title,
                'company': company,
                'location': location,
                'experience': experience,
                'salary': salary,
                'skills': skills,
                'description': description,
                'requirements': requirements,
                'scraped_at': datetime.now().isoformat(),
                'source': 'naukri.com',
            }

            logging.info(f"Naukri scrape complete — Title: '{title}', Company: '{company}'")
            if any(v in ("Unknown Title", "Unknown Company", "Unknown Location", "No description found")
                   for v in (title, company, location, description)):
                logging.warning("Some fields could not be extracted — matching may be affected")

            return job_details

        except Exception as e:
            logging.error(f"Error scraping Naukri job {job_url}: {e}")
            return {}

    # ------------------------------------------------------------------
    # Individual field extractors
    # ------------------------------------------------------------------

    def extract_job_title(self) -> str:
        """Extracts the job title from a Naukri job detail page."""
        selectors = [
            'h1[class*="jd-header-title"]',
            'h1[class*="styles_jd-header-title"]',
            '.jd-header-title',
            'h1[class*="job-title"]',
            'input[name="pageTitle"]',  # hidden input sometimes present
        ]
        result = self._extract_text(selectors)
        if result:
            return result

        # Fallback: first h1 on page
        try:
            h1 = self.driver.find_element(By.TAG_NAME, 'h1')
            if h1.text.strip():
                return h1.text.strip()
        except NoSuchElementException:
            pass

        return "Unknown Title"

    def extract_company_name(self) -> str:
        """Extracts the company name from a Naukri job detail page."""
        selectors = [
            'a[class*="jd-header-comp-name"]',
            'a[class*="comp-name"]',
            'div[class*="jd-header-comp-name"]',
            '.jd-header-comp-name',
            'a[href*="/company-jobs"]',
        ]
        result = self._extract_text(selectors)
        if result:
            return result

        # Fallback: anchor near the title whose href mentions 'company'
        try:
            links = self.driver.find_elements(By.TAG_NAME, 'a')
            for link in links:
                href = link.get_attribute('href') or ''
                if '/company-jobs' in href or '/companies/' in href:
                    text = link.text.strip()
                    if text and len(text) < 100:
                        return text
        except Exception:
            pass

        return "Unknown Company"

    def extract_location(self) -> str:
        """Extracts the job location from a Naukri job detail page."""
        selectors = [
            'span[class*="location"]',
            'a[class*="location"]',
            'div[class*="jd-loc"]',
            '.loc-icon + span',
            '.location a',
        ]
        result = self._extract_text(selectors)
        if result:
            return result

        # Fallback: look for spans inside the header details area
        try:
            header_area = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="jd-header"] span')
            for span in header_area:
                text = span.text.strip()
                if text and any(c.isalpha() for c in text) and len(text) < 80:
                    if any(city in text.lower() for city in
                           ['bangalore', 'mumbai', 'delhi', 'hyderabad', 'pune',
                            'chennai', 'kolkata', 'noida', 'gurgaon', 'remote']):
                        return text
        except Exception:
            pass

        return "Unknown Location"

    def extract_experience(self) -> str:
        """Extracts the required experience from a Naukri job detail page."""
        selectors = [
            'span[class*="experience"]',
            'div[class*="experience"]',
            'span[class*="exp"]',
            '.exp-icon + span',
            '.experience',
        ]
        result = self._extract_text(selectors)
        if result:
            return result

        # Fallback: regex on page
        try:
            body_text = self.driver.find_element(By.TAG_NAME, 'body').text
            match = re.search(r'(\d+\s*-\s*\d+\s*(?:Yrs?|years?))', body_text, re.IGNORECASE)
            if match:
                return match.group(1)
        except Exception:
            pass

        return "Not specified"

    def extract_salary(self) -> str:
        """Extracts the salary range from a Naukri job detail page."""
        selectors = [
            'span[class*="salary"]',
            'div[class*="salary"]',
            'span[class*="sal"]',
            '.salary-icon + span',
            '.salary',
        ]
        result = self._extract_text(selectors)
        if result:
            return result

        return "Not disclosed"

    def extract_skills(self) -> List[str]:
        """Extracts the key skills / tags from a Naukri job detail page."""
        skill_container_selectors = [
            'div[class*="key-skill"] a',
            'div[class*="keyskill"] span',
            'a[class*="chip"]',
            '.key-skill a',
            'div[class*="chip-body"] span',
            'span[class*="keyword"]',
        ]

        for selector in skill_container_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    skills = [el.text.strip() for el in elements if el.text.strip()]
                    if skills:
                        return skills
            except Exception:
                continue

        return []

    def extract_job_description(self) -> str:
        """Extracts the full job description from a Naukri job detail page."""
        selectors = [
            'div[class*="job-desc"]',
            'div[class*="jobDescription"]',
            'section[class*="job-desc"]',
            'div[class*="dang-inner-html"]',
            '.job-desc',
            '#job_desc',
        ]
        result = self._extract_text(selectors)
        if result and len(result) > 50:
            return result

        # Fallback: largest text block with job-related keywords
        try:
            sections = self.driver.find_elements(By.CSS_SELECTOR, 'div, section')
            best = ""
            for sec in sections:
                text = sec.text.strip()
                if len(text) > len(best) and len(text) > 200:
                    keywords = ['responsibility', 'requirement', 'experience', 'skill', 'role', 'qualification']
                    if any(kw in text.lower() for kw in keywords):
                        best = text
            if best:
                return best
        except Exception:
            pass

        return "No description found"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _derive_requirements(self, description: str, skills: List[str]) -> List[str]:
        """
        Builds a combined requirements list from extracted skills and
        technology keywords found in the description.

        Args:
            description (str): The full job description text.
            skills (List[str]): Skills already extracted from skill tags.

        Returns:
            List[str]: Merged, de-duplicated list of requirement keywords.
        """
        requirements = [s.lower() for s in skills]

        tech_keywords = [
            'python', 'java', 'javascript', 'react', 'node.js', 'angular',
            'vue', 'sql', 'nosql', 'mongodb', 'aws', 'azure', 'gcp',
            'docker', 'kubernetes', 'machine learning', 'ai', 'deep learning',
            'django', 'flask', 'spring', '.net', 'c#', 'c++', 'go', 'rust',
            'tensorflow', 'pytorch', 'pandas', 'spark', 'hadoop',
            'bachelor', 'master', 'phd', 'b.tech', 'm.tech', 'mca',
        ]
        desc_lower = description.lower()
        for kw in tech_keywords:
            if kw in desc_lower and kw not in requirements:
                requirements.append(kw)

        return requirements

    def _extract_text(self, selectors: List[str]) -> Optional[str]:
        """
        Tries each CSS selector in order and returns the text of the first
        non-empty match.

        Args:
            selectors (List[str]): CSS selectors to try.

        Returns:
            Optional[str]: The matched text, or None if all selectors fail.
        """
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                text = element.text.strip()
                if text:
                    return text
            except (NoSuchElementException, Exception):
                continue
        return None

    def _find_first_element(self, selectors: List[str]):
        """
        Returns the first visible element matching any of the selectors.
        Supports both CSS selectors and XPath (strings starting with ``//``).

        Args:
            selectors (List[str]): CSS or XPath selectors.

        Returns:
            WebElement or None.
        """
        for selector in selectors:
            try:
                by = By.XPATH if selector.startswith('//') else By.CSS_SELECTOR
                element = self.driver.find_element(by, selector)
                if element.is_displayed():
                    return element
            except (NoSuchElementException, Exception):
                continue
        return None

    def close(self):
        """Closes the browser and cleans up the driver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.logged_in = False
