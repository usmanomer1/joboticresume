# Analysis Endpoint Integration Guide

## 🎯 Overview

This guide covers integration with the `/api/resume/analyze` endpoint, which analyzes resumes against job descriptions and provides optimization recommendations.

## 🔗 Endpoint Details

- **URL**: `/api/resume/analyze`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Authentication**: Bearer token required
- **Rate Limit**: 10 requests/minute **per user** ✅

## 📝 Request Format

### Required Fields

```typescript
// Form data fields
interface AnalyzeRequest {
  resume: File;              // PDF file upload
  job_description: string;   // Min 50 characters
  job_title: string;        // Min 2 characters, Max 100
  company_name: string;     // Min 2 characters, Max 100
}
```

### TypeScript Request Example

```typescript
async function analyzeResume(
  resumeFile: File,
  jobDescription: string,
  jobTitle: string,
  companyName: string
): Promise<AnalysisResponse> {
  const formData = new FormData();
  formData.append('resume', resumeFile);
  formData.append('job_description', jobDescription);
  formData.append('job_title', jobTitle);
  formData.append('company_name', companyName);

  const response = await fetch('/api/resume/analyze', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Analysis failed');
  }

  return response.json();
}
```

## 📋 Response Structure

### Success Response

```typescript
interface AnalysisResponse {
  success: boolean;
  data: {
    analysisId: string;
    summary: {
      overallScore: number;        // 0-10 scale
      keywordMatches: string[];    // Matched keywords from job description
      missingSkills: string[];     // Top missing skills (up to 10)
      suggestions: string[];       // Actionable recommendations
    };
    sections: SectionAnalysis[];   // Section-by-section analysis
    skills: {
      current: string[];           // Current skills found in resume
      suggested: string[];         // Recommended skills to add
      relevanceScores: Record<string, number>; // Skill relevance (0.0-1.0)
    };
  };
}

interface SectionAnalysis {
  id: string;           // Unique section identifier
  type: string;         // Section type (experience, skills, etc.)
  original: string;     // Original section text
  suggested: string;    // Suggested improvements
  improvements: string[]; // List of specific improvements
}
```

### Example Response

```json
{
  "success": true,
  "data": {
    "analysisId": "34745206-ec02-4085-b240-d2099e98e4c2",
    "summary": {
      "overallScore": 5.9,
      "keywordMatches": ["React", "JavaScript", "Python"],
      "missingSkills": ["AWS", "Docker", "Kubernetes"],
      "suggestions": [
        "Add 3 missing keywords from the job description",
        "Quantify your achievements with specific metrics",
        "Emphasize experience with required technologies",
        "Highlight your Senior Software Engineer relevant experience"
      ]
    },
    "sections": [
      {
        "id": "exp-154c1430",
        "type": "experience",
        "original": "Experience\nMachine Learning Intern Aug 2021 – Oct 2021...",
        "suggested": "Add keywords: AWS, Docker",
        "improvements": [
          "Add missing technologies",
          "Quantify achievements",
          "Use action verbs"
        ]
      }
    ],
    "skills": {
      "current": ["React", "JavaScript", "Python"],
      "suggested": ["React", "JavaScript", "Python", "AWS", "Docker"],
      "relevanceScores": {
        "React": 0.9,
        "JavaScript": 0.9,
        "Python": 0.9,
        "AWS": 0.7,
        "Docker": 0.7
      }
    }
  }
}
```

## 🛠️ Implementation Examples

### React Hook

```typescript
import { useState, useCallback } from 'react';

interface UseAnalysisResult {
  analysis: AnalysisResponse | null;
  loading: boolean;
  error: string | null;
  analyzeResume: (
    file: File,
    jobDescription: string,
    jobTitle: string,
    companyName: string
  ) => Promise<void>;
  resetAnalysis: () => void;
}

export function useResumeAnalysis(apiToken: string): UseAnalysisResult {
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyzeResume = useCallback(async (
    file: File,
    jobDescription: string,
    jobTitle: string,
    companyName: string
  ) => {
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('resume', file);
      formData.append('job_description', jobDescription);
      formData.append('job_title', jobTitle);
      formData.append('company_name', companyName);

      const response = await fetch('/api/resume/analyze', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiToken}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Analysis failed');
      }

      const result = await response.json();
      setAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [apiToken]);

  const resetAnalysis = useCallback(() => {
    setAnalysis(null);
    setError(null);
  }, []);

  return {
    analysis,
    loading,
    error,
    analyzeResume,
    resetAnalysis,
  };
}
```

### Vue 3 Composable

