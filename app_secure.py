from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Depends, Request, Body, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
import base64
import os
import uuid
from datetime import datetime, timedelta
import json
import tempfile
from pathlib import Path
import re
import hashlib
import logging
from functools import lru_cache
import asyncio
from contextlib import asynccontextmanager

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# JWT for authentication  
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import requests

# Import our existing modules
from resume_parser import ResumeParser
from ai_optimizer import AIOptimizer
from gemini_latex_generator import GeminiLatexGenerator
from resume_generator import ResumeGenerator
import google.generativeai as genai

# Supabase imports
from supabase import create_client, Client
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Supabase JWT configuration
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")  # Get from Supabase dashboard
if not SUPABASE_JWT_SECRET:
    logger.warning("SUPABASE_JWT_SECRET not set - authentication will fail")

# File upload limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = ["application/pdf"]

# Rate limiting
def get_user_id_for_rate_limit(request: Request):
    """Extract user ID from JWT token for rate limiting, fallback to IP"""
    try:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
    except:
        pass
    # Fallback to IP for unauthenticated requests  
    return f"ip:{get_remote_address(request)}"

limiter = Limiter(key_func=get_user_id_for_rate_limit)

# App lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Resume Optimizer API")
    # Schedule cleanup task
    asyncio.create_task(cleanup_old_cache())
    yield
    # Shutdown
    logger.info("Shutting down Resume Optimizer API")

app = FastAPI(
    title="Resume Optimizer API", 
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,  # Disable docs in production
    redoc_url=None  # Disable redoc in production
)

# Add rate limit error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Configure CORS for frontend
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

# For testing, allow all origins if ALLOWED_ORIGINS contains "*"
if "*" in ALLOWED_ORIGINS:
    cors_origins = ["*"]
else:
    cors_origins = ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Add trusted host middleware
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")
# Only add if not using wildcard
if ALLOWED_HOSTS != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

# Initialize Supabase client for development branch
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://fwtazrqqrtqmcsdzzdmi.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY) if SUPABASE_ANON_KEY else None

# Initialize AI Optimizer
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")

# Secure in-memory storage with TTL
from typing import NamedTuple
class CacheEntry(NamedTuple):
    data: Dict
    expires_at: datetime

analysis_cache: Dict[str, CacheEntry] = {}
generation_cache: Dict[str, CacheEntry] = {}
CACHE_TTL_MINUTES = 60

# Authentication
security = HTTPBearer()

