import os
import subprocess
from typing import Dict
from pathlib import Path


class GeminiLatexGenerator:
    def __init__(self, ai_optimizer):
        self.ai_optimizer = ai_optimizer
        self.template_path = None  # No longer needed since we use embedded template
        
    def generate_latex(self, optimized_data: Dict, output_path: str):
        """Generate LaTeX resume using Gemini AI"""
        
        print("  Using Gemini to map content to Jake's template...")
        
        # Extract data
        contact_info = optimized_data.get('contact_info', {})
        optimized_resume = optimized_data.get('optimized_resume', '')
        
        # Use Gemini to generate the complete LaTeX code
        try:
            latex_code = self.ai_optimizer.generate_latex_resume(
                self.template_path,
                optimized_resume,
                contact_info
            )
            
            # Write the LaTeX file
            tex_path = output_path.replace('.pdf', '.tex')
            with open(tex_path, 'w') as f:
                f.write(latex_code)
            
            print(f"  ✓ LaTeX file generated at {tex_path}")
            
            # Debug: Check if Gemini is including template definitions in the output
            import re
            
            # Check for template command definitions that shouldn't be in the output
            if '\\newcommand{\\resumeItem}' in latex_code:
                print("  ⚠ Warning: Gemini included template definitions in output")
                # This suggests Gemini is copying the entire template including definitions
            
            resume_items = re.findall(r'\\resumeItem.*', latex_code)
            if resume_items:
                print(f"  Debug: Sample resumeItem lines from Gemini:")
                for item in resume_items[:3]:
                    print(f"    {item[:80]}...")
            
            # Quick validation check
            if latex_code.count('\\resumeItem') > 0:
                # Check if all resumeItem commands are properly closed
                resume_items_bad = re.findall(r'\\resumeItem[^{]', latex_code)
                if resume_items_bad:
                    print(f"  ⚠ Warning: Found {len(resume_items_bad)} potentially unclosed \\resumeItem commands")
            
            # Compile to PDF
            success = self._compile_latex(tex_path, output_path)
            
            if not success:
                # Save the problematic LaTeX file for debugging
                debug_path = tex_path.replace('.tex', '_debug.tex')
                import shutil
                shutil.copy(tex_path, debug_path)
                print(f"  Debug: Problematic LaTeX file saved to {debug_path}")
                raise Exception("Failed to compile LaTeX to PDF - check debug file for syntax errors")
            
            return output_path
            
        except Exception as e:
            print(f"  ⚠ Error: {e}")
            raise
    
    def _compile_latex(self, tex_path: str, pdf_path: str) -> bool:
        """Compile LaTeX to PDF using pdflatex"""
        try:
            tex_dir = os.path.dirname(tex_path)
            tex_filename = os.path.basename(tex_path)
            
            print("  Compiling LaTeX to PDF...")
            
            # Run pdflatex twice to resolve references
            for i in range(2):
                result = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', tex_filename],
                    cwd=tex_dir,
                    capture_output=True,
                    text=True
                )
            
            # Check if PDF was created
            pdf_exists = os.path.exists(pdf_path)
            
            if pdf_exists:
                print("  ✓ PDF generated successfully")
                
                # Clean up auxiliary files
                for ext in ['.aux', '.log', '.out']:
                    aux_file = tex_path.replace('.tex', ext)
                    if os.path.exists(aux_file):
                        os.remove(aux_file)
                
                return True
            else:
                print("  ⚠ LaTeX compilation failed")
                
                # Read the log file for detailed errors
                log_path = tex_path.replace('.tex', '.log')
                if os.path.exists(log_path):
                    with open(log_path, 'r') as log_file:
                        log_content = log_file.read()
                        
                    # Find error messages
                    error_lines = []
                    lines = log_content.split('\n')
                    for i, line in enumerate(lines):
                        if line.startswith('!'):
                            error_lines.append(line)
                            # Add context
                            if i + 1 < len(lines):
                                error_lines.append(lines[i + 1])
                    
                    if error_lines:
                        print("  LaTeX errors found:")
                        for err in error_lines[:10]:  # Show first 10 error lines
                            print(f"    {err}")
                    
                    # Check for unclosed braces or commands
                    if "File ended while scanning use of" in log_content:
                        print("  ⚠ LaTeX syntax error: Unclosed command or brace detected")
                        print("  This usually means a LaTeX command is missing its closing brace")
                
                # Also show stdout errors
                if result.stdout:
                    errors = [line for line in result.stdout.split('\n') if '!' in line]
                    if errors and not error_lines:  # Only show if we didn't already show log errors
                        print("  LaTeX compilation errors:")
                        for err in errors[:5]:
                            print(f"    {err}")
                
                return False
                
        except FileNotFoundError:
            print("  ⚠ pdflatex not found. Please install LaTeX.")
            return False
        except Exception as e:
            print(f"  ⚠ Error during compilation: {e}")
            return False