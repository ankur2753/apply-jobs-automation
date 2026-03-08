Job Application Automation System

This is an automated system designed to help you streamline the job application process. It scrapes job listings, modifies your resume for specific roles, and automates the filling of application forms.
Features

    Job Scraping: Automatically extracts job title, company, location, and description from various websites.

    Resume Customization: Generates a tailored PDF resume for each job by highlighting relevant skills and keywords.

    Application Tracking: Keeps a log of all applications in a CSV file for easy management.

    Browser Automation: Fills out job application forms automatically using your personal details.

    Job Matching: Filters jobs based on your preferred criteria (keywords, titles, locations).

Project Structure

job_apply/
├── main.py                 # Main orchestrator
├── job_scraper.py          # Scraping module
├── resume_modifier.py      # Resume customization
├── application_tracker.py  # Application tracking
├── browser_automation.py   # Form automation
├── job_matcher.py          # Job matching logic
├── requirements.txt        # Python dependencies
├── setup.sh                # Setup script
└── README.md               # This documentation

Setup Instructions

    Clone or Download the Project

    Run the Setup Script: Open a terminal in the project directory and execute the setup script. This will create a virtual environment, install dependencies, and create a resumes directory.

    chmod +x setup.sh
    ./setup.sh

    Install Chrome WebDriver: Ensure you have the Chrome WebDriver installed and in your system's PATH. The script will provide a link to the download page.

    Create config.json: Create a config.json file in the main directory. This file is crucial for the bot's functionality and should contain your personal information and job preferences. A sample structure is provided below.

config.json Example

{
    "personal_details": {
        "name": "Your Name",
        "email": "your_email@example.com",
        "phone": "+1 (555) 123-4567",
        "linkedin": "https://www.linkedin.com/in/your-profile",
        "location": "Your City, State",
        "summary": "A brief professional summary.",
        "skills": ["Python", "Selenium", "Data Analysis", "SQL", "Machine Learning"],
        "core_skills": ["software development", "problem solving"],
        "experience": [
            {
                "title": "Software Engineer",
                "company": "Tech Solutions Inc.",
                "duration": "2020 - Present",
                "bullets": [
                    "Developed and maintained scalable web applications.",
                    "Improved system performance by 20% through code optimization.",
                    "Collaborated with cross-functional teams."
                ]
            }
        ]
    },
    "preferred_jobs": [
        {
            "title": "Software Engineer",
            "keywords": ["python", "flask", "django"],
            "locations": ["san francisco", "remote"]
        },
        {
            "title": "Data Scientist",
            "keywords": ["ml", "pandas", "pytorch"],
            "locations": ["new york"]
        }
    ]
}

Usage

    Ensure you have completed all the setup steps.

    Run the main application from your terminal:

    python3 main.py

    Follow the on-screen prompts to apply for jobs individually or in bulk.