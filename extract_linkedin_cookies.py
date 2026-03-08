#!/usr/bin/env python3
"""
LinkedIn Cookie Extractor Helper

This script helps you extract LinkedIn cookies from your browser for authentication.
Run this after logging into LinkedIn in your browser.
"""

import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def extract_cookies_from_browser():
    """Extract cookies by opening LinkedIn in automated browser."""
    print("🔐 LinkedIn Cookie Extractor")
    print("=" * 40)
    print("This will open LinkedIn in a browser window.")
    print("Please log in manually, then press Enter here to extract cookies.")
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.binary_location = "/usr/bin/chromium-browser"
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = None
    try:
        # Create driver
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to LinkedIn
        print("🌐 Opening LinkedIn...")
        driver.get("https://www.linkedin.com/login")
        
        # Wait for user to log in
        print("\n📝 Please complete these steps:")
        print("1. Log in to LinkedIn in the opened browser window")
        print("2. Make sure you can see your LinkedIn home page")
        print("3. Come back here and press Enter")
        
        input("\nPress Enter after you've logged in to LinkedIn...")
        
        # Extract cookies
        print("🍪 Extracting cookies...")
        cookies = driver.get_cookies()
        
        # Filter important LinkedIn cookies
        important_cookies = []
        important_cookie_names = [
            'li_at', 'JSESSIONID', 'liap', 'li_mc', 'li_rm', 'lms_ads', 'lms_analytics', 
            'UserMatchHistory', 'AnalyticsSyncHistory', 'li_sugr', 'dfpfpt', 'li_gc',
            'timezone', 'lang', 'li_theme', 'li_theme_set'
        ]
        
        for cookie in cookies:
            # Include all LinkedIn cookies to be safe
            if '.linkedin.com' in cookie.get('domain', '') or cookie.get('name', '') in important_cookie_names:
                important_cookies.append(cookie)
        
        if important_cookies:
            # Save cookies to file
            cookies_file = "linkedin_cookies.json"
            with open(cookies_file, 'w') as f:
                json.dump(important_cookies, f, indent=2)
            
            print(f"✅ Successfully extracted {len(important_cookies)} cookies")
            print(f"💾 Saved to: {cookies_file}")
            
            # Show cookie info
            print(f"\n📊 Cookie Summary:")
            for cookie in important_cookies[:5]:  # Show first 5
                print(f"   • {cookie['name']}: {'*' * min(len(cookie['value']), 20)}")
            if len(important_cookies) > 5:
                print(f"   • ... and {len(important_cookies) - 5} more")
            
            print(f"\n✅ Cookie extraction complete!")
            print(f"You can now run the LinkedIn automation script.")
            return True
        else:
            print("❌ No LinkedIn cookies found. Make sure you're logged in.")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if driver:
            print("🔒 Closing browser...")
            driver.quit()

def create_sample_personal_details():
    """Create a sample personal details file."""
    personal_details = {
        "name": "Your Full Name",
        "first_name": "Your",
        "last_name": "Name",
        "email": "your.email@example.com",
        "phone": "+1234567890",
        "linkedin": "https://linkedin.com/in/yourprofile",
        "years_experience": "3",
        "education_level": "bachelor",
        "country": "India",
        "resume_path": "/path/to/your/resume.pdf",
        "cover_letter": "I am excited to apply for this position and believe my skills and experience make me a strong candidate. I look forward to contributing to your team."
    }
    
    filename = "linkedin_personal_details.json"
    with open(filename, 'w') as f:
        json.dump(personal_details, f, indent=2)
    
    print(f"📝 Created sample personal details file: {filename}")
    print("Please edit this file with your actual information before running the automation.")

if __name__ == "__main__":
    print("LinkedIn Easy Apply Setup")
    print("=" * 30)
    
    print("Choose an option:")
    print("1. Extract cookies from browser (requires manual login)")
    print("2. Create sample personal details file")
    print("3. Both")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice in ['1', '3']:
        print("\n" + "=" * 50)
        extract_cookies_from_browser()
    
    if choice in ['2', '3']:
        print("\n" + "=" * 50)
        create_sample_personal_details()
    
    print("\n🎉 Setup complete!")
    print("Next steps:")
    print("1. Edit 'linkedin_personal_details.json' with your information")
    print("2. Update the resume path to point to your actual resume file")
    print("3. Run: python3 linkedin_automation.py")
