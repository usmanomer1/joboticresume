# Resume Optimizer - Claude Instructions

## Project Overview
Build a Python-based resume optimizer that takes a PDF resume and job description, uses Gemini AI to analyze and optimize the resume, then outputs an improved version while maintaining the original formatting.

## Core Functionality Needed

### 1. Resume Parser (`resume_parser.py`)
Create a module that:
- Extracts text from PDF resumes using PyPDF2
- Identifies and preserves resume sections (Education, Experience, Skills, etc.)
- Maintains bullet points and formatting structure
- Extracts contact information separately

### 2. AI Integration (`ai_optimizer.py`)
Create a module that:
- Takes resume text and job description as input
- Sends structured prompt to Gemini API
- Gets back optimized resume with tracked changes
- Returns JSON with:
  - Optimized resume content
  - List of changes made
  - Score improvement
  - Keywords added/modified

### 3. Resume Generator (`resume_generator.py`)
Create a module that:
- Takes optimized text and recreates PDF
- Maintains original layout/formatting as much as possible
- Highlights changes (optional for v1)
- Outputs clean PDF file

### 4. Main Script (`main.py`)
Create the main entry point that:
- Reads resume PDF from `input/resume.pdf`
- Reads job description from `input/job_description.txt`
- Reads Gemini API key from `config.json` or `.env`
- Processes the resume through all modules
- Saves output to `output/optimized_resume.pdf`
- Prints summary of changes made

## File Structure
```
resume-optimizer/
├── main.py
├── resume_parser.py
├── ai_optimizer.py
├── resume_generator.py
├── requirements.txt
├── config.json (or .env)
├── input/
│   ├── resume.pdf
│   └── job_description.txt
└── output/
    └── optimized_resume.pdf
```

## Requirements
```
PyPDF2==3.0.1
google-generativeai==0.3.2
python-dotenv==1.0.0
reportlab==4.0.8
pdfplumber==0.10.3
```

## Gemini Prompt Structure
When calling Gemini, use this prompt structure:

```
You are an ATS optimization expert. Analyze this resume against the job description and provide an optimized version.

RESUME:
[resume text]

JOB DESCRIPTION:
[job description]

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

Return ONLY valid JSON.
```

## Implementation Steps

1. Start with `resume_parser.py` - get it working to extract text cleanly
2. Test `ai_optimizer.py` with hardcoded text first
3. Build simple `resume_generator.py` that outputs text to PDF
4. Connect everything in `main.py`
5. Iterate on formatting preservation

## Testing Instructions
1. Place a test resume in `input/resume.pdf`
2. Place job description in `input/job_description.txt`
3. Add Gemini API key to config
4. Run: `python main.py`
5. Check `output/optimized_resume.pdf`

## Success Metrics
- Successfully extracts resume text
- Gemini returns valid optimization suggestions
- Output PDF is generated
- Changes are tracked and displayed
- Resume is actually improved for the job

## Future Enhancements (Not for v1)
- Better layout preservation
- Multiple resume template support
- Batch processing
- API endpoint for integration
- Visual diff between original and optimized
- Multiple AI provider support