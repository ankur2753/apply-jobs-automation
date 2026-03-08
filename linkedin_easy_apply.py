#!/usr/bin/env python3
"""
LinkedIn Easy Apply Main Runner

This is the main script to run LinkedIn Easy Apply automation.
It uses the specialized LinkedIn automation class with cookie authentication.
"""

import json
import os
import sys
from linkedin_automation import LinkedInEasyApply

def load_personal_details(filename="personal_details.json"):
    """Load personal details from JSON file (same format as resume_modifier)."""
    if not os.path.exists(filename):
        print(f"❌ Personal details file '{filename}' not found!")
        print("Please create the file with your information in the same format as used by resume_modifier.py")
        return None
    
    try:
        with open(filename, 'r') as f:
            details = json.load(f)
        
        # Load and merge custom details if available
        if os.path.exists("custom_details.json"):
            try:
                with open("custom_details.json", 'r') as f:
                    custom_details = json.load(f)
                details.update(custom_details)
                print("✅ Loaded and merged custom details")
            except json.JSONDecodeError:
                print("⚠️ Could not decode custom_details.json")

        # Validate required fields for LinkedIn applications
        required_fields = ['name', 'email', 'phone']
        missing_fields = [field for field in required_fields if not details.get(field)]
        
        if missing_fields:
            print(f"❌ Please update these fields in {filename} or custom_details.json: {', '.join(missing_fields)}")
            return None
        
        # Add derived fields that LinkedIn forms might need
        if details.get('name'):
            name_parts = details['name'].split()
            details['first_name'] = name_parts[0] if name_parts else ''
            details['last_name'] = name_parts[-1] if len(name_parts) > 1 else ''
        
        # Add phone with country code if available
        if details.get('country_code') and details.get('phone'):
            details['full_phone'] = f"{details['country_code']}{details['phone']}"
        else:
            details['full_phone'] = details.get('phone', '')
        
        # Set default values for LinkedIn application fields if not present
        defaults = {
            'years_experience': '2',  # Based on the experience in the JSON
            'education_level': 'bachelor',
            'country': 'India',
            'cover_letter': 'I am excited to apply for this position and contribute to your team with my technical skills and experience.'
        }
        
        for field, default_value in defaults.items():
            if field not in details:
                details[field] = default_value
        print(f"✅ Loaded personal details from {filename}")
        return details
        
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in {filename}")
        return None

def interactive_job_search():
    """Interactive job search and application."""
    print("🚀 LinkedIn Easy Apply - Interactive Mode")
    print("=" * 50)

    # Load personal details
    personal_details = load_personal_details()
    if not personal_details:
        return
    
    # Get job search parameters
    
    try:
        with open('config.json', 'r') as f:
                prefrences  = json.load(f)
    except FileNotFoundError:
        print(f"Configuration file not found!")

    if not prefrences:
        location = input("Enter location (optional, e.g., 'Bangalore'): ").strip()
        job_title = input("Enter job title to search for (e.g., 'Software Engineer'): ").strip()
        if not job_title:
            print("❌ Job title is required")
            return
    else:
        location = prefrences.get('preferred_locations', '')[0]
        job_title = prefrences.get('preferred_jobs', '')[0]
    print(f"\n🔍 Searching for jobs: '{job_title}' in '{location or 'Any'}' location")

    try:
        max_apps = int(input("Maximum number of applications (default 5): ").strip() or "5")
    except ValueError:
        max_apps = 5
    
    print(f"\n📋 Job Search Parameters:")
    print(f"   Job Title: {job_title}")
    print(f"   Location: {location or 'Any'}")
    print(f"   Max Applications: {max_apps}")
    print(f"   Personal Profile: {personal_details['name']} ({personal_details['email']})")
    
    confirm = input("\nProceed with job search and applications? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Cancelled by user")
        return
    
    # Run automation
    linkedin = LinkedInEasyApply()
    
    try:
        print("\n🔧 Setting up browser...")
        linkedin.setup_driver(headless=False)  # Visual mode for monitoring
        
        print("🔐 Authenticating with LinkedIn...")
        if not linkedin.load_cookies():
            print("❌ Authentication failed. Please run cookie extraction first:")
            print("   python3 extract_linkedin_cookies.py")
            return
        
        print("🎯 Starting job search and applications...")
        linkedin.bulk_apply_easy_jobs(
            job_title=job_title,
            personal_details=personal_details,
            location=location,
            max_applications=max_apps
        )
        
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("🔒 Closing browser...")
        linkedin.close()

