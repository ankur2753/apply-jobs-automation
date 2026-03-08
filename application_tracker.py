# application_tracker.py - Module for tracking job applications
import pandas as pd
from datetime import datetime
from typing import Dict, List

class ApplicationTracker:
    """
    A class to track job applications in a CSV file.
    It provides methods to add new applications, load existing data, and get statistics.
    """
    def __init__(self, csv_file: str = 'job_applications.csv'):
        """Initializes the ApplicationTracker with a specified CSV file."""
        self.csv_file = csv_file
        self.df = self.load_existing_data()
    
    def load_existing_data(self) -> pd.DataFrame:
        """
        Loads existing application data from the CSV file.
        If the file does not exist, it creates a new DataFrame with predefined columns.
        
        Returns:
            pd.DataFrame: The DataFrame containing application data.
        """
        try:
            return pd.read_csv(self.csv_file)
        except FileNotFoundError:
            return pd.DataFrame(columns=[
                'date_applied', 'job_title', 'company', 'location', 
                'job_url', 'status', 'notes'
            ])
    
    def add_application(self, job_url: str, job_details: Dict):
        """
        Adds a new job application entry to the tracker DataFrame.
        
        Args:
            job_url (str): The URL of the job that was applied for.
            job_details (Dict): A dictionary with the details of the job.
        """
        new_row = {
            'date_applied': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'job_title': job_details.get('title', 'Unknown'),
            'company': job_details.get('company', 'Unknown'),
            'location': job_details.get('location', 'Unknown'),
            'job_url': job_url,
            'status': 'Applied',
            'notes': f"Auto-applied via bot. Requirements: {', '.join(job_details.get('requirements', []))}"
        }
        
        # Use pandas.concat to append the new row
        self.df = pd.concat([self.df, pd.DataFrame([new_row])], ignore_index=True)
        self.save_data()
    
    def save_data(self):
        """Saves the current DataFrame to the CSV file."""
        self.df.to_csv(self.csv_file, index=False)
    
    def get_application_stats(self) -> Dict:
        """
        Calculates and returns a dictionary of application statistics.
        
        Returns:
            Dict: A dictionary with 'total_applications', 'applications_this_week', and 'unique_companies'.
        """
        # Calculate applications this week based on date_applied column
        self.df['date_applied'] = pd.to_datetime(self.df['date_applied'])
        this_week_start = datetime.now() - pd.Timedelta(days=7)
        applications_this_week = len(self.df[self.df['date_applied'] >= this_week_start])
        
        return {
            'total_applications': len(self.df),
            'applications_this_week': applications_this_week,
            'unique_companies': self.df['company'].nunique()
        }