def verify_supabase_token(token: str) -> dict:
    """Verify a Supabase JWT token and return the payload"""
    try:
        # Decode and verify the Supabase JWT
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_aud": True}
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except InvalidTokenError as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify the Supabase JWT token from the Authorization header"""
    token = credentials.credentials
    
    # Verify it's a valid Supabase JWT
    payload = verify_supabase_token(token)
    
    # Extract user ID from Supabase token
    user_id = payload.get("sub")  # Supabase uses 'sub' for user ID
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: no user ID")
    
    # Optional: You can also extract email, role, etc.
    # email = payload.get("email")
    # role = payload.get("role")
    
    return user_id

# Cleanup task
async def cleanup_old_cache():
    while True:
        try:
            now = datetime.now()
            # Clean analysis cache
            expired_analyses = [k for k, v in analysis_cache.items() if v.expires_at < now]
            for k in expired_analyses:
                del analysis_cache[k]
            
            # Clean generation cache
            expired_generations = [k for k, v in generation_cache.items() if v.expires_at < now]
            for k in expired_generations:
                # Files are auto-deleted by Supabase signed URL expiry
                # Just remove from cache
                del generation_cache[k]
            
            if expired_analyses or expired_generations:
                logger.info(f"Cleaned up {len(expired_analyses)} analyses and {len(expired_generations)} generations")
        
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
        
        await asyncio.sleep(300)  # Run every 5 minutes

# Pydantic models with validation
class AnalyzeRequest(BaseModel):
    resumeText: str = Field(..., min_length=100, max_length=50000)
    resumeFile: Optional[str] = Field(None, max_length=15_000_000)  # ~10MB base64
    jobDescription: str = Field(..., min_length=50, max_length=10000)
    jobTitle: str = Field(..., min_length=2, max_length=100)
    companyName: str = Field(..., min_length=2, max_length=100)
    
    @validator('companyName')
    def sanitize_company_name(cls, v):
        # Remove special characters that could cause issues
        return re.sub(r'[^\w\s-]', '', v).strip()
    
    @validator('resumeFile')
    def validate_base64_pdf(cls, v):
        if v:
            try:
                # Check if it's valid base64
                decoded = base64.b64decode(v)
                # Check file size
                if len(decoded) > MAX_FILE_SIZE:
                    raise ValueError(f"File size exceeds {MAX_FILE_SIZE/1024/1024}MB limit")
                # Check if it starts with PDF header
                if not decoded.startswith(b'%PDF'):
                    raise ValueError("Invalid PDF file")
            except Exception as e:
                raise ValueError(f"Invalid PDF file: {str(e)}")
        return v

class GenerateRequest(BaseModel):
    analysisId: str = Field(..., pattern=r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
    editType: str = Field(..., pattern=r'^(quick|full)$')
    selectedSections: List[str] = Field(..., max_items=10)
    selectedSkills: List[str] = Field(..., max_items=20)
    additionalInstructions: Optional[str] = Field(None, max_length=500)
    
    @validator('selectedSections', 'selectedSkills')
    def validate_ids(cls, v):
        # Ensure all IDs are safe - allow alphanumeric, hyphens, dots, and spaces
        pattern = re.compile(r'^[\w\s.-]+$')
        for item in v:
            if not pattern.match(item):
                raise ValueError(f"Invalid ID format: {item}")
        return v

# Keep other models the same but add validation...

def escape_latex(text: str) -> str:
    """Properly escape all special LaTeX characters"""
    if not text:
        return ""
    
    # Special handling for backslash - replace with placeholder first
    # to avoid escaping the backslashes in our LaTeX commands
    BACKSLASH_PLACEHOLDER = "<<<BACKSLASH_PLACEHOLDER>>>"
    
    result = text.replace('\\', BACKSLASH_PLACEHOLDER)
    
    # Now escape other characters
    replacements = [
        ('{', r'\{'),  # Left brace
        ('}', r'\}'),  # Right brace  
        ('$', r'\$'),  # Dollar
        ('&', r'\&'),  # Ampersand
        ('%', r'\%'),  # Percent
        ('#', r'\#'),  # Hash
        ('_', r'\_'),  # Underscore
        ('^', r'\textasciicircum{}'),  # Caret
        ('~', r'\textasciitilde{}'),  # Tilde
    ]
    
    for old, new in replacements:
        result = result.replace(old, new)
    
    # Finally, replace backslash placeholder with the LaTeX command
    result = result.replace(BACKSLASH_PLACEHOLDER, r'\textbackslash{}')
    
    return result

def validate_latex_content(content: str) -> bool:
    """Validate LaTeX content before compilation"""
    # Check for unmatched braces (excluding escaped ones)
    temp = content.replace(r'\{', '').replace(r'\}', '')
    open_braces = temp.count('{')
    close_braces = temp.count('}')
    
    if open_braces != close_braces:
        raise ValueError(f"Unmatched braces: {open_braces} open, {close_braces} close")
    
    # Check for required commands
    required = [r'\begin{document}', r'\end{document}']
    for cmd in required:
        if cmd not in content:
            raise ValueError(f"Missing required command: {cmd}")
    
    return True

def create_json_extraction_prompt(optimized_resume: str, contact_info: dict) -> str:
    """Create prompt to extract structured JSON from optimized resume"""
    prompt = f"""Extract the resume content into this EXACT JSON structure. Be very careful to extract ALL information accurately.