def batch_mode():
    """Batch mode for multiple job searches."""
    print("🔄 LinkedIn Easy Apply - Batch Mode")
    print("=" * 50)
    
    # Load personal details
    personal_details = load_personal_details()
    if not personal_details:
        return
    
    # Define job searches
    job_searches = [
        {"title": "Software Engineer", "location": "Bangalore", "max_apps": 3},
        {"title": "Full Stack Developer", "location": "Mumbai", "max_apps": 3},
        {"title": "Python Developer", "location": "Remote", "max_apps": 2},
    ]
    
    print("📋 Planned job searches:")
    for i, search in enumerate(job_searches, 1):
        print(f"   {i}. {search['title']} in {search['location']} (max {search['max_apps']})")
    
    total_apps = sum(search['max_apps'] for search in job_searches)
    print(f"\nTotal maximum applications: {total_apps}")
    
    confirm = input("Proceed with batch job applications? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Cancelled by user")
        return
    
    # Run automation
    linkedin = LinkedInEasyApply()
    
    try:
        print("\n🔧 Setting up browser...")
        linkedin.setup_driver(headless=False)
        
        print("🔐 Authenticating with LinkedIn...")
        if not linkedin.load_cookies():
            print("❌ Authentication failed.")
            return
        
        total_successful = 0
        
        for i, search in enumerate(job_searches, 1):
            print(f"\n🎯 Job search {i}/{len(job_searches)}: {search['title']}")
            
            # Run job search and applications
            jobs = linkedin.search_easy_apply_jobs(
                job_title=search['title'],
                location=search['location'],
                limit=search['max_apps'] * 2
            )
            
            if jobs:
                # Apply to jobs
                easy_apply_jobs = [job for job in jobs if job.get('easy_apply', False)][:search['max_apps']]
                
                for job in easy_apply_jobs:
                    if linkedin.apply_to_job(job, personal_details):
                        total_successful += 1
            
            # Short delay between searches
            if i < len(job_searches):
                import time
                time.sleep(5)
        
        print(f"\n🎉 Batch processing complete!")
        print(f"Total successful applications: {total_successful}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        linkedin.close()

def main():
    """Main menu and runner."""
    print("LinkedIn Easy Apply Automation")
    print("=" * 40)
    print("Specialized automation for LinkedIn Easy Apply jobs")
    print("=" * 40)
    
    # Check prerequisites
    if not os.path.exists("linkedin_cookies.json"):
        print("⚠️ LinkedIn cookies not found!")
        print("Please run setup first: python3 extract_linkedin_cookies.py")
        return
    
    if not os.path.exists("personal_details.json"):
        print("⚠️ Personal details not found!")
        print("Please create personal_details.json with your information (same format as used by resume_modifier.py)")
        return
    
    print("Choose mode:")
    print("1. Interactive job search")
    print("2. Batch mode (multiple searches)")
    print("3. Test authentication only")
    print("4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        interactive_job_search()
    elif choice == "2":
        batch_mode()
    elif choice == "3":
        test_authentication()
    elif choice == "4":
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")

def test_authentication():
    """Test LinkedIn authentication only."""
    print("🔐 Testing LinkedIn Authentication")
    print("=" * 40)
    
    linkedin = LinkedInEasyApply()
    
    try:
        linkedin.setup_driver(headless=False)
        
        if linkedin.load_cookies():
            print("✅ Authentication successful!")
            print("Navigating to LinkedIn jobs page...")
            linkedin.driver.get("https://www.linkedin.com/jobs/")
            
            print("Browser will stay open for 10 seconds for you to verify...")
            import time
            time.sleep(10)
        else:
            print("❌ Authentication failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        linkedin.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
