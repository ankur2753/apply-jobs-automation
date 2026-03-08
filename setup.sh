#!/bin/bash

# setup.sh - Setup script for the Job Application Automation System

# 1. Create a virtual environment
echo "Creating a Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies from requirements.txt
echo "Installing dependencies..."
pip install -r requirements.txt

# 3. Create necessary directories
echo "Creating necessary directories..."
mkdir -p resumes

# 4. Guide the user to download the correct WebDriver
echo "--------------------------------------------------------"
echo "Setup complete!"
echo "Next steps:"
echo "1. Ensure you have the Chrome WebDriver installed."
echo "   You can download it from: https://chromedriver.chromium.org/"
echo "   And make sure it's in your system's PATH."
echo "2. Customize the 'config.json' file with your details and preferences."
echo "3. Run the main application with: python3 main.py"
echo "--------------------------------------------------------"
