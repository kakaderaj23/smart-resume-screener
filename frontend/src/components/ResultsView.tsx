import React, { useEffect, useState, useCallback } from 'react';
import { LayoutList, RefreshCw, AlertCircle, User, Award, ArrowRight } from 'lucide-react';
import { listScreenings, getScreeningDetail, ApiError } from '../services/api';
import { ScreeningSummary, ScreeningResult, Recommendation } from '../types/api';
import { ResultDetail } from './ResultDetail';

interface ResultsViewProps {
  onSelectResult?: (result: ScreeningResult) => void;
}

export const ResultsView: React.FC<ResultsViewProps> = () => {
  const [summaries, setSummaries] = useState<ScreeningSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedResult, setSelectedResult] = useState<ScreeningResult | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);

  const fetchScreenings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listScreenings();
      setSummaries(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load screening summaries from server.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScreenings();
  }, [fetchScreenings]);

  const handleSelectSummary = async (resumeId: number) => {
    setDetailLoading(true);
    setError(null);
    try {
      const detail = await getScreeningDetail(resumeId);
      setSelectedResult(detail);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load candidate evaluation details.');
      }
    } finally {
      setDetailLoading(false);
    }
  };

  const getRecommendationBadge = (rec?: Recommendation | null) => {
    if (!rec) return null;
    switch (rec) {
      case 'STRONG_HIRE':
        return <span className="badge badge-strong-hire">Strong Hire</span>;
      case 'SHORTLIST':
        return <span className="badge badge-shortlist">Shortlist</span>;
      case 'CONSIDER':
        return <span className="badge badge-consider">Consider</span>;
      case 'REJECT':
        return <span className="badge badge-reject">Reject</span>;
      default:
        return <span className="badge badge-consider">{rec}</span>;
    }
  };

  if (selectedResult) {
    return <ResultDetail result={selectedResult} onBack={() => setSelectedResult(null)} />;
  }

  return (
    <div className="card">
      <div className="card-header flex-between">
        <div>
          <h2 className="card-title">
            <LayoutList size={22} style={{ color: 'var(--primary)' }} />
            Evaluated Candidates
          </h2>
          <p className="card-subtitle">
            Review completed screening summaries across all processed resumes.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={fetchScreenings}
          disabled={loading || detailLoading}
        >
          <RefreshCw size={16} className={loading ? 'spinner' : ''} style={loading ? { border: 'none' } : {}} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={20} />
          <div>{error}</div>
        </div>
      )}

      {detailLoading && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '3rem', color: 'var(--text-muted)', gap: '0.75rem' }}>
          <div className="spinner" />
          <span>Loading candidate evaluation details...</span>
        </div>
      )}

      {!detailLoading && loading && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '4rem', color: 'var(--text-muted)', gap: '0.75rem' }}>
          <div className="spinner" />
          <span>Querying screening repository...</span>
        </div>
      )}

      {!detailLoading && !loading && summaries.length === 0 && (
        <div style={{ textAlign: 'center', padding: '4rem 2rem', background: 'var(--bg-input)', borderRadius: 'var(--radius-md)' }}>
          <User size={48} style={{ color: 'var(--text-dim)', marginBottom: '1rem' }} />
          <h3 style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>No Evaluated Candidates Found</h3>
          <p style={{ color: 'var(--text-muted)', maxWidth: '400px', margin: '0 auto' }}>
            Upload a candidate resume and run an AI screening against a job description to see results appear here.
          </p>
        </div>
      )}

      {!detailLoading && !loading && summaries.length > 0 && (
        <div className="summary-grid">
          {summaries.map((item) => (
            <div
              key={item.resume_id}
              className="summary-card"
              onClick={() => handleSelectSummary(item.resume_id)}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                  <div style={{ fontWeight: 600, fontSize: '1.1rem', color: 'var(--text-main)' }}>
                    {item.candidate_name || `Resume #${item.resume_id}`}
                  </div>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>ID: #{item.resume_id}</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                  {getRecommendationBadge(item.recommendation)}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Award size={16} style={{ color: 'var(--primary)' }} />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Score:</span>
                  <strong style={{ color: 'var(--text-main)' }}>{item.semantic_score ?? '-'}/10</strong>
                </div>

                <span style={{ display: 'flex', alignItems: 'center', gap: '0.2rem', color: 'var(--primary)', fontSize: '0.85rem', fontWeight: 600 }}>
                  View Analysis <ArrowRight size={14} />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
