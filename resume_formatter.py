import google.generativeai as genai
import json
import re
from typing import Dict, List, Any


class ResumeFormatter:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def identify_highlighting_opportunities(self, resume_content: str) -> Dict[str, Any]:
        """
        Use AI to identify what should be highlighted, bolded, or emphasized in the resume
        """
        prompt = f"""You are an expert resume formatter and ATS optimization specialist. Analyze this resume content and identify specific text that should be highlighted, bolded, or emphasized for maximum impact.

RESUME CONTENT:
{resume_content}

Your task is to identify:
1. METRICS & NUMBERS: Percentages, dollar amounts, team sizes, time periods, quantities
2. KEY ACHIEVEMENTS: Major accomplishments, awards, recognitions
3. IMPORTANT TECHNOLOGIES: Critical programming languages, frameworks, tools mentioned in context
4. ACTION VERBS: Strong action words that should be emphasized
5. COMPANY NAMES: Important company/organization names
6. LEADERSHIP INDICATORS: Words/phrases showing leadership or impact

FORMATTING CATEGORIES:
- bold: For metrics, numbers, key achievements, important technologies
- underline: For company names, job titles, project names
- emphasis: For action verbs and leadership indicators
- highlight: For exceptional achievements or standout metrics

Return a JSON object with this EXACT structure:
{{
    "formatting_suggestions": [
        {{
            "text": "exact text to format",
            "type": "bold|underline|emphasis|highlight",
            "reason": "why this should be formatted",
            "context": "surrounding context for accuracy"
        }}
    ],
    "metrics_found": [
        {{
            "metric": "40% performance improvement",
            "type": "percentage|dollar|number|time",
            "importance": "high|medium|low"
        }}
    ],
    "key_technologies": [
        "Python", "React", "AWS", "etc"
    ],
    "achievements": [
        "Led team of 15 engineers",
        "Increased revenue by $2M",
        "etc"
    ]
}}

IDENTIFICATION RULES:
- Look for specific numbers: "40%", "$2M", "15 engineers", "3 years"
- Identify quantified achievements: "increased by X", "reduced by Y", "led team of Z"
- Find important technologies mentioned in achievement context
- Spot action verbs: "developed", "architected", "optimized", "led"
- Recognize company names and project names
- Be selective - only highlight truly impactful elements

EXAMPLES of what to highlight:
✅ "increased performance by 40%" → bold "40%"
✅ "led team of 15 engineers" → bold "15 engineers", emphasis "led"
✅ "built React application" → bold "React" (if it's a key skill)
✅ "reduced costs by $500K" → bold "$500K"
✅ "Google" (company name) → underline
✅ "Senior Software Engineer" (job title) → underline

❌ Don't highlight common words like "the", "and", "with"
❌ Don't highlight every technology mention, only key ones
❌ Don't over-format - be selective for maximum impact

Return ONLY valid JSON, no explanations."""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up response
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            result = json.loads(response_text)
            
            # Validate structure
            if 'formatting_suggestions' not in result:
                result['formatting_suggestions'] = []
            if 'metrics_found' not in result:
                result['metrics_found'] = []
            if 'key_technologies' not in result:
                result['key_technologies'] = []
            if 'achievements' not in result:
                result['achievements'] = []
            
            return result
            
        except Exception as e:
            print(f"Error in highlighting analysis: {e}")
            return {
                'formatting_suggestions': [],
                'metrics_found': [],
                'key_technologies': [],
                'achievements': []
            }
    
    def apply_latex_formatting(self, text: str, formatting_suggestions: List[Dict]) -> str:
        """
        Apply LaTeX formatting based on AI suggestions
        """
        formatted_text = text
        
        # Sort suggestions by text length (longest first) to avoid partial replacements
        suggestions = sorted(formatting_suggestions, key=lambda x: len(x['text']), reverse=True)
        
        for suggestion in suggestions:
            target_text = suggestion['text']
            format_type = suggestion['type']
            
            # Skip if text not found or already formatted
            if target_text not in formatted_text or '\\textbf{' in target_text:
                continue
            
            # Apply appropriate LaTeX formatting
            if format_type == 'bold':
                replacement = f"\\textbf{{{target_text}}}"
            elif format_type == 'underline':
                replacement = f"\\underline{{{target_text}}}"
            elif format_type == 'emphasis':
                replacement = f"\\emph{{{target_text}}}"
            elif format_type == 'highlight':
                # Use bold + emphasis for highlighting
                replacement = f"\\textbf{{\\emph{{{target_text}}}}}"
            else:
                continue
            
            # Replace only exact matches to avoid partial replacements
            formatted_text = formatted_text.replace(target_text, replacement)
        
        return formatted_text
    
    def format_resume_sections(self, structured_resume: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply AI-powered formatting to all resume sections
        """
        sections = structured_resume.get('sections', {})
        formatted_sections = {}
        all_formatting_suggestions = []
        
        for section_name, content in sections.items():
            if not content.strip():
                formatted_sections[section_name] = content
                continue
            
            print(f"Analyzing formatting for {section_name} section...")
            
            # Get AI formatting suggestions for this section
            formatting_analysis = self.identify_highlighting_opportunities(content)
            suggestions = formatting_analysis.get('formatting_suggestions', [])
            
            # Apply formatting
            formatted_content = self.apply_latex_formatting(content, suggestions)
            formatted_sections[section_name] = formatted_content
            
            # Collect all suggestions for summary
            all_formatting_suggestions.extend(suggestions)
        
        # Return enhanced structured resume with formatting
        result = structured_resume.copy()
        result['sections'] = formatted_sections
        result['formatting_analysis'] = {
            'total_suggestions': len(all_formatting_suggestions),
            'formatting_applied': all_formatting_suggestions,
            'metrics_highlighted': sum(1 for s in all_formatting_suggestions if s['type'] == 'bold'),
            'achievements_emphasized': sum(1 for s in all_formatting_suggestions if s['type'] == 'highlight')
        }
        
        return result
    
    def enhance_latex_with_smart_formatting(self, latex_code: str, formatting_suggestions: List[Dict]) -> str:
        """
        Post-process LaTeX code to add additional smart formatting
        """
        enhanced_latex = latex_code
        
        # Add some smart LaTeX enhancements
        enhancements = [
            # Make percentages stand out
            (r'(\d+%)', r'\\textbf{\1}'),
            # Make dollar amounts stand out
            (r'(\$[\d,]+[KMB]?)', r'\\textbf{\1}'),
            # Make years stand out in date ranges
            (r'(\d{4})\s*-\s*(\d{4}|\w+)', r'\\textbf{\1} - \\textbf{\2}'),
            # Make programming languages in context stand out
            (r'\b(Python|JavaScript|React|Node\.js|AWS|Docker|Kubernetes)\b(?=\s*[,\s])', r'\\textbf{\1}'),
        ]
        
        for pattern, replacement in enhancements:
            # Only apply if not already formatted
            enhanced_latex = re.sub(pattern, replacement, enhanced_latex)
        
        return enhanced_latex


class SmartLatexGenerator:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.formatter = ResumeFormatter(api_key)
    
    def generate_formatted_latex(self, structured_resume: Dict[str, Any]) -> str:
        """
        Generate LaTeX with intelligent formatting and highlighting
        """
        from latex_template import JAKES_TEMPLATE
        
        # First, apply AI-powered formatting to the content
        formatted_resume = self.formatter.format_resume_sections(structured_resume)
        
        contact_info = formatted_resume.get('contact_info', {})
        sections = formatted_resume.get('sections', {})
        
        prompt = f"""You are a LaTeX expert specializing in professional resume formatting. Generate a complete LaTeX resume using Jake's template with the provided structured data that already includes smart formatting.

JAKE'S TEMPLATE:
{JAKES_TEMPLATE}

STRUCTURED RESUME DATA (with formatting applied):
Contact Info: {json.dumps(contact_info, indent=2)}
Education: {sections.get('education', '')}
Experience: {sections.get('experience', '')}
Projects: {sections.get('projects', '')}
Skills: {sections.get('skills', '')}
Other: {sections.get('other', '')}

CRITICAL FORMATTING INSTRUCTIONS:
1. The content already includes LaTeX formatting commands like \\textbf{{}}, \\underline{{}}, \\emph{{}}
2. PRESERVE ALL existing formatting commands in the content
3. Do NOT add additional formatting that conflicts with existing formatting
4. Apply the standard Jake's template structure around the formatted content

LATEX GENERATION RULES:
1. Replace Jake Ryan's contact info with the provided contact info
2. Map sections appropriately:
   - Education → \\section{{Education}}
   - Experience → \\section{{Experience}}  
   - Projects → \\section{{Projects}}
   - Skills → \\section{{Technical Skills}}
   - Other → Additional sections if substantial content

3. PRESERVE FORMATTING: Keep all \\textbf{{}}, \\underline{{}}, \\emph{{}} commands from the content
4. Use proper LaTeX structure:
   - \\resumeSubheading for jobs/education
   - \\resumeProjectHeading for projects  
   - \\resumeItem{{}} for bullet points
   - Proper list structures with Start/End commands

5. FORMATTING PRESERVATION EXAMPLE:
   If content contains: "Improved performance by \\textbf{{40%}}"
   Keep it as: \\resumeItem{{Improved performance by \\textbf{{40%}}}}

6. Skip empty sections entirely
7. Don't add placeholder text or instructions

Return ONLY the complete LaTeX code starting with \\documentclass and ending with \\end{{document}}."""

        try:
            response = self.model.generate_content(prompt)
            latex_code = response.text.strip()
            
            # Clean up response
            if latex_code.startswith('```'):
                latex_code = latex_code.split('\n', 1)[1]
            if latex_code.endswith('```'):
                latex_code = latex_code.rsplit('\n', 1)[0]
            
            # Apply additional smart formatting enhancements
            formatting_suggestions = formatted_resume.get('formatting_analysis', {}).get('formatting_applied', [])
            enhanced_latex = self.formatter.enhance_latex_with_smart_formatting(latex_code, formatting_suggestions)
            
            return enhanced_latex
            
        except Exception as e:
            print(f"Error generating formatted LaTeX: {e}")
            raise