IMPORTANT URL HANDLING:
- Keep ALL URLs exactly as they appear in the resume
- Include full URLs (e.g., https://github.com/username/project)
- Do NOT replace URLs with placeholder text like "link" or "website"
- Preserve the actual URL addresses for all links

RESUME CONTENT:
{optimized_resume}

CONTACT INFO PROVIDED:
{json.dumps(contact_info, indent=2)}

Return ONLY valid JSON in this exact format:
{{
  "contact": {{
    "name": "{contact_info.get('name', 'Your Name')}",
    "email": "{contact_info.get('email', 'email@example.com')}",
    "phone": "{contact_info.get('phone', '123-456-7890')}",
    "linkedin": "{contact_info.get('linkedin', 'linkedin.com/in/profile')}",
    "github": "{contact_info.get('github', 'github.com/profile')}"
  }},
  "education": [
    {{
      "school": "University Name",
      "location": "City, State",
      "degree": "Degree and Major",
      "dates": "Start Year - End Year",
      "gpa": "3.8/4.0",
      "honors": ["Dean's List", "Honor Society"]
    }}
  ],
  "experience": [
    {{
      "title": "Job Title",
      "company": "Company Name",
      "location": "City, State",
      "dates": "Start Date - End Date",
      "bullets": [
        "Achievement or responsibility 1",
        "Achievement or responsibility 2"
      ]
    }}
  ],
  "projects": [
    {{
      "name": "Project Name",
      "tech": "Python, Flask, React, PostgreSQL",
      "dates": "",  // Use empty string if no dates
      "link": "",  // Project URL if available (e.g., github.com/user/project)
      "bullets": [
        "What you built and why",
        "Key features or achievements",
        "Include any URLs mentioned in the bullets exactly as they appear"
      ]
    }}
  ],
  "skills": {{
    "Languages": "List of programming languages",
    "Frameworks": "List of frameworks",
    "Developer Tools": "List of tools",
    "Libraries": "List of libraries"
  }}
}}

IMPORTANT:
- Extract ALL sections from the resume
- If a section doesn't exist, use empty array []
- For skills, group them by category as shown
- Keep all dates, locations, and other details exactly as they appear
- Do not summarize or shorten content
- NEVER include placeholder text like [add details], [quantify], etc.
- All content must be complete and ready to use
- If you see placeholder text in the input, replace it with reasonable estimates
- For optional fields like dates on projects: if not present, use empty string "" not "NONE" or "N/A"
- Leave fields blank when information is missing rather than writing placeholder text
- PRESERVE ALL URLs - never replace them with "link" or other placeholder text
- Keep GitHub, LinkedIn, portfolio, and other web links exactly as they appear
- Extract project links into the "link" field when available
"""
    return prompt

def build_latex_from_json(resume_json: dict) -> str:
    """Build LaTeX document by injecting JSON data into Jake's template structure"""
    from latex_template import JAKES_TEMPLATE
    
    # Read Jake's template to understand structure
    template_lines = JAKES_TEMPLATE.split('\n')
    
    # Start building the LaTeX document
    latex_parts = []
    
    # Copy everything up to and including \begin{document}
    in_document = False
    for line in template_lines:
        latex_parts.append(line)
        if '\\begin{document}' in line:
            in_document = True
            break
    
    # Add spacing
    latex_parts.append('')
    
    # Build the heading section with escaped content
    contact = resume_json['contact']
    latex_parts.append(f"""\\begin{{center}}
    \\textbf{{\\Huge \\scshape {escape_latex(contact['name'])}}} \\\\ \\vspace{{1pt}}
    \\small {escape_latex(contact['phone'])} $|$ \\href{{mailto:{contact['email']}}}{{\\underline{{{escape_latex(contact['email'])}}}}} $|$ 
    \\href{{https://{contact['linkedin']}}}{{\\underline{{{escape_latex(contact['linkedin'])}}}}} $|$
    \\href{{https://{contact['github']}}}{{\\underline{{{escape_latex(contact['github'])}}}}}
\\end{{center}}

""")
    
    # Education Section
    if resume_json['education']:
        latex_parts.append("%-----------EDUCATION-----------")
        latex_parts.append("\\section{Education}")
        latex_parts.append("  \\resumeSubHeadingListStart")
        
        for edu in resume_json['education']:
            latex_parts.append(f"""    \\resumeSubheading
      {{{escape_latex(edu['school'])}}}{{{escape_latex(edu['location'])}}}
      {{{escape_latex(edu['degree'])}}}{{{escape_latex(edu['dates'])}}}""")
            
            # Add GPA or honors if present
            if edu.get('gpa') or edu.get('honors'):
                latex_parts.append("      \\resumeItemListStart")
                if edu.get('gpa'):
                    latex_parts.append(f"        \\resumeItem{{GPA: {escape_latex(str(edu['gpa']))}}}")
                for honor in edu.get('honors', []):
                    latex_parts.append(f"        \\resumeItem{{{escape_latex(honor)}}}")
                latex_parts.append("      \\resumeItemListEnd")
        
        latex_parts.append("  \\resumeSubHeadingListEnd\n")
    
    # Experience Section
    if resume_json['experience']:
        latex_parts.append("%-----------EXPERIENCE-----------")
        latex_parts.append("\\section{Experience}")
        latex_parts.append("  \\resumeSubHeadingListStart\n")
        
        for exp in resume_json['experience']:
            latex_parts.append(f"""    \\resumeSubheading
      {{{escape_latex(exp['title'])}}}{{{escape_latex(exp['dates'])}}}
      {{{escape_latex(exp['company'])}}}{{{escape_latex(exp['location'])}}}
      \\resumeItemListStart""")
            
            for bullet in exp['bullets']:
                # Use comprehensive escaping function
                escaped_bullet = escape_latex(bullet)
                latex_parts.append(f"        \\resumeItem{{{escaped_bullet}}}")
            
            latex_parts.append("      \\resumeItemListEnd\n")
        
        latex_parts.append("  \\resumeSubHeadingListEnd\n")
    
    # Projects Section
    if resume_json.get('projects'):
        latex_parts.append("%-----------PROJECTS-----------")
        latex_parts.append("\\section{Projects}")
        latex_parts.append("    \\resumeSubHeadingListStart")
        
        for proj in resume_json['projects']:
            # Handle project name with optional link
            project_name = escape_latex(proj['name'])
            if proj.get('link'):
                # Make project name clickable
                link = proj['link']
                if not link.startswith(('http://', 'https://')):
                    link = 'https://' + link
                project_name = f"\\href{{{link}}}{{\\underline{{{project_name}}}}}"
            
            # Handle projects with or without dates
            dates_part = proj.get('dates', '')
            if dates_part and dates_part.upper() not in ['NONE', 'N/A', 'NA', 'NULL']:
                latex_parts.append(f"""      \\resumeProjectHeading
          {{\\textbf{{{project_name}}} $|$ \\emph{{{escape_latex(proj.get('tech', ''))}}}}}{{{escape_latex(dates_part)}}}""")
            else:
                # For projects without dates, use empty braces
                latex_parts.append(f"""      \\resumeProjectHeading
          {{\\textbf{{{project_name}}} $|$ \\emph{{{escape_latex(proj.get('tech', ''))}}}}}{{}}""")
            
            if proj.get('bullets'):
                latex_parts.append("          \\resumeItemListStart")
                for bullet in proj['bullets']:
                    # Use comprehensive escaping function
                    escaped_bullet = escape_latex(bullet)
                    latex_parts.append(f"            \\resumeItem{{{escaped_bullet}}}")
                latex_parts.append("          \\resumeItemListEnd")
        
        latex_parts.append("    \\resumeSubHeadingListEnd\n")
    
    # Skills Section
    if resume_json.get('skills'):
        latex_parts.append("%-----------PROGRAMMING SKILLS-----------")
        latex_parts.append("\\section{Technical Skills}")
        latex_parts.append(" \\begin{itemize}[leftmargin=0.15in, label={}]")
        latex_parts.append("    \\small{\\item{")
        
        skills_items = []
        for category, items in resume_json['skills'].items():
            if items:  # Only add if there are items
                skills_items.append(f"     \\textbf{{{escape_latex(category)}}}: {escape_latex(items)}")
        
        latex_parts.append(" \\\\\n".join(skills_items))
        
        latex_parts.append("    }}")
        latex_parts.append(" \\end{itemize}\n")
    
    # Close the document
    latex_parts.append("\n%-------------------------------------------")
    latex_parts.append("\\end{document}")
    
    return '\n'.join(latex_parts)

@app.get("/")
async def root():
    return {"status": "healthy", "service": "Resume Optimizer API", "port": os.getenv("PORT", "8000")}

@app.get("/health")
async def health_check():
    # Simple health check that doesn't depend on external services
    return {"status": "healthy", "version": "1.0.0"}

# Remove the mock auth endpoint - frontend should use Supabase Auth directly
# The frontend will get tokens from Supabase and send them to our API

@app.get("/api/auth/verify")
@limiter.limit("10/minute")
async def verify_auth(request: Request, user_id: str = Depends(verify_token)):
    """Verify that the user's Supabase token is valid"""
    return {
        "authenticated": True,
        "user_id": user_id,
        "message": "Token is valid"
    }

@app.post("/api/resume/analyze")
@limiter.limit("10/minute")
async def analyze_resume(
    request: Request,
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    job_title: str = Form(..., min_length=2, max_length=100),
    company_name: str = Form(..., min_length=2, max_length=100),
    user_id: str = Depends(verify_token)
):
    """Analyze resume PDF against job description and provide optimization suggestions"""
    try:
        analysis_id = str(uuid.uuid4())
        
        # Sanitize company name
        safe_company_name = re.sub(r'[^\w\s-]', '', company_name).strip()
        
        # Log the analysis request
        logger.info(f"Analysis request from user {user_id} for {safe_company_name}")
        logger.info(f"Resume file: {resume.filename}, size: {resume.size if hasattr(resume, 'size') else 'unknown'}")
        
        # Validate file type
        if not resume.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are accepted")
        
        # Read PDF content
        pdf_content = await resume.read()
        
        # Check file size (10MB limit)
        if len(pdf_content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File size exceeds {MAX_FILE_SIZE/1024/1024}MB limit")
        
        # Save temporarily and parse
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(pdf_content)
            tmp_file_path = tmp_file.name
        
        try:
            # Initialize parser with AI capabilities
            resume_parser = ResumeParser(gemini_api_key=GEMINI_API_KEY)
            resume_text = resume_parser.extract_text_from_pdf(tmp_file_path)
            contact_info = resume_parser.extract_contact_info(resume_text)
            
            logger.info(f"Extracted {len(resume_text)} characters from PDF")
            logger.info(f"Contact info: {bool(contact_info)}")
            
            # Parse sections using AI-powered parsing
            resume_data = resume_parser.parse_resume(tmp_file_path)
            
            logger.info(f"AI parsing used: {resume_data.get('ai_parsed', False)}")
            if resume_data.get('section_mappings'):
                logger.info(f"Section mappings: {resume_data['section_mappings']}")
        except Exception as parse_error:
            logger.error(f"PDF parsing error: {str(parse_error)}")
            logger.error(f"Error type: {type(parse_error).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(parse_error)}")
        finally:
            # Clean up temp file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
        
        # Initialize optimizer
        optimizer = AIOptimizer(GEMINI_API_KEY)
        
        # Get optimization suggestions
        keywords = optimizer.extract_keywords_from_job(job_description)
        
        # Calculate scores
        resume_text_lower = resume_text.lower()
        matched_keywords = [kw for kw in keywords if kw.lower() in resume_text_lower]
        current_score = min(50 + len(matched_keywords) * 3, 100)
        potential_score = min(current_score + 20, 95)
        
        # Generate suggestions based on missing keywords
        missing_keywords = [kw for kw in keywords if kw.lower() not in resume_text_lower]
        
        # Create suggested sections
        suggested_sections = []
        
        # Check experience section
        if "experience" in resume_text_lower:
            exp_start = resume_text_lower.find("experience")
            exp_section = resume_text[exp_start:exp_start+500] if exp_start != -1 else ""
            if exp_section and len(missing_keywords) > 0:
                suggested_sections.append({
                    "id": f"exp-{uuid.uuid4().hex[:8]}",
                    "type": "experience",
                    "original": exp_section[:200] + "...",
                    "suggested": f"Add keywords: {', '.join(missing_keywords[:3])}",
                    "improvements": ["Add missing technologies", "Quantify achievements", "Use action verbs"]
                })
        
        # Create suggested skills
        suggested_skills = []
        for skill in missing_keywords[:10]:  # Top 10 missing skills
            suggested_skills.append({
                "id": f"skill-{uuid.uuid4().hex[:8]}",
                "skill": skill,
                "relevance": "high" if skill.lower() in ["python", "javascript", "react"] else "medium",
                "reason": f"Required for {job_title}"
            })
        
        # Store analysis data in cache with TTL
        expires_at = datetime.now() + timedelta(minutes=CACHE_TTL_MINUTES)
        analysis_cache[analysis_id] = CacheEntry(
            data={
                'user_id': user_id,
                'request': {
                    'jobDescription': job_description,
                    'jobTitle': job_title,
                    'companyName': safe_company_name
                },
                'resume_data': resume_data,
                'keywords': keywords,
                'matched_keywords': matched_keywords,
                'missing_keywords': missing_keywords,
                'suggested_sections': suggested_sections,
                'suggested_skills': suggested_skills,
                'timestamp': datetime.now().isoformat()
            },
            expires_at=expires_at
        )
        
        # Return complete response matching frontend expectations
        return {
            "success": True,
            "data": {
                "analysisId": analysis_id,
                "summary": {
                    "overallScore": current_score / 10.0,  # Convert to 0-10 scale
                    "keywordMatches": matched_keywords,
                    "missingSkills": missing_keywords[:10],  # Top 10 missing skills
                    "suggestions": [
                        f"Add {len(missing_keywords)} missing keywords from the job description",
                        "Quantify your achievements with specific metrics",
                        "Emphasize experience with required technologies",
                        f"Highlight your {job_title} relevant experience"
                    ]
                },
                "sections": suggested_sections,
                "skills": {
                    "current": matched_keywords,
                    "suggested": matched_keywords + missing_keywords[:5],  # Current + top 5 missing
                    "relevanceScores": {
                        kw: 0.9 if kw in matched_keywords else 0.7 
                        for kw in (matched_keywords + missing_keywords[:5])
                    }
                }
            }
        }
        
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred during analysis")

@app.post("/api/resume/generate")
@limiter.limit("5/minute")
async def generate_resume(
    request: Request,
    generate_request: GenerateRequest,
    user_id: str = Depends(verify_token),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Generate optimized resume based on analysis and user selections"""
    try:
        # Retrieve analysis data
        if generate_request.analysisId not in analysis_cache:
            raise HTTPException(status_code=404, detail="Analysis not found or expired")
        
        cache_entry = analysis_cache[generate_request.analysisId]
        analysis_data = cache_entry.data
        
        # Verify the analysis belongs to the authenticated user
        if analysis_data['user_id'] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized access to analysis")
        
        generation_id = str(uuid.uuid4())
        
        # Generate the optimized resume
        logger.info(f"Generating resume for user {user_id}, generation {generation_id}")
        logger.info(f"Edit type: {generate_request.editType}")
        logger.info(f"Selected sections: {len(generate_request.selectedSections)}")
        logger.info(f"Selected skills: {len(generate_request.selectedSkills)}")
        
        # Create a temporary directory for this generation
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Created temp directory: {temp_dir}")
            
            # Initialize AI optimizer
            logger.info("Initializing AI optimizer...")
            optimizer = AIOptimizer(GEMINI_API_KEY)
            
            # Get the optimized resume text
            resume_data = analysis_data['resume_data']
            logger.info(f"Resume data keys: {list(resume_data.keys())}")
            logger.info(f"Resume text length: {len(resume_data.get('raw_text', ''))}")
            
            try:
                logger.info("Calling Gemini for structured optimization...")
                # Use the new structured approach
                optimization_result = optimizer.optimize_resume_structured(
                    resume_data,
                    analysis_data['request']['jobDescription'],
                    analysis_data['request']['jobTitle'],
                    analysis_data['request']['companyName']
                )
                logger.info("Structured optimization complete")
                logger.info(f"Optimized text length: {len(optimization_result.get('optimized_resume', ''))}")
                
                # Check if we have LaTeX code from structured generation
                if 'latex_code' in optimization_result:
                    logger.info("Using LaTeX code from structured generation")
                    latex_code = optimization_result['latex_code']
                    
                    # Save LaTeX file
                    tex_path = Path(temp_dir) / f"{generation_id}.tex"
                    with open(tex_path, 'w') as f:
                        f.write(latex_code)
                    
                    # Compile to PDF
                    output_path = Path(temp_dir) / f"{generation_id}.pdf"
                    latex_generator = GeminiLatexGenerator(optimizer)
                    success = latex_generator._compile_latex(str(tex_path), str(output_path))
                    
                    if not success:
                        logger.warning("Structured LaTeX compilation failed, falling back to JSON approach")
                        optimization_result.pop('latex_code', None)  # Remove to trigger fallback
                    else:
                        logger.info("Structured LaTeX compilation successful")
                        
            except Exception as opt_error:
                logger.error(f"Structured optimization error: {str(opt_error)}")
                logger.info("Falling back to original optimization method...")
                try:
                    optimization_result = optimizer.optimize_resume(
                        resume_data,
                        analysis_data['request']['jobDescription']
                    )
                    logger.info("Fallback optimization complete")
                except Exception as fallback_error:
                    logger.error(f"Fallback optimization also failed: {str(fallback_error)}")
                    raise ValueError(f"Failed to optimize resume: {str(fallback_error)}")
            
            # Only use JSON-based approach if structured generation didn't work
            if 'latex_code' not in optimization_result:
                logger.info("Using JSON-based LaTeX generation approach...")
                
                # Extract structured data from optimized resume
                genai.configure(api_key=GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                json_prompt = create_json_extraction_prompt(
                    optimization_result['optimized_resume'],
                    optimization_result['contact_info']
                )
                
                try:
                    logger.info("Extracting structured data from Gemini...")
                    response = model.generate_content(json_prompt)
                    json_text = response.text.strip()
                    
                    # Clean up the response
                    if json_text.startswith('```json'):
                        json_text = json_text[7:]
                    if json_text.endswith('```'):
                        json_text = json_text[:-3]
                    
                    resume_json = json.loads(json_text)
                    logger.info("Successfully extracted structured data")
                    
                except Exception as e:
                    logger.error(f"JSON extraction failed: {e}")
                    # Fallback to traditional method
                    logger.info("Falling back to traditional LaTeX generation...")
                    latex_generator = GeminiLatexGenerator(optimizer)
                    output_path = Path(temp_dir) / f"{generation_id}.pdf"
                    latex_generator.generate_latex(
                        optimized_data=optimization_result,
                        output_path=str(output_path)
                    )
                else:
                    # Build LaTeX from JSON
                    logger.info("Building LaTeX from structured data...")
                    latex_code = build_latex_from_json(resume_json)
                    
                    # Save LaTeX file
                    tex_path = Path(temp_dir) / f"{generation_id}.tex"
                    with open(tex_path, 'w') as f:
                        f.write(latex_code)
                    
                    # Validate LaTeX before compilation
                    try:
                        validate_latex_content(latex_code)
                    except ValueError as e:
                        logger.error(f"LaTeX validation failed: {e}")
                        raise ValueError(f"Invalid LaTeX generated: {e}")
                    
                    # Compile to PDF
                    output_path = Path(temp_dir) / f"{generation_id}.pdf"
                    latex_generator = GeminiLatexGenerator(optimizer)
                    success = latex_generator._compile_latex(str(tex_path), str(output_path))
                    
                    if not success:
                        raise ValueError("LaTeX compilation failed")
                    
                    logger.info(f"PDF generated at {output_path}")
                    logger.info(f"PDF size: {os.path.getsize(output_path) if output_path.exists() else 'not found'}")
            
            # Upload to Supabase storage with temporary path
            supabase_url = os.getenv("SUPABASE_URL")
            # Use service role key for uploads (bypasses RLS)
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_ANON_KEY"))
            
            if not supabase_url or not supabase_key:
                raise ValueError("Supabase configuration missing")
            
            supabase = create_client(supabase_url, supabase_key)
            
            with open(output_path, 'rb') as f:
                pdf_content = f.read()
            
            # Use generation ID in path for uniqueness
            storage_path = f"temp/{user_id}/{generation_id}.pdf"
            
            try:
                # Upload to storage
                response = supabase.storage.from_('resume-outputs').upload(
                    storage_path,
                    pdf_content,
                    {"content-type": "application/pdf"}
                )
                logger.info(f"PDF uploaded to Supabase: {storage_path}")
            except Exception as e:
                # If file already exists, that's ok (idempotent)
                if "already exists" not in str(e):
                    logger.error(f"Supabase upload error: {e}")
                    raise
            
            # Create signed URL that expires in 30 minutes
            signed_url_response = supabase.storage.from_('resume-outputs').create_signed_url(
                storage_path,
                expires_in=1800  # 30 minutes
            )
            
            # The response is a dict with 'signedUrl' key directly
            if isinstance(signed_url_response, dict):
                if 'error' in signed_url_response:
                    raise ValueError(f"Failed to create signed URL: {signed_url_response['error']}")
                signed_url = signed_url_response.get('signedUrl') or signed_url_response.get('signedURL')
            else:
                # It might be an object with data attribute
                signed_url = signed_url_response.data.get('signedUrl') or signed_url_response.data.get('signedURL')
            
            if not signed_url:
                logger.error(f"Unexpected signed URL response format: {signed_url_response}")
                # Fallback to public URL
                signed_url = supabase.storage.from_('resume-outputs').get_public_url(storage_path)
            
            logger.info(f"Created signed URL for temporary download")
        
        # Sanitize filename
        safe_company_name = re.sub(r'[^\w\s-]', '', analysis_data['request']['companyName'])
        safe_company_name = re.sub(r'[-\s]+', '-', safe_company_name)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"resume_{safe_company_name}_{timestamp}.pdf"
        
        # Store with TTL
        expires_at = datetime.now() + timedelta(minutes=CACHE_TTL_MINUTES)
        generation_cache[generation_id] = CacheEntry(
            data={
                'signed_url': signed_url,
                'storage_path': storage_path,
                'filename': filename,
                'user_id': user_id,
                'timestamp': datetime.now()
            },
            expires_at=expires_at
        )
        
        # Schedule cleanup
        background_tasks.add_task(
            cleanup_generation,
            generation_id,
            delay_minutes=CACHE_TTL_MINUTES
        )
        
        return {
            "success": True,
            "data": {
                "generationId": generation_id,
                "status": "completed",
                "downloadUrl": signed_url,
                "filename": filename,
                "expiresIn": 1800,  # 30 minutes
                "message": "Your resume has been generated successfully"
            }
        }
        
    except Exception as e:
        logger.error(f"Generation error for user {user_id}: {str(e)}")
        # In development, return the actual error for debugging
        if os.getenv("ENVIRONMENT", "development") == "development":
            raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")
        else:
            raise HTTPException(status_code=500, detail="An error occurred during generation")

@app.get("/api/resume/download/{generation_id}")
@limiter.limit("20/minute")
async def download_resume(
    request: Request,
    generation_id: str,
    user_id: str = Depends(verify_token)
):
    """Download generated resume"""
    # Validate generation_id format
    if not re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', generation_id):
        raise HTTPException(status_code=400, detail="Invalid generation ID")
    
    if generation_id not in generation_cache:
        raise HTTPException(status_code=404, detail="Generation not found or expired")
    
    cache_entry = generation_cache[generation_id]
    data = cache_entry.data
    
    # Verify the generation belongs to the authenticated user
    if data['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    # Get the signed URL from cache
    signed_url = data.get('signed_url')
    if not signed_url:
        raise HTTPException(status_code=404, detail="Download URL not found or expired")
    
    # Redirect to the signed URL
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=signed_url, status_code=302)

async def cleanup_generation(generation_id: str, delay_minutes: int):
    """Clean up generated files from Supabase after delay"""
    await asyncio.sleep(delay_minutes * 60)
    try:
        if generation_id in generation_cache:
            data = generation_cache[generation_id].data
            storage_path = data.get('storage_path')
            
            if storage_path:
                # Delete from Supabase storage
                supabase_url = os.getenv("SUPABASE_URL")
                # Use service role key for deletions (bypasses RLS)
                supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_ANON_KEY"))
                
                if supabase_url and supabase_key:
                    supabase = create_client(supabase_url, supabase_key)
                    try:
                        supabase.storage.from_('resume-outputs').remove([storage_path])
                        logger.info(f"Deleted {storage_path} from Supabase storage")
                    except Exception as e:
                        logger.error(f"Failed to delete from Supabase: {e}")
            
            del generation_cache[generation_id]
    except Exception as e:
        logger.error(f"Cleanup error for {generation_id}: {e}")

if __name__ == "__main__":
    import uvicorn
    # In production, use gunicorn with multiple workers
    uvicorn.run(app, host="127.0.0.1", port=8000)