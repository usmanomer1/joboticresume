# Complete Frontend Integration Guide for Resume Optimizer API

## 🚀 API Overview

**Base URL**: `terrific-imagination-production-6ca9.up.railway.app` (you'll get this after deployment)

**Authentication**: JWT Bearer token (required for all endpoints except `/health`)

## 🔐 Authentication

### Step 1: Get Authentication Token

After user logs in via Supabase Auth, get an API token:

```typescript
// api/auth.ts
export async function getApiToken(userId: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/auth/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ user_id: userId }),
  });

  if (!response.ok) {
    throw new Error('Failed to get API token');
  }

  const data = await response.json();
  return data.access_token;
}
```

### Step 2: Store Token

```typescript
// Store in memory or secure storage
let apiToken: string | null = null;
let tokenExpiry: Date | null = null;

export function setApiToken(token: string) {
  apiToken = token;
  // Token expires in 30 minutes
  tokenExpiry = new Date(Date.now() + 29 * 60 * 1000);
}

export async function getValidToken(userId: string): Promise<string> {
  if (!apiToken || !tokenExpiry || new Date() > tokenExpiry) {
    const newToken = await getApiToken(userId);
    setApiToken(newToken);
    return newToken;
  }
  return apiToken;
}
```

### Step 3: API Client with Auto-Auth

```typescript
// api/client.ts
export class ResumeApiClient {
  private baseUrl: string;
  private userId: string;

  constructor(baseUrl: string, userId: string) {
    this.baseUrl = baseUrl;
    this.userId = userId;
  }

  private async fetchWithAuth(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<Response> {
    const token = await getValidToken(this.userId);
    
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    // Handle token expiration
    if (response.status === 401) {
      // Clear token and retry once
      setApiToken('');
      const newToken = await getValidToken(this.userId);
      
      return fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: {
          'Authorization': `Bearer ${newToken}`,
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });
    }

    return response;
  }
}
```

## 📋 API Endpoints

### 1. Analyze Resume

```typescript
// types/api.ts
interface AnalyzeRequest {
  resumeText: string;
  resumeFile?: string; // base64 encoded PDF
  jobDescription: string;
  jobTitle: string;
  companyName: string;
}

interface SuggestedSection {
  id: string;
  sectionName: string;
  currentContent: string;
  suggestedChanges: string;
  impact: 'high' | 'medium' | 'low';
  selected: boolean;
}

interface SuggestedSkill {
  id: string;
  skill: string;
  relevance: 'high' | 'medium' | 'low';
  reason: string;
}

interface AnalyzeResponse {
  analysisId: string;
  currentScore: number;
  potentialScore: number;
  suggestedSections: SuggestedSection[];
  suggestedSkills: SuggestedSkill[];
  missingKeywords: string[];
  editOptions: {
    quickEdit: {
      description: string;
      estimatedTime: string;
      scoreImprovement: string;
    };
    fullEdit: {
      description: string;
      estimatedTime: string;
      scoreImprovement: string;
    };
  };
}

// api/resume.ts
export async function analyzeResume(
  client: ResumeApiClient,
  request: AnalyzeRequest
): Promise<AnalyzeResponse> {
  // Validate inputs
  if (request.resumeText.length < 100) {
    throw new Error('Resume text too short');
  }
  
  if (request.resumeFile && request.resumeFile.length > 15_000_000) {
    throw new Error('Resume file too large (max 10MB)');
  }

  const response = await client.fetchWithAuth('/api/resume/analyze', {
    method: 'POST',
    body: JSON.stringify(request),
  });

  if (response.status === 429) {
    const retryAfter = response.headers.get('Retry-After') || '60';
    throw new Error(`Rate limited. Please wait ${retryAfter} seconds.`);
  }

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to analyze resume');
  }

  return response.json();
}
```

### 2. Generate Optimized Resume

```typescript
interface GenerateRequest {
  analysisId: string;
  editType: 'quick' | 'full';
  selectedSections: string[];
  selectedSkills: string[];
  additionalInstructions?: string;
}

interface GenerateResponse {
  generationId: string;
  status: 'completed' | 'failed';
  previewUrl: string;
  downloadUrl: string;
  fileName: string;
  finalScore: number;
  improvements: {
    before: {
      score: number;
      keywordMatches: number;
      atsCompatibility: number;
    };
    after: {
      score: number;
      keywordMatches: number;
      atsCompatibility: number;
    };
  };
  changelog: string[];
}

export async function generateResume(
  client: ResumeApiClient,
  request: GenerateRequest
): Promise<GenerateResponse> {
  const response = await client.fetchWithAuth('/api/resume/generate', {
    method: 'POST',
    body: JSON.stringify(request),
  });

  if (response.status === 404) {
    throw new Error('Analysis not found or expired. Please analyze again.');
  }

  if (response.status === 429) {
    const retryAfter = response.headers.get('Retry-After') || '60';
    throw new Error(`Rate limited. Please wait ${retryAfter} seconds.`);
  }

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to generate resume');
  }

  return response.json();
}
```

### 3. Download Resume

```typescript
export async function downloadResume(
  client: ResumeApiClient,
  generationId: string,
  fileName: string
): Promise<void> {
  const response = await client.fetchWithAuth(
    `/api/resume/download/${generationId}`
  );

  if (!response.ok) {
    throw new Error('Failed to download resume');
  }

  // Create blob and download
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}
```

## 📄 File Handling

### Convert PDF to Base64

```typescript
export async function pdfToBase64(file: File): Promise<string> {
  // Validate file type
  if (file.type !== 'application/pdf') {
    throw new Error('Only PDF files are allowed');
  }

  // Validate file size (10MB limit)
  if (file.size > 10 * 1024 * 1024) {
    throw new Error('File size must be less than 10MB');
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => {
      // Remove data URL prefix
      const base64 = reader.result as string;
      const base64Data = base64.split(',')[1];
      resolve(base64Data);
    };
    reader.onerror = reject;
  });
}
```

## 🎯 Complete Integration Example

```typescript
// hooks/useResumeOptimizer.ts
import { useState } from 'react';
import { useUser } from '@supabase/auth-helpers-react';

export function useResumeOptimizer() {
  const user = useUser();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalyzeResponse | null>(null);
  const [generationResult, setGenerationResult] = useState<GenerateResponse | null>(null);

  const client = new ResumeApiClient(
    process.env.NEXT_PUBLIC_API_URL!,
    user?.id || ''
  );

  const analyzeResume = async (
    resumeText: string,
    resumeFile: File | null,
    jobDescription: string,
    jobTitle: string,
    companyName: string
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      let resumeFileBase64: string | undefined;
      
      if (resumeFile) {
        resumeFileBase64 = await pdfToBase64(resumeFile);
      }

      const result = await analyzeResume(client, {
        resumeText,
        resumeFile: resumeFileBase64,
        jobDescription,
        jobTitle,
        companyName,
      });

      setAnalysisResult(result);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const generateOptimizedResume = async (
    editType: 'quick' | 'full',
    selectedSections: string[],
    selectedSkills: string[],
    additionalInstructions?: string
  ) => {
    if (!analysisResult) {
      throw new Error('No analysis result available');
    }

    setLoading(true);
    setError(null);

    try {
      const result = await generateResume(client, {
        analysisId: analysisResult.analysisId,
        editType,
        selectedSections,
        selectedSkills,
        additionalInstructions,
      });

      setGenerationResult(result);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const downloadResume = async () => {
    if (!generationResult) {
      throw new Error('No generated resume available');
    }

    try {
      await downloadResume(
        client,
        generationResult.generationId,
        generationResult.fileName
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download failed');
      throw err;
    }
  };

  return {
    loading,
    error,
    analysisResult,
    generationResult,
    analyzeResume,
    generateOptimizedResume,
    downloadResume,
  };
}
```

## 🖥️ UI Component Example

```tsx
// components/ResumeOptimizer.tsx
export function ResumeOptimizer() {
  const {
    loading,
    error,
    analysisResult,
    generationResult,
    analyzeResume,
    generateOptimizedResume,
    downloadResume,
  } = useResumeOptimizer();

  const [selectedSections, setSelectedSections] = useState<string[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);

  const handleAnalyze = async () => {
    try {
      const result = await analyzeResume(
        resumeText,
        resumeFile,
        jobDescription,
        jobTitle,
        companyName
      );
      
      // Auto-select all high-impact sections
      const highImpactSections = result.suggestedSections
        .filter(s => s.impact === 'high')
        .map(s => s.id);
      setSelectedSections(highImpactSections);
    } catch (err) {
      // Error is handled by hook
    }
  };

  const handleGenerate = async (editType: 'quick' | 'full') => {
    try {
      await generateOptimizedResume(
        editType,
        selectedSections,
        selectedSkills,
        additionalInstructions
      );
    } catch (err) {
      // Error is handled by hook
    }
  };

  if (loading) {
    return <LoadingSpinner message="Optimizing your resume..." />;
  }

  return (
    <div>
      {error && <ErrorAlert message={error} />}
      
      {!analysisResult && (
        <ResumeUploadForm onSubmit={handleAnalyze} />
      )}
      
      {analysisResult && !generationResult && (
        <OptimizationOptions
          analysis={analysisResult}
          selectedSections={selectedSections}
          selectedSkills={selectedSkills}
          onSectionToggle={(id) => {
            setSelectedSections(prev =>
              prev.includes(id)
                ? prev.filter(s => s !== id)
                : [...prev, id]
            );
          }}
          onSkillToggle={(id) => {
            setSelectedSkills(prev =>
              prev.includes(id)
                ? prev.filter(s => s !== id)
                : [...prev, id]
            );
          }}
          onGenerate={handleGenerate}
        />
      )}
      
      {generationResult && (
        <GenerationResults
          result={generationResult}
          onDownload={downloadResume}
          onStartOver={() => {
            setAnalysisResult(null);
            setGenerationResult(null);
          }}
        />
      )}
    </div>
  );
}
```

## ⚠️ Important Notes

### Rate Limits
- Analyze: 10 requests/minute
- Generate: 5 requests/minute
- Download: 20 requests/minute

### Timeouts
- Analysis: ~10-20 seconds
- Generation: ~20-30 seconds
- Files expire after 60 minutes

### Error Handling
```typescript
try {
  // API call
} catch (error) {
  if (error.message.includes('Rate limited')) {
    // Show rate limit UI
  } else if (error.message.includes('expired')) {
    // Restart flow
  } else {
    // Generic error
  }
}
```

### Environment Variables
```bash
# .env.local
NEXT_PUBLIC_API_URL=https://your-api.up.railway.app
```

## 🧪 Testing Checklist

- [ ] Test file upload with PDF > 10MB (should fail)
- [ ] Test file upload with non-PDF (should fail)
- [ ] Test rate limiting (make 11 analyze requests in 1 minute)
- [ ] Test token expiration (wait 31 minutes)
- [ ] Test downloading after 61 minutes (should fail)
- [ ] Test with very long job descriptions
- [ ] Test with special characters in company names

## 📱 Mobile Considerations

- File uploads might not work on all mobile browsers
- Consider adding a text-only option for mobile
- Download might open in a new tab instead of downloading

## 🔧 Debugging

Enable detailed logging:
```typescript
if (process.env.NODE_ENV === 'development') {
  console.log('API Request:', endpoint, options);
  console.log('API Response:', response.status, await response.clone().text());
}
```

## 🚀 Production Checklist

- [ ] Set `NEXT_PUBLIC_API_URL` in Vercel/Netlify
- [ ] Test with real Supabase user IDs
- [ ] Monitor API errors in production
- [ ] Set up error tracking (Sentry)
- [ ] Test on slow connections
- [ ] Add analytics for conversion tracking