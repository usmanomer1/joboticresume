import google.generativeai as genai
import json
import re
from typing import Dict, List, Any


class IntelligentSectionMapper:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def analyze_and_map_sections(self, resume_text: str) -> Dict[str, Any]:
        """
        Use AI to intelligently identify and map resume sections to template structure.
        This can handle ANY creative section headings by using AI understanding.
        """
        prompt = f"""You are an expert resume analyzer with deep understanding of resume content. Your job is to intelligently parse ANY resume format and map it to a standard template structure.

RESUME TEXT:
{resume_text}

TASK: Analyze this resume and intelligently categorize ALL content, regardless of how creative or unusual the section headings are.

EXAMPLES of creative headings you might encounter:
- "My Journey" (could be experience)
- "Brain Food" (could be education) 
- "Cool Stuff I Built" (could be projects)
- "My Superpowers" (could be skills)
- "Where I've Been" (could be experience)
- "What I Know" (could be skills/education)
- "Things I've Made" (could be projects)

YOUR ANALYSIS PROCESS:
1. READ the entire resume carefully
2. IDENTIFY all section headings (no matter how creative)
3. ANALYZE the content under each heading to understand what it actually contains
4. MAP each section to the most appropriate template category based on CONTENT, not heading name

TEMPLATE CATEGORIES (map based on content, not heading names):
- education: Schools, degrees, courses, certifications, academic achievements
- experience: Jobs, internships, work roles, professional positions, career history
- projects: Personal projects, side projects, portfolio items, things built/created
- skills: Technical abilities, programming languages, tools, software, competencies
- other: Summary, objective, awards, interests, references, misc content

MAPPING RULES:
- Look at CONTENT, not heading names
- If content describes work/jobs → experience
- If content describes schools/learning → education  
- If content describes things built/created → projects
- If content lists abilities/technologies → skills
- Be creative and intelligent in your mapping
- Don't get confused by unusual heading names

OUTPUT FORMAT - Return EXACTLY this JSON structure:
{{
    "contact_info": {{
        "name": "extracted name",
        "email": "extracted email", 
        "phone": "extracted phone",
        "linkedin": "extracted linkedin"
    }},
    "sections": {{
        "education": "All education-related content combined...",
        "experience": "All work/job-related content combined...", 
        "projects": "All project/creation-related content combined...",
        "skills": "All skills/abilities-related content combined...",
        "other": "Summary, awards, interests, and other misc content..."
    }},
    "original_sections": {{
        "Creative Heading 1": "original content...",
        "Creative Heading 2": "original content...",
        "etc": "..."
    }},
    "section_mappings": {{
        "Creative Heading 1": "experience",
        "Creative Heading 2": "skills",
        "etc": "education"
    }}
}}

CRITICAL REQUIREMENTS:
- Use CONTENT analysis, not heading name matching
- Handle ANY creative or unusual section names
- Preserve all original formatting and bullet points
- Include ALL resume content in appropriate categories
- If unsure about a section, analyze the actual content to determine category
- Empty sections should be empty strings ""
- Be intelligent about content categorization

Return ONLY valid JSON, no explanations or markdown."""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up response
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            # Parse JSON
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise ValueError("Could not extract valid JSON from AI response")
            
            # Validate structure
            if 'sections' not in result:
                result['sections'] = {}
            if 'contact_info' not in result:
                result['contact_info'] = {}
            if 'original_sections' not in result:
                result['original_sections'] = {}
            if 'section_mappings' not in result:
                result['section_mappings'] = {}
            
            # Ensure all required template sections exist
            template_sections = ['education', 'experience', 'projects', 'skills', 'other']
            for section in template_sections:
                if section not in result['sections']:
                    result['sections'][section] = ""
            
            return result
            
        except Exception as e:
            print(f"Error in AI section mapping: {e}")
            # Fallback to basic parsing
            return self._fallback_parsing(resume_text)
    
    def _fallback_parsing(self, resume_text: str) -> Dict[str, Any]:
        """Fallback parsing if AI fails"""
        return {
            'contact_info': {},
            'sections': {
                'education': "",
                'experience': resume_text,  # Put everything in experience as fallback
                'projects': "",
                'skills': "",
                'other': ""
            },
            'original_sections': {
                'Full Resume': resume_text
            }
        }


