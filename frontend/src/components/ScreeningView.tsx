import React, { useState } from 'react';
import { Sparkles, AlertCircle, Briefcase, Hash } from 'lucide-react';
import { screenCandidate, ApiError } from '../services/api';
import { ScreeningResult } from '../types/api';

interface ScreeningViewProps {
  initialResumeId: number;
  onScreeningComplete: (result: ScreeningResult) => void;
}

export const ScreeningView: React.FC<ScreeningViewProps> = ({ initialResumeId, onScreeningComplete }) => {
  const [resumeId, setResumeId] = useState<number>(initialResumeId);
  const [jobDescription, setJobDescription] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (resumeId <= 0 || isNaN(resumeId)) {
      setError('Please enter a valid Resume ID.');
      return;
    }
    if (!jobDescription.trim()) {
      setError('Please provide the Job Description to evaluate against.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await screenCandidate(resumeId, jobDescription);
      onScreeningComplete(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred during screening.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">
          <Sparkles size={22} style={{ color: 'var(--primary)' }} />
          AI Candidate Screening
        </h2>
        <p className="card-subtitle">
          Evaluate an uploaded resume against specific job qualifications and requirements.
        </p>
      </div>

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={20} />
          <div>{error}</div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label" htmlFor="resume-id-input">
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Hash size={16} /> Target Resume ID
            </span>
          </label>
          <input
            id="resume-id-input"
            type="number"
            min="1"
            className="form-input"
            style={{ maxWidth: '220px' }}
            value={resumeId}
            onChange={(e) => setResumeId(parseInt(e.target.value, 10) || 1)}
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="job-desc-textarea">
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Briefcase size={16} /> Job Description & Qualifications
            </span>
          </label>
          <textarea
            id="job-desc-textarea"
            className="form-textarea"
            placeholder="Paste the full job description here (e.g. required technical skills like Python, FastAPI, Docker, qualifications, and responsibilities)..."
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            disabled={loading}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '2rem' }}>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading || !jobDescription.trim()}
          >
            {loading ? (
              <>
                <div className="spinner" />
                Executing Semantic Evaluation...
              </>
            ) : (
              <>
                <Sparkles size={18} />
                Screen Candidate
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
