# main.py - Main orchestrator for job application automation
import os
import json
import pandas as pd
from datetime import datetime
import logging
from typing import Dict, List, Optional
import time

# Import custom modules
from job_scraper import JobScraper
from resume_modifier import ResumeModifier  
from application_tracker import ApplicationTracker
from browser_automation import BrowserAutomation
from job_matcher import JobMatcher
from naukri_scraper import NaukriScraper
from naukri_automation import NaukriAutomation

class JobApplicationBot:
    def __init__(self, config_file: str = "config.json"):
        """Initialize the job application bot with configuration."""
        self.setup_logging()
        self.config = self.load_config(config_file)
        self.personal_details = self.load_personal_details()
        self.job_tracker = ApplicationTracker()
        self.job_scraper = JobScraper()
        self.resume_modifier = ResumeModifier()
        self.browser_automation = BrowserAutomation()
        self.job_matcher = JobMatcher(self.config.get('preferred_jobs', []))
        
        # Naukri.com modules (shared scraper session)
        self.naukri_scraper = NaukriScraper()
        self.naukri_automation = NaukriAutomation(
            self.naukri_scraper, self.job_matcher, self.job_tracker
        )
        self.naukri_config = self.config.get('naukri', {})
        
    def setup_logging(self):
        """Setup logging for debugging purposes."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('job_application.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.show_error_popup(f"Configuration file {config_file} not found!")
            return {}
    
    def load_personal_details(self) -> Dict:
        """Load personal details from file."""
        try:
            details_file = self.config.get('personal_details_file', 'personal_details.json')
            with open(details_file, 'r') as f:
                details = json.load(f)
            
            # Load and merge custom details if available
            if os.path.exists("custom_details.json"):
                try:
                    with open("custom_details.json", 'r') as f:
                        custom_details = json.load(f)
                    details.update(custom_details)
                    self.logger.info("Loaded and merged custom details")
                except json.JSONDecodeError:
                    self.logger.warning("Could not decode custom_details.json")
            
            return details
        except FileNotFoundError:
            self.show_error_popup(f"Personal details file not found!")
            return {}
    
    def show_error_popup(self, message: str):
        """Show error popup and pause execution."""
        print(f"\n{'='*50}")
        print(f"ERROR: {message}")
        print("Please fix the issue and press Enter to continue...")
        print(f"{'='*50}")
        input()
    
    def _is_naukri_url(self, url: str) -> bool:
        """Returns True if the URL belongs to Naukri.com."""
        return 'naukri.com' in url.lower()

    def apply_for_job(self, job_url: str) -> bool:
        """Main function to apply for a single job.
        
        Automatically detects Naukri.com URLs and routes them through
        the Naukri-specific pipeline.
        """
        # Auto-detect Naukri URLs
        if self._is_naukri_url(job_url):
            return self._apply_naukri_single(job_url)

        try:
            self.logger.info(f"Starting application process for: {job_url}")
            
            # Step 1: Scrape job details
            job_details = self.job_scraper.scrape_job(job_url)
            if not job_details:
                self.show_error_popup("Failed to scrape job details")
                return False
            
            # Step 2: Check if job matches preferences
            if not self.job_matcher.match_job(job_details):
                self.logger.info("Job doesn't match preferences, skipping...")
                return False
            
            # Step 3: Modify resume for this job
            modified_resume_path = self.resume_modifier.modify_resume(
                job_details, self.personal_details
            )
            if not modified_resume_path:
                self.show_error_popup("Failed to modify resume")
                return False
            
            # Step 4: Fill application form
            application_success = self.browser_automation.fill_application(
                job_url, job_details, self.personal_details, modified_resume_path
            )
            
            if not application_success:
                self.show_error_popup("Failed to submit application")
                return False
            
            # Step 5: Track the application
            self.job_tracker.add_application(job_url, job_details)
            
            self.logger.info("Successfully applied for job!")
            return True
            
        except Exception as e:
            self.show_error_popup(f"Unexpected error: {str(e)}")
            return False
    
    def bulk_apply(self, job_urls: List[str]):
        """Apply for multiple jobs."""
        successful_applications = 0
        for url in job_urls:
            if self.apply_for_job(url):
                successful_applications += 1
            time.sleep(2)  # Rate limiting
        
        print(f"Applied to {successful_applications}/{len(job_urls)} jobs successfully")

    # ------------------------------------------------------------------
    # Naukri-specific methods
    # ------------------------------------------------------------------

    def naukri_login(self) -> bool:
        """Logs in to Naukri.com using credentials from config or user input."""
        email = self.naukri_config.get('email', '')
        password = self.naukri_config.get('password', '')

        if not email:
            email = input("Enter Naukri email / username: ").strip()
        if not password:
            import getpass
            password = getpass.getpass("Enter Naukri password: ")

        return self.naukri_scraper.login(email, password)

    def _apply_naukri_single(self, job_url: str) -> bool:
        """Applies to a single job via the Naukri pipeline.
        
        Ensures the user is logged in first, then delegates to
        NaukriAutomation.apply_to_job.
        """
        if not self.naukri_scraper.logged_in:
            print("You must log in to Naukri first.")
            if not self.naukri_login():
                return False
        return self.naukri_automation.apply_to_job(job_url, self.personal_details)

    def naukri_search_and_apply(self):
        """Interactive prompt for Naukri search-and-apply.
        
        Asks the user for search keywords, location, experience, and
        max applications, then runs the search → match → apply pipeline.
        """
        if not self.naukri_scraper.logged_in:
            print("You must log in to Naukri first.")
            if not self.naukri_login():
                return

        keywords = input("Enter search keywords (e.g. 'python developer'): ").strip()
        if not keywords:
            # Fall back to config keywords
            kw_list = self.naukri_config.get('search_keywords',
                                            self.config.get('preferred_jobs', []))
            keywords = ', '.join(kw_list) if kw_list else 'software engineer'
            print(f"Using keywords from config: {keywords}")

        location = input("Enter location (blank for any): ").strip()
        if not location:
            locations = self.naukri_config.get('search_locations', [])
            location = locations[0] if locations else ''

        experience = input("Enter experience in years (blank for any): ").strip()
        if not experience:
            experience = self.naukri_config.get('experience_years', '')

        max_apps_str = input("Max applications this session (default 20): ").strip()
        max_apps = int(max_apps_str) if max_apps_str.isdigit() else 20

        self.naukri_automation.search_and_apply(
            keywords=keywords, personal_details=self.personal_details, location=location,
            experience=experience, max_applications=max_apps
        )

    def naukri_update_resume(self):
        """Uploads a resume to the user's Naukri profile."""
        if not self.naukri_scraper.logged_in:
            print("You must log in to Naukri first.")
            if not self.naukri_login():
                return

        path = input("Enter path to resume PDF: ").strip()
        if path and os.path.exists(path):
            self.naukri_automation.update_profile_resume(path)
        else:
            print("File not found!")

