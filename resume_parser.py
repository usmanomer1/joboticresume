import PyPDF2
import pdfplumber
import re
from typing import Dict, List, Tuple


class ResumeParser:
    def __init__(self, gemini_api_key: str = None):
        # Keep basic section detection for fallback, but now we'll primarily use AI
        self.basic_sections = [
            'education', 'experience', 'skills', 'certifications',
            'achievements', 'projects', 'summary', 'objective',
            'professional summary', 'work experience', 'employment',
            'technical skills', 'languages', 'awards', 'honors',
            'academic background', 'work history', 'portfolio',
            'technical expertise', 'competencies', 'tools'
        ]
        
        # Initialize AI mapper if API key provided
        self.ai_mapper = None
        if gemini_api_key:
            from intelligent_section_mapper import IntelligentSectionMapper
            self.ai_mapper = IntelligentSectionMapper(gemini_api_key)
        
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
            for section in self.basic_sections:
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
    
    def map_sections_to_template(self, sections: Dict[str, str]) -> Dict[str, str]:
        """Map user's section names to template section names"""
        mapped_sections = {}
        
        for user_section, content in sections.items():
            user_section_lower = user_section.lower().strip()
            
            # Find the best template section match
            best_match = None
            for template_section, keywords in self.template_sections.items():
                for keyword in keywords:
                    if keyword in user_section_lower:
                        best_match = template_section
                        break
                if best_match:
                    break
            
            # If no direct match, use heuristics
            if not best_match:
                if any(word in user_section_lower for word in ['work', 'job', 'career', 'employment']):
                    best_match = 'experience'
                elif any(word in user_section_lower for word in ['school', 'university', 'college', 'degree']):
                    best_match = 'education'
                elif any(word in user_section_lower for word in ['project', 'portfolio']):
                    best_match = 'projects'
                elif any(word in user_section_lower for word in ['skill', 'technology', 'tool', 'language']):
                    best_match = 'skills'
                else:
                    # Default unmapped sections to a generic category
                    best_match = 'other'
            
            # Combine content if section already exists
            if best_match in mapped_sections:
                mapped_sections[best_match] += f"\n\n{content}"
            else:
                mapped_sections[best_match] = content
        
        return mapped_sections
    
    def parse_resume_with_ai(self, pdf_path: str) -> Dict:
        """
        Enhanced parsing using AI to handle ANY section headings
        """
        if not self.ai_mapper:
            raise ValueError("AI mapper not initialized. Provide gemini_api_key to constructor.")
        
        # Extract raw text
        raw_text = self.extract_text_from_pdf(pdf_path)
        
        # Use AI to analyze and map sections intelligently
        ai_result = self.ai_mapper.analyze_and_map_sections(raw_text)
        
        # Preserve formatting
        formatted_text = self.preserve_bullet_points(raw_text)
        
        return {
            'raw_text': raw_text,
            'formatted_text': formatted_text,
            'contact_info': ai_result.get('contact_info', {}),
            'sections': ai_result.get('original_sections', {}),  # Original sections with creative names
            'mapped_sections': ai_result.get('sections', {}),  # AI-mapped to template structure
            'section_mappings': ai_result.get('section_mappings', {}),  # Shows how AI mapped each section
            'ai_parsed': True  # Flag to indicate AI parsing was used
        }
    
    def parse_resume(self, pdf_path: str) -> Dict:
        """
        Main parsing method - uses AI if available, falls back to basic parsing
        """
        # Try AI parsing first if available
        if self.ai_mapper:
            try:
                return self.parse_resume_with_ai(pdf_path)
            except Exception as e:
                print(f"AI parsing failed, falling back to basic parsing: {e}")
        
        # Fallback to basic parsing
        raw_text = self.extract_text_from_pdf(pdf_path)
        
        contact_info = self.extract_contact_info(raw_text)
        sections = self.identify_sections(raw_text)
        
        # Map sections to template structure using basic rules
        mapped_sections = self.map_sections_to_template(sections)
        
        formatted_text = self.preserve_bullet_points(raw_text)
        
        return {
            'raw_text': raw_text,
            'formatted_text': formatted_text,
            'contact_info': contact_info,
            'sections': sections,  # Original sections
            'mapped_sections': mapped_sections,  # Template-compatible sections
            'ai_parsed': False  # Flag to indicate basic parsing was used
        }