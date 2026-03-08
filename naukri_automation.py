# naukri_automation.py - Module for Naukri.com application automation
import json
import logging
import os
import time
from typing import Dict, List, Optional

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sentence_transformers import SentenceTransformer, util

from application_tracker import ApplicationTracker
from browser_automation import BrowserSetup
from job_matcher import JobMatcher
from naukri_scraper import NaukriScraper


class NaukriAutomation:
    """
    Automates the Naukri.com job-application workflow.

    Manages a shared browser session with NaukriScraper so that a single
    login is reused for searching, scraping, and applying.  Supports:

    * One-click "Apply" on Naukri (profile-based).
    * Handling the pre-apply chatbot questionnaire.
    * Uploading / updating the profile resume.
    * External-apply detection (redirects to company site).
    * A full search → match → apply pipeline.
    """

    PROFILE_URL = "https://www.naukri.com/mnjuser/profile"

    def __init__(
        self,
        naukri_scraper: NaukriScraper,
        job_matcher: JobMatcher,
        tracker: ApplicationTracker,
    ):
        """
        Initializes NaukriAutomation.

        Args:
            naukri_scraper (NaukriScraper): An already-initialised scraper
                (its driver and login session are shared).
            job_matcher (JobMatcher): Used to filter jobs before applying.
            tracker (ApplicationTracker): Used to record applications.
        """
        self.scraper = naukri_scraper
        self.job_matcher = job_matcher
        self.tracker = tracker
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def driver(self):
        """Returns the Selenium driver from the shared scraper."""
        return self.scraper.driver

    @property
    def wait(self):
        """Returns the WebDriverWait from the shared scraper."""
        return self.scraper.wait

    # ------------------------------------------------------------------
    # Resume / profile management
    # ------------------------------------------------------------------

    def update_profile_resume(self, resume_path: str) -> bool:
        """
        Uploads a new resume to the user's Naukri profile.

        Navigates to the Naukri profile page, locates the resume-upload
        section, and sends the file path to the file-input element.

        Args:
            resume_path (str): Absolute or relative path to the PDF resume.

        Returns:
            bool: True if the upload appeared to succeed.
        """
        if not self.scraper.logged_in:
            logging.error("Must be logged in to update profile resume")
            return False

        try:
            logging.info("Navigating to Naukri profile page...")
            self.driver.get(self.PROFILE_URL)
            time.sleep(3)

            abs_path = os.path.abspath(resume_path)
            if not os.path.exists(abs_path):
                logging.error(f"Resume file not found: {abs_path}")
                return False

            # Naukri profile page upload selectors
            upload_selectors = [
                'input[type="file"][id*="attachCV"]',
                'input[type="file"][name*="resume"]',
                'input[type="file"][id*="resume"]',
                'input[type="file"][accept*=".pdf"]',
                'input[type="file"]',
            ]

            for selector in upload_selectors:
                try:
                    file_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    file_input.send_keys(abs_path)
                    time.sleep(3)
                    logging.info(f"Resume uploaded to Naukri profile: {abs_path}")
                    return True
                except NoSuchElementException:
                    continue

            # Fallback: click the visible "Update Resume" button first
            update_btn_selectors = [
                '//button[contains(text(), "Update resume")]',
                '//a[contains(text(), "Update resume")]',
                '//span[contains(text(), "Update resume")]',
                'a[class*="update-resume"]',
                'button[class*="update-resume"]',
            ]
            for selector in update_btn_selectors:
                try:
                    by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                    btn = self.driver.find_element(by, selector)
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(2)
                        # After clicking, try file input again
                        for fselector in upload_selectors:
                            try:
                                file_input = self.driver.find_element(
                                    By.CSS_SELECTOR, fselector
                                )
                                file_input.send_keys(abs_path)
                                time.sleep(3)
                                logging.info(
                                    f"Resume uploaded to Naukri profile: {abs_path}"
                                )
                                return True
                            except NoSuchElementException:
                                continue
                except (NoSuchElementException, Exception):
                    continue

            logging.error("Could not find resume upload input on Naukri profile page")
            return False

        except Exception as e:
            logging.error(f"Error updating Naukri profile resume: {e}")
            return False

    # ------------------------------------------------------------------
    # Single-job application
    # ------------------------------------------------------------------

    def apply_to_job(
        self,
        job_url: str,
        personal_details: Dict,
        job_details: Optional[Dict] = None,
    ) -> bool:
        """
        Applies to a single Naukri.com job.

        Navigates to the job page, locates the Apply button, clicks it,
        handles any chatbot questionnaire or confirmation dialog, and
        records the application.

        If *job_details* is not provided the method will scrape them first.

        Args:
            job_url (str): URL of the Naukri job listing.
            personal_details (Dict): The user's personal information.
            job_details (Optional[Dict]): Pre-scraped details (saves a reload).

        Returns:
            bool: True if the application was submitted successfully.
        """
        if not self.scraper.logged_in:
            logging.error("Must be logged in to apply for jobs on Naukri")
            return False

        try:
            # Scrape if needed
            if not job_details:
                job_details = self.scraper.scrape_job(job_url)
                if not job_details:
                    logging.error(f"Could not scrape job details for {job_url}")
                    return False
            else:
                # Make sure we're on the right page
                if self.driver.current_url != job_url:
                    self.driver.get(job_url)
                    time.sleep(3)

            title = job_details.get("title", "Unknown")
            company = job_details.get("company", "Unknown")
            logging.info(f"Applying to: {title} at {company}")

            # --- Find and click the Apply button ---
            apply_btn = self._find_apply_button()
            if not apply_btn:
                logging.warning("No Apply button found — may be an external-apply job")
                external = self._handle_external_apply()
                if external:
                    logging.info(
                        "External apply link opened for user to complete manually"
                    )
                    self.tracker.add_application(job_url, job_details)
                    return True
                return False

            # Click apply
            if not self._safe_click(apply_btn):
                return False

            time.sleep(2)

            # --- Handle chatbot / questionnaire ---
            if self._detect_chatbot():
                logging.info("Chatbot questionnaire detected, handling...")
                self._handle_chatbot_questions(personal_details)
                time.sleep(2)

            # --- Handle confirmation dialog ---
            self._handle_apply_confirmation()
            time.sleep(2)

            # --- Check for success ---
            if self._verify_application_success():
                logging.info(f"Successfully applied to {title} at {company}")
                self.tracker.add_application(job_url, job_details)
                return True

            logging.warning("Could not verify application success")
            # Still track it as attempted
            self.tracker.add_application(job_url, job_details)
            return True

        except Exception as e:
            logging.error(f"Error applying to Naukri job {job_url}: {e}")
            return False

    # ------------------------------------------------------------------
    # Search-and-apply pipeline
    # ------------------------------------------------------------------

    def search_and_apply(
        self,
        keywords: str,
        personal_details: Dict,
        location: str = "",
        experience: str = "",
        max_applications: int = 20,
        max_pages: int = 3,
    ) -> Dict:
        """
        Searches for jobs on Naukri, filters them with JobMatcher, and
        applies to the matching ones.

        Args:
            keywords (str):          Search keywords.
            personal_details (Dict): The user's personal information.
            location (str):          Desired location.
            experience (str):        Experience in years.
            max_applications (int):  Stop after this many successful applies.
            max_pages (int):         Maximum search-result pages to scrape.

        Returns:
            Dict: Summary with keys ``total_found``, ``matched``, ``applied``,
                  ``skipped``, ``failed``.
        """
        stats = {
            "total_found": 0,
            "matched": 0,
            "applied": 0,
            "skipped": 0,
            "failed": 0,
        }

        # Step 1 — search
        jobs = self.scraper.search_jobs(
            keywords, location, experience, max_pages=max_pages
        )
        stats["total_found"] = len(jobs)
        logging.info(f"Search returned {len(jobs)} jobs for '{keywords}'")

        if not jobs:
            print("No jobs found matching your search criteria.")
            return stats

        # Step 2 — iterate, match, apply
        for idx, job_summary in enumerate(jobs, 1):
            if stats["applied"] >= max_applications:
                logging.info(
                    f"Reached max applications ({max_applications}), stopping."
                )
                break

            job_url = job_summary.get("url", "")
            if not job_url:
                continue

            print(
                f"\n[{idx}/{len(jobs)}] {job_summary.get('title', '?')} "
                f"at {job_summary.get('company', '?')} — {job_summary.get('location', '?')}"
            )

            # Scrape full details
            job_details = self.scraper.scrape_job(job_url)
            if not job_details:
                stats["failed"] += 1
                continue

            # Match
            if not self.job_matcher.match_job(job_details):
                print("  ⏩ Skipped (does not match preferences)")
                stats["skipped"] += 1
                continue

            stats["matched"] += 1

            # Apply
            if self.apply_to_job(job_url, personal_details, job_details):
                print("  ✅ Applied successfully")
                stats["applied"] += 1
            else:
                print("  ❌ Application failed")
                stats["failed"] += 1

            time.sleep(2)  # rate limiting

        # Summary
        print(f"\n{'='*50}")
        print("Naukri Search & Apply Summary")
        print(f"{'='*50}")
        print(f"  Total jobs found : {stats['total_found']}")
        print(f"  Matched prefs    : {stats['matched']}")
        print(f"  Applied          : {stats['applied']}")
        print(f"  Skipped          : {stats['skipped']}")
        print(f"  Failed           : {stats['failed']}")

        return stats

    # ------------------------------------------------------------------
    # Apply-button finding
    # ------------------------------------------------------------------

    def _find_apply_button(self):
        """
        Locates the Apply / Apply Now button on a Naukri job detail page.

        Tries Naukri-specific selectors first, then falls back to
        generic text-based XPath searches.

        Returns:
            WebElement or None.
        """
        # Naukri-specific selectors
        css_selectors = [
            'button[class*="apply-button"]',
            'button[id*="apply"]',
            'button[class*="apply-btn"]',
            ".apply-button-container button",
            'button[class*="styles_apply"]',
            'div[class*="apply"] button',
        ]
        for selector in css_selectors:
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                if btn.is_displayed() and btn.is_enabled():
                    return btn
            except NoSuchElementException:
                continue

        # XPath text-based
        xpaths = [
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
            "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
        ]
        for xp in xpaths:
            try:
                elements = self.driver.find_elements(By.XPATH, xp)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        text = el.text.strip().lower()
                        # Avoid "apply filters" or similar
                        if "filter" not in text and "save" not in text:
                            return el
            except Exception:
                continue

        return None

    # ------------------------------------------------------------------
    # Chatbot / questionnaire
    # ------------------------------------------------------------------

    def _detect_chatbot(self) -> bool:
        """
        Checks whether Naukri's pre-apply chatbot questionnaire appeared
        after clicking Apply.

        Returns:
            bool: True if a chatbot / questionnaire dialog is visible.
        """
        chatbot_indicators = [
            'div[class*="chatbot"]',
            'div[class*="chat-window"]',
            'div[class*="apply-dialog"]',
            'div[class*="screening"]',
            'div[class*="questionnaire"]',
        ]
        for selector in chatbot_indicators:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, selector)
                if el.is_displayed():
                    return True
            except NoSuchElementException:
                continue
        return False

    def _handle_chatbot_questions(self, personal_details: Dict):
        """
        Attempts to answer Naukri's pre-apply chatbot questions automatically.

        Iterates over visible text inputs, textareas, radio buttons, and
        dropdowns inside the chatbot dialog and fills them with reasonable
        defaults. After each answer it clicks the "Next" / "Submit" button
        if one is found, up to a maximum of 10 rounds.
        """
        max_rounds = 10
        for round_num in range(max_rounds):
            time.sleep(1)

            # --- Text inputs ---
            text_inputs = self.driver.find_elements(
                By.CSS_SELECTOR,
                'div[class*="chatbot"] input[type="text"], '
                'div[class*="apply-dialog"] input[type="text"], '
                'div[class*="screening"] input[type="text"], '
                'div[class*="chatbot"] textarea, '
                'div[class*="apply-dialog"] textarea, '
                'div[class*="screening"] textarea',
            )
            for inp in text_inputs:
                try:
                    if inp.is_displayed() and not inp.get_attribute("value"):
                        placeholder = (inp.get_attribute("placeholder") or "").lower()
                        field_found = False
                        if "year" in placeholder or "experience" in placeholder:
                            value = personal_details.get("years_experience")
                            if value:
                                inp.send_keys(str(value))
                                field_found = True
                        elif "salary" in placeholder or "ctc" in placeholder:
                            value = personal_details.get("current_ctc")
                            if value:
                                inp.send_keys(str(value))
                                field_found = True
                        elif "notice" in placeholder:
                            value = personal_details.get("notice_period")
                            if value:
                                inp.send_keys(str(value))
                                field_found = True

                        if not field_found:
                            self._handle_unknown_field(inp, personal_details)

                except Exception:
                    continue

            # --- Radio buttons — pick the first option ---
            radios = self.driver.find_elements(
                By.CSS_SELECTOR,
                'div[class*="chatbot"] input[type="radio"], '
                'div[class*="apply-dialog"] input[type="radio"], '
                'div[class*="screening"] input[type="radio"]',
            )
            clicked_groups = set()
            for radio in radios:
                try:
                    name = radio.get_attribute("name")
                    if name not in clicked_groups and not radio.is_selected():
                        self._safe_click(radio)
                        clicked_groups.add(name)
                except Exception:
                    continue

            # --- Dropdowns — select the first non-empty option ---
            selects = self.driver.find_elements(
                By.CSS_SELECTOR,
                'div[class*="chatbot"] select, '
                'div[class*="apply-dialog"] select, '
                'div[class*="screening"] select',
            )
            for sel_elem in selects:
                try:
                    from selenium.webdriver.support.ui import Select

                    select = Select(sel_elem)
                    if len(select.options) > 1:
                        select.select_by_index(1)
                except Exception:
                    continue

            # --- Click Next / Submit / Continue ---
            next_btn = self._find_chatbot_next_button()
            if next_btn:
                self._safe_click(next_btn)
                time.sleep(1)
            else:
                # No more steps
                break

    def _handle_unknown_field(self, input_elem, personal_details):
        """Handle unknown fields by asking the user for input."""
        try:
            label_text = self._get_field_label(input_elem)
            if not label_text:
                print("     ⚠️ Could not determine label for an input field. Skipping.")
                return

            print(f"     ❓ Found an unknown field: '{label_text}'")
            answer = input(
                "     Enter the value for this field (or press Enter to skip): "
            ).strip()

            if answer:
                input_elem.send_keys(answer)
                print(f"     ✅ Filled '{label_text}' with '{answer}'")

                save_answer = (
                    input("     Do you want to save this answer for future use? (y/N): ")
                    .strip()
                    .lower()
                )
                if save_answer == "y":
                    field_key = input(
                        "     Enter a key to save this value as (e.g., 'current_compensation'): "
                    ).strip()
                    if field_key:
                        self._save_custom_detail(field_key, answer)
                        personal_details[field_key] = answer
        except Exception as e:
            logging.error(f"Error handling unknown field: {e}")

    def _save_custom_detail(self, key, value):
        """Save a new key-value pair to custom_details.json."""
        custom_details_file = "custom_details.json"
        details = {}
        if os.path.exists(custom_details_file):
            with open(custom_details_file, "r") as f:
                try:
                    details = json.load(f)
                except json.JSONDecodeError:
                    pass  # Overwrite if invalid JSON

        details[key] = value
        with open(custom_details_file, "w") as f:
            json.dump(details, f, indent=4)
        print(f"     💾 Saved '{key}' to {custom_details_file}")

    def _get_field_label(self, element) -> str:
        """Get the label or context for a form field."""
        try:
            # Try to find associated label
            field_id = element.get_attribute("id")
            if field_id:
                try:
                    label = self.driver.find_element(
                        By.CSS_SELECTOR, f'label[for="{field_id}"]'
                    )
                    return label.text
                except:
                    pass

            # Look for nearby text
            parent = element.find_element(By.XPATH, "..")
            return parent.text

        except:
            return ""

    def _find_chatbot_next_button(self):
        """
        Finds the Next / Submit / Continue button inside a chatbot dialog.

        Returns:
            WebElement or None.
        """
        xpaths = [
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'next')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'save')]",
        ]
        for xp in xpaths:
            try:
                elements = self.driver.find_elements(By.XPATH, xp)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        return el
            except Exception:
                continue
        return None

    # ------------------------------------------------------------------
    # External apply
    # ------------------------------------------------------------------

    def _handle_external_apply(self) -> bool:
        """
        Detects and handles "Apply on company site" links.

        Looks for outbound links or buttons that redirect to an external
        application page and opens them for the user to complete manually.

        Returns:
            bool: True if an external apply link was found and opened.
        """
        external_selectors = [
            "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply on company')]",
            "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply on company site')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'company site')]",
            'a[class*="external-apply"]',
            'a[class*="company-site"]',
        ]
        for selector in external_selectors:
            try:
                by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                el = self.driver.find_element(by, selector)
                if el.is_displayed():
                    href = el.get_attribute("href")
                    print(f"\n  External apply detected → {href or '(click to open)'}")
                    print(
                        "  The link will be opened; please complete the application manually."
                    )
                    self._safe_click(el)
                    time.sleep(2)
                    return True
            except (NoSuchElementException, Exception):
                continue
        return False

    # ------------------------------------------------------------------
    # Confirmation & verification
    # ------------------------------------------------------------------

    def _handle_apply_confirmation(self):
        """
        Clicks confirmation buttons that Naukri may show after clicking Apply
        (e.g. "Submit", "Confirm", "Done").
        """
        confirm_selectors = [
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'confirm')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'done')]",
            'button[class*="submit"]',
            'button[class*="confirm"]',
        ]
        for selector in confirm_selectors:
            try:
                by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                el = self.driver.find_element(by, selector)
                if el.is_displayed() and el.is_enabled():
                    self._safe_click(el)
                    return
            except (NoSuchElementException, Exception):
                continue

    def _verify_application_success(self) -> bool:
        """
        Checks the page for visual cues that the application was submitted
        successfully (e.g. "already applied", "application submitted" text).

        Returns:
            bool: True if a success indicator is found.
        """
        if self._verify_application_success_transformer():
            return True

        success_indicators = [
            "already applied",
            "application submitted",
            "successfully applied",
            "applied successfully",
            "you have applied",
            "application sent",
        ]
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            return any(indicator in body_text for indicator in success_indicators)
        except Exception:
            return False

    def _verify_application_success_transformer(self) -> bool:
        """
        Checks the page for visual cues that the application was submitted
        successfully using sentence transformers.

        Returns:
            bool: True if a success indicator is found.
        """
        success_indicators = [
            "you have successfully applied",
            "your application has been submitted",
            "thanks for applying",
        ]
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            sentences = body_text.split("\n")
            sentences = [s.strip() for s in sentences if s.strip()]

            if not sentences:
                return False

            target_embeddings = self.model.encode(
                success_indicators, convert_to_tensor=True
            )
            sentence_embeddings = self.model.encode(sentences, convert_to_tensor=True)

            cosine_scores = util.pytorch_cos_sim(
                sentence_embeddings, target_embeddings
            )

            for i in range(len(sentences)):
                for j in range(len(success_indicators)):
                    if cosine_scores[i][j] > 0.7:
                        logging.info(
                            f"Found success message with score {cosine_scores[i][j]}: '{sentences[i]}'"
                        )
                        return True
            return False
        except Exception as e:
            logging.error(f"Error verifying application success with transformer: {e}")
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _safe_click(self, element) -> bool:
        """
        Clicks an element, falling back to a JavaScript click if the
        normal click is intercepted by an overlay.

        Args:
            element: Selenium WebElement.

        Returns:
            bool: True if the click succeeded.
        """
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            element.click()
            return True
        except ElementClickInterceptedException:
            try:
                logging.debug("Click intercepted, trying JS click...")
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as e:
                logging.error(f"JS click also failed: {e}")
                return False
        except Exception as e:
            logging.error(f"Click failed: {e}")
            return False
