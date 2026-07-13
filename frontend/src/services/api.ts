import {
  ResumeUploadResponse,
  ScreeningResult,
  ScreeningSummary
} from '../types/api';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorMessage = typeof errorData.detail === 'string' 
          ? errorData.detail 
          : JSON.stringify(errorData.detail);
      }
    } catch {
      // Ignore JSON parse error if body is not JSON
    }
    throw new ApiError(response.status, errorMessage);
  }
  return response.json();
}

export async function uploadResume(file: File): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append('resume', file);

  const response = await fetch('/resume/upload', {
    method: 'POST',
    body: formData,
  });
  return handleResponse<ResumeUploadResponse>(response);
}

export async function screenCandidate(resumeId: number, jobDescription: string): Promise<ScreeningResult> {
  const response = await fetch('/screen', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      resume_id: resumeId,
      job_description: jobDescription,
    }),
  });
  return handleResponse<ScreeningResult>(response);
}

export async function listScreenings(): Promise<ScreeningSummary[]> {
  const response = await fetch('/screenings');
  return handleResponse<ScreeningSummary[]>(response);
}

export async function getScreeningDetail(resumeId: number): Promise<ScreeningResult> {
  const response = await fetch(`/screenings/${resumeId}`);
  return handleResponse<ScreeningResult>(response);
}