```typescript
import { ref, computed } from 'vue';

export function useResumeAnalysis(apiToken: string) {
  const analysis = ref<AnalysisResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const overallScore = computed(() => 
    analysis.value?.data.summary.overallScore ?? 0
  );

  const missingSkillsCount = computed(() => 
    analysis.value?.data.summary.missingSkills.length ?? 0
  );

  const analyzeResume = async (
    file: File,
    jobDescription: string,
    jobTitle: string,
    companyName: string
  ) => {
    loading.value = true;
    error.value = null;

    try {
      const formData = new FormData();
      formData.append('resume', file);
      formData.append('job_description', jobDescription);
      formData.append('job_title', jobTitle);
      formData.append('company_name', companyName);

      const response = await fetch('/api/resume/analyze', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiToken}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Analysis failed');
      }

      analysis.value = await response.json();
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error';
    } finally {
      loading.value = false;
    }
  };

  return {
    analysis: readonly(analysis),
    loading: readonly(loading),
    error: readonly(error),
    overallScore,
    missingSkillsCount,
    analyzeResume,
  };
}
```

### React Component Example

```tsx
import React, { useState } from 'react';
import { useResumeAnalysis } from './hooks/useResumeAnalysis';

interface AnalysisFormProps {
  apiToken: string;
  onAnalysisComplete: (analysisId: string) => void;
}

export function AnalysisForm({ apiToken, onAnalysisComplete }: AnalysisFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [companyName, setCompanyName] = useState('');

  const { analysis, loading, error, analyzeResume } = useResumeAnalysis(apiToken);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!file || !jobDescription || !jobTitle || !companyName) {
      return;
    }

    await analyzeResume(file, jobDescription, jobTitle, companyName);
  };

  // Auto-trigger callback when analysis completes
  React.useEffect(() => {
    if (analysis?.success && analysis.data.analysisId) {
      onAnalysisComplete(analysis.data.analysisId);
    }
  }, [analysis, onAnalysisComplete]);

  if (analysis) {
    return <AnalysisResults analysis={analysis} />;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-2">
          Resume (PDF only)
        </label>
        <input
          type="file"
          accept=".pdf"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          required
          className="w-full border rounded-md p-2"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">
          Job Description
        </label>
        <textarea
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
          placeholder="Paste the job description here..."
          minLength={50}
          required
          rows={6}
          className="w-full border rounded-md p-2"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">
            Job Title
          </label>
          <input
            type="text"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
            placeholder="e.g., Senior Software Engineer"
            minLength={2}
            maxLength={100}
            required
            className="w-full border rounded-md p-2"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">
            Company Name
          </label>
          <input
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder="e.g., Google"
            minLength={2}
            maxLength={100}
            required
            className="w-full border rounded-md p-2"
          />
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-3">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      <button
        type="submit"
        disabled={loading || !file || !jobDescription || !jobTitle || !companyName}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400"
      >
        {loading ? 'Analyzing Resume...' : 'Analyze Resume'}
      </button>
    </form>
  );
}
```

### Results Display Component

