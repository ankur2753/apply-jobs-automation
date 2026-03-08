# resume_modifier.py - Module for modifying resumes
import os
import json
from datetime import datetime
from typing import Dict, List
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

class ResumeModifier:
    """
    A class to generate and modify a PDF resume based on job details.
    It uses the reportlab library to create a customized PDF document.
    """
    def __init__(self):
        """Initializes ResumeModifier."""
        self.base_resume_path = None
        
    def modify_resume(self, job_details: Dict, personal_details: Dict) -> str:
        """
        Modifies and creates a new resume PDF customized for a specific job.
        
        Args:
            job_details (Dict): A dictionary containing details of the job.
            personal_details (Dict): A dictionary with the user's personal information.
            
        Returns:
            str: The file path of the generated resume, or None on failure.
        """
        try:
            # Create customized resume
            output_path = f"resumes/resume_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            os.makedirs('resumes', exist_ok=True)
            
            # Generate PDF resume
            self.create_customized_resume(job_details, personal_details, output_path)
            
            return output_path
            
        except Exception as e:
            print(f"Error modifying resume: {e}")
            return None
    
    def create_customized_resume(self, job_details: Dict, personal_details: Dict, output_path: str):
        """
        Creates a PDF resume with sections like header, summary, skills, and experience.
        The summary and skills are customized based on job requirements.
        """
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, height - 100, personal_details.get('name', 'Your Name'))
        
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 120, personal_details.get('email', 'email@example.com'))
        c.drawString(100, height - 140, personal_details.get('phone', '+1234567890'))
        c.drawString(100, height - 160, personal_details.get('location', 'Your Location'))
        
        # Customized summary based on job
        y_position = height - 200
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y_position, "Professional Summary")
        
        y_position -= 30
        c.setFont("Helvetica", 10)
        summary = self.generate_customized_summary(job_details, personal_details)
        
        # Word wrap the summary
        words = summary.split(' ')
        lines = []
        current_line = ""
        
        for word in words:
            if len(current_line + word) < 80:
                current_line += word + " "
            else:
                lines.append(current_line.strip())
                current_line = word + " "
        lines.append(current_line.strip())
        
        for line in lines:
            c.drawString(100, y_position, line)
            y_position -= 15
        
        # Skills section (highlight relevant skills)
        y_position -= 20
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y_position, "Key Skills")
        
        y_position -= 20
        c.setFont("Helvetica", 10)
        relevant_skills = self.get_relevant_skills(job_details, personal_details)
        skills_text = " • ".join(relevant_skills)
        c.drawString(100, y_position, skills_text)
        
        # Experience section
        y_position -= 40
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y_position, "Experience")
        
        y_position -= 20
        for experience in personal_details.get('experience', []):
            c.setFont("Helvetica-Bold", 11)
            c.drawString(100, y_position, f"{experience['title']} - {experience['company']}")
            y_position -= 15
            
            c.setFont("Helvetica", 9)
            c.drawString(100, y_position, f"{experience['duration']}")
            y_position -= 15
            
            # Customize bullet points based on job requirements
            for bullet in experience.get('bullets', [])[:3]:  # Limit to 3 bullets
                c.drawString(110, y_position, f"• {bullet}")
                y_position -= 12
            y_position -= 10
        
        c.save()
    
    def generate_customized_summary(self, job_details: Dict, personal_details: Dict) -> str:
        """Generates a professional summary that highlights skills relevant to the job posting."""
        base_summary = personal_details.get('summary', 'Experienced professional')
        job_title = job_details.get('title', '')
        requirements = job_details.get('requirements', [])
        
        # Customize summary based on job requirements
        customized_summary = f"{base_summary} with expertise in {', '.join(requirements[:3])}. "
        customized_summary += f"Seeking to contribute to {job_title} role with proven track record in "
        customized_summary += f"{', '.join(personal_details.get('core_skills', ['software development', 'problem solving']))}."
        
        return customized_summary
    
    def get_relevant_skills(self, job_details: Dict, personal_details: Dict) -> List[str]:
        """Gets a list of skills from the user's profile that are most relevant to the job requirements."""
        all_skills = personal_details.get('skills', [])
        job_requirements = [req.lower() for req in job_details.get('requirements', [])]
        
        # Prioritize skills that match job requirements
        relevant_skills = []
        for skill in all_skills:
            if any(req in skill.lower() for req in job_requirements):
                relevant_skills.append(skill)
        
        # Add remaining skills up to a limit
        for skill in all_skills:
            if skill not in relevant_skills and len(relevant_skills) < 10:
                relevant_skills.append(skill)
        
        return relevant_skills
