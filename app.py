from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import base64
import os
import uuid
from datetime import datetime
import json
import tempfile
from pathlib import Path

# Import our existing modules
from resume_parser import ResumeParser
from ai_optimizer import AIOptimizer
from gemini_latex_generator import GeminiLatexGenerator
from resume_generator import ResumeGenerator

# Supabase imports
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Resume Optimizer API", version="1.0.0")

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client for development branch
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://fwtazrqqrtqmcsdzzdmi.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY) if SUPABASE_ANON_KEY else None

# Initialize AI Optimizer
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")

# In-memory storage for analysis results (use Redis in production)
analysis_cache = {}
generation_cache = {}

# Pydantic models
class AnalyzeRequest(BaseModel):
    resumeText: str
    resumeFile: Optional[str] = None  # base64 encoded PDF
    jobDescription: str
    jobTitle: str
    companyName: str
    userId: str

class SuggestedSection(BaseModel):
    id: str
    sectionName: str
    currentContent: str
    suggestedChanges: str
    impact: str
    selected: bool = True

class SuggestedSkill(BaseModel):
    id: str
    skill: str
    relevance: str
    reason: str

class EditOptions(BaseModel):
    quickEdit: Dict[str, str]
    fullEdit: Dict[str, str]

class AnalyzeResponse(BaseModel):
    analysisId: str
    currentScore: int
    potentialScore: int
    suggestedSections: List[SuggestedSection]
    suggestedSkills: List[SuggestedSkill]
    missingKeywords: List[str]
    editOptions: EditOptions

class GenerateRequest(BaseModel):
    analysisId: str
    editType: str  # "quick" or "full"
    selectedSections: List[str]
    selectedSkills: List[str]
    additionalInstructions: Optional[str] = None