class StructuredResumeGenerator:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def optimize_structured_resume(self, structured_resume: Dict[str, Any], job_description: str, job_title: str, company_name: str) -> Dict[str, Any]:
        """
        Optimize each section of the resume against the job description
        """
        prompt = f"""You are an ATS optimization expert. I will provide you with a structured resume and job description. 
Your task is to optimize each section for maximum ATS compatibility and relevance.

STRUCTURED RESUME:
{json.dumps(structured_resume, indent=2)}

JOB DESCRIPTION:
{job_description}

JOB TITLE: {job_title}
COMPANY: {company_name}

Optimize each section by:
1. Adding relevant keywords from the job description
2. Strengthening action verbs and quantifying achievements
3. Ensuring ATS compatibility
4. Maintaining professional tone and accuracy

Return a JSON with this EXACT structure:
{{
    "contact_info": {{
        "name": "optimized name",
        "email": "email", 
        "phone": "phone",
        "linkedin": "linkedin"
    }},
    "sections": {{
        "education": "Optimized education content with relevant keywords...",
        "experience": "Optimized work experience with strong action verbs and metrics...",
        "projects": "Optimized projects highlighting relevant technologies...",
        "skills": "Optimized skills section with job-relevant technologies...",
        "other": "Optimized other content..."
    }},
    "optimization_summary": {{
        "keywords_added": ["keyword1", "keyword2"],
        "changes_made": ["change1", "change2"],
        "ats_score_before": 6,
        "ats_score_after": 9
    }}
}}

CRITICAL RULES:
- Keep all factual information accurate - don't invent experience or skills
- Preserve original structure and formatting (bullet points, etc.)
- Focus on relevance to the job description
- If a section is empty, keep it empty
- Add metrics and quantification where possible (but don't fabricate numbers)
- Use strong action verbs (developed, implemented, led, optimized, etc.)

Return ONLY valid JSON."""

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
            if 'sections' not in result:
                result['sections'] = structured_resume.get('sections', {})
            if 'contact_info' not in result:
                result['contact_info'] = structured_resume.get('contact_info', {})
            if 'optimization_summary' not in result:
                result['optimization_summary'] = {
                    'keywords_added': [],
                    'changes_made': [],
                    'ats_score_before': 5,
                    'ats_score_after': 7
                }
            
            return result
            
        except Exception as e:
            print(f"Error in structured optimization: {e}")
            # Return original with minimal optimization summary
            return {
                'contact_info': structured_resume.get('contact_info', {}),
                'sections': structured_resume.get('sections', {}),
                'optimization_summary': {
                    'keywords_added': [],
                    'changes_made': [f'Error during optimization: {str(e)}'],
                    'ats_score_before': 5,
                    'ats_score_after': 5
                }
            }
    
    def generate_structured_latex(self, optimized_resume: Dict[str, Any]) -> str:
        """
        Generate LaTeX code using the structured, optimized resume data with smart formatting
        """
        try:
            # Use the new smart formatter for enhanced LaTeX generation
            from resume_formatter import SmartLatexGenerator
            # Get API key from environment or use a stored one
            import os
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not available for smart formatting")
            
            smart_generator = SmartLatexGenerator(api_key)
            return smart_generator.generate_formatted_latex(optimized_resume)
            
        except Exception as e:
            print(f"Smart formatting failed, falling back to basic LaTeX generation: {e}")
            # Fallback to original method
            return self._generate_basic_latex(optimized_resume)
    
    def _generate_basic_latex(self, optimized_resume: Dict[str, Any]) -> str:
        """
        Fallback LaTeX generation without advanced formatting
        """
        from latex_template import JAKES_TEMPLATE
        
        contact_info = optimized_resume.get('contact_info', {})
        sections = optimized_resume.get('sections', {})
        
        prompt = f"""You are a LaTeX expert. Generate a complete LaTeX resume using Jake's template with the provided structured data.

JAKE'S TEMPLATE:
{JAKES_TEMPLATE}

STRUCTURED RESUME DATA:
Contact Info: {json.dumps(contact_info, indent=2)}
Education: {sections.get('education', '')}
Experience: {sections.get('experience', '')}
Projects: {sections.get('projects', '')}
Skills: {sections.get('skills', '')}
Other: {sections.get('other', '')}

CRITICAL INSTRUCTIONS:
1. Replace Jake Ryan's contact info with the provided contact info
2. Map each section to the appropriate LaTeX section:
   - Education data → \\section{{Education}}
   - Experience data → \\section{{Experience}}  
   - Projects data → \\section{{Projects}}
   - Skills data → \\section{{Technical Skills}}
   - Other data → Add as additional sections if substantial content

3. LATEX SYNTAX RULES:
   - Every \\resumeItem MUST have curly braces: \\resumeItem{{content}}
   - Use \\resumeSubheading for jobs/education: \\resumeSubheading{{Title}}{{Date}}{{Company/School}}{{Location}}
   - Use \\resumeProjectHeading for projects: \\resumeProjectHeading{{\\textbf{{Project Name}} $|$ \\emph{{Technologies}}}}{{Date}}
   - Wrap each section in \\resumeSubHeadingListStart and \\resumeSubHeadingListEnd
   - Wrap bullet points in \\resumeItemListStart and \\resumeItemListEnd

4. CONTENT RULES:
   - If a section is empty, skip it entirely
   - Preserve all bullet points as \\resumeItem{{}}
   - Keep dates, company names, and locations from the content
   - If dates/locations are missing, use reasonable defaults
   - Don't add placeholder text like [Date] or [Location]

Return ONLY the complete LaTeX code starting with \\documentclass and ending with \\end{{document}}."""

        try:
            response = self.model.generate_content(prompt)
            latex_code = response.text.strip()
            
            # Clean up response
            if latex_code.startswith('```'):
                latex_code = latex_code.split('\n', 1)[1]
            if latex_code.endswith('```'):
                latex_code = latex_code.rsplit('\n', 1)[0]
            
            return latex_code
            
        except Exception as e:
            print(f"Error generating basic LaTeX: {e}")
            raise
