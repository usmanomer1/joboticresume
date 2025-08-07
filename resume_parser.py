import PyPDF2
import pdfplumber
import re
from typing import Dict, List, Tuple


class ResumeParser:
    def __init__(self):
        self.sections = [
            'education', 'experience', 'skills', 'certifications',
            'achievements', 'projects', 'summary', 'objective',
            'professional summary', 'work experience', 'employment',
            'technical skills', 'languages', 'awards', 'honors'
        ]
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"Error with pdfplumber, trying PyPDF2: {e}")
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
        
        return text.strip()
    
    def extract_contact_info(self, text: str) -> Dict[str, str]:
        contact_info = {}
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text)
        if email_match:
            contact_info['email'] = email_match.group()
        
        phone_patterns = [
            r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,4}',
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text)
            if phone_match:
                contact_info['phone'] = phone_match.group()
                break
        
        linkedin_pattern = r'(?:linkedin\.com/in/|linkedin:\s*)([a-zA-Z0-9-]+)'
        linkedin_match = re.search(linkedin_pattern, text, re.IGNORECASE)
        if linkedin_match:
            contact_info['linkedin'] = linkedin_match.group(1)
        
        lines = text.split('\n')[:10]
        for line in lines:
            if not any(key in contact_info for key in ['name']):
                cleaned_line = line.strip()
                if cleaned_line and len(cleaned_line.split()) <= 4 and not any(char.isdigit() for char in cleaned_line):
                    if not re.search(r'[|,]', cleaned_line):
                        contact_info['name'] = cleaned_line
                        break
        
        return contact_info
    
    def identify_sections(self, text: str) -> Dict[str, str]:
        sections_found = {}
        lines = text.split('\n')
        current_section = 'header'
        section_content = []
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            is_section_header = False
            for section in self.sections:
                if section in line_lower and len(line.split()) <= 4:
                    is_section_header = True
                    if current_section and section_content:
                        sections_found[current_section] = '\n'.join(section_content).strip()
                    current_section = section
                    section_content = []
                    break
            
            if not is_section_header:
                section_content.append(line)
        
        if current_section and section_content:
            sections_found[current_section] = '\n'.join(section_content).strip()
        
        return sections_found
    
    def preserve_bullet_points(self, text: str) -> str:
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped:
                if re.match(r'^[•·▪▫◦‣⁃●○■□►▶★☆\-\*]\s', stripped):
                    formatted_lines.append(line)
                elif re.match(r'^\d+[\.\)]\s', stripped):
                    formatted_lines.append(line)
                else:
                    formatted_lines.append(line)
            else:
                formatted_lines.append('')
        
        return '\n'.join(formatted_lines)
    
    def parse_resume(self, pdf_path: str) -> Dict:
        raw_text = self.extract_text_from_pdf(pdf_path)
        
        contact_info = self.extract_contact_info(raw_text)
        sections = self.identify_sections(raw_text)
        
        formatted_text = self.preserve_bullet_points(raw_text)
        
        return {
            'raw_text': raw_text,
            'formatted_text': formatted_text,
            'contact_info': contact_info,
            'sections': sections
        }