class GenerateResponse(BaseModel):
    generationId: str
    status: str
    previewUrl: str
    downloadUrl: str
    fileName: str
    finalScore: int
    improvements: Dict[str, Dict[str, Any]]
    changelog: List[str]


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/api/resume/analyze", response_model=AnalyzeResponse)
async def analyze_resume(request: AnalyzeRequest):
    """Analyze resume against job description and provide optimization suggestions"""
    try:
        analysis_id = str(uuid.uuid4())
        
        # Parse resume from text or file
        resume_parser = ResumeParser()
        
        if request.resumeFile:
            # Decode base64 PDF and save temporarily
            pdf_data = base64.b64decode(request.resumeFile)
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(pdf_data)
                tmp_path = tmp_file.name
            
            resume_data = resume_parser.parse_resume(tmp_path)
            os.unlink(tmp_path)
        else:
            # Create a temporary text-based resume structure
            resume_data = {
                'raw_text': request.resumeText,
                'formatted_text': request.resumeText,
                'contact_info': {},
                'sections': {}
            }
        
        # Initialize optimizer
        optimizer = AIOptimizer(GEMINI_API_KEY)
        
        # Get optimization suggestions (not the full optimization yet)
        # For now, we'll analyze the resume and job description
        keywords = optimizer.extract_keywords_from_job(request.jobDescription)
        
        # Calculate scores (simplified scoring)
        resume_text_lower = request.resumeText.lower()
        matched_keywords = [kw for kw in keywords if kw.lower() in resume_text_lower]
        current_score = min(50 + len(matched_keywords) * 3, 100)
        potential_score = min(current_score + 20, 95)
        
        # Generate suggestions based on analysis
        suggested_sections = []
        
        # Check for professional summary
        if 'summary' not in resume_text_lower and 'objective' not in resume_text_lower:
            suggested_sections.append(SuggestedSection(
                id="section-summary",
                sectionName="Professional Summary",
                currentContent="No summary found",
                suggestedChanges=f"Add a professional summary highlighting your experience relevant to {request.jobTitle} at {request.companyName}",
                impact="high",
                selected=True
            ))
        
        # Analyze experience section
        if 'experience' in resume_text_lower:
            suggested_sections.append(SuggestedSection(
                id="section-experience",
                sectionName="Work Experience",
                currentContent="Current experience section found",
                suggestedChanges="Quantify achievements with metrics, use action verbs, and align with job requirements",
                impact="high",
                selected=True
            ))
        
        # Analyze skills section
        missing_skills = [kw for kw in keywords[:10] if kw.lower() not in resume_text_lower]
        if missing_skills:
            suggested_sections.append(SuggestedSection(
                id="section-skills",
                sectionName="Technical Skills",
                currentContent="Current skills section",
                suggestedChanges=f"Add missing skills: {', '.join(missing_skills[:5])}",
                impact="medium",
                selected=True
            ))
        
        # Generate suggested skills
        suggested_skills = []
        for i, skill in enumerate(missing_skills[:5]):
            suggested_skills.append(SuggestedSkill(
                id=f"skill-{i+1}",
                skill=skill,
                relevance="high" if i < 3 else "medium",
                reason=f"{'Required' if i < 3 else 'Mentioned'} in job description"
            ))
        
        # Store analysis data in cache
        analysis_cache[analysis_id] = {
            'request': request,
            'resume_data': resume_data,
            'keywords': keywords,
            'matched_keywords': matched_keywords,
            'timestamp': datetime.now()
        }
        
        response = AnalyzeResponse(
            analysisId=analysis_id,
            currentScore=current_score,
            potentialScore=potential_score,
            suggestedSections=suggested_sections,
            suggestedSkills=suggested_skills,
            missingKeywords=missing_skills[:10],
            editOptions=EditOptions(
                quickEdit={
                    "description": "AI optimizes selected sections only",
                    "estimatedTime": "30 seconds",
                    "scoreImprovement": "+10-15 points"
                },
                fullEdit={
                    "description": "Complete resume rewrite with AI",
                    "estimatedTime": "2 minutes",
                    "scoreImprovement": "+15-25 points"
                }
            )
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/resume/generate", response_model=GenerateResponse)
async def generate_resume(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Generate optimized resume based on analysis and user selections"""
    try:
        # Retrieve analysis data
        if request.analysisId not in analysis_cache:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        analysis_data = analysis_cache[request.analysisId]
        original_request = analysis_data['request']
        resume_data = analysis_data['resume_data']
        
        generation_id = str(uuid.uuid4())
        
        # Initialize optimizer
        optimizer = AIOptimizer(GEMINI_API_KEY)
        
        # Prepare job description with emphasis on selected skills
        enhanced_job_desc = original_request.jobDescription
        if request.selectedSkills:
            # Add selected skills to job description to ensure they're included
            skill_emphasis = f"\n\nIMPORTANT SKILLS TO INCLUDE: {', '.join(request.selectedSkills)}"
            enhanced_job_desc += skill_emphasis
        
        # Add user instructions if provided
        if request.additionalInstructions:
            enhanced_job_desc += f"\n\nADDITIONAL REQUIREMENTS: {request.additionalInstructions}"
        
        # Optimize resume
        optimized_data = optimizer.optimize_resume(resume_data, enhanced_job_desc)
        
        # Generate PDF using LaTeX
        generator = GeminiLatexGenerator(optimizer)
        
        # Create output directory
        output_dir = Path("generated_resumes")
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"optimized_resume_{original_request.companyName}_{timestamp}.pdf"
        output_path = output_dir / filename
        
        # Generate the PDF
        generator.generate_latex(optimized_data, str(output_path))
        
        # Upload to Supabase storage if available
        preview_url = f"/api/resume/preview/{generation_id}"
        download_url = f"/api/resume/download/{generation_id}"
        
        if supabase:
            try:
                # Upload to Supabase storage
                with open(output_path, 'rb') as f:
                    file_data = f.read()
                
                storage_path = f"resumes/{original_request.userId}/{generation_id}/{filename}"
                supabase.storage.from_('resume-uploads').upload(
                    storage_path,
                    file_data,
                    file_options={"content-type": "application/pdf"}
                )
                
                # Get public URL
                storage_url = supabase.storage.from_('resume-uploads').get_public_url(storage_path)
                preview_url = storage_url
                download_url = storage_url
                
            except Exception as e:
                print(f"Supabase upload failed: {e}")
                # Fall back to local serving
        
        # Calculate improvements
        keywords = analysis_data['keywords']
        matched_before = len(analysis_data['matched_keywords'])
        optimized_text = optimized_data.get('optimized_resume', '').lower()
        matched_after = len([kw for kw in keywords if kw.lower() in optimized_text])
        
        final_score = min(50 + matched_after * 3, 95)
        
        # Generate changelog
        changelog = []
        if matched_after > matched_before:
            changelog.append(f"Added {matched_after - matched_before} relevant keywords")
        changelog.append("Optimized content for ATS compatibility")
        changelog.append("Enhanced formatting for better readability")
        if request.editType == "full":
            changelog.append("Performed complete resume restructuring")
        
        # Store generation data
        generation_cache[generation_id] = {
            'output_path': str(output_path),
            'filename': filename,
            'user_id': original_request.userId,
            'timestamp': datetime.now()
        }
        
        response = GenerateResponse(
            generationId=generation_id,
            status="completed",
            previewUrl=preview_url,
            downloadUrl=download_url,
            fileName=filename,
            finalScore=final_score,
            improvements={
                "before": {
                    "score": analysis_data.get('current_score', 75),
                    "keywordMatches": matched_before,
                    "atsCompatibility": 80
                },
                "after": {
                    "score": final_score,
                    "keywordMatches": matched_after,
                    "atsCompatibility": 95
                }
            },
            changelog=changelog
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/resume/preview/{generation_id}")
async def preview_resume(generation_id: str):
    """Get resume preview (returns PDF for now, could be converted to HTML)"""
    if generation_id not in generation_cache:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    file_path = generation_cache[generation_id]['output_path']
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"}
    )


@app.get("/api/resume/download/{generation_id}")
async def download_resume(generation_id: str):
    """Download generated resume"""
    if generation_id not in generation_cache:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    data = generation_cache[generation_id]
    file_path = data['output_path']
    filename = data['filename']
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)