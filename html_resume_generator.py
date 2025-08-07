import re
from typing import Dict, List
from pathlib import Path

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False


class HTMLResumeGenerator:
    def __init__(self):
        self.template = self.get_template()
        
    def get_template(self) -> str:
        """HTML template that mimics Jake's LaTeX resume style"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {
            size: letter;
            margin: 0.75in;
        }
        
        body {
            font-family: 'Times New Roman', Times, serif;
            font-size: 11pt;
            line-height: 1.2;
            margin: 0;
            padding: 0;
            color: #000;
        }
        
        /* Header */
        .header {
            text-align: center;
            margin-bottom: 10px;
        }
        
        .name {
            font-size: 24pt;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }
        
        .contact-info {
            font-size: 10pt;
            margin-top: 5px;
        }
        
        .contact-info a {
            color: #000;
            text-decoration: underline;
        }
        
        /* Sections */
        .section {
            margin-top: 12px;
            margin-bottom: 8px;
        }
        
        .section-title {
            font-size: 14pt;
            font-weight: bold;
            text-transform: uppercase;
            border-bottom: 1px solid #000;
            padding-bottom: 2px;
            margin-bottom: 8px;
            color: #2c3e50;
        }
        
        /* Subsections */
        .subsection {
            margin-bottom: 10px;
        }
        
        .subsection-header {
            display: table;
            width: 100%;
            margin-bottom: 4px;
        }
        
        .subsection-left {
            display: table-cell;
            font-weight: bold;
        }
        
        .subsection-right {
            display: table-cell;
            text-align: right;
        }
        
        .subsection-subtitle {
            display: table;
            width: 100%;
            font-style: italic;
            font-size: 10pt;
            margin-bottom: 4px;
        }
        
        .subtitle-left {
            display: table-cell;
        }
        
        .subtitle-right {
            display: table-cell;
            text-align: right;
            font-size: 10pt;
        }
        
        /* Lists */
        ul {
            margin: 0;
            padding-left: 20px;
            margin-bottom: 4px;
        }
        
        li {
            margin-bottom: 2px;
            text-align: justify;
        }
        
        /* Skills section */
        .skills-category {
            margin-bottom: 4px;
        }
        
        .skills-category strong {
            font-weight: bold;
        }
        
        /* Projects */
        .project-header {
            margin-bottom: 4px;
        }
        
        .project-title {
            font-weight: bold;
        }
        
        .project-tech {
            font-style: italic;
        }
    </style>
</head>
<body>
    {content}
</body>
</html>
"""
    
    def escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        if not text:
            return ""
        
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#39;')
        
        return text
    
    def parse_sections(self, optimized_text: str) -> Dict[str, List[str]]:
        """Parse the optimized resume text into sections"""
        sections = {
            'summary': [],
            'education': [],
            'experience': [],
            'projects': [],
            'skills': []
        }
        
        current_section = None
        lines = optimized_text.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            line_upper = line_stripped.upper()
            
            # Check section headers
            if any(keyword in line_upper for keyword in ['SUMMARY', 'OBJECTIVE', 'PROFILE']):
                current_section = 'summary'
                continue
            elif 'EDUCATION' in line_upper:
                current_section = 'education'
                continue
            elif any(keyword in line_upper for keyword in ['EXPERIENCE', 'WORK EXPERIENCE', 'EMPLOYMENT']):
                current_section = 'experience'
                continue
            elif 'PROJECT' in line_upper:
                current_section = 'projects'
                continue
            elif any(keyword in line_upper for keyword in ['SKILL', 'TECHNICAL', 'TECHNOLOGIES']):
                current_section = 'skills'
                continue
            
            # Add content to current section
            if current_section and line_stripped:
                sections[current_section].append(line_stripped)
        
        return sections
    
    def format_header(self, contact_info: Dict) -> str:
        """Format the header section"""
        name = self.escape_html(contact_info.get('name', 'Your Name'))
        email = contact_info.get('email', 'email@example.com')
        phone = self.escape_html(contact_info.get('phone', '123-456-7890'))
        linkedin = contact_info.get('linkedin', '')
        
        contact_parts = []
        contact_parts.append(phone)
        contact_parts.append(f'<a href="mailto:{email}">{email}</a>')
        if linkedin:
            contact_parts.append(f'<a href="https://linkedin.com/in/{linkedin}">linkedin.com/in/{linkedin}</a>')
        
        return f"""
    <div class="header">
        <div class="name">{name}</div>
        <div class="contact-info">{' | '.join(contact_parts)}</div>
    </div>
"""
    
    def format_education(self, entries: List[str]) -> str:
        """Format education entries"""
        html = '<div class="section">\n<div class="section-title">Education</div>\n'
        
        i = 0
        while i < len(entries):
            if i + 2 < len(entries):
                institution = self.escape_html(entries[i])
                degree = self.escape_html(entries[i + 1])
                date = self.escape_html(entries[i + 2])
                
                html += f"""
    <div class="subsection">
        <div class="subsection-header">
            <div class="subsection-left">{institution}</div>
            <div class="subsection-right">Location</div>
        </div>
        <div class="subsection-subtitle">
            <div class="subtitle-left">{degree}</div>
            <div class="subtitle-right">{date}</div>
        </div>
    </div>
"""
                i += 3
            else:
                i += 1
        
        html += '</div>\n'
        return html
    
    def format_experience(self, entries: List[str]) -> str:
        """Format experience entries"""
        html = '<div class="section">\n<div class="section-title">Experience</div>\n'
        
        current_job = None
        job_items = []
        
        for entry in entries:
            # Check if this is a job header
            if not entry.startswith('•') and not entry.startswith('-') and len(entry.split()) > 2:
                # Save previous job
                if current_job and job_items:
                    html += current_job
                    html += '<ul>\n'
                    for item in job_items:
                        html += f'<li>{item}</li>\n'
                    html += '</ul>\n</div>\n'
                
                # Parse new job
                parts = entry.split('|') if '|' in entry else [entry]
                title = self.escape_html(parts[0].strip())
                company = self.escape_html(parts[1].strip()) if len(parts) > 1 else "Company"
                date = self.escape_html(parts[2].strip()) if len(parts) > 2 else "Date"
                
                current_job = f"""
    <div class="subsection">
        <div class="subsection-header">
            <div class="subsection-left">{title}</div>
            <div class="subsection-right">{date}</div>
        </div>
        <div class="subsection-subtitle">
            <div class="subtitle-left">{company}</div>
            <div class="subtitle-right">Location</div>
        </div>
"""
                job_items = []
            
            # Bullet points
            elif entry.startswith('•') or entry.startswith('-'):
                bullet_text = entry.lstrip('•-').strip()
                job_items.append(self.escape_html(bullet_text))
        
        # Don't forget last job
        if current_job and job_items:
            html += current_job
            html += '<ul>\n'
            for item in job_items:
                html += f'<li>{item}</li>\n'
            html += '</ul>\n</div>\n'
        
        html += '</div>\n'
        return html
    
    def format_skills(self, skills_entries: List[str]) -> str:
        """Format skills section"""
        html = '<div class="section">\n<div class="section-title">Technical Skills</div>\n'
        
        skills_dict = {
            'Languages': [],
            'Frameworks': [],
            'Developer Tools': [],
            'Libraries': []
        }
        
        # Categorize skills
        for entry in skills_entries:
            entry_lower = entry.lower()
            
            if any(lang in entry_lower for lang in ['python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'go', 'swift', 'sql', 'html', 'css', 'typescript']):
                skills_dict['Languages'].append(entry)
            elif any(fw in entry_lower for fw in ['react', 'angular', 'vue', 'django', 'flask', 'spring', 'node', 'express']):
                skills_dict['Frameworks'].append(entry)
            elif any(tool in entry_lower for tool in ['git', 'docker', 'jenkins', 'aws', 'azure', 'gcp', 'kubernetes']):
                skills_dict['Developer Tools'].append(entry)
            else:
                skills_dict['Libraries'].append(entry)
        
        # Format HTML
        for category, items in skills_dict.items():
            if items:
                items_str = ', '.join([self.escape_html(item) for item in items[:10]])
                html += f'<div class="skills-category"><strong>{category}:</strong> {items_str}</div>\n'
        
        html += '</div>\n'
        return html
    
    def generate_html_pdf(self, optimized_data: Dict, output_path: str):
        """Generate PDF from HTML template"""
        
        # Extract data
        contact_info = optimized_data.get('contact_info', {})
        optimized_text = optimized_data.get('optimized_resume', '')
        sections = self.parse_sections(optimized_text)
        
        # Build HTML content
        content = self.format_header(contact_info)
        
        if sections['summary']:
            content += '<div class="section">\n<div class="section-title">Summary</div>\n'
            content += '<p>' + ' '.join(sections['summary']) + '</p>\n</div>\n'
        
        if sections['education']:
            content += self.format_education(sections['education'])
        
        if sections['experience']:
            content += self.format_experience(sections['experience'])
        
        if sections['projects']:
            content += '<div class="section">\n<div class="section-title">Projects</div>\n'
            content += '<p>' + ' '.join(sections['projects']) + '</p>\n</div>\n'
        
        if sections['skills']:
            content += self.format_skills(sections['skills'])
        
        # Generate full HTML
        html = self.template.replace('{content}', content)
        
        # Save HTML
        html_path = output_path.replace('.pdf', '.html')
        with open(html_path, 'w') as f:
            f.write(html)
        
        # Convert to PDF using available library
        pdf_generated = False
        
        if WEASYPRINT_AVAILABLE:
            try:
                HTML(string=html).write_pdf(output_path)
                print(f"✓ PDF generated using weasyprint")
                pdf_generated = True
            except Exception as e:
                print(f"Warning: weasyprint failed ({e})")
        
        if not pdf_generated and PDFKIT_AVAILABLE:
            try:
                pdfkit.from_string(html, output_path)
                print(f"✓ PDF generated using pdfkit")
                pdf_generated = True
            except Exception as e:
                print(f"Warning: pdfkit failed ({e})")
        
        if not pdf_generated:
            print(f"Warning: No PDF library available. HTML file saved at: {html_path}")
            print("To generate PDF, install weasyprint: pip install weasyprint")
        
        return html_path