```tsx
interface AnalysisResultsProps {
  analysis: AnalysisResponse;
}

export function AnalysisResults({ analysis }: AnalysisResultsProps) {
  const { data } = analysis;

  return (
    <div className="space-y-6">
      {/* Score Overview */}
      <div className="bg-white rounded-lg border p-6">
        <h3 className="text-lg font-semibold mb-4">Analysis Summary</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600">
              {data.summary.overallScore.toFixed(1)}
            </div>
            <div className="text-sm text-gray-600">Overall Score</div>
          </div>
          
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600">
              {data.summary.keywordMatches.length}
            </div>
            <div className="text-sm text-gray-600">Keywords Matched</div>
          </div>
          
          <div className="text-center">
            <div className="text-3xl font-bold text-orange-600">
              {data.summary.missingSkills.length}
            </div>
            <div className="text-sm text-gray-600">Missing Skills</div>
          </div>
        </div>

        <div>
          <h4 className="font-medium mb-2">Recommendations:</h4>
          <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
            {data.summary.suggestions.map((suggestion, index) => (
              <li key={index}>{suggestion}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Skills Analysis */}
      <div className="bg-white rounded-lg border p-6">
        <h3 className="text-lg font-semibold mb-4">Skills Analysis</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-medium text-green-700 mb-2">Matched Skills</h4>
            <div className="flex flex-wrap gap-2">
              {data.skills.current.map((skill) => (
                <span
                  key={skill}
                  className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
          
          <div>
            <h4 className="font-medium text-orange-700 mb-2">Missing Skills</h4>
            <div className="flex flex-wrap gap-2">
              {data.summary.missingSkills.map((skill) => (
                <span
                  key={skill}
                  className="px-2 py-1 bg-orange-100 text-orange-800 rounded-full text-xs"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-4">
          <h4 className="font-medium mb-2">Skill Relevance Scores</h4>
          <div className="space-y-2">
            {Object.entries(data.skills.relevanceScores).map(([skill, score]) => (
              <div key={skill} className="flex items-center justify-between">
                <span className="text-sm">{skill}</span>
                <div className="flex items-center space-x-2">
                  <div className="w-24 bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${score * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-600">
                    {(score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Section Analysis */}
      <div className="bg-white rounded-lg border p-6">
        <h3 className="text-lg font-semibold mb-4">Section-by-Section Analysis</h3>
        
        <div className="space-y-4">
          {data.sections.map((section) => (
            <div key={section.id} className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium capitalize">{section.type}</h4>
                <span className="text-xs text-gray-500">ID: {section.id}</span>
              </div>
              
              <div className="text-sm text-gray-700 mb-2">
                <strong>Original:</strong> {section.original.substring(0, 150)}...
              </div>
              
              <div className="text-sm text-blue-700 mb-2">
                <strong>Suggestion:</strong> {section.suggested}
              </div>
              
              <div>
                <strong className="text-sm">Improvements:</strong>
                <ul className="list-disc list-inside text-sm text-gray-600 mt-1">
                  {section.improvements.map((improvement, index) => (
                    <li key={index}>{improvement}</li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

## ✅ Per-User Rate Limiting

### **How It Works**
The rate limiting is **per authenticated user**, providing a fair experience:

- **Each user gets their own 10 requests/minute**
- **Corporate networks**: Each employee has their own limit
- **Shared WiFi**: Each user maintains their individual quota
- **User identification**: Based on JWT token user ID

### **Frontend Benefits**
```typescript
// Each user has predictable rate limiting
const [rateLimitInfo, setRateLimitInfo] = useState({
  remaining: 10,
  resetTime: null,
  isPersonalized: true // Each user gets their own limit
});

// Check response headers for rate limit info
const response = await fetch('/api/resume/analyze', options);
if (response.headers.has('X-RateLimit-Remaining')) {
  setRateLimitInfo({
    remaining: parseInt(response.headers.get('X-RateLimit-Remaining')),
    resetTime: new Date(response.headers.get('X-RateLimit-Reset') * 1000),
    isPersonalized: true
  });
}

// User-friendly rate limit messaging
if (rateLimitInfo.remaining <= 2) {
  showWarning(`You have ${rateLimitInfo.remaining} analyses remaining this minute.`);
}
```

### **User Communication**
When rate limited, users understand that:
- ✅ **It's their personal limit** (10 requests/minute)
- ✅ **Other users don't affect their quota**
- ✅ **Predictable reset time** (every minute)
- ✅ **Fair usage for all users**

## ⚠️ Error Handling

### Common Error Responses

```typescript
// Validation errors (400)
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "jobDescription"],
      "msg": "String should have at least 50 characters",
      "input": "Short description",
      "ctx": {"min_length": 50}
    }
  ]
}

// Rate limiting (429)
{
  "detail": "Rate limit exceeded"
}

// Server error (500)
{
  "detail": "An error occurred during analysis"
}
```

### Error Handling Implementation

```typescript
function handleAnalysisError(error: any) {
  if (Array.isArray(error.detail)) {
    // Validation errors
    const messages = error.detail.map((err: any) => err.msg);
    return `Validation errors: ${messages.join(', ')}`;
  }
  
  if (typeof error.detail === 'string') {
    if (error.detail.includes('Rate limit')) {
      return 'Too many requests. Please wait a minute before trying again.';
    }
    return error.detail;
  }
  
  return 'An unexpected error occurred during analysis.';
}
```

## 🔧 Integration Checklist

- [ ] Set up authentication with Bearer tokens
- [ ] Implement file upload with PDF validation
- [ ] Handle form data correctly (multipart/form-data)
- [ ] Implement proper error handling for all error types
- [ ] Add loading states and progress indicators
- [ ] Display analysis results in a user-friendly format
- [ ] Cache analysis results using the `analysisId`
- [ ] Handle rate limiting gracefully
- [ ] Test with various file sizes and content types
- [ ] Implement retry logic for failed requests

## 📊 Usage Analytics

Consider tracking these metrics:
- Analysis completion rate
- Average processing time
- Most common error types
- Score distribution
- Feature usage (which sections users focus on)

This data can help improve the user experience and identify areas for optimization.