# Configuration templates
config_template = {
    "personal_details_file": "personal_details.json",
    "preferred_jobs": [
        "software engineer",
        "python developer", 
        "data scientist",
        "full stack developer",
        "backend developer"
    ],
    "excluded_companies": [],
    "min_salary": 0,
    "preferred_locations": ["Remote", "New York", "San Francisco"],
    "experience_level": ["Mid-level", "Senior"],
    "naukri": {
        "email": "",
        "password": "",
        "search_keywords": ["python developer", "software engineer"],
        "search_locations": ["Bangalore", "Remote"],
        "experience_years": "3",
        "max_applications_per_session": 20
    }
}

personal_details_template = {
    "name": "Your Full Name",
    "email": "your.email@example.com",
    "phone": "+1234567890",
    "location": "Your City, State",
    "linkedin": "https://linkedin.com/in/yourprofile",
    "summary": "Experienced software engineer with expertise in full-stack development",
    "core_skills": ["Python", "JavaScript", "React", "SQL", "AWS"],
    "skills": [
        "Python", "JavaScript", "React", "Node.js", "SQL", "MongoDB",
        "AWS", "Docker", "Kubernetes", "Git", "Machine Learning", "APIs"
    ],
    "experience": [
        {
            "title": "Software Engineer",
            "company": "Tech Company Inc",
            "duration": "2020 - Present",
            "bullets": [
                "Developed scalable web applications using Python and React",
                "Improved system performance by 40% through optimization",
                "Led a team of 3 developers on key projects"
            ]
        }
    ],
    "education": [
        {
            "degree": "Bachelor of Science in Computer Science",
            "school": "University Name",
            "year": "2020"
        }
    ]
}

if __name__ == "__main__":
    # Create configuration files if they don't exist
    if not os.path.exists('config.json'):
        with open('config.json', 'w') as f:
            json.dump(config_template, f, indent=4)
        print("Created config.json template - please customize it!")
    
    if not os.path.exists('personal_details.json'):
        with open('personal_details.json', 'w') as f:
            json.dump(personal_details_template, f, indent=4)
        print("Created personal_details.json template - please fill in your details!")
    
    # Initialize the bot
    bot = JobApplicationBot()
    
    # Interactive mode
    while True:
        print("\n" + "="*50)
        print("Job Application Bot")
        print("="*50)
        print("--- General ---")
        print("1. Apply for single job (enter URL)")
        print("2. Apply for multiple jobs (enter file with URLs)")
        print("3. View application statistics")
        print("--- Naukri.com ---")
        print("5. Naukri: Login")
        print("6. Naukri: Apply for single job (enter URL)")
        print("7. Naukri: Search & Auto-Apply")
        print("8. Naukri: Update profile resume")
        print("---")
        print("9. Exit")
        
        choice = input("Select option: ").strip()
        
        if choice == "1":
            url = input("Enter job URL: ").strip()
            if url:
                bot.apply_for_job(url)
        
        elif choice == "2":
            file_path = input("Enter file path with job URLs: ").strip()
            try:
                with open(file_path, 'r') as f:
                    urls = [line.strip() for line in f if line.strip()]
                bot.bulk_apply(urls)
            except FileNotFoundError:
                print("File not found!")
        
        elif choice == "3":
            stats = bot.job_tracker.get_application_stats()
            print(f"Total applications: {stats['total_applications']}")
            print(f"Applications this week: {stats['applications_this_week']}")
            print(f"Unique companies: {stats['unique_companies']}")
        
        elif choice == "5":
            bot.naukri_login()
        
        elif choice == "6":
            url = input("Enter Naukri job URL: ").strip()
            if url:
                bot._apply_naukri_single(url)
        
        elif choice == "7":
            bot.naukri_search_and_apply()
        
        elif choice == "8":
            bot.naukri_update_resume()
        
        elif choice == "9":
            break
        
        else:
            print("Invalid choice!")
