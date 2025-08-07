FROM python:3.11-slim

# Install minimal LaTeX packages needed for Jake's template
RUN apt-get update && apt-get install -y \
    # Core LaTeX
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    # Required packages for Jake's template
    texlive-latex-extra \
    # PDF processing dependencies for pdfplumber
    poppler-utils \
    python3-cffi \
    python3-brotli \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    # Other dependencies
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py ./

# Create necessary directories
RUN mkdir -p output input

# Test LaTeX installation
RUN echo "Testing LaTeX installation..." && \
    pdflatex --version && \
    echo "LaTeX installed successfully"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# Use shell form to allow environment variable expansion
CMD ["sh", "-c", "uvicorn app_secure:app --host 0.0.0.0 --port ${PORT:-8080}"]