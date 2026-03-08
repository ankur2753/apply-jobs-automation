#!/usr/bin/env python3
"""
LinkedIn Easy Apply Job Application Automation

This module specifically targets LinkedIn's Easy Apply jobs using cookie-based authentication
to avoid login issues with Google-connected accounts. It now includes automatic resume customization
for each job application using the ResumeModifier.
"""

import json
import logging
import os
import re
import time
from typing import Dict, List, Optional

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from sentence_transformers import SentenceTransformer, util

from browser_automation import BrowserSetup
from logger import JobApplicationLogger
from resume_modifier import ResumeModifier


class LinkedInEasyApply:
    """
    LinkedIn-specific Easy Apply automation with cookie authentication.
    """

    def __init__(self, cookies_file: str = "linkedin_cookies.json"):
        """
        Initialize LinkedIn automation.

        Args:
            cookies_file: Path to JSON file containing LinkedIn cookies
        """
        self.driver = None
        self.wait = None
        self.cookies_file = cookies_file
        self.base_url = "https://www.linkedin.com"
        self.resume_modifier = ResumeModifier()
        self.generated_resumes_dir = "generated_resumes"
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        # Initialize logger
        self.logger = JobApplicationLogger().get_logger()

        # Create directory for generated resumes
        if not os.path.exists(self.generated_resumes_dir):
            os.makedirs(self.generated_resumes_dir)

        # LinkedIn-specific selectors (updated as of 2024)
        self.selectors = {
            # Job search and listing
            "job_search_input": 'input[placeholder*="Title, skill or Company"], input[placeholder*="Title, skill or Company"]',
            "location_input": 'input[aria-label*="City"], input[placeholder*="City"]',
            "search_button": 'button[aria-label*="Search"], button:contains("Search")',
            "easy_apply_filter": 'button[aria-label*="Easy Apply"]',
            "job_cards": ".job-card-list, .job-card-container--clickable",
            # Easy Apply process
            "easy_apply_button": "#jobs-apply-button-id",
            "next_button": 'button[aria-label*="Continue"], button[data-control-name*="continue"], button:contains("Next")',
            "submit_button": 'button[aria-label*="Submit application"], button[data-control-name*="submit"]',
            "review_button": 'button[aria-label*="Review"], button:contains("Review")',
            # Form fields
            "text_input": 'input[type="text"], input[type="email"], input[type="tel"]',
            "textarea": "textarea",
            "select": "select",
            "radio": 'input[type="radio"]',
            "checkbox": 'input[type="checkbox"]',
            "file_input": 'input[type="file"]',
            # Modal and overlay
            "modal": '.jobs-easy-apply-modal, [role="dialog"]',
            "close_modal": 'button[aria-label*="Dismiss"], .artdeco-modal__dismiss',
            "success_message": ".jobs-easy-apply-modal__success",
        }

    def setup_driver(self, headless: bool = False):
        """Setup Chrome driver with LinkedIn-optimized settings."""
        if not self.driver:
            self.driver = (
                BrowserSetup.create_interactive_driver()
                if not headless
                else BrowserSetup.create_driver(headless=True)
            )
            self.wait = WebDriverWait(self.driver, 15)

            # Add user agent to look more legitimate
            self.driver.execute_cdp_cmd(
                "Network.setUserAgentOverride",
                {
                    "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                },
            )

    def load_cookies(self):
        """Load cookies from file to authenticate with LinkedIn."""
        if not os.path.exists(self.cookies_file):
            print(f"❌ Cookie file {self.cookies_file} not found!")
            print("Please follow these steps:")
            print("1. Open LinkedIn in your browser and log in")
            print("2. Open Developer Tools (F12) → Application → Cookies → linkedin.com")
            print(
                "3. Copy all cookies to a JSON file named 'linkedin_cookies.json'"
            )
            print(
                "4. Format: [{'name': 'cookie_name', 'value': 'cookie_value', 'domain': '.linkedin.com'}, ...]"
            )
            return False

        try:
            with open(self.cookies_file, "r") as f:
                cookies = json.load(f)

            # Navigate to LinkedIn first
            self.driver.get("https://www.linkedin.com/login/")
            time.sleep(2)

            # Add each cookie
            for cookie in cookies:
                try:
                    # Ensure required fields
                    if "name" in cookie and "value" in cookie:
                        cookie_dict = {
                            "name": cookie["name"],
                            "value": cookie["value"],
                            "domain": cookie.get("domain", ".linkedin.com"),
                        }
                        # Add optional fields if they exist
                        if "path" in cookie:
                            cookie_dict["path"] = cookie["path"]
                        if "secure" in cookie:
                            cookie_dict["secure"] = cookie["secure"]
                        if "httpOnly" in cookie:
                            cookie_dict["httpOnly"] = cookie["httpOnly"]

                        self.driver.add_cookie(cookie_dict)
                except Exception as e:
                    self.logger.error(
                        f"Failed to add cookie {cookie.get('name', 'unknown')}: {e}"
                    )

            # Refresh to apply cookies
            self.driver.refresh()
            time.sleep(3)

            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".member-profile-block"))
            )
            profile_block = self.driver.find_element(
                By.CSS_SELECTOR, ".member-profile-block"
            )
            profile_block.click()
            # Check if we're logged in
            try:
                # Look for profile menu or navigation indicating we're logged in
                self.wait.until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, ".profile-card-name")
                    )
                )
                print("✅ Successfully authenticated with LinkedIn using cookies")
                return True
            except TimeoutException:
                print("❌ Cookie authentication failed - cookies may be expired")
                return False

        except json.JSONDecodeError:
            print("❌ Invalid JSON format in cookie file")
            return False
        except Exception as e:
            print(f"❌ Error loading cookies: {e}")
            return False

    def search_easy_apply_jobs(
        self, job_title: str, location: str = "", limit: int = 50
    ):
        """
        Search for Easy Apply jobs on LinkedIn.

        Args:
            job_title: Job title to search for
            location: Location (optional)
            limit: Maximum number of jobs to process
        """
        try:
            # Navigate to jobs page
            jobs_url = f"{self.base_url}/jobs/collections/easy-apply/?discover=true&discoveryOrigin=JOBS_HOME_EXPANDED_JOB_COLLECTIONS&subscriptionOrigin=JOBS_HOME"
            self.driver.get(jobs_url)
            time.sleep(3)

            # Search for jobs
            print(f"🔍 Searching for '{job_title}' jobs...")

            # Enter job title
            # try:
            #     job_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors['job_search_input'])))
            #     job_input.clear()
            #     job_input.send_keys(job_title)
            #     time.sleep(1)
            # except TimeoutException:
            #     print("❌ Could not find job search input")
            #     return []

            # # Enter location if provided
            # if location:
            #     try:
            #         location_input = self.driver.find_element(By.CSS_SELECTOR, self.selectors['location_input'])
            #         location_input.clear()
            #         location_input.send_keys(location)
            #         time.sleep(1)
            #     except NoSuchElementException:
            #         print("⚠️ Location input not found, continuing without location")

            # # Click search
            # try:
            #     search_btn = self.driver.find_element(By.CSS_SELECTOR, self.selectors['search_button'])
            #     search_btn.click()
            #     time.sleep(3)
            # except NoSuchElementException:
            #     # Try pressing Enter on job input as fallback
            #     job_input.send_keys(Keys.RETURN)
            #     time.sleep(3)

            # Apply Easy Apply filter
            # print("🎯 Applying Easy Apply filter...")
            # try:
            #     # Look for Easy Apply filter button
            #     easy_apply_filter = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Easy Apply')]")))
            #     easy_apply_filter.click()
            #     time.sleep(2)
            #     print("✅ Easy Apply filter applied")
            # except TimeoutException:
            #     print("⚠️ Easy Apply filter not found, continuing with all jobs")

            # Get job listings
            job_cards = []
            try:
                # Wait for job results to load
                self.wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, self.selectors["job_cards"])
                    )
                )
                job_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, self.selectors["job_cards"]
                )[:limit]

                for idx, job_element in enumerate(job_elements):
                    try:
                        # Extract job information
                        job_info = self._extract_job_info(job_element)
                        if job_info:
                            job_cards.append(job_info)
                            print(
                                f"   {idx+1}. {job_info['title']} at {job_info['company']}"
                            )
                    except Exception as e:
                        self.logger.info(
                            f"Failed to extract job info for element {idx}: {e}"
                        )

                print(f"✅ Found {len(job_cards)} Easy Apply jobs")
                return job_cards

            except TimeoutException:
                print("❌ No job results found")
                return []

        except Exception as e:
            print(f"❌ Error searching for jobs: {e}")
            return []

    def _extract_job_info(self, job_element) -> Optional[Dict]:
        """Extract job information from a job card element."""
        try:
            job_info = {}
            footer = job_element.find_element(
                By.CLASS_NAME, "job-card-list__footer-wrapper"
            )
            if "applied" in footer.text.lower():
                return  # Return from function if 'applied' is found anywhere inside footer or its children

            # Job title and URL
            try:
                title_element = job_element.find_element(
                    By.CSS_SELECTOR, "a.job-card-list__title--link"
                )
                job_info["title"] = title_element.text.strip()
                job_info["url"] = title_element.get_attribute("href")
                job_info["job_id"] = job_element.get_attribute("data-job-id")
            except Exception:
                job_info["title"] = "Unknown Title"
                job_info["url"] = ""

            # Company name
            try:
                company_element = job_element.find_element(
                    By.CSS_SELECTOR, ".artdeco-entity-lockup__subtitle"
                )
                job_info["company"] = company_element.text.strip()
            except Exception:
                job_info["company"] = "Unknown Company"

            # Location
            try:
                location_element = job_element.find_element(
                    By.CSS_SELECTOR, ".job-card-container__metadata-wrapper li"
                )
                job_info["location"] = location_element.text.strip()
            except Exception:
                job_info["location"] = "Unknown Location"

            # Easy Apply status
            try:
                footer_items = job_element.find_elements(
                    By.CSS_SELECTOR, ".job-card-list__footer-wrapper li"
                )
                job_info["easy_apply"] = any(
                    "easy apply" in item.text.lower() for item in footer_items
                )
            except Exception:
                job_info["easy_apply"] = False

            # Initialize description and requirements
            job_info["description"] = ""
            job_info["requirements"] = []

            return job_info if job_info["title"] != "Unknown Title" else None

        except Exception as e:
            self.logger.error(f"Error extracting job info: {e}")
            return None

    def apply_to_job(self, job_info: Dict, personal_details: Dict) -> bool:
        """
        Apply to a specific job using Easy Apply with custom resume generation.

        Args:
            job_info: Job information dictionary
            personal_details: Personal details for application
        """
        try:
            print(f"\n🎯 Applying to: {job_info['title']} at {job_info['company']}")

            # Navigate to job page and extract full job description
            if job_info.get("job_id"):
                self.driver.get(
                    f"https://www.linkedin.com/jobs/collections/easy-apply/?currentJobId={job_info['job_id']}&discover=recommended&discoveryOrigin=JOBS_HOME_JYMBII"
                )
                time.sleep(3)

                # Extract full job description for resume customization
                print("   📋 Extracting job description for resume customization...")
                job_info = self._extract_full_job_description(job_info)
            elif job_info.get("url"):
                self.driver.get(job_info["url"])
                time.sleep(3)

                # Extract full job description for resume customization
                print("   📋 Extracting job description for resume customization...")
                job_info = self._extract_full_job_description(job_info)

            # Generate custom resume for this job
            print("   🔧 Generating custom resume for this job...")
            custom_resume_path = self._generate_custom_resume(job_info, personal_details)

            if custom_resume_path:
                # Update personal details with the custom resume path
                personal_details = personal_details.copy()  # Don't modify original
                personal_details["resume_path"] = custom_resume_path
                print(
                    f"   ✅ Custom resume generated: {os.path.basename(custom_resume_path)}"
                )
            else:
                print("   ⚠️ Failed to generate custom resume, using default if available")

            # Find and click Easy Apply button
            try:
                easy_apply_btn = self.wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, self.selectors["easy_apply_button"])
                    )
                )
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", easy_apply_btn
                )
                wait = WebDriverWait(self.driver, 10)
                button = wait.until(
                    EC.element_to_be_clickable((By.ID, "jobs-apply-button-id"))
                )

                easy_apply_btn.click()
                time.sleep(2)
                print("   ✅ Opened Easy Apply modal")
            except TimeoutException:
                print("   ❌ Easy Apply button not found")
                return False

            # Handle multi-step application process
            step = 1
            max_steps = 10  # Safety limit

            while step <= max_steps:
                print(f"   📝 Processing application step {step}...")

                # Fill form fields in current step
                self._fill_current_step(personal_details)

                # Try to proceed to next step or submit
                if self._click_next_or_submit():
                    # Check if application was successful
                    if self._check_application_success():
                        print("   🎉 Application submitted successfully!")
                        return True
                else:
                    print("   ❌ Could not proceed to next step")
                    return False

                step += 1
                time.sleep(2)

            print(f"   ❌ Application process exceeded {max_steps} steps")
            return False

        except Exception as e:
            print(f"   ❌ Error during application: {e}")
            return False

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
            self.logger.error(f"Error handling unknown field: {e}")

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

    def _fill_current_step(self, personal_details: Dict, max_retries: int = 2):
        """Fill form fields in the current application step with stale element retry."""
        for attempt in range(max_retries + 1):
            try:
                # Wait for modal to be present
                modal = self.wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, self.selectors["modal"])
                    )
                )
                time.sleep(0.5)  # Let DOM settle

                # Find and fill text inputs
                text_inputs = modal.find_elements(
                    By.CSS_SELECTOR, self.selectors["text_input"]
                )
                for input_elem in text_inputs:
                    try:
                        field_type, confidence, value_path = self._identify_field_type(
                            input_elem
                        )
                        value = personal_details.get(field_type)

                        if value:
                            if input_elem.is_displayed() and input_elem.is_enabled():
                                self.driver.execute_script(
                                    "arguments[0].scrollIntoView({block: 'center'});",
                                    input_elem,
                                )
                                time.sleep(0.2)
                                input_elem.clear()
                                input_elem.send_keys(str(value))
                                print(f"     ✅ Filled {field_type} field")
                        else:
                            self._handle_unknown_field(input_elem, personal_details)
                    except StaleElementReferenceException:
                        self.logger.warning(f"Stale element on text input, will retry")
                        break  # Break inner loop to retry from outer loop
                    except Exception as e:
                        self.logger.error(f"Failed to fill text input: {e}")
                else:
                    # Inner loop completed without break (no stale elements)
                    # Continue with textareas, selects, file uploads
                    self._fill_textareas(modal, personal_details)
                    self._fill_selects(modal, personal_details)
                    self._fill_file_uploads(modal, personal_details)
                    return  # Success

                # If we broke out of the inner loop due to stale element, retry
                if attempt < max_retries:
                    self.logger.info(
                        f"Retrying form fill (attempt {attempt + 2}/{max_retries + 1})"
                    )
                    time.sleep(1)
                    continue

            except TimeoutException:
                print("     ⚠️ No modal found or form fields not accessible")
                return
            except StaleElementReferenceException:
                if attempt < max_retries:
                    self.logger.info(
                        f"Stale modal element, retrying (attempt {attempt + 2}/{max_retries + 1})"
                    )
                    time.sleep(1)
                    continue
                print("     ❌ Form elements kept going stale, giving up")
                return
            except Exception as e:
                print(f"     ❌ Error filling form: {e}")
                return

    def _fill_textareas(self, modal, personal_details: Dict):
        """Fill textarea fields within the modal."""
        textareas = modal.find_elements(By.CSS_SELECTOR, self.selectors["textarea"])
        for textarea in textareas:
            try:
                if textarea.is_displayed() and textarea.is_enabled():
                    cover_letter = personal_details.get("cover_letter", "")
                    if cover_letter and not textarea.get_attribute("value"):
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", textarea
                        )
                        time.sleep(0.2)
                        textarea.clear()
                        textarea.send_keys(cover_letter)
                        print("     ✅ Added cover letter")
            except StaleElementReferenceException:
                self.logger.warning("Stale element on textarea, skipping")
            except Exception as e:
                self.logger.error(f"Failed to fill textarea: {e}")

    def _fill_selects(self, modal, personal_details: Dict):
        """Fill select/dropdown fields within the modal."""
        selects = modal.find_elements(By.CSS_SELECTOR, self.selectors["select"])
        for select_elem in selects:
            try:
                if select_elem.is_displayed() and select_elem.is_enabled():
                    self._handle_select_field(select_elem, personal_details)
            except StaleElementReferenceException:
                self.logger.warning("Stale element on select, skipping")
            except Exception as e:
                self.logger.error(f"Failed to handle select: {e}")

    def _fill_file_uploads(self, modal, personal_details: Dict):
        """Handle file upload fields within the modal."""
        file_inputs = modal.find_elements(By.CSS_SELECTOR, self.selectors["file_input"])
        for file_input in file_inputs:
            try:
                if file_input.is_displayed():
                    resume_path = personal_details.get("resume_path")
                    if resume_path and os.path.exists(resume_path):
                        file_input.send_keys(os.path.abspath(resume_path))
                        print("     ✅ Uploaded resume")
                        time.sleep(2)
            except StaleElementReferenceException:
                self.logger.warning("Stale element on file input, skipping")
            except Exception as e:
                self.logger.error(f"Failed to upload file: {e}")

    def _identify_field_type(self, input_elem) -> tuple:
        """Identify the type of form field based on attributes and context.

        Returns:
            tuple: (field_type, confidence_level, suggested_value_path)
        """
        try:
            # Check various attributes to determine field type
            attrs_to_check = [
                input_elem.get_attribute("name") or "",
                input_elem.get_attribute("id") or "",
                input_elem.get_attribute("placeholder") or "",
                input_elem.get_attribute("aria-label") or "",
            ]

            # Get surrounding context
            label_text = self._get_field_label(input_elem).lower()
            combined_attrs = " ".join(attrs_to_check + [label_text]).lower()

            self.logger.info(f"Field detection: analyzing '{combined_attrs}' (confidence: high)")

            # Enhanced field detection with confidence levels

            # Basic contact information
            if any(keyword in combined_attrs for keyword in ["email", "e-mail"]):
                return "email", "high", "email"
            elif any(
                keyword in combined_attrs for keyword in ["phone", "mobile", "tel", "contact"]
            ):
                return "phone", "high", "phone"
            elif any(keyword in combined_attrs for keyword in ["first", "given", "fname"]):
                return "first_name", "high", "first_name"
            elif any(
                keyword in combined_attrs for keyword in ["last", "surname", "family", "lname"]
            ):
                return "last_name", "high", "last_name"
            elif (
                any(keyword in combined_attrs for keyword in ["full name", "name"])
                and "first" not in combined_attrs
                and "last" not in combined_attrs
            ):
                return "name", "high", "name"

            # Professional links
            elif any(keyword in combined_attrs for keyword in ["linkedin", "profile"]):
                return "linkedin", "high", "linkedin"
            elif any(
                keyword in combined_attrs for keyword in ["website", "portfolio", "github"]
            ):
                return "portfolio", "medium", "additional_info.portfolio_url"

            # Salary and compensation
            elif any(
                keyword in combined_attrs
                for keyword in [
                    "current ctc",
                    "current salary",
                    "current compensation",
                    "present salary",
                ]
            ):
                return "current_ctc", "high", "salary_and_compensation.current_ctc"
            elif any(
                keyword in combined_attrs
                for keyword in [
                    "expected ctc",
                    "expected salary",
                    "salary expectation",
                    "desired salary",
                ]
            ):
                return "expected_ctc", "high", "salary_and_compensation.expected_ctc"
            elif any(
                keyword in combined_attrs for keyword in ["minimum salary", "min salary"]
            ):
                return "minimum_salary", "high", "salary_and_compensation.minimum_salary"
            elif any(
                keyword in combined_attrs for keyword in ["maximum salary", "max salary"]
            ):
                return "maximum_salary", "high", "salary_and_compensation.maximum_salary"
            elif any(
                keyword in combined_attrs for keyword in ["hourly rate", "rate per hour"]
            ):
                return "hourly_rate", "medium", "salary_and_compensation.hourly_rate"

            # Work authorization
            elif any(
                keyword in combined_attrs
                for keyword in ["visa status", "work authorization", "legal authorization"]
            ):
                return "visa_status", "high", "work_authorization.visa_status"
            elif any(
                keyword in combined_attrs
                for keyword in ["sponsorship", "visa sponsorship", "work permit"]
            ):
                return (
                    "sponsorship_required",
                    "high",
                    "work_authorization.sponsorship_required",
                )
            elif any(
                keyword in combined_attrs
                for keyword in ["authorized to work", "eligible to work"]
            ):
                return (
                    "authorized_to_work",
                    "high",
                    "work_authorization.authorized_to_work",
                )

            # Availability and notice period
            elif any(
                keyword in combined_attrs
                for keyword in ["notice period", "notice", "availability"]
            ):
                return "notice_period", "high", "availability.notice_period"
            elif any(
                keyword in combined_attrs
                for keyword in ["start date", "joining date", "available from"]
            ):
                return "start_date", "medium", "availability.start_date"
            elif any(
                keyword in combined_attrs for keyword in ["immediate", "immediately available"]
            ):
                return "immediate_start", "medium", "availability.immediate_start"
            elif any(
                keyword in combined_attrs
                for keyword in ["relocate", "relocation", "willing to relocate"]
            ):
                return (
                    "willing_to_relocate",
                    "medium",
                    "availability.willing_to_relocate",
                )

            # Background and compliance
            elif any(
                keyword in combined_attrs
                for keyword in ["background check", "background screening"]
            ):
                return (
                    "background_check",
                    "medium",
                    "background_checks.background_check_consent",
                )
            elif any(
                keyword in combined_attrs for keyword in ["drug test", "drug screening"]
            ):
                return "drug_test", "medium", "background_checks.drug_test_consent"
            elif any(
                keyword in combined_attrs for keyword in ["criminal", "criminal background"]
            ):
                return (
                    "criminal_background",
                    "medium",
                    "background_checks.criminal_background",
                )

            # Additional work preferences
            elif any(keyword in combined_attrs for keyword in ["travel", "willing to travel"]):
                return "willing_to_travel", "medium", "additional_info.willing_to_travel"
            elif any(keyword in combined_attrs for keyword in ["overtime", "extra hours"]):
                return "overtime", "medium", "additional_info.overtime_willingness"
            elif any(
                keyword in combined_attrs
                for keyword in ["remote work", "work from home", "remote"]
            ):
                return (
                    "remote_preference",
                    "medium",
                    "availability.remote_work_preference",
                )

            # Experience and education
            elif any(
                keyword in combined_attrs
                for keyword in [
                    "years of experience",
                    "experience years",
                    "total experience",
                ]
            ):
                return "years_experience", "high", "years_experience"
            elif any(
                keyword in combined_attrs
                for keyword in ["education", "degree", "qualification"]
            ):
                return "education_level", "high", "education_level"

            # Open-ended questions
            elif any(
                keyword in combined_attrs for keyword in ["why interested", "why apply", "interest"]
            ):
                return "why_interested", "medium", "common_responses.why_interested"
            elif any(
                keyword in combined_attrs
                for keyword in ["why leaving", "reason for leaving", "career change"]
            ):
                return (
                    "why_leaving",
                    "medium",
                    "common_responses.why_leaving_current_job",
                )
            elif any(
                keyword in combined_attrs
                for keyword in ["career goal", "future goal", "aspiration"]
            ):
                return "career_goals", "medium", "common_responses.career_goals"
            elif any(keyword in combined_attrs for keyword in ["strength", "greatest strength"]):
                return "strength", "medium", "common_responses.greatest_strength"

            # Demographic information (handle carefully)
            elif any(keyword in combined_attrs for keyword in ["gender", "sex"]):
                return "gender", "low", "additional_info.gender"
            elif any(keyword in combined_attrs for keyword in ["ethnicity", "race"]):
                return "ethnicity", "low", "additional_info.ethnicity"
            elif any(keyword in combined_attrs for keyword in ["veteran", "military"]):
                return "veteran_status", "low", "additional_info.veteran_status"
            elif any(keyword in combined_attrs for keyword in ["disability", "disabled"]):
                return "disability", "low", "additional_info.disability_status"

            else:
                return "unknown", "low", None

        except Exception as e:
            self.logger.error(f"Form field error [text_input/field_detection]: {e}")
            return "unknown", "low", None

    def _handle_select_field(self, select_elem, personal_details: Dict):
        """Handle dropdown selection intelligently."""
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", select_elem
            )
            time.sleep(0.2)
            select = Select(select_elem)
            options = [opt.text.lower() for opt in select.options]

            # Get context from nearby labels
            label_text = self._get_field_label(select_elem).lower()

            # Make intelligent selections based on field context
            if "experience" in label_text or "years" in label_text:
                experience = personal_details.get("years_experience", "3")
                # Try to match experience options
                for option in select.options:
                    if str(experience) in option.text or "mid" in option.text.lower():
                        select.select_by_visible_text(option.text)
                        print(f"     ✅ Selected experience: {option.text}")
                        break

            elif "education" in label_text or "degree" in label_text:
                degree = personal_details.get("education_level", "bachelor")
                for option in select.options:
                    if degree.lower() in option.text.lower():
                        select.select_by_visible_text(option.text)
                        print(f"     ✅ Selected education: {option.text}")
                        break

            elif "country" in label_text or "location" in label_text:
                location = personal_details.get("country", "India")
                for option in select.options:
                    if location.lower() in option.text.lower():
                        select.select_by_visible_text(option.text)
                        print(f"     ✅ Selected location: {option.text}")
                        break

            # Default: select the second option (skip "Please select")
            else:
                if len(select.options) > 1:
                    select.select_by_index(1)
                    print(f"     ✅ Made default selection: {select.options[1].text}")

        except Exception as e:
            self.logger.error(f"Failed to handle select field: {e}")

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

    def _click_next_or_submit(self) -> bool:
        """Click next button or submit application."""
        try:
            # Try to find and click next/continue button
            try:
                next_btn = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(text(), 'Next') or contains(text(), 'Continue') or contains(@aria-label, 'Continue')]",
                )
                if next_btn.is_enabled():
                    next_btn.click()
                    time.sleep(2)
                    return True
            except NoSuchElementException:
                pass

            # Try to find and click review button
            try:
                review_btn = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(text(), 'Review') or contains(@aria-label, 'Review')]",
                )
                if review_btn.is_enabled():
                    review_btn.click()
                    time.sleep(2)
                    return True
            except NoSuchElementException:
                pass

            # Try to find and click submit button
            try:
                submit_btn = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(text(), 'Submit') or contains(@aria-label, 'Submit')]",
                )
                if submit_btn.is_enabled():
                    print("     ⚠️ Submitting application...")
                    submit_btn.click()
                    time.sleep(3)
                    return True
            except NoSuchElementException:
                pass

            print("     ❌ No next/submit button found")
            return False

        except Exception as e:
            print(f"     ❌ Error clicking next/submit: {e}")
            return False

    def _check_application_success(self) -> bool:
        """Check if application was successfully submitted."""
        if self._check_application_success_transformer():
            return True
        try:
            # Look for success message
            success_indicators = [
                "application submitted",
                "successfully applied",
                "thank you for applying",
                "application received",
            ]

            page_text = self.driver.page_source.lower()
            return any(indicator in page_text for indicator in success_indicators)

        except:
            return False

    def _check_application_success_transformer(self) -> bool:
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

    def _extract_full_job_description(self, job_info: Dict) -> Dict:
        """
        Extract full job description from the job page for resume customization.

        Args:
            job_info: Job information dictionary

        Returns:
            Updated job_info with description and requirements
        """
        try:
            # Try multiple selectors for job description
            description_selectors = [
                ".jobs-description-content__text",
                ".jobs-description__content",
                ".description",
                ".job-description",
                '[data-test-id="job-description"]',
                ".jobs-box--fadeable",
            ]

            description = ""
            for selector in description_selectors:
                try:
                    desc_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    description = desc_element.text.strip()
                    if len(description) > 100:  # Reasonable minimum length
                        break
                except NoSuchElementException:
                    continue

            if not description:
                # Fallback: get main content from body
                try:
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text
                    # Extract a reasonable portion that might contain job description
                    lines = body_text.split("\n")
                    description_lines = []
                    collecting = False

                    for line in lines:
                        line = line.strip()
                        if any(
                            keyword in line.lower()
                            for keyword in [
                                "about the role",
                                "job description",
                                "responsibilities",
                                "requirements",
                            ]
                        ):
                            collecting = True
                        if collecting and line:
                            description_lines.append(line)
                        if len(description_lines) > 20:  # Don't collect too much
                            break

                    description = "\n".join(description_lines)
                except:
                    pass

            job_info["description"] = description

            # Extract requirements/skills from description
            requirements = self._extract_requirements_from_text(description)
            job_info["requirements"] = requirements

            return job_info

        except Exception as e:
            self.logger.warning(f"Failed to extract job description: {e}")
            job_info["description"] = job_info.get("description", "")
            job_info["requirements"] = job_info.get("requirements", [])
            return job_info

    def _extract_requirements_from_text(self, text: str) -> List[str]:
        """
        Extract skills and requirements from job description text.

        Args:
            text: Job description text

        Returns:
            List of identified requirements/skills
        """
        requirements = []
        text_lower = text.lower()

        # Common technical skills and requirements keywords
        skill_keywords = [
            # Programming languages
            "python",
            "java",
            "javascript",
            "typescript",
            "c++",
            "c#",
            "go",
            "rust",
            "php",
            "ruby",
            # Web technologies
            "react",
            "angular",
            "vue",
            "node.js",
            "express",
            "django",
            "flask",
            "spring",
            "laravel",
            # Databases
            "sql",
            "mysql",
            "postgresql",
            "mongodb",
            "redis",
            "elasticsearch",
            # Cloud & DevOps
            "aws",
            "azure",
            "gcp",
            "docker",
            "kubernetes",
            "jenkins",
            "terraform",
            "ansible",
            # Data & AI
            "machine learning",
            "ai",
            "deep learning",
            "tensorflow",
            "pytorch",
            "pandas",
            "numpy",
            # Mobile
            "ios",
            "android",
            "react native",
            "flutter",
            "kotlin",
            "swift",
            # Other
            "git",
            "agile",
            "scrum",
            "rest api",
            "graphql",
            "microservices",
        ]

        for keyword in skill_keywords:
            if keyword in text_lower:
                requirements.append(keyword)

        # Experience requirements
        import re

        exp_pattern = r"(\d+)\+?\s*years?\s*(of\s*)?experience"
        exp_matches = re.findall(exp_pattern, text_lower)
        if exp_matches:
            years = exp_matches[0][0]
            requirements.append(f"{years} years experience")

        # Education requirements
        education_keywords = [
            "bachelor",
            "master",
 "phd",
 "degree",
 "computer science",
 "engineering",
 ]
        for keyword in education_keywords:
            if keyword in text_lower:
                requirements.append(keyword)

        return list(set(requirements)) # Remove duplicates

    def _generate_custom_resume(
        self, job_info: Dict, personal_details: Dict
    ) -> Optional[str]:
        """
        Generate a custom resume for the specific job.

        Args:
            job_info: Job information dictionary
            personal_details: Personal details for resume

        Returns:
            Path to generated resume file, or None if generation failed
        """
        try:
            # Create a safe filename for the resume
            import re

            job_title_safe = re.sub(r"[^a-zA-Z0-9\s-]", "", job_info.get("title", "job"))
            company_safe = re.sub(
                r"[^a-zA-Z0-9\s-]", "", job_info.get("company", "company")
            )
            filename = f"{job_title_safe}_{company_safe}_resume.pdf"
            filename = re.sub(r"\s+", "_", filename)  # Replace spaces with underscores

            resume_path = os.path.join(self.generated_resumes_dir, filename)

            # Prepare job details for resume modification
            job_details = {
                "title": job_info.get("title", ""),
                "company": job_info.get("company", ""),
                "location": job_info.get("location", ""),
                "description": job_info.get("description", ""),
                "requirements": job_info.get("requirements", []),
                "url": job_info.get("url", ""),
            }

            # Generate the custom resume
            resume_path = self.resume_modifier.modify_resume(
                job_details=job_details, personal_details=personal_details
            )

            if os.path.exists(resume_path):
                return resume_path
            else:
                self.logger.warning("Resume generation failed")
                return None

        except Exception as e:
            self.logger.error(f"Error generating custom resume: {e}")
            return None

    def bulk_apply_easy_jobs(
        self,
        job_title: str,
        personal_details: Dict,
        location: str = "",
        max_applications: int = 10,
    ):
        """
        Search for and apply to multiple Easy Apply jobs.

        Args:
            job_title: Job title to search for
            personal_details: Personal details for applications
            location: Location filter
            max_applications: Maximum number of applications to submit
        """
        print(f"🚀 Starting bulk Easy Apply for '{job_title}' jobs")

        # Search for jobs
        jobs = self.search_easy_apply_jobs(
            job_title, location, max_applications * 2
        )  # Get more than needed

        if not jobs:
            print("❌ No jobs found")
            return

        # Filter Easy Apply jobs
        easy_apply_jobs = [job for job in jobs if job.get("easy_apply", False)]

        if not easy_apply_jobs:
            print("❌ No Easy Apply jobs found")
            return

        print(
            f"📋 Found {len(easy_apply_jobs)} Easy Apply jobs, applying to up to {max_applications}"
        )

        successful_applications = 0

        for i, job in enumerate(easy_apply_jobs[:max_applications]):
            print(
                f"\n📌 Application {i+1}/{min(len(easy_apply_jobs), max_applications)}"
            )

            if self.apply_to_job(job, personal_details):
                successful_applications += 1
                print(f"   ✅ Successfully applied!")
            else:
                print(f"   ❌ Application failed")

            # Small delay between applications
            if i < len(easy_apply_jobs) - 1:
                time.sleep(3)

        print(f"\n🎉 Bulk application complete!")
        print(
            f"   ✅ Successful applications: {successful_applications}/{min(len(easy_apply_jobs), max_applications)}"
        )

    def close(self):
        """Clean up and close browser."""
        if self.driver:
            self.driver.quit()


if __name__ == "__main__":
    # Example usage
    print("LinkedIn Easy Apply Automation")
    print("=" * 40)

    # Sample personal details
    personal_details = {
        "name": "Your Name",
        "first_name": "Your",
        "last_name": "Name",
        "email": "your.email@example.com",
        "phone": "+1234567890",
        "linkedin": "https://linkedin.com/in/yourprofile",
        "years_experience": "3",
        "education_level": "bachelor",
        "country": "India",
        "resume_path": "/path/to/your/resume.pdf",
        "cover_letter": "I am excited to apply for this position...",
    }

    linkedin = LinkedInEasyApply()

    try:
        linkedin.setup_driver(headless=False)  # Set to True for headless mode

        if linkedin.load_cookies():
            linkedin.bulk_apply_easy_jobs(
                job_title="Software Engineer",
                personal_details=personal_details,
                location="Bangalore",
                max_applications=5,
            )
        else:
            print("❌ Authentication failed. Please check your cookie file.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        linkedin.close()
