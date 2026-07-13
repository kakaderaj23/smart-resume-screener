export type Recommendation = 'STRONG_HIRE' | 'SHORTLIST' | 'CONSIDER' | 'REJECT';
export type ConfidenceLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export interface ResumeUploadResponse {
  message: string;
  resume_id: number;
  filename: string;
  original_filename: string;
  size_bytes: number;
}

export interface ScreenRequest {
  resume_id: number;
  job_description: string;
}

export interface PersonalInfo {
  full_name: string;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
}

export interface ProfessionalInfo {
  summary?: string | null;
  skills: string[];
  years_experience?: number | null;
}

export interface CandidateProfile {
  personal_info: PersonalInfo;
  professional_info: ProfessionalInfo;
  metadata?: any;
}

export interface JobRequirements {
  required_skills: string[];
  preferred_skills?: string[];
  minimum_experience?: number | null;
  education?: string | null;
  domain?: string | null;
}

export interface EvidenceItem {
  skill: string;
  found: boolean;
  context_snippet: string;
  confidence: ConfidenceLevel;
}

export interface MatchResult {
  semantic_score: number;
  confidence: ConfidenceLevel;
  matched_skills: string[];
  missing_skills: string[];
  strengths: string[];
  weaknesses: string[];
  evidence: EvidenceItem[];
  justification: string;
}

export interface RuleEvidence {
  matched_skills: string[];
  missing_skills: string[];
  skill_overlap_percentage: number;
  required_skill_count: number;
  matched_skill_count: number;
}

export interface ScreeningResult {
  candidate_profile: CandidateProfile;
  job_requirements: JobRequirements;
  rule_evidence: RuleEvidence;
  match_result: MatchResult;
  recommendation: Recommendation;
  screened_at?: string;
}

export interface ScreeningSummary {
  resume_id: number;
  candidate_name?: string;
  semantic_score?: number | null;
  recommendation?: Recommendation | null;
  screened_at?: string;
}
