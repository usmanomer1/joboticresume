import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from resume_parser import ResumeParser
from ai_optimizer import AIOptimizer
from resume_generator import ResumeGenerator
from gemini_latex_generator import GeminiLatexGenerator


def load_config():
    load_dotenv()
    
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key and os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                api_key = config.get('gemini_api_key')
        except Exception as e:
            print(f"Error loading config.json: {e}")
    
    if not api_key:
        print("Error: Gemini API key not found!")
        print("Please set it in one of the following ways:")
        print("1. Create a .env file with: GEMINI_API_KEY=your_api_key")
        print("2. Create a config.json file with: {\"gemini_api_key\": \"your_api_key\"}")
        sys.exit(1)
    
    return api_key


def main():
    print("=== Resume Optimizer ===\n")
    
    # Check for command line argument for output format
    use_latex = '--latex' in sys.argv or '-l' in sys.argv
    
    resume_path = Path("input/resume.pdf")
    job_desc_path = Path("input/job_description.txt")
    output_path = Path("output/optimized_resume.pdf")
    
    if not resume_path.exists():
        print(f"Error: Resume not found at {resume_path}")
        print("Please place your resume PDF in the input folder")
        sys.exit(1)
    
    if not job_desc_path.exists():
        print(f"Error: Job description not found at {job_desc_path}")
        print("Please create a job_description.txt file in the input folder")
        sys.exit(1)
    
    api_key = load_config()
    
    try:
        with open(job_desc_path, 'r', encoding='utf-8') as f:
            job_description = f.read()
    except Exception as e:
        print(f"Error reading job description: {e}")
        sys.exit(1)
    
    print("Step 1: Parsing resume...")
    parser = ResumeParser()
    resume_data = parser.parse_resume(str(resume_path))
    print(f"✓ Resume parsed successfully")
    print(f"  - Found contact info: {', '.join(resume_data['contact_info'].keys())}")
    print(f"  - Found sections: {len(resume_data['sections'])}")
    
    print("\nStep 2: Optimizing resume with AI...")
    optimizer = AIOptimizer(api_key)
    optimized_data = optimizer.optimize_resume(resume_data, job_description)
    
    if 'error' in optimized_data and optimized_data['error']:
        print(f"⚠ Optimization completed with warnings: {optimized_data['error']}")
    else:
        print("✓ Resume optimized successfully")
    
    score = optimized_data.get('score', {})
    if score:
        print(f"  - ATS Score: {score.get('before', 'N/A')} → {score.get('after', 'N/A')}")
    
    keywords = optimized_data.get('keywords_added', [])
    if keywords:
        print(f"  - Keywords added: {len(keywords)}")
    
    print("\nStep 3: Generating PDF...")
    
    if use_latex:
        print("  Using LaTeX template (Jake's Resume format with Gemini)...")
        # Pass the optimizer instance to the generator
        generator = GeminiLatexGenerator(optimizer)
        pdf_path = generator.generate_latex(optimized_data, str(output_path))
        print(f"✓ PDF generated successfully at {pdf_path}")
    else:
        print("  Using standard PDF format...")
        generator = ResumeGenerator()
        generator.generate_pdf(optimized_data, str(output_path))
        print(f"✓ PDF generated successfully at {output_path}")
    
    print("\n" + "="*50)
    if not use_latex:
        summary = generator.generate_summary_report(optimized_data)
        print(summary)
    else:
        print("=== Resume Optimization Summary ===")
        score = optimized_data.get('score', {})
        if score:
            print(f"ATS Score Improvement: {score.get('before', 'N/A')} → {score.get('after', 'N/A')}")
        keywords = optimized_data.get('keywords_added', [])
        if keywords:
            print(f"\nKeywords Added: {len(keywords)}")
    
    print("\n✓ Resume optimization complete!")
    print(f"  Input: {resume_path}")
    print(f"  Output: {output_path}")
    
    if use_latex:
        print("\nNote: LaTeX template used (Jake's Resume format)")
        print("Using LaTeX.Online API - no local installation needed!")
    
    print("\nOutput format options:")
    print("  python main.py          # Standard PDF (reportlab)")
    print("  python main.py --latex  # LaTeX-based (uses Jake's template via API)")


if __name__ == "__main__":
    main()