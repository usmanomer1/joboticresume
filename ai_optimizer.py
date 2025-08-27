import google.generativeai as genai
import json
from typing import Dict, List
import re
from intelligent_section_mapper import IntelligentSectionMapper, StructuredResumeGenerator


class AIOptimizer:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.section_mapper = IntelligentSectionMapper(api_key)
        self.structured_generator = StructuredResumeGenerator(api_key)
        
    def create_optimization_prompt(self, resume_text: str, job_description: str) -> str:
        prompt = f"""You are an ATS optimization expert. Analyze this resume against the job description and provide an optimized version.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Return a JSON with:
1. optimized_resume: Full optimized resume text
2. changes_made: Array of changes with type, location, description
3. keywords_added: New keywords incorporated
4. score: Before/after ATS compatibility score (1-10)

Ensure the optimized resume:
- Includes all relevant keywords from job description
- Uses strong action verbs
- Quantifies achievements where possible
- Maintains professional formatting
- Is ATS-friendly

Return ONLY valid JSON."""
        
        return prompt
    
    def extract_keywords_from_job(self, job_description: str) -> List[str]:
        technical_keywords = []
        
        common_tech_patterns = [
            r'\b(?:Python|Java|JavaScript|C\+\+|C#|Ruby|Go|Swift|Kotlin|PHP|TypeScript)\b',
            r'\b(?:React|Angular|Vue|Node\.js|Django|Flask|Spring|\.NET|Rails)\b',
            r'\b(?:AWS|Azure|GCP|Docker|Kubernetes|Jenkins|CI/CD|DevOps)\b',
            r'\b(?:SQL|NoSQL|MongoDB|PostgreSQL|MySQL|Redis|Elasticsearch)\b',
            r'\b(?:Machine Learning|AI|Deep Learning|NLP|Computer Vision)\b',
            r'\b(?:Agile|Scrum|Kanban|JIRA|Git|GitHub|GitLab)\b'
        ]
        
        for pattern in common_tech_patterns:
            matches = re.findall(pattern, job_description, re.IGNORECASE)
            technical_keywords.extend(matches)
        
        skill_patterns = r'(?:require[sd]?|must have|experience with|knowledge of|skills?:)\s*([^.]+)'
        skill_matches = re.findall(skill_patterns, job_description, re.IGNORECASE)
        for match in skill_matches:
            words = match.split(',')
            for word in words:
                clean_word = word.strip()
                if 2 < len(clean_word) < 30:
                    technical_keywords.append(clean_word)
        
        return list(set(technical_keywords))
    
    def generate_latex_resume(self, template_path: str, optimized_resume: str, contact_info: Dict) -> str:
        """Use Gemini to generate LaTeX code by mapping resume content to Jake's template"""
        
        # Use embedded template instead of reading from file
        from latex_template import JAKES_TEMPLATE
        jakes_template = JAKES_TEMPLATE
        
        prompt = f"""You are a LaTeX expert. I will provide you with:
1. A LaTeX resume template (Jake's Resume)
2. Resume content that needs to be inserted into this template
3. Contact information

Your task is to return ONLY the complete LaTeX code with the resume content properly mapped into Jake's template structure. 

CRITICAL LaTeX SYNTAX RULES:
- Every \\resumeItem command MUST be followed by curly braces containing the text: \\resumeItem{{text here}}
- NEVER write \\resumeItem without the curly braces
- Each \\resumeItem must be on its own line within \\resumeItemListStart and \\resumeItemListEnd
- Example of CORRECT syntax:
  \\resumeItemListStart
    \\resumeItem{{Developed a REST API using FastAPI}}
    \\resumeItem{{Led a team of 5 engineers}}
  \\resumeItemListEnd

IMPORTANT RULES:
- Keep ALL LaTeX commands, packages, and formatting from the template
- Replace Jake's placeholder content with the provided resume content
- Map sections appropriately (Education, Experience, Skills, etc.)
- Ensure all LaTeX commands are properly closed with matching braces
- Every opening brace {{ must have a closing brace }}
- Maintain the exact structure of resumeSubheading, resumeItem, etc.
- Return ONLY valid LaTeX code, no explanations
- DO NOT include placeholder text like [quantify], [specific metric], [improvement percentage], etc.
- If specific metrics are not available, make reasonable estimates based on context
- Example: Instead of "Improved performance by [X%]", write "Improved performance by 25%"
- Example: Instead of "Led team of [number] engineers", write "Led team of 5 engineers"
- Generate COMPLETE content - no instructions or suggestions for the user
- Make educated guesses for dates, locations, and details based on context
- For dates, use formats like "Jan 2023 - Present" or "2022 - 2023"
- For locations, use city names or "Remote" if unclear
- ALWAYS ensure \\resumeItem commands have their content in curly braces

IMPORTANT: The template I'm providing already contains all command definitions like \\newcommand{{\\resumeItem}}. 
DO NOT copy these command definitions. Only use them to format the resume content.

Replace ONLY the CONTENT in the template with the actual resume content below:
- Replace Jake Ryan's information with the actual contact info
- Replace the sample education entries with actual education  
- Replace the sample experience entries with actual experience
- Replace the sample skills with actual skills
- KEEP ALL SPACING COMMANDS AND STRUCTURE EXACTLY AS IN THE TEMPLATE
- The template is professionally designed with specific spacing - DO NOT modify it
- IMPORTANT: Look at how Jake's template spaces sections - maintain that EXACT spacing

DO NOT include:
- Command definitions (\\newcommand)
- Template comments
- The words "ListStart" or "ListEnd" as visible text
- Placeholder text like [1] or [0]

CRITICAL SPACING RULES to prevent overlapping:
- COPY THE EXACT STRUCTURE from the template - each section has specific formatting
- IMPORTANT: Each major section (Education, Experience, Projects, Skills) MUST:
  1. Start with \\section{{Section Name}}
  2. Have proper list structure with \\resumeSubHeadingListStart and \\resumeSubHeadingListEnd
  3. Keep the EXACT spacing between sections as shown in the template
- For EXPERIENCE section, use EXACTLY this structure:
\\section{{Experience}}
  \\resumeSubHeadingListStart
    \\resumeSubheading
      {{Job Title}}{{Date Range}}
      {{Company Name}}{{Location}}
      \\resumeItemListStart
        \\resumeItem{{Achievement 1}}
        \\resumeItem{{Achievement 2}}
      \\resumeItemListEnd
  \\resumeSubHeadingListEnd
- NEVER add extra \\vspace, \\newline, or blank lines
- The template spacing is PERFECT - just replace the content, not the structure

TEMPLATE:
{jakes_template}

CONTACT INFO:
Name: {contact_info.get('name', 'Your Name')}
Email: {contact_info.get('email', 'email@example.com')}
Phone: {contact_info.get('phone', '123-456-7890')}
LinkedIn: {contact_info.get('linkedin', 'linkedin.com/in/profile')}

RESUME CONTENT TO INSERT:
{optimized_resume}

Return ONLY the complete LaTeX code with the resume content properly inserted, starting with \\documentclass and ending with \\end{{document}}."""

        try:
            response = self.model.generate_content(prompt)
            latex_code = response.text.strip()
            
            # Clean up the response - remove any markdown code blocks
            if latex_code.startswith('```'):
                latex_code = latex_code.split('\n', 1)[1]
            if latex_code.endswith('```'):
                latex_code = latex_code.rsplit('\n', 1)[0]
            
            # Don't do any post-processing - just return what Gemini gives us
            # The issue is that post-processing is breaking the LaTeX
            return latex_code
            
        except Exception as e:
            print(f"Error generating LaTeX with Gemini: {e}")
            raise
    
    def optimize_resume_structured(self, resume_data: Dict, job_description: str, job_title: str = "", company_name: str = "") -> Dict:
        """
        New structured approach: AI maps sections intelligently, then optimizes each section
        """
        try:
            resume_text = resume_data.get('formatted_text', resume_data.get('raw_text', ''))
            
            # Step 1: Use AI to intelligently map sections
            print("Step 1: Analyzing and mapping resume sections...")
            structured_resume = self.section_mapper.analyze_and_map_sections(resume_text)
            
            # Step 2: Optimize each section against job description  
            print("Step 2: Optimizing each section for ATS compatibility...")
            optimized_resume = self.structured_generator.optimize_structured_resume(
                structured_resume, job_description, job_title, company_name
            )
            
            # Step 3: Generate LaTeX using structured data
            print("Step 3: Generating LaTeX from structured data...")
            latex_code = self.structured_generator.generate_structured_latex(optimized_resume)
            
            # Prepare result in expected format
            optimization_summary = optimized_resume.get('optimization_summary', {})
            
            result = {
                'optimized_resume': resume_text,  # Keep original for compatibility
                'structured_resume': optimized_resume,  # New structured data
                'latex_code': latex_code,  # Generated LaTeX
                'changes_made': optimization_summary.get('changes_made', []),
                'keywords_added': optimization_summary.get('keywords_added', []),
                'score': {
                    'before': optimization_summary.get('ats_score_before', 5),
                    'after': optimization_summary.get('ats_score_after', 8)
                },
                'contact_info': optimized_resume.get('contact_info', resume_data.get('contact_info', {}))
            }
            
            return result
            
        except Exception as e:
            print(f"Error during structured optimization: {e}")
            # Fallback to original method
            return self.optimize_resume(resume_data, job_description)
    
    def optimize_resume(self, resume_data: Dict, job_description: str) -> Dict:
        try:
            resume_text = resume_data.get('formatted_text', resume_data.get('raw_text', ''))
            
            prompt = self.create_optimization_prompt(resume_text, job_description)
            
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise ValueError("Could not extract valid JSON from response")
            
            if 'optimized_resume' not in result:
                result['optimized_resume'] = resume_text
            
            if 'changes_made' not in result:
                result['changes_made'] = []
            
            if 'keywords_added' not in result:
                keywords = self.extract_keywords_from_job(job_description)
                result['keywords_added'] = keywords[:10]
            
            if 'score' not in result:
                result['score'] = {'before': 5, 'after': 8}
            
            result['contact_info'] = resume_data.get('contact_info', {})
            
            return result
            
        except Exception as e:
            print(f"Error during optimization: {e}")
            return {
                'optimized_resume': resume_data.get('formatted_text', resume_data.get('raw_text', '')),
                'changes_made': [{'type': 'error', 'description': str(e)}],
                'keywords_added': self.extract_keywords_from_job(job_description)[:10],
                'score': {'before': 5, 'after': 5},
                'contact_info': resume_data.get('contact_info', {}),
                'error': str(e)
            }