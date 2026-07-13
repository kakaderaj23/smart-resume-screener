import React from 'react';
import {
  User,
  Award,
  ShieldCheck,
  CheckCircle,
  AlertTriangle,
  ThumbsUp,
  ThumbsDown,
  FileText,
  Quote,
  ArrowLeft,
  Calendar
} from 'lucide-react';
import { ScreeningResult, Recommendation } from '../types/api';

interface ResultDetailProps {
  result: ScreeningResult;
  onBack?: () => void;
}

export const ResultDetail: React.FC<ResultDetailProps> = ({ result, onBack }) => {
  const { candidate_profile, match_result, recommendation, screened_at } = result;
  const fullName = candidate_profile.personal_info.full_name || 'Anonymous Candidate';
  const email = candidate_profile.personal_info.email;

  const getRecommendationBadge = (rec: Recommendation) => {
    switch (rec) {
      case 'STRONG_HIRE':
        return <span className="badge badge-strong-hire"><Award size={14} /> Strong Hire</span>;
      case 'SHORTLIST':
        return <span className="badge badge-shortlist"><CheckCircle size={14} /> Shortlist</span>;
      case 'CONSIDER':
        return <span className="badge badge-consider"><AlertTriangle size={14} /> Consider</span>;
      case 'REJECT':
        return <span className="badge badge-reject">Reject</span>;
      default:
        return <span className="badge badge-consider">{rec}</span>;
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'Recently';
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {onBack && (
        <div>
          <button type="button" className="btn btn-secondary" onClick={onBack}>
            <ArrowLeft size={16} /> Back to All Screenings
          </button>
        </div>
      )}

      {/* Header Card */}
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1.5rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
            <User size={26} style={{ color: 'var(--primary)' }} />
            <h1 style={{ fontSize: '1.8rem', margin: 0 }}>{fullName}</h1>
          </div>
          {email && (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.95rem', marginBottom: '0.5rem' }}>
              {email}
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1rem', flexWrap: 'wrap' }}>
            {getRecommendationBadge(recommendation)}
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              <ShieldCheck size={16} style={{ color: 'var(--info)' }} />
              <span>Confidence: <strong style={{ color: 'var(--text-main)' }}>{match_result.confidence}</strong></span>
            </div>

            {screened_at && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                <Calendar size={16} />
                <span>{formatDate(screened_at)}</span>
              </div>
            )}
          </div>
        </div>

        <div className="score-indicator">
          <div className="score-value" style={{ color: match_result.semantic_score >= 7 ? 'var(--success)' : match_result.semantic_score >= 5 ? 'var(--warning)' : 'var(--danger)' }}>
            {match_result.semantic_score}/10
          </div>
          <div className="score-label">Semantic Match Score</div>
        </div>
      </div>

      {/* Skills Grid */}
      <div className="grid-2">
        <div className="card">
          <h3 className="card-title" style={{ fontSize: '1.1rem' }}>
            <CheckCircle size={18} style={{ color: 'var(--success)' }} />
            Matched Skills ({match_result.matched_skills.length})
          </h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
            {match_result.matched_skills.length > 0 ? (
              match_result.matched_skills.map((skill, idx) => (
                <span key={idx} className="pill-matched">
                  {skill}
                </span>
              ))
            ) : (
              <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No direct skill matches found.</span>
            )}
          </div>
        </div>

        <div className="card">
          <h3 className="card-title" style={{ fontSize: '1.1rem' }}>
            <AlertTriangle size={18} style={{ color: 'var(--danger)' }} />
            Missing Skills ({match_result.missing_skills.length})
          </h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
            {match_result.missing_skills.length > 0 ? (
              match_result.missing_skills.map((skill, idx) => (
                <span key={idx} className="pill-missing">
                  {skill}
                </span>
              ))
            ) : (
              <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Candidate possesses all required skills.</span>
            )}
          </div>
        </div>
      </div>

      {/* Strengths & Weaknesses Grid */}
      <div className="grid-2">
        <div className="card">
          <h3 className="card-title" style={{ fontSize: '1.1rem' }}>
            <ThumbsUp size={18} style={{ color: 'var(--primary)' }} />
            Key Strengths
          </h3>
          <ul style={{ listStyle: 'none', padding: 0, marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {match_result.strengths.length > 0 ? (
              match_result.strengths.map((item, idx) => (
                <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.6rem', fontSize: '0.925rem' }}>
                  <CheckCircle size={16} style={{ color: 'var(--success)', marginTop: '0.2rem', flexShrink: 0 }} />
                  <span>{item}</span>
                </li>
              ))
            ) : (
              <li style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No highlighted strengths noted.</li>
            )}
          </ul>
        </div>

        <div className="card">
          <h3 className="card-title" style={{ fontSize: '1.1rem' }}>
            <ThumbsDown size={18} style={{ color: 'var(--warning)' }} />
            Noted Weaknesses & Gaps
          </h3>
          <ul style={{ listStyle: 'none', padding: 0, marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {match_result.weaknesses.length > 0 ? (
              match_result.weaknesses.map((item, idx) => (
                <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.6rem', fontSize: '0.925rem' }}>
                  <AlertTriangle size={16} style={{ color: 'var(--warning)', marginTop: '0.2rem', flexShrink: 0 }} />
                  <span>{item}</span>
                </li>
              ))
            ) : (
              <li style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No major weaknesses identified.</li>
            )}
          </ul>
        </div>
      </div>

      {/* Justification Card */}
      <div className="card">
        <h3 className="card-title" style={{ fontSize: '1.1rem' }}>
          <FileText size={18} style={{ color: 'var(--info)' }} />
          Evaluation Justification
        </h3>
        <div style={{ marginTop: '1rem', background: 'rgba(0,0,0,0.25)', padding: '1.25rem', borderRadius: 'var(--radius-md)', borderLeft: '3px solid var(--info)', lineHeight: 1.6, fontSize: '0.95rem', color: 'var(--text-main)' }}>
          {match_result.justification || 'No justification provided.'}
        </div>
      </div>

      {/* Evidence Section */}
      {match_result.evidence && match_result.evidence.length > 0 && (
        <div className="card">
          <h3 className="card-title" style={{ fontSize: '1.1rem' }}>
            <Quote size={18} style={{ color: 'var(--primary)' }} />
            Supporting Snippets & Evidence ({match_result.evidence.length})
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
            {match_result.evidence.map((ev, idx) => (
              <div key={idx} style={{ background: 'var(--bg-input)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: 600, color: ev.found ? 'var(--success)' : 'var(--danger)' }}>
                    {ev.skill} {ev.found ? '(Found)' : '(Not Found)'}
                  </span>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Confidence: {ev.confidence}</span>
                </div>
                <div style={{ fontStyle: 'italic', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  "{ev.context_snippet}"
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
