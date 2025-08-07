from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
import re
from typing import Dict, List


class ResumeGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
        
    def _create_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=18,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=6,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='ContactInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            spaceAfter=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=8,
            spaceBefore=12,
            borderWidth=1,
            borderColor=colors.HexColor('#2c3e50'),
            borderPadding=3
        ))
        
        self.styles.add(ParagraphStyle(
            name='BulletPoint',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=20,
            spaceAfter=4,
            alignment=TA_JUSTIFY
        ))
        
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        ))
    
    def _format_contact_info(self, contact_info: Dict) -> str:
        parts = []
        
        if 'name' in contact_info:
            parts.append(f"<b>{contact_info['name']}</b>")
        
        contact_line = []
        if 'email' in contact_info:
            contact_line.append(contact_info['email'])
        if 'phone' in contact_info:
            contact_line.append(contact_info['phone'])
        if 'linkedin' in contact_info:
            contact_line.append(f"LinkedIn: {contact_info['linkedin']}")
        
        if contact_line:
            parts.append(' | '.join(contact_line))
        
        return '<br/>'.join(parts)
    
    def _process_text_formatting(self, text: str) -> List:
        story = []
        
        section_pattern = r'^(EDUCATION|EXPERIENCE|SKILLS|CERTIFICATIONS|ACHIEVEMENTS|PROJECTS|SUMMARY|OBJECTIVE|PROFESSIONAL SUMMARY|WORK EXPERIENCE|EMPLOYMENT|TECHNICAL SKILLS|LANGUAGES|AWARDS|HONORS)(?:\s*:)?'
        
        lines = text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                story.append(Spacer(1, 0.1 * inch))
                i += 1
                continue
            
            section_match = re.match(section_pattern, line, re.IGNORECASE)
            if section_match:
                story.append(Paragraph(line.upper(), self.styles['SectionHeading']))
                i += 1
                continue
            
            if re.match(r'^[•·▪▫◦‣⁃●○■□►▶★☆\-\*]\s', line):
                formatted_line = re.sub(r'^[•·▪▫◦‣⁃●○■□►▶★☆\-\*]\s', '• ', line)
                story.append(Paragraph(formatted_line, self.styles['BulletPoint']))
            elif re.match(r'^\d+[\.\)]\s', line):
                story.append(Paragraph(line, self.styles['BulletPoint']))
            else:
                story.append(Paragraph(line, self.styles['NormalText']))
            
            i += 1
        
        return story
    
    def generate_pdf(self, optimized_data: Dict, output_path: str):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        story = []
        
        contact_info = optimized_data.get('contact_info', {})
        if contact_info:
            contact_text = self._format_contact_info(contact_info)
            story.append(Paragraph(contact_text, self.styles['ContactInfo']))
            story.append(Spacer(1, 0.2 * inch))
        
        optimized_text = optimized_data.get('optimized_resume', '')
        if optimized_text:
            formatted_content = self._process_text_formatting(optimized_text)
            story.extend(formatted_content)
        
        doc.build(story)
        
    def generate_summary_report(self, optimized_data: Dict) -> str:
        report = []
        report.append("=== Resume Optimization Summary ===\n")
        
        score = optimized_data.get('score', {})
        if score:
            report.append(f"ATS Score Improvement: {score.get('before', 'N/A')} → {score.get('after', 'N/A')}")
        
        keywords = optimized_data.get('keywords_added', [])
        if keywords:
            report.append(f"\nKeywords Added ({len(keywords)}):")
            for keyword in keywords[:10]:
                report.append(f"  • {keyword}")
        
        changes = optimized_data.get('changes_made', [])
        if changes:
            report.append(f"\nChanges Made ({len(changes)}):")
            for i, change in enumerate(changes[:10]):
                if isinstance(change, dict):
                    desc = change.get('description', change.get('type', 'Change'))
                    report.append(f"  {i+1}. {desc}")
                else:
                    report.append(f"  {i+1}. {change}")
        
        if optimized_data.get('error'):
            report.append(f"\nError encountered: {optimized_data['error']}")
        
        return '\n'.join(report)