#!/usr/bin/env python3
"""
Non-interactive LinkedIn Easy Apply runner.
Bypasses the menu and runs the automation directly.
"""

import json
import os
import sys
from linkedin_automation import LinkedInEasyApply

def load_personal_details(filename="personal_details.json"):
    with open(filename, 'r') as f:
        details = json.load(f)
    
    # Derived fields
    if details.get('name'):
        name_parts = details['name'].split()
        details['first_name'] = name_parts[0] if name_parts else ''
        details['last_name'] = name_parts[-1] if len(name_parts) > 1 else ''
    
    if details.get('country_code') and details.get('phone'):
        details['full_phone'] = f"{details['country_code']}{details['phone']}"
    else:
        details['full_phone'] = details.get('phone', '')
    
    defaults = {
        'years_experience': '2',
        'education_level': 'bachelor',
        'country': 'India',
        'cover_letter': 'I am excited to apply for this position and contribute to your team with my technical skills and experience.'
    }
    for field, default_value in defaults.items():
        if field not in details:
            details[field] = default_value
    
    return details

def main():
    # Load config and personal details
    with open('config.json', 'r') as f:
        preferences = json.load(f)
    
    personal_details = load_personal_details()
    
    location = preferences.get('preferred_locations', [''])[0]
    job_title = preferences.get('preferred_jobs', ['Software Engineer'])[0]
    max_apps = 5

    print(f"Job Title: {job_title}")
    print(f"Location: {location}")
    print(f"Max Applications: {max_apps}")
    print(f"Profile: {personal_details['name']} ({personal_details['email']})")
    print()

    linkedin = LinkedInEasyApply()

    try:
        print("Setting up browser...")
        linkedin.setup_driver(headless=False)

        print("Authenticating with LinkedIn...")
        if not linkedin.load_cookies():
            print("Authentication failed. Run: python3 extract_linkedin_cookies.py")
            sys.exit(1)

        print("Starting job search and applications...")
        linkedin.bulk_apply_easy_jobs(
            job_title=job_title,
            personal_details=personal_details,
            location=location,
            max_applications=max_apps
        )

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Closing browser...")
        linkedin.close()

if __name__ == "__main__":
    main()
