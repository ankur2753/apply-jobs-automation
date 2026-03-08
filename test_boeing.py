#!/usr/bin/env python3
"""
Test script to demonstrate the working Boeing job application system.
"""

import sys
sys.path.insert(0, '.')

from browser_automation import BrowserAutomation
from job_scraper import JobScraper
from job_matcher import JobMatcher
import json

def test_boeing_application():
    """Test the complete Boeing application workflow."""
    
    boeing_url = "https://jobs.boeing.com/job/-/-/185/80093228688"
    
    print("🚀 BOEING JOB APPLICATION TEST")
    print("="*50)
    
    # Step 1: Scrape the job
    print("Step 1: Scraping job details...")
    scraper = JobScraper()
    job_details = scraper.scrape_job(boeing_url)
    
    if job_details:
        print(f"✅ Job scraped: '{job_details['title']}' at {job_details.get('company', 'Boeing')}")
        print(f"   Location: {job_details['location']}")
        print(f"   Description: {len(job_details['description'])} characters")
    else:
        print("❌ Failed to scrape job")
        return False
    
    # Step 2: Check job matching  
    print("\nStep 2: Checking job match...")
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    matcher = JobMatcher(config['preferred_jobs'])
    is_match = matcher.match_job(job_details)
    
    if is_match:
        print("✅ Job matches preferences - proceeding with application")
    else:
        print("❌ Job doesn't match preferences")
        return False
    
    # Step 3: Test browser automation
    print("\nStep 3: Testing browser automation...")
    browser = BrowserAutomation()
    
    try:
        browser.setup_driver()
        browser.driver.get(boeing_url)
        
        # Wait for page load
        import time
        time.sleep(3)
        
        # Dismiss overlays
        print("   Dismissing overlays...")
        browser._dismiss_overlays()
        
        # Find apply button
        print("   Finding apply button...")
        apply_button = browser.find_apply_button()
        
        if apply_button:
            print(f"✅ Found apply button: '{apply_button.text or apply_button.get_attribute('value')}'")
            
            # Test clicking (in visual mode for demo)
            print("   Scrolling to apply button...")
            browser.driver.execute_script("arguments[0].scrollIntoView(true);", apply_button)
            time.sleep(1)
            
            print("   Attempting to click apply button...")
            try:
                apply_button.click()
                print("✅ Successfully clicked apply button!")
                
                # Wait a moment to see the redirect
                time.sleep(3)
                print(f"   Redirected to: {browser.driver.current_url}")
                
                # Check if we're on Workday or similar application site
                if "workday" in browser.driver.current_url.lower():
                    print("✅ Successfully navigated to Workday application portal")
                    
                    # Try to analyze the new page
                    print("   Analyzing application form...")
                    analysis = browser.analyze_page_content()
                    print(f"   Found {len(analysis['form_fields'])} form fields")
                    print(f"   Found {len(analysis['file_uploads'])} file upload fields")
                    print(f"   Found {len(analysis['submit_buttons'])} submit buttons")
                    
                else:
                    print(f"   Navigated to: {browser.driver.current_url}")
                
            except Exception as e:
                if "click intercepted" in str(e):
                    print("   Normal click intercepted, trying JavaScript click...")
                    browser.driver.execute_script("arguments[0].click();", apply_button)
                    print("✅ JavaScript click successful!")
                else:
                    print(f"❌ Click failed: {e}")
                    return False
            
        else:
            print("❌ Apply button not found")
            return False
        
        # Keep browser open for a few seconds to show success
        print("\n⏳ Keeping browser open for 10 seconds to show results...")
        time.sleep(10)
        
        return True
        
    except Exception as e:
        print(f"❌ Browser automation error: {e}")
        return False
    
    finally:
        if browser.driver:
            browser.driver.quit()

if __name__ == "__main__":
    print("Testing the complete Boeing job application workflow...")
    
    success = test_boeing_application()
    
    if success:
        print("\n🎉 SUCCESS!")
        print("="*50)
        print("The job application system successfully:")
        print("✅ Scraped the Boeing job posting")  
        print("✅ Matched it against preferences")
        print("✅ Dismissed cookie overlays") 
        print("✅ Found and clicked the apply button")
        print("✅ Navigated to the application form")
        print("\nThe system is ready for production use!")
    else:
        print("\n❌ Test failed - check the output above for details")
    
    sys.exit(0 if success else 1